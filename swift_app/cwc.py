"""
CWC Flood Forecasting Station downloader for SWIFT
"""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from .utils import Console, Logger
from .wris import build_metadata

# ---------------------------------------------------------
# HTTP session (connection reuse)
# ---------------------------------------------------------

session = requests.Session()

adapter = requests.adapters.HTTPAdapter(
    pool_connections=40,
    pool_maxsize=40,
)

session.mount("https://", adapter)

CWC_API = "https://ffs.india-water.gov.in/iam/api/new-entry-data/specification/sorted"


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

CACHE_DIR = Path.home() / ".swift_cache"
CACHE_FILE = CACHE_DIR / "cwc_meta.csv"
PACKAGED_CSV = Path(__file__).parent / "cwc_meta.csv"

CACHE_TTL = 86400  # 24 hours


def _read_csv_safe(path):
    """Read a CSV, normalise column names, return DataFrame or None."""
    try:
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        if not df.empty:
            return df
    except Exception:
        pass
    return None


def _write_cache(df):
    """Persist a DataFrame to the user-level cache file."""
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        df.to_csv(CACHE_FILE, index=False)
    except Exception:
        pass


# ---------------------------------------------------------
# Load station table
# ---------------------------------------------------------

def load_station_table(refresh=False):
    """
    Load CWC station metadata.

    Parameters
    ----------
    refresh : bool, default False
        False — read the packaged cwc_meta.csv (fast, no network).
        True  — fetch fresh metadata from the CWC FFS API, update the
                local cache, then return the new table.  Falls back to
                the packaged CSV on failure.
    """
    if not refresh:
        df = _read_csv_safe(CACHE_FILE)
        if df is not None:
            return df
        df = _read_csv_safe(PACKAGED_CSV)
        if df is not None:
            return df
        raise RuntimeError("Packaged CWC metadata file not found")

    # refresh=True — live fetch
    import warnings
    warnings.warn(
        "CWC station metadata is mostly static (updated only when a new "
        "HFL is recorded).  A live refresh takes ~2 minutes.  The "
        "packaged metadata file is usually sufficient.",
        stacklevel=3,
    )
    try:
        df = fetch_cwc_station_metadata()
        if df is not None and not df.empty:
            _write_cache(df)
            return df
    except Exception:
        pass
    # fall back to cache then packaged
    df = _read_csv_safe(CACHE_FILE)
    if df is not None:
        return df
    df = _read_csv_safe(PACKAGED_CSV)
    if df is not None:
        return df
    raise RuntimeError("Unable to retrieve CWC station metadata")

# ---------------------------------------------------------
# Station code pattern for CWC flood forecasting stations
# that have time series data (e.g. "040-CDJAPR").
# The layer-station API returns ALL station types; only
# codes matching NNN-... carry HHS water-level data.
# ---------------------------------------------------------

import re

_TS_CODE_RE = re.compile(r"^\d{3}-")

CWC_BASE = "https://ffs.india-water.gov.in/iam/api"
LAYER_STATION_BASE = f"{CWC_BASE}/layer-station"


def _fetch_lookup_sorted(entity, sort_field="name"):
    """Fetch a complete lookup table via the /specification/sorted endpoint."""
    import json

    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"{CWC_BASE}/{entity}/specification/sorted"
    params = {
        "sort-criteria": json.dumps(
            {"sortOrderDtos": [{"sortDirection": "ASC", "field": sort_field}]}
        ),
        "specification": json.dumps({"unique": True}),
    }
    r = session.get(url, params=params, headers=headers, timeout=120)
    r.raise_for_status()
    return r.json()


