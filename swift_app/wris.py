"""WRIS download pipeline for SWIFT."""

from __future__ import annotations

import glob
import importlib
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pandas as pd

from .utils import Console, Logger


try:
    tqdm = importlib.import_module("tqdm").tqdm
except Exception:
    def tqdm(iterable, **_kwargs):
        return iterable

# ---------------------------------------------------------
# Metadata builder (WRIS + CWC compatible)
# ---------------------------------------------------------
def build_metadata(meta, dataset, source):

    md = {
        "source": source,
        "dataset": dataset,
        "station_code": meta.get("station_code"),
        "station_name": meta.get("station_Name") or meta.get("station_name"),
        "latitude": meta.get("latitude") or meta.get("lat"),
        "longitude": meta.get("longitude") or meta.get("lon"),
        "river": meta.get("riverName") or meta.get("river"),
    }

    if source == "WRIS":
        md["agency"] = meta.get("agencyName")

    if source == "CWC":
        md["rl_zero"] = meta.get("rl_zero")
        md["warning_level"] = meta.get("warning_level")
        md["danger_level"] = meta.get("danger_level")
        md["hfl"] = meta.get("hfl")

    return md




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

    # ---------------------------------------------------------
    # Standardize dataframe
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Determine source and build metadata
    # ---------------------------------------------------------

    source = "CWC" if getattr(args, "cwc", False) else "WRIS"

    meta_dict = build_metadata(meta, dataset, source)

    meta_dict["station_code"] = station

    # ---------------------------------------------------------
    # CSV Output
    # ---------------------------------------------------------

    if args.format == "csv":

        header_lines = ["# SWIFT Hydrological Timeseries"]

        for key, value in meta_dict.items():
            if value is not None and value != "":
                header_lines.append(f"# {key}: {value}")

        with open(output_path, "w") as f:
            for line in header_lines:
                f.write(line + "\n")

        df.to_csv(output_path, mode="a", index=False)

    # ---------------------------------------------------------
    # Excel Output
    # ---------------------------------------------------------

    else:

        meta_df = pd.DataFrame(
            [{"field": k, "value": v} for k, v in meta_dict.items() if v is not None]
        )

        with pd.ExcelWriter(output_path) as writer:
            df.to_excel(writer, sheet_name="timeseries", index=False)
            meta_df.to_excel(writer, sheet_name="metadata", index=False)

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

def run_wris_download(args, selected: dict[str, str], client, basin_code: str):

    import json

    base_output = os.path.join(args.output_dir, args.basin.lower())
    os.makedirs(base_output, exist_ok=True)
    
    Console.is_quiet = getattr(args, "quiet", False)
    logger = Logger(base_output)
    
    logger.log("INFO", f"Starting WRIS download for basin: {args.basin}")

    metadata_records = {}
    metadata_cache = {}
    summary = []
    lock = Lock()

    # ---------------------------------------------------------
    # Basin structure cache (in-memory)
    # ---------------------------------------------------------

    if not hasattr(client, "_basin_structure_cache"):
        client._basin_structure_cache = {}

    if basin_code not in client._basin_structure_cache:
        client._basin_structure_cache[basin_code] = build_basin_structure(client, basin_code)

    basin_structure = client._basin_structure_cache[basin_code]

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

    # ---------------------------------------------------------
    # Estimate total runtime across all datasets
    # ---------------------------------------------------------

    total_stations = 0
    station_filter = getattr(args, "stations", None)
    if station_filter:
        station_filter = {str(s) for s in station_filter}

    for dataset_code in selected.keys():

        if dataset_code in basin_station_cache:
            stations = list(basin_station_cache[dataset_code])
        else:
            stations = discover_stations(
                client,
                basin_structure,
                dataset_code,
                agency_cache,
                station_cache
            )
            basin_station_cache[dataset_code] = stations
            cache_updated = True

        stations_for_run = stations
        if station_filter:
            stations_for_run = [s for s in stations if s in station_filter]

        total_stations += len(stations_for_run)

    workers = min(8, (os.cpu_count() or 1) * 2)
    est_runtime = int(total_stations * args.delay / max(workers, 1))

    if est_runtime > 600 and not Console.is_quiet:
        mins = est_runtime // 60
        Console.info(f"Estimated total runtime: ~{mins} minutes ({total_stations} stations)")
        print(f"{Console.ITALIC}Tip: enable --coffee mode for long runs ☕{Console.RESET}")

    for dataset_code, folder in selected.items():

        from .cli import DATASET_COLUMNS
        from .merge import merge_dataset_folder

        var_col = DATASET_COLUMNS.get(dataset_code, "value")

        Console.section(f"Dataset: {folder}")
        logger.log("INFO", f"Processing dataset: {folder}")

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
            logger.log("INFO", f"Discovered {len(stations)} stations from WRIS API")

        stations_for_run = stations
        if station_filter:
            stations_for_run = [s for s in stations if s in station_filter]

        dataset_dir = os.path.join(base_output, folder)
        os.makedirs(dataset_dir, exist_ok=True)

        ext = args.format.lower()

        if args.overwrite:
            station_list = stations_for_run
        else:
            station_list = filter_existing_stations(stations_for_run, dataset_dir, ext)

        remaining = len(station_list)
        skipped = 0 if args.overwrite else len(stations_for_run) - remaining


        if skipped > 0:
            Console.warn(f"Stations skipped (already downloaded): {skipped}")
            if not Console.is_quiet:
                print(f"{Console.ITALIC}Tip: use --overwrite to refresh data.{Console.RESET}")
            logger.log("INFO", f"Skipped {skipped} existing stations")

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
                    logger.log("WARN", f"No metadata found for station: {station_code}")
                    return
                metadata_cache[station_code] = meta

            frame = client.get_timeseries(
                station_code,
                dataset_code,
                start_date=args.start_date,
                end_date=args.end_date,
            )

            if frame is None or frame.empty:
                logger.log("WARN", f"No data returned for station: {station_code}")
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
                logger.log("SUCCESS", f"Downloaded {station_code} -> {os.path.basename(outfile)}")

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
                    dynamic_ncols=True,
                    disable=Console.is_quiet
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
                logger.log("INFO", f"Merging {folder} to GeoPackage")
                merge_dataset_folder(dataset_dir, gpkg_path, folder)

        runtime = round(time.time() - dataset_start, 1)

        if counter["downloaded"] > 0:
            if not Console.is_quiet:
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
        
        logger.log("INFO", f"Finished {folder}: Downloaded {counter['downloaded']}, Skipped {skipped} in {runtime}s")

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

    if not Console.is_quiet:
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