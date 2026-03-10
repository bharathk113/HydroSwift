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


def _save_timeseries(args, base_output, folder, meta, station, dataset, df, var_col):
    """Standardize columns and save station timeseries file."""

    station_name = str(meta.get("station_Name", "unknown")).replace("/", "-")
    lat = meta.get("latitude", "")
    lon = meta.get("longitude", "")

    ext = args.format
    filename = f"{station}_{station_name}_{dataset}.{ext}"

    output_path = os.path.join(base_output, folder, filename)

    if os.path.exists(output_path) and not args.overwrite:
        return None

    # Standardize columns
    df = df.copy()
    df["station_code"] = station
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    if "value" in df.columns:
        df.rename(columns={"value": var_col}, inplace=True)

    df["lat"] = lat
    df["lon"] = lon

    # Keep only standardized columns
    out_cols = ["station_code", "time", var_col, "unit", "lat", "lon"]
    out_cols = [c for c in out_cols if c in df.columns]
    df = df[out_cols]

    if args.format == "csv":
        df.to_csv(output_path, index=False)

    elif args.format == "xlsx":
        df.to_excel(output_path, index=False)

    return output_path


def run_download(args, selected: dict[str, str], client, basin_code: str):
    """Run discovery and download workflow for selected datasets."""

    base_output = os.path.join(args.output_dir, args.basin.lower())
    os.makedirs(base_output, exist_ok=True)

    metadata_records: list[dict] = []
    downloaded: list[str] = []
    lock = Lock()

    def worker(station_code: str, dataset_code: str, folder: str, var_col: str):

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
            var_col=var_col,
        )

        if saved_file:
            with lock:
                metadata_records.append(meta)
                downloaded.append(station_code)

    for dataset_code, folder in selected.items():

        from .cli import DATASET_COLUMNS
        var_col = DATASET_COLUMNS.get(dataset_code, "value")

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

        # ---------------------------------------------------------
        # Execution summary
        # ---------------------------------------------------------

        n_stations = len(station_list)

        start_year = str(args.start_date)[:4] if args.start_date else "1950"
        end_year = str(args.end_date)[:4] if args.end_date else "2026"

        fmt = args.format.upper()

        print(
            f"Mode: WRIS download | Basin: {args.basin} | "
            f"Dataset: {folder} | Stations: {n_stations} | "
            f"Format: {fmt} | Time range: {start_year}–{end_year}"
        )

        print("Stations discovered:", n_stations)



        os.makedirs(os.path.join(base_output, folder), exist_ok=True)

        max_workers = min(8, (os.cpu_count() or 1) * 2)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures = [
                executor.submit(worker, station_code, dataset_code, folder, var_col)
                for station_code in station_list
            ]

            for future in tqdm(
                futures,
                total=len(futures),
                desc="Downloading",
                unit="station"
            ):
                future.result()

        if args.merge:

            pattern = "*.csv" if args.format == "csv" else "*.xlsx"

            files = glob.glob(os.path.join(base_output, folder, pattern))

            if files:

                try:
                    gpd_mod = importlib.import_module("geopandas")

                    frames = [
                        pd.read_csv(f) if f.endswith(".csv") else pd.read_excel(f)
                        for f in files
                    ]

                    merged = pd.concat(frames, ignore_index=True)

                    # Convert lat/lon to numeric for geometry
                    merged["lat"] = pd.to_numeric(merged["lat"], errors="coerce")
                    merged["lon"] = pd.to_numeric(merged["lon"], errors="coerce")

                    has_coords = merged["lat"].notna() & merged["lon"].notna()

                    if has_coords.any():
                        gdf = gpd_mod.GeoDataFrame(
                            merged[has_coords],
                            geometry=gpd_mod.points_from_xy(
                                merged.loc[has_coords, "lon"],
                                merged.loc[has_coords, "lat"]
                            ),
                            crs="EPSG:4326",
                        )

                        gpkg_path = os.path.join(
                            base_output, f"{args.basin}_{folder}.gpkg"
                        )

                        gdf.to_file(gpkg_path, layer=folder, driver="GPKG")
                        print(f"Saved GeoPackage: {gpkg_path} ({len(gdf)} rows)")

                    else:
                        print("No coordinates found — skipping GeoPackage")

                except Exception as e:
                    print(f"GeoPackage merge failed: {e}")

    # ---------------------------------------------------------
    # Plotting
    # ---------------------------------------------------------

    if args.plot:

        try:

            from plot_station_timeseries import plot_station  # noqa: top-level script
            from pathlib import Path

            print("\nGenerating hydrographs...")

            files = list(Path(base_output).rglob("*.csv"))
            files.extend(Path(base_output).rglob("*.xlsx"))

            # Exclude metadata files from plotting
            files = [f for f in files if "metadata" not in f.name]

            if not files:
                print("No station files found for plotting")

            else:

                for f in tqdm(files, desc="Plotting", ncols=100):
                    plot_station(f)

                print("Plots generated:", len(files))

        except Exception as e:
            print("Plotting failed:", str(e))

    # ---------------------------------------------------------
    # Metadata export
    # ---------------------------------------------------------

    if metadata_records:

        meta_df = pd.DataFrame(metadata_records)

        cols = [
            "station_Code",
            "station_Name",
            "latitude",
            "longitude",
            "agency_Name",
            "state",
            "independent_river"
        ]

        cols = [c for c in cols if c in meta_df.columns]

        meta_df[cols].rename(
            columns={
                "station_Code": "station_code",
                "station_Name": "station_name",
                "agency_Name": "agency",
                "independent_river": "river"
            }
        ).to_csv(
            os.path.join(base_output, "stations_metadata.csv"),
            index=False
        )

    print(f"\nDownload complete. Files saved to: {base_output}")
    print(f"Stations downloaded: {len(downloaded)}")

    return 0