def _fetch_lookup_paged(entity, sort_field="name", page_size=5000):
    """Fetch a lookup table via the paginated /specification/sorted-page endpoint."""
    import json

    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"{CWC_BASE}/{entity}/specification/sorted-page"
    all_items = []
    for page in range(20):
        params = {
            "sort-criteria": json.dumps(
                {"sortOrderDtos": [{"sortDirection": "ASC", "field": sort_field}]}
            ),
            "page-number": page,
            "page-size": page_size,
            "specification": json.dumps({"unique": True}),
        }
        r = session.get(url, params=params, headers=headers, timeout=120)
        r.raise_for_status()
        items = r.json()
        if not items:
            break
        all_items.extend(items)
        if len(items) < page_size:
            break
    return all_items


def _fetch_all_lookups():
    """
    Fetch all CWC lookup tables in parallel and return dicts for
    in-memory chain resolution.
    """
    _TASKS = {
        "localrivers": ("master-basin-localriver", "sorted", "name"),
        "subsubtribs": ("master-basin-subsubtributary", "sorted", "name"),
        "subtribs": ("master-basin-subtributary", "paged", "subtributaryId"),
        "tributaries": ("master-basin-tributary", "paged", "tributaryId"),
        "rivers": ("layer-river", "sorted", "name"),
        "basins": ("layer-basin", "sorted", "name"),
        "tahsils": ("master-tahsil", "sorted", "name"),
        "districts": ("layer-district", "sorted", "name"),
        "states": ("layer-state", "sorted", "name"),
        "subdiv_offices": ("master-subdivisional-office", "sorted", "name"),
        "div_offices": ("master-divisional-office", "sorted", "name"),
        "flood_forecast": ("flood-forecast-static", "sorted", "stationCode"),
    }

    raw = {}

    def _do(key, entity, mode, sf):
        if mode == "sorted":
            return key, _fetch_lookup_sorted(entity, sf)
        return key, _fetch_lookup_paged(entity, sf)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {
            pool.submit(_do, k, ent, m, sf): k
            for k, (ent, m, sf) in _TASKS.items()
        }
        for f in as_completed(futs):
            try:
                k, data = f.result()
                raw[k] = data
            except Exception:
                raw[futs[f]] = []

    # -- river name -------------------------------------------------
    lr_name = {
        x["localriverId"]: x.get("name")
        for x in raw.get("localrivers", [])
    }

    # -- basin chain: localriver → subsubtrib → subtrib → trib → river → basin
    lr_ssub = {
        x["localriverId"]: x.get("subsubtributaryId")
        for x in raw.get("localrivers", [])
    }
    ssub_sub = {
        x["subsubtributaryId"]: x.get("subtributaryId")
        for x in raw.get("subsubtribs", [])
    }
    sub_trib = {
        x["subtributaryId"]: x.get("tributaryId")
        for x in raw.get("subtribs", [])
    }
    trib_riv = {
        x["tributaryId"]: x.get("riverId")
        for x in raw.get("tributaries", [])
    }
    riv_basin = {
        x["riverId"]: x.get("basinCode")
        for x in raw.get("rivers", [])
    }
    basin_name = {
        x["basinCode"]: x.get("name")
        for x in raw.get("basins", [])
    }

    def resolve_basin(lr_id):
        ssid = lr_ssub.get(lr_id)
        sid = ssub_sub.get(ssid) if ssid else None
        tid = sub_trib.get(sid) if sid else None
        rid = trib_riv.get(tid) if tid else None
        bc = riv_basin.get(rid) if rid else None
        return basin_name.get(bc) if bc else None

    # -- district / state chain: tahsil → district → state ----------
    tah_dist = {
        x["tahsilId"]: x.get("districtId")
        for x in raw.get("tahsils", [])
    }
    dist_info = {
        x["districtId"]: (x.get("name"), x.get("stateCode"))
        for x in raw.get("districts", [])
    }
    state_name = {
        x["stateCode"]: x.get("name")
        for x in raw.get("states", [])
    }

    def resolve_district(tahsil_id):
        did = tah_dist.get(tahsil_id)
        return dist_info.get(did, (None, None))[0] if did else None

    def resolve_state(tahsil_id):
        did = tah_dist.get(tahsil_id)
        if not did:
            return None
        _, sc = dist_info.get(did, (None, None))
        return state_name.get(sc) if sc else None

    # -- division chain: subdiv_office → div_office -----------------
    subdiv_div = {
        x["subdivisionalOfficeId"]: x.get("divisionalOfficeId")
        for x in raw.get("subdiv_offices", [])
    }
    div_name = {
        x["divisionalOfficeId"]: x.get("name")
        for x in raw.get("div_offices", [])
    }

    def resolve_division(subdiv_id):
        did = subdiv_div.get(subdiv_id)
        return div_name.get(did) if did else None

    # -- flood forecast data ----------------------------------------
    ff_map = {}
    for ff in raw.get("flood_forecast", []):
        code = ff.get("stationCode") or ff.get("layerStationStationCode")
        if code:
            ff_map[code] = ff

    return (
        lr_name,
        resolve_basin,
        resolve_state,
        resolve_district,
        resolve_division,
        ff_map,
    )


