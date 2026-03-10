"""Download pipeline for SWIFT."""

from __future__ import annotations

import glob
import importlib
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pandas as pd

try:
    tqdm = importlib.import_module("tqdm").tqdm
except Exception:
    def tqdm(iterable, **_kwargs):
        return iterable


def _save_timeseries(args, base_output, folder, meta, station, dataset, df):

    station_name = str(meta.get("station_Name", "unknown")).replace("/", "-")

    ext = args.format
    filename = f"{station}_{station_name}_{dataset}.{ext}"

    output_path = os.path.join(base_output, folder, filename)

    if os.path.exists(output_path) and not args.overwrite:
        return None

    if args.format == "csv":
        df.to_csv(output_path, index=False)

    elif args.format == "xlsx":
        df.to_excel(output_path, index=False)

    if args.plot:
        from plot_station_timeseries import plot_station
        plot_station(output_path)

    return output_path


def run_download(args, selected: dict[str, str], client, basin_code: str):
    """Run discovery and download workflow for selected datasets."""
    base_output = os.path.join(args.output_dir, args.basin.lower())
    os.makedirs(base_output, exist_ok=True)

    metadata_records: list[dict] = []
    downloaded: list[str] = []
    lock = Lock()

    def worker(station_code: str, dataset_code: str, folder: str):
        meta = client.get_metadata(station_code, dataset_code)
        if not meta:
            return

        frame = client.get_timeseries(
            station_code,
            dataset_code,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        if frame is None:
            return

        saved_file = _save_timeseries(
            args=args,
            base_output=base_output,
            folder=folder,
            meta=meta,
            station=station_code,
            dataset=dataset_code,
            df=frame,
        )

        if saved_file:
            with lock:
                metadata_records.append(meta)
                downloaded.append(station_code)

    for dataset_code, folder in selected.items():
        print(f"\nDataset: {folder}")

        stations: set[str] = set()
        tributaries = client.get_tributaries(basin_code, dataset_code)
        for tributary in tributaries:
            tributary_id = tributary.get("tributaryid")
            rivers = client.get_rivers(tributary_id, dataset_code)
            for river in rivers:
                river_id = river.get("localriverid")
                agencies = client.get_agencies(tributary_id, river_id, dataset_code)
                for agency in agencies:
                    agency_id = agency.get("agencyid")
                    station_items = client.get_stations(
                        tributary_id, river_id, agency_id, dataset_code
                    )
                    for station in station_items:
                        station_code = station.get("stationcode")
                        if station_code:
                            stations.add(station_code)

        station_list = sorted(stations)
        print("Stations discovered:", len(station_list))

        if args.stations:
            pd.DataFrame({"station": station_list}).to_csv(
                os.path.join(base_output, "stations.csv"), index=False
            )

        os.makedirs(os.path.join(base_output, folder), exist_ok=True)
        max_workers = min(8, (os.cpu_count() or 1) * 2)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(worker, station_code, dataset_code, folder)
                for station_code in station_list
            ]
            for future in tqdm(
                futures, total=len(futures), desc="Downloading", unit="station"
            ):
                future.result()

        if args.merge:
            pattern = "*.csv" if args.format == "csv" else "*.xlsx"
            files = glob.glob(os.path.join(base_output, folder, pattern))
            if files:
                frames = [
                    pd.read_csv(f) if f.endswith(".csv") else pd.read_excel(f)
                    for f in files
                ]
                merged = pd.concat(frames, ignore_index=True)
                merged.to_parquet(
                    os.path.join(base_output, f"{args.basin}_{folder}.parquet")
                )

    if args.metadata and metadata_records:
        pd.DataFrame(metadata_records).to_csv(
            os.path.join(base_output, "stations_metadata.csv"), index=False
        )

    if args.geopackage and metadata_records:
        gpd = importlib.import_module("geopandas")

        metadata_df = pd.DataFrame(metadata_records)
        gdf = gpd.GeoDataFrame(
            metadata_df,
            geometry=gpd.points_from_xy(metadata_df["longitude"], metadata_df["latitude"]),
            crs="EPSG:4326",
        )
        gdf.to_file(os.path.join(base_output, "stations.gpkg"), driver="GPKG")

    return {
        "base_output": base_output,
        "downloaded_count": len(downloaded),
    }
