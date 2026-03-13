"""
CWC Flood Forecasting Station downloader for SWIFT
"""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

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
# Load station table
# ---------------------------------------------------------
def load_station_table():

    import time

    cache_dir = Path.home() / ".swift_cache"
    cache_file = cache_dir / "cwc_stations.csv"

    cache_dir.mkdir(exist_ok=True)

    # ---------------------------------------------------------
    # Use cache if fresh (<24 hours)
    # ---------------------------------------------------------

    if cache_file.exists():

        age = time.time() - cache_file.stat().st_mtime

        if age < 86400:  # 24 hours
            try:
                df = pd.read_csv(cache_file)
                if not df.empty:
                    return df
                print("Using cached CWC station metadata")
            except Exception:
                pass

    # ---------------------------------------------------------
    # Fetch from API
    # ---------------------------------------------------------

    try:

        df = fetch_cwc_station_metadata()
        print("Fetching CWC station metadata from API")

        if not df.empty:
            df.to_csv(cache_file, index=False)
            return df


    except Exception:
        pass

    # ---------------------------------------------------------
    # Fallback to packaged CSV
    # ---------------------------------------------------------

    station_file = Path(__file__).parent / "cwc_stations.csv"

    if station_file.exists():
        df = pd.read_csv(station_file)
        df.columns = [c.lower().strip() for c in df.columns]
        return df

    raise RuntimeError("Unable to retrieve CWC station metadata")

# Get metadata for all stations

def fetch_cwc_station_metadata():

    base_url = "https://ffs.india-water.gov.in/iam/api/station"

    headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_page(page):

        params = {"page": page, "size": 100}

        for _ in range(3):
            try:
                r = session.get(base_url, params=params, headers=headers, timeout=60)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass

        return []


    rows = []

    pages = range(0, 20)   # adjust if needed

    with ThreadPoolExecutor(max_workers=6) as executor:

        results = executor.map(fetch_page, pages)

    for page_data in results:

        if not page_data:
            break

        for s in page_data:

                rows.append({
                    "code": s.get("stationCode"),
                    "name": s.get("stationName"),
                    "river": s.get("river"),
                    "basin": s.get("basin"),
                    "lat": s.get("latitude"),
                    "lon": s.get("longitude"),
                    "rl_zero": s.get("rl"),
                    "warning_level": s.get("warningLevel"),
                    "danger_level": s.get("dangerLevel"),
                    "hfl": s.get("hfl"),
                    "hfl_date": s.get("hflDate"),
                })

    return pd.DataFrame(rows)

# ---------------------------------------------------------
# Fetch CWC station data
# ---------------------------------------------------------

def fetch_station_data(code, retries=3):

    import time
    
    params = {
        "sort-criteria": "%7B%22sortOrderDtos%22:%5B%7B%22sortDirection%22:%22ASC%22,%22field%22:%22id.dataTime%22%7D%5D%7D",
        "specification": (
            "%7B%22where%22:%7B%22expression%22:%7B"
            f"%22fieldName%22:%22id.stationCode%22,%22operator%22:%22eq%22,%22value%22:%22{code}%22"
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

                if isinstance(data, list):
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
                        df = pd.DataFrame(rows, columns=["station_code", "time", "wse"])
                        df["time"] = pd.to_datetime(df["time"])
                        return df

        except Exception:
            pass
            
        if attempt < retries - 1:
            time.sleep(delays[attempt])

    return None


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

    outfile = os.path.join(
        output_dir,
        f"{code}_{safe_name}.{ext}"
    )

    # ---------------------------------------------------------
    # Skip existing file unless overwrite
    # ---------------------------------------------------------

    if os.path.exists(outfile) and not args.overwrite:
        return "skipped"

    # ---------------------------------------------------------
    # Fetch data
    # ---------------------------------------------------------

    df = fetch_station_data(code)

    if df is None or df.empty:
        return False

    # ---------------------------------------------------------
    # Parse timestamps
    # ---------------------------------------------------------

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    # ---------------------------------------------------------
    # Date filtering
    # ---------------------------------------------------------

    try:

        if args.start_date:
            start = pd.to_datetime(args.start_date)
            df = df[df["time"] >= start]

        if args.end_date:
            end = pd.to_datetime(args.end_date)
            df = df[df["time"] <= end]

    except Exception:
        pass

    if df.empty:
        return False
    
    rl = station.get("rl_zero")

    if rl is not None:
        try:
            df["water_depth"] = df["wse"] - float(rl)
        except Exception:
            pass    

    # ---------------------------------------------------------
    # Attach station metadata
    # ---------------------------------------------------------

    df["station_name"] = name
    df["unit"] = "m"
    df["lat"] = lat
    df["lon"] = lon

    # Optional metadata
    for field in [
        "river",
        "basin",
        "rl_zero",
        "warning_level",
        "danger_level",
        "hfl",
        "hfl_date",
    ]:
        if field in station:
            df[field] = station.get(field)

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
    # Save file
    # ---------------------------------------------------------

    try:

        if args.format == "csv":
            df.to_csv(outfile, index=False)

        elif args.format == "xlsx":
            df.to_excel(outfile, index=False)

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
    from concurrent.futures import ThreadPoolExecutor
    from .download import Console, Logger

    try:
        import importlib
        tqdm_mod = importlib.import_module("tqdm").tqdm
    except Exception:
        def tqdm_mod(iterable, **_kwargs):
            return iterable

    base_output = os.path.join(args.output_dir, "cwc", "stations")
    os.makedirs(base_output, exist_ok=True)
    
    Console.is_quiet = getattr(args, "quiet", False)
    logger = Logger(base_output)
    
    Console.section("Dataset: water_level (CWC)")
    logger.log("INFO", "Starting CWC water_level download")

    dataset_start = _time.time()

    stations = load_station_table()

    # ---------------------------------------------------------
    # Station filter
    # ---------------------------------------------------------

    if args.cwc_station:
        stations = stations[stations["code"].isin(args.cwc_station)]

        if stations.empty:
            logger.log("ERROR", "No matching CWC stations found")
            raise SystemExit("No matching CWC stations found")

    n_stations = len(stations)

    start_year = str(args.start_date)[:4] if args.start_date else "1950"
    end_year = str(args.end_date)[:4] if args.end_date else "2026"
    fmt = args.format.upper()

    Console.info(
        f"Mode: CWC download | Stations: {n_stations} | "
        f"Format: {fmt} | Time range: {start_year}\u2013{end_year}"
    )
    
    if not Console.is_quiet:
        print(f"{Console.ITALIC}Note: The CWC servers stream full historical datasets at slow speeds (~100 KB/s).{Console.RESET}")
        print(f"{Console.ITALIC}A single station may take 1-2 minutes to appear on the progress bar. Please do not cancel the process.{Console.RESET}\n")

    logger.log("INFO", f"Discovered {n_stations} CWC stations natively")

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
            print(f"{Console.ITALIC}Tip: use --overwrite to refresh data.{Console.RESET}")
        logger.log("INFO", f"Skipped {skipped} existing stations")

    downloaded = 0
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
                for f in tqdm_mod(files, desc="Plotting", unit="plot", dynamic_ncols=True, disable=Console.is_quiet):
                    try:
                        plot_station(f)
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
        from .merge import merge_dataset_folder

        gpkg_path = os.path.join(args.output_dir, "cwc", "cwc_timeseries.gpkg")

        if downloaded == 0 and os.path.exists(gpkg_path):
            Console.info("Using cached GeoPackage for CWC")
        else:
            logger.log("INFO", "Merging CWC data to GeoPackage")
            merge_dataset_folder(base_output, gpkg_path, "cwc_timeseries")

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