def fetch_cwc_station_metadata():
    """
    Fetch comprehensive metadata for all CWC flood-forecast stations
    that have time-series data.

    Uses the same API filter as the CWC website (agencyId=41, non-null
    floodForecastStaticStationCode).  Metadata is resolved through bulk
    lookup tables fetched in parallel — river, basin, state, district,
    division, and flood-level data — then joined in memory.
    """
    import json

    headers = {"User-Agent": "Mozilla/5.0"}
    list_url = f"{LAYER_STATION_BASE}/specification/sorted-page"

    # -- Fetch all lookup tables in parallel while we paginate ------
    (
        lr_name,
        resolve_basin,
        resolve_state,
        resolve_district,
        resolve_division,
        ff_map,
    ) = _fetch_all_lookups()

    # -- Paginate station listing -----------------------------------
    sort = json.dumps(
        {"sortOrderDtos": [{"sortDirection": "ASC", "field": "name"}]}
    )
    spec = json.dumps({
        "where": {
            "expression": {
                "valueIsRelationField": False,
                "fieldName": (
                    "subdivisionalOfficeId.divisionalOfficeId"
                    ".circleOfficeId.regionalOfficeId.agencyId.agencyId"
                ),
                "operator": "eq",
                "value": "41",
            }
        },
        "and": {
            "expression": {
                "valueIsRelationField": False,
                "fieldName": "floodForecastStaticStationCode.stationCode",
                "operator": "null",
                "value": "false",
            }
        },
        "unique": True,
    })
    page_size = 500

    rows = []

    for page_num in range(50):
        params = {
            "sort-criteria": sort,
            "page-number": page_num,
            "page-size": page_size,
            "specification": spec,
        }

        r = session.get(list_url, params=params, headers=headers, timeout=180)

        if r.status_code != 200:
            break

        stations = r.json()
        if not isinstance(stations, list) or len(stations) == 0:
            break

        for s in stations:
            code = s.get("stationCode")
            if not code or not _TS_CODE_RE.match(code):
                continue

            lr_id = s.get("streamLocalriverId")
            tahsil_id = s.get("tahsilId")
            subdiv_id = s.get("subdivisionalOfficeId")
            ff = ff_map.get(code, {})

            rows.append({
                "code": code,
                "name": s.get("name"),
                "river": lr_name.get(lr_id) if lr_id else None,
                "basin": resolve_basin(lr_id) if lr_id else None,
                "state": resolve_state(tahsil_id) if tahsil_id else None,
                "district": resolve_district(tahsil_id) if tahsil_id else None,
                "division": resolve_division(subdiv_id) if subdiv_id else None,
                "lat": s.get("lat"),
                "lon": s.get("lon"),
                "rl_zero": s.get("reducedLevelOfZeroGauge"),
                "warning_level": ff.get("warningLevel"),
                "danger_level": ff.get("dangerLevel"),
                "hfl": ff.get("highestFlowLevel"),
                "hfl_date": ff.get("highestFlowLevelDate"),
            })

        if len(stations) < page_size:
            break

    if not rows:
        raise RuntimeError("No CWC time-series station codes found")

    # -- Fetch lat/lon/rl_zero from per-station detail endpoint -----
    # The listing returns these as null; only the detail endpoint
    # (/layer-station/{code}) populates them.

    import time as _time

    codes_to_fetch = [r["code"] for r in rows]

    def _fetch_geo(code, retries=3):
        delays = [2, 5, 10]
        for attempt in range(retries):
            try:
                resp = session.get(
                    f"{LAYER_STATION_BASE}/{code}",
                    headers=headers,
                    timeout=60,
                )
                if resp.status_code != 200:
                    if attempt < retries - 1:
                        _time.sleep(delays[attempt])
                        continue
                    return code, None, None, None
                d = resp.json()
                return (
                    code,
                    d.get("lat"),
                    d.get("lon"),
                    d.get("reducedLevelOfZeroGauge"),
                )
            except Exception:
                if attempt < retries - 1:
                    _time.sleep(delays[attempt])
                    continue
                return code, None, None, None
        return code, None, None, None

    geo = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        for result in pool.map(_fetch_geo, codes_to_fetch):
            code, lat, lon, rl = result
            geo[code] = (lat, lon, rl)

    for row in rows:
        lat, lon, rl = geo.get(row["code"], (None, None, None))
        row["lat"] = lat
        row["lon"] = lon
        row["rl_zero"] = rl

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset="code")
    df = df.sort_values("code").reset_index(drop=True)

    # Strip stray whitespace / tab characters from string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    return df

