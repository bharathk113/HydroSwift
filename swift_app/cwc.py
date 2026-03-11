"""
CWC Flood Forecasting Station downloader for SWIFT
"""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

# ---------------------------------------------------------
# HTTP session (connection reuse)
# ---------------------------------------------------------

session = requests.Session()

CWC_API = "https://ffs.india-water.gov.in/iam/api/new-entry-data/specification/sorted"


# ---------------------------------------------------------
# Load station table
# ---------------------------------------------------------

def load_station_table():

    station_file = Path(__file__).parent / "cwc_stations.csv"
    location_file = Path(__file__).parent / "station_locations.csv"

    if not station_file.exists():
        raise RuntimeError("CWC station file missing")

    df = pd.read_csv(station_file)
    df.columns = [c.lower().strip() for c in df.columns]

    # ---------------------------------------------------------
    # Load station locations if available
    # ---------------------------------------------------------

    if location_file.exists():

        loc = pd.read_csv(location_file)
        loc.columns = [c.lower().strip() for c in loc.columns]

        # normalize names for matching
        df["name"] = (
            df["name"]
            .astype(str)
            .str.lower()
            .str.replace(r"\(.*?\)", "", regex=True)
            .str.strip()
        )

        loc["name"] = (
            loc["name"]
            .astype(str)
            .str.lower()
            .str.replace(r"\(.*?\)", "", regex=True)
            .str.strip()
        )

        # merge coordinates
        df = df.merge(
            loc[["name", "lat", "lon"]],
            on="name",
            how="left"
        )

    else:
        print("Warning: station_locations.csv not found; Skipping lat/lon entries.")

    return df


# ---------------------------------------------------------
# Fetch CWC station data
# ---------------------------------------------------------

def fetch_station_data(code, retries=2):

    params = {
        "sort-criteria": "%7B%22sortOrderDtos%22:%5B%7B%22sortDirection%22:%22ASC%22,%22field%22:%22id.dataTime%22%7D%5D%7D",
        "specification": (
            "%7B%22where%22:%7B%22expression%22:%7B"
            f"%22fieldName%22:%22id.stationCode%22,%22operator%22:%22eq%22,%22value%22:%22{code}%22"
            "%7D%7D%7D"
        )
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    for _ in range(retries):

        try:

            r = session.get(
                CWC_API,
                params=params,
                headers=headers,
                timeout=120
            )

            if r.status_code != 200:
                return None

            data = r.json()

            if not isinstance(data, list):
                return None

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

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=["station_code", "time", "wse"])

            df["time"] = pd.to_datetime(df["time"])

            return df

        except Exception:
            pass

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

    # ---------------------------------------------------------
    # Attach station metadata
    # ---------------------------------------------------------

    df["station_name"] = name
    df["unit"] = "m"
    df["lat"] = lat
    df["lon"] = lon

    cols = ["station_code", "time", "wse", "unit", "lat", "lon"]
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
    from .download import Console

    try:
        import importlib
        tqdm_mod = importlib.import_module("tqdm").tqdm
    except Exception:
        def tqdm_mod(iterable, **_kwargs):
            return iterable

    Console.section("Dataset: water_level (CWC)")

    dataset_start = _time.time()

    base_output = os.path.join(args.output_dir, "cwc", "stations")
    os.makedirs(base_output, exist_ok=True)

    stations = load_station_table()

    # ---------------------------------------------------------
    # Station filter
    # ---------------------------------------------------------

    if args.cwc_station:
        stations = stations[stations["code"].isin(args.cwc_station)]

        if stations.empty:
            raise SystemExit("No matching CWC stations found")

    n_stations = len(stations)

    start_year = str(args.start_date)[:4] if args.start_date else "1950"
    end_year = str(args.end_date)[:4] if args.end_date else "2026"
    fmt = args.format.upper()

    Console.info(
        f"Mode: CWC download | Stations: {n_stations} | "
        f"Format: {fmt} | Time range: {start_year}\u2013{end_year}"
    )

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
        print(f"{Console.ITALIC}Tip: use --overwrite to refresh data.{Console.RESET}")

    downloaded = 0
    workers = min(8, (os.cpu_count() or 1) * 2)

    # ---------------------------------------------------------
    # Parallel downloads
    # ---------------------------------------------------------

    if remaining > 0:

        def _worker(item):
            _, station_row = item
            return download_station(station_row, base_output, args)

        with ThreadPoolExecutor(max_workers=workers) as executor:

            futures = [executor.submit(_worker, item) for item in station_list]

            for f in tqdm_mod(
                futures,
                total=len(futures),
                desc="water_level",
                unit="station",
                leave=True,
                dynamic_ncols=True,
            ):
                try:
                    result = f.result()
                    if result is True:
                        downloaded += 1
                except Exception:
                    pass

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
                for f in tqdm_mod(files, desc="Plotting", unit="plot", dynamic_ncols=True):
                    plot_station(f)

                Console.success(f"Plots generated: {len(files)}")

        except Exception as e:
            Console.warn(f"Plotting failed: {str(e)}")

    # ---------------------------------------------------------
    # Merge
    # ---------------------------------------------------------

    if args.merge:
        from .merge import merge_dataset_folder

        gpkg_path = os.path.join(args.output_dir, "cwc", "cwc_timeseries.gpkg")

        if downloaded == 0 and os.path.exists(gpkg_path):
            Console.info("Using cached GeoPackage for CWC")
        else:
            merge_dataset_folder(base_output, gpkg_path, "cwc_timeseries")

    # ---------------------------------------------------------
    # Summary table (mirrors WRIS format)
    # ---------------------------------------------------------

    runtime = round(_time.time() - dataset_start, 1)

    if downloaded > 0:
        print()
        Console.success(f"water_level downloaded in {runtime} seconds")

    found = downloaded + skipped

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

