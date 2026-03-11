"""Download pipeline for SWIFT."""

from __future__ import annotations

import glob
import importlib
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pandas as pd


# ---------------------------------------------------------
# SWIFT Console Styling
# ---------------------------------------------------------

class Console:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"

    @staticmethod
    def section(title):
        print(f"\n{Console.MAGENTA}{Console.BOLD}{title}{Console.RESET}")

    @staticmethod
    def warn(msg):
        print(f"{Console.YELLOW}{Console.BOLD}{msg}{Console.RESET}")

    @staticmethod
    def info(msg):
        print(f"{Console.CYAN}{msg}{Console.RESET}")

    @staticmethod
    def success(msg):
        print(f"{Console.GREEN}{Console.BOLD}{msg}{Console.RESET}")


try:
    tqdm = importlib.import_module("tqdm").tqdm
except Exception:
    def tqdm(iterable, **_kwargs):
        return iterable


# ---------------------------------------------------------
# Save station timeseries
# ---------------------------------------------------------

def _save_timeseries(args, base_output, folder, meta, station, dataset, df, var_col):

    station_name = str(meta.get("station_Name", "unknown")).replace("/", "-")
    lat = meta.get("latitude", "")
    lon = meta.get("longitude", "")

    ext = args.format.lower()
    filename = f"{station}_{station_name}_{dataset}.{ext}"

    output_path = os.path.join(base_output, folder, filename)

    if os.path.exists(output_path) and not args.overwrite:
        return None

    df = df.copy()
    df["station_code"] = station
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    if "value" in df.columns:
        df.rename(columns={"value": var_col}, inplace=True)

    df["lat"] = lat
    df["lon"] = lon

    cols = ["station_code", "time", var_col, "unit", "lat", "lon"]
    cols = [c for c in cols if c in df.columns]
    df = df[cols]

    if args.format == "csv":
        df.to_csv(output_path, index=False)
    else:
        df.to_excel(output_path, index=False)

    return output_path


# ---------------------------------------------------------
# Basin structure cache
# ---------------------------------------------------------

def build_basin_structure(client, basin_code):

    structure = []

    tributaries = client.get_tributaries(basin_code, "DISCHARG")

    for trib in tributaries:

        trib_id = trib.get("tributaryid")
        rivers = client.get_rivers(trib_id, "DISCHARG")

        for river in rivers:
            structure.append((trib_id, river.get("localriverid")))

    return structure


# ---------------------------------------------------------
# Station discovery
# ---------------------------------------------------------

def discover_stations(client, basin_structure, dataset_code, agency_cache, station_cache):

    stations = set()

    for tributary_id, river_id in basin_structure:

        key = (tributary_id, river_id, dataset_code)

        if key not in agency_cache:
            agency_cache[key] = client.get_agencies(
                tributary_id, river_id, dataset_code
            )

        for agency in agency_cache[key]:

            agency_id = agency.get("agencyid")

            key = (tributary_id, river_id, agency_id)

            if key in station_cache:
                items = station_cache[key]
            else:
                items = client.get_stations(
                    tributary_id,
                    river_id,
                    agency_id,
                    dataset_code
                )
                station_cache[key] = items

            for s in items:
                code = s.get("stationcode")
                if code:
                    stations.add(code)

    return sorted(stations)


# ---------------------------------------------------------
# Resume filter
# ---------------------------------------------------------

def filter_existing_stations(stations, dataset_dir, ext):

    remaining = []

    for s in stations:
        pattern = os.path.join(dataset_dir, f"{s}_*.{ext}")
        if not glob.glob(pattern):
            remaining.append(s)

    return remaining


# ---------------------------------------------------------
# Main download engine
# ---------------------------------------------------------