# ---------------------------------------------------------
# Fetch CWC station data
# ---------------------------------------------------------

def fetch_station_data(code, start_date=None, end_date=None, retries=3):

    import time

    start = start_date or "1950-01-01"
    end = end_date or "2100-01-01"

    params = {
        "sort-criteria": "%7B%22sortOrderDtos%22:%5B%7B%22sortDirection%22:%22ASC%22,%22field%22:%22id.dataTime%22%7D%5D%7D",

        "specification": (
            "%7B%22where%22:%7B%22where%22:%7B%22where%22:%7B%22expression%22:%7B"
            f"%22valueIsRelationField%22:false,%22fieldName%22:%22id.stationCode%22,%22operator%22:%22eq%22,%22value%22:%22{code}%22"
            "%7D%7D,%22and%22:%7B%22expression%22:%7B"
            "%22valueIsRelationField%22:false,%22fieldName%22:%22id.datatypeCode%22,%22operator%22:%22eq%22,%22value%22:%22HHS%22"
            "%7D%7D%7D,%22and%22:%7B%22expression%22:%7B"
            "%22valueIsRelationField%22:false,%22fieldName%22:%22dataValue%22,%22operator%22:%22null%22,%22value%22:%22false%22"
            "%7D%7D%7D,%22and%22:%7B%22expression%22:%7B"
            f"%22valueIsRelationField%22:false,%22fieldName%22:%22id.dataTime%22,%22operator%22:%22btn%22,%22value%22:%22{start}T00:00:00,{end}T00:00:00%22"
            "%7D%7D%7D"
        )
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    delays = [5, 10, 20]

    for attempt in range(retries):

        try:

            r = session.get(
                CWC_API,
                params=params,
                headers=headers,
                timeout=120
            )

            if r.status_code == 200:

                data = r.json()

                rows = []

                for j in data:
                    try:
                        rows.append([
                            j["stationCode"],
                            j["id"]["dataTime"],
                            j["dataValue"]
                        ])
                    except Exception:
                        pass

                if rows:
                    df = pd.DataFrame(rows, columns=["station_code", "time", "water_level"])
                    df["time"] = pd.to_datetime(df["time"])
                    return df

        except Exception:
            pass

        if attempt < retries - 1:
            time.sleep(delays[attempt])

    return None

def _normalize_list_filter(value):
    """Return a list of non-empty strings from str or list/tuple/set."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(v).strip() for v in value if str(v).strip()]


def get_cwc_station_metadata(
    station=None, basin=None, river=None, state=None, refresh=False
):
    """
    Return metadata for CWC flood-forecast stations.

    Parameters
    ----------
    station : str, optional
        Station code or partial name to search for.
    basin : str or list[str], optional
        Basin name filter (substring match). Pass a list for multiple basins.
    river : str, optional
        River name filter (substring match).
    state : str or list[str], optional
        State name filter (substring match). Pass a list for multiple states.
    refresh : bool, default False
        If True, fetch fresh metadata from the CWC FFS API.
    """
    stations = load_station_table(refresh=refresh)
    df = stations.copy()

    basins = _normalize_list_filter(basin)
    if basins:
        mask = pd.Series(False, index=df.index)
        for b in basins:
            mask |= df["basin"].astype(str).str.lower().str.contains(b.lower(), na=False)
        df = df[mask]

    if river:
        df = df[df["river"].astype(str).str.lower().str.contains(river.lower(), na=False)]

    states = _normalize_list_filter(state)
    if states:
        mask = pd.Series(False, index=df.index)
        for s in states:
            mask |= df["state"].astype(str).str.lower().str.contains(s.lower(), na=False)
        df = df[mask]

    if station:
        q = str(station).lower()
        df = df[
            df["code"].astype(str).str.lower().str.contains(q, na=False)
            | df["name"].astype(str).str.lower().str.contains(q, na=False)
        ]

    if df.empty:
        raise ValueError("No matching CWC stations found")

    return df.sort_values("code").reset_index(drop=True)
# ---------------------------------------------------------
# Worker function for parallel downloads
# ---------------------------------------------------------

def download_station(station, output_dir, args):

    code = str(station["code"]).strip()
    name = str(station["name"]).strip()

    lat = station.get("lat")
    lon = station.get("lon")

    safe_name = (
        name.replace("/", "-")
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )

    ext = args.format

    outfile = os.path.join(output_dir, f"{code}_{safe_name}.{ext}")

    # ---------------------------------------------------------
    # Skip existing file unless overwrite
    # ---------------------------------------------------------

    if os.path.exists(outfile) and not args.overwrite:
        return "skipped"

    # ---------------------------------------------------------
    # Fetch data
    # ---------------------------------------------------------

    df = fetch_station_data(
        code,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    if df is None or df.empty:
        return False

    # ---------------------------------------------------------
    # Parse timestamps
    # ---------------------------------------------------------

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])


    if df.empty:
        return False

    # Normalise CWC value column so downstream plot/merge logic can rely on `wse`.
    if "wse" not in df.columns and "water_level" in df.columns:
        df["wse"] = pd.to_numeric(df["water_level"], errors="coerce")
    
    rl = station.get("rl_zero")

    if rl is not None:
        try:
            df["water_depth"] = df["wse"] - float(rl)
        except Exception:
            # If rl_zero cannot be parsed, just skip water_depth.
            pass

    # ---------------------------------------------------------
    # Attach minimal station metadata to rows
    # (full metadata moved to file header for CSV/XLSX)
    # ---------------------------------------------------------

    df["unit"] = "m"
    df["lat"] = lat
    df["lon"] = lon
    df["station_code"] = code

    # Keep the row-level dataframe lean: only fields needed for
    # plotting/merge; richer metadata is written once in the header.
    cols = [
        "station_code",
        "time",
        "wse",
        "water_depth",
        "unit",
        "lat",
        "lon",
    ]
    df = df[[c for c in cols if c in df.columns]]

    # ---------------------------------------------------------
    # Build metadata header (WRIS-style, but for CWC)
    # ---------------------------------------------------------

    meta_src = dict(station)
    meta_src.setdefault("station_code", code)
    meta_src.setdefault("station_name", name)

    meta_dict = build_metadata(meta_src, dataset="water_level", source="CWC")

    # ---------------------------------------------------------
    # Save file (WRIS-compatible layout)
    # ---------------------------------------------------------

    try:
        if args.format == "csv":
            # CSV: write a metadata preamble with "#" lines followed by
            # a compact timeseries table.
            header_lines = ["# SWIFT Hydrological Timeseries"]
            for key, value in meta_dict.items():
                if value is not None and value != "":
                    header_lines.append(f"# {key}: {value}")

            with open(outfile, "w") as f:
                for line in header_lines:
                    f.write(line + "\n")

            df.to_csv(outfile, mode="a", index=False)

        elif args.format == "xlsx":
            # XLSX: mirror WRIS convention — one sheet for timeseries,
            # one sheet for station metadata.
            meta_items = [
                (k, v) for k, v in meta_dict.items() if v is not None and v != ""
            ]
            meta_df = pd.DataFrame(
                [{"field": k, "value": v} for k, v in meta_items]
            )

            with pd.ExcelWriter(outfile) as writer:
                df.to_excel(writer, sheet_name="timeseries", index=False)
                meta_df.to_excel(writer, sheet_name="metadata", index=False)

    except Exception:
        return False

    return True

# ---------------------------------------------------------
# Main CWC downloader
# ---------------------------------------------------------

def run_cwc_download(args):

    import glob
    import time as _time
    from pathlib import Path

    try:
        import importlib
        tqdm_mod = importlib.import_module("tqdm").tqdm
    except Exception:
        def tqdm_mod(iterable, **_kwargs):
            return iterable

    # Root CWC output directory; basin-specific subfolders are attached
    # later once we know which stations are included in this run.
    cwc_root = os.path.join(args.output_dir, "cwc")
    os.makedirs(cwc_root, exist_ok=True)
    
    Console.is_quiet = getattr(args, "quiet", False)
    logger = Logger(cwc_root)
    
    Console.section("Dataset: water_level (CWC)")
    logger.log("INFO", "Starting CWC water_level download")

    dataset_start = _time.time()

    stations = load_station_table(
        refresh=getattr(args, "cwc_refresh", False)
    )

    # ---------------------------------------------------------
    # Station filter
    # ---------------------------------------------------------

    if args.cwc_station:
        stations = stations[stations["code"].isin(args.cwc_station)]

        if stations.empty:
            logger.log("ERROR", "No matching CWC stations found")
            raise SystemExit("No matching CWC stations found")

    # Optional basin filter (case-insensitive substring matching) to
    # mirror swift.cwc.stations(..., basin=...) behavior. This acts as
    # a defensive filter in case only basin names are provided upstream.
    basin_filters = getattr(args, "cwc_basin_filter", None)
    if basin_filters:
        if isinstance(basin_filters, str):
            basin_filters = [basin_filters]
        basin_filters = [str(b).strip() for b in basin_filters if str(b).strip()]
        if basin_filters and "basin" in stations.columns:
            basin_mask = pd.Series(False, index=stations.index)
            basin_series = stations["basin"].astype(str)
            for b in basin_filters:
                basin_mask |= basin_series.str.lower().str.contains(b.lower(), na=False)
            stations = stations[basin_mask]
            if stations.empty:
                logger.log(
                    "ERROR",
                    "No matching CWC stations found for basin filter: "
                    + ", ".join(basin_filters),
                )
                raise SystemExit(
                    "No matching CWC stations found for basin filter: "
                    + ", ".join(basin_filters)
                )

    n_stations = len(stations)

    start_year = str(args.start_date)[:4] if args.start_date else "1950"
    end_year = str(args.end_date)[:4] if args.end_date else "2026"
    fmt = args.format.upper()

    Console.info(
        f"Mode: CWC download | Stations: {n_stations} | "
        f"Format: {fmt} | Time range: {start_year}\u2013{end_year}"
    )
    if basin_filters:
        Console.info("Basin filter: " + ", ".join(basin_filters))
    
    if not Console.is_quiet:
        print(f"{Console.ITALIC}Note: The CWC servers stream full historical datasets at slow speeds (~100 KB/s).{Console.RESET}")
        print(f"{Console.ITALIC}A single station may take 1-2 minutes to appear on the progress bar. Please do not cancel the process.{Console.RESET}\n")

    logger.log("INFO", f"Discovered {n_stations} CWC stations natively")

    # ---------------------------------------------------------
    # Output folder: basin-aware when possible
    # ---------------------------------------------------------
    
    # When called from fetch() with a basin-column table, args.basin is set.
    # Otherwise infer from the filtered station table if all share one basin.
    basin_slug = ""
    if getattr(args, "basin", None):
        basin_slug = str(args.basin).strip().lower().replace(" ", "_")
    elif not stations.empty and "basin" in stations.columns:
        unique_basins = {
            str(b).strip().lower().replace(" ", "_")
            for b in stations["basin"].dropna()
        }
        if len(unique_basins) == 1:
            basin_slug = next(iter(unique_basins))

    if basin_slug:
        base_output = os.path.join(cwc_root, basin_slug, "stations")
    else:
        base_output = os.path.join(cwc_root, "stations")
    os.makedirs(base_output, exist_ok=True)
    
    # ---------------------------------------------------------
    # Resume filter
    # ---------------------------------------------------------
    
    ext = args.format.lower()
    all_codes = [str(row["code"]).strip() for _, row in stations.iterrows()]

    if args.overwrite:
        station_list = list(stations.iterrows())
    else:
        station_list = []
        for _, row in stations.iterrows():
            code = str(row["code"]).strip()
            pattern = os.path.join(base_output, f"{code}_*.{ext}")
            if not glob.glob(pattern):
                station_list.append((_, row))

    remaining = len(station_list)
    skipped = 0 if args.overwrite else n_stations - remaining

    if skipped > 0:
        Console.warn(f"Stations skipped (already downloaded): {skipped}")
        if not Console.is_quiet:
            print(f"{Console.ITALIC}Tip: call with overwrite=True to refresh data.{Console.RESET}")
        logger.log("INFO", f"Skipped {skipped} existing stations")

    downloaded = 0
    downloaded_codes = []
    workers = min(32, max(8, (os.cpu_count() or 1) * 4))

    # ---------------------------------------------------------
    # Parallel downloads
    # ---------------------------------------------------------

    if remaining > 0:

        def _worker(item):
            _, station_row = item
            res = download_station(station_row, base_output, args)
            return (res, station_row["code"])

        with ThreadPoolExecutor(max_workers=workers) as executor:

            futures = [executor.submit(_worker, item) for item in station_list]

        for f in tqdm_mod(
            as_completed(futures),
            total=len(futures),
            desc="water_level",
            unit="station",
            leave=True,
            dynamic_ncols=True,
            disable=Console.is_quiet
        ):
            try:
                result, stcode = f.result()
                if result is True:
                    downloaded += 1
                    downloaded_codes.append(str(stcode).strip())
                    logger.log("SUCCESS", f"Downloaded {stcode}")
                elif result is False or result is None:
                    logger.log("WARN", f"Failed or empty data for {stcode}")
            except Exception as e:
                logger.log("ERROR", f"Worker crash: {str(e)}")

    else:
        Console.info("All stations already downloaded \u2014 skipping download step.")

    # ---------------------------------------------------------
    # Plotting
    # ---------------------------------------------------------

    if args.plot:
        try:
            from .plot_station_timeseries import plot_station

            files = list(Path(base_output).glob("*.csv"))
            files.extend(Path(base_output).glob("*.xlsx"))

            if not files:
                Console.warn("No station files found for plotting")
            else:
                image_root = str(args.output_dir) if getattr(args, "output_dir", None) else None

                for f in tqdm_mod(files, desc="Plotting", unit="plot", dynamic_ncols=True, disable=Console.is_quiet):
                    try:
                        plot_station(f, image_root=image_root)
                    except Exception as pe:
                        logger.log("WARN", f"Plot failed for {f.name}: {str(pe)}")
                        
                Console.success(f"Plots generated: {len(files)}")
                logger.log("INFO", f"Successfully generated {len(files)} plots")

        except Exception as e:
            Console.warn(f"Plotting failed: {str(e)}")
            logger.log("ERROR", f"Plotting suite failed: {str(e)}")

    # ---------------------------------------------------------
    # Merge
    # ---------------------------------------------------------

    if args.merge:
        from .merge import merge_dataset_folder, merge_dataset_files

        # Basin-aware, time-period-aware GeoPackage name (like WRIS).
        # Format: cwc_waterlevel_<basin>_<start_date>_<end_date>.gpkg
        basin_slug = ""
        if getattr(args, "basin", None):
            basin_slug = str(args.basin).strip().lower().replace(" ", "_")
        elif not stations.empty and "basin" in stations.columns:
            unique_basins = {
                str(b).strip().lower().replace(" ", "_")
                for b in stations["basin"].dropna()
            }
            if len(unique_basins) == 1:
                basin_slug = next(iter(unique_basins))

        start_slug = (str(args.start_date)[:10] if args.start_date else "1950-01-01")
        end_slug = (str(args.end_date)[:10] if args.end_date else _time.strftime("%Y-%m-%d"))

        name_parts = ["cwc_waterlevel"]
        if basin_slug:
            name_parts.append(basin_slug)
        name_parts.extend([start_slug, end_slug])
        gpkg_name = "_".join(name_parts) + ".gpkg"

        gpkg_path = os.path.join(args.output_dir, "cwc", gpkg_name)

        if downloaded == 0 and os.path.exists(gpkg_path):
            Console.info(f"Using cached GeoPackage for CWC ({start_slug} to {end_slug})")
        elif downloaded > 0:
            # Merge only files downloaded in this run so the GeoPackage is
            # time-period aware and does not include stale files.
            ext = args.format.lower()
            merge_files = []
            for code in downloaded_codes:
                pattern = os.path.join(base_output, f"{code}_*.{ext}")
                merge_files.extend(glob.glob(pattern))

            if not merge_files:
                logger.log("WARN", "No station files found to merge for current run")
            else:
                logger.log(
                    "INFO",
                    f"Merging {len(merge_files)} CWC file(s) to GeoPackage: {gpkg_name}",
                )
                merge_dataset_files(merge_files, gpkg_path, "cwc_waterlevel")

    # ---------------------------------------------------------
    # Summary table (mirrors WRIS format)
    # ---------------------------------------------------------

    runtime = round(_time.time() - dataset_start, 1)

    if downloaded > 0:
        if not Console.is_quiet:
            print()
        Console.success(f"water_level downloaded in {runtime} seconds")

    found = downloaded + skipped
    
    logger.log("INFO", f"Finished CWC: Downloaded {downloaded}, Skipped {skipped} in {runtime}s")

    if not Console.is_quiet:
        print("\n-------------------------------------------------------------")
        print("Download Summary")
        print("-------------------------------------------------------------")
        print(f"{'Dataset':<18}{'Found':<12}{'Downloaded':<12}{'Skipped':<12}{'Time(s)'}")
        print("-------------------------------------------------------------")
        print(
            f"{'water_level':<18}"
            f"{found:<12}"
            f"{downloaded:<12}"
            f"{skipped:<12}"
            f"{runtime}"
        )
        print("-------------------------------------------------------------")
        print(f"Output directory: {base_output}")
        print("-------------------------------------------------------------")

    return 0