def run_download(args, selected: dict[str, str], client, basin_code: str):

    import json

    base_output = os.path.join(args.output_dir, args.basin.lower())
    os.makedirs(base_output, exist_ok=True)

    metadata_records = {}
    metadata_cache = {}
    summary = []
    lock = Lock()

    basin_structure = build_basin_structure(client, basin_code)
    agency_cache = {}
    station_cache = {}

    # ---------------------------------------------------------
    # Basin station cache (disk)
    # ---------------------------------------------------------

    cache_file = os.path.join(base_output, "_station_tree.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                basin_station_cache = json.load(f)
        except Exception:
            basin_station_cache = {}
    else:
        basin_station_cache = {}

    cache_updated = False

    for dataset_code, folder in selected.items():

        from .cli import DATASET_COLUMNS
        from .merge import merge_dataset_folder

        var_col = DATASET_COLUMNS.get(dataset_code, "value")

        Console.section(f"Dataset: {folder}")

        dataset_start = time.time()

        # ---------------------------------------------------------
        # Station discovery with disk cache
        # ---------------------------------------------------------

        if dataset_code in basin_station_cache:

            stations = list(basin_station_cache[dataset_code])
            Console.info("Using cached station discovery")

        else:

            stations = discover_stations(
                client,
                basin_structure,
                dataset_code,
                agency_cache, station_cache
            )

            basin_station_cache[dataset_code] = stations
            cache_updated = True

        dataset_dir = os.path.join(base_output, folder)
        os.makedirs(dataset_dir, exist_ok=True)

        ext = args.format.lower()

        if args.overwrite:
            station_list = stations
        else:
            station_list = filter_existing_stations(stations, dataset_dir, ext)

        remaining = len(station_list)
        skipped = 0 if args.overwrite else len(stations) - remaining


        if skipped > 0:
            Console.warn(f"Stations skipped (already downloaded): {skipped}")
            print(f"{Console.ITALIC}Tip: use --overwrite to refresh data.{Console.RESET}")

        counter = {"downloaded": 0}

        # ---------------------------------------------------------
        # Worker
        # ---------------------------------------------------------

        def worker(station_code):

            if station_code in metadata_cache:
                meta = metadata_cache[station_code]
            else:
                meta = client.get_metadata(station_code, dataset_code)
                if not meta:
                    return
                metadata_cache[station_code] = meta

            frame = client.get_timeseries(
                station_code,
                dataset_code,
                start_date=args.start_date,
                end_date=args.end_date,
            )

            if frame is None or frame.empty:
                return

            outfile = _save_timeseries(
                args,
                base_output,
                folder,
                meta,
                station_code,
                dataset_code,
                frame,
                var_col,
            )

            if outfile:
                with lock:
                    metadata_records[station_code] = meta
                    counter["downloaded"] += 1

        # ---------------------------------------------------------
        # Parallel download
        # ---------------------------------------------------------

        if remaining > 0:

            max_workers = min(8, (os.cpu_count() or 1) * 2)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:

                futures = [executor.submit(worker, s) for s in station_list]

                for f in tqdm(
                    futures,
                    total=len(futures),
                    desc=f"{folder}",
                    unit="station",
                    leave=True,
                    dynamic_ncols=True
                ):
                    f.result()

        else:
            Console.info("All stations already downloaded — skipping download step.")

        # ---------------------------------------------------------
        # Merge
        # ---------------------------------------------------------

        if args.merge:

            gpkg_path = os.path.join(base_output, f"{args.basin}_{folder}.gpkg")

            if counter["downloaded"] == 0 and os.path.exists(gpkg_path):
                Console.info(f"Using cached GeoPackage for {folder}")
            else:
                merge_dataset_folder(dataset_dir, gpkg_path, folder)

        runtime = round(time.time() - dataset_start, 1)

        if counter["downloaded"] > 0:
            print()
            Console.success(f"{folder} downloaded in {runtime} seconds")

        found = counter["downloaded"] + skipped

        summary.append({
            "dataset": folder,
            "found": found,
            "downloaded": counter["downloaded"],
            "skipped": skipped,
            "time": runtime
        })

    # ---------------------------------------------------------
    # Save updated station cache
    # ---------------------------------------------------------

    if cache_updated:
        try:
            with open(cache_file, "w") as f:
                json.dump(basin_station_cache, f)
        except Exception:
            pass

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    print("\n-------------------------------------------------------------")
    print("Download Summary")
    print("-------------------------------------------------------------")
    print(f"{'Dataset':<18}{'Found':<12}{'Downloaded':<12}{'Skipped':<12}{'Time(s)'}")
    print("-------------------------------------------------------------")

    for item in summary:
        print(
            f"{item['dataset']:<18}"
            f"{item['found']:<12}"
            f"{item['downloaded']:<12}"
            f"{item['skipped']:<12}"
            f"{item['time']}"
        )

    print("-------------------------------------------------------------")
    print(f"Output directory: {base_output}")
    print("-------------------------------------------------------------")