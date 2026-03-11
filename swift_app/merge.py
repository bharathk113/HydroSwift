from __future__ import annotations

import glob
import os
import pandas as pd
import importlib


def merge_dataset_folder(dataset_dir: str, gpkg_path: str, layer: str):

    files = glob.glob(os.path.join(dataset_dir, "*.csv"))
    files += glob.glob(os.path.join(dataset_dir, "*.xlsx"))

    if not files:
        print("No station files found:", dataset_dir)
        return 0

    frames = []

    for f in files:
        try:
            df = pd.read_csv(f) if f.endswith(".csv") else pd.read_excel(f)

            if {"lat", "lon"}.issubset(df.columns):
                frames.append(df)

        except Exception:
            continue

    if not frames:
        print("No valid station files with coordinates.")
        return 0

    merged = pd.concat(frames, ignore_index=True)

    merged["lat"] = pd.to_numeric(merged["lat"], errors="coerce")
    merged["lon"] = pd.to_numeric(merged["lon"], errors="coerce")

    mask = merged["lat"].notna() & merged["lon"].notna()

    gpd = importlib.import_module("geopandas")

    gdf = gpd.GeoDataFrame(
        merged[mask],
        geometry=gpd.points_from_xy(
            merged.loc[mask, "lon"],
            merged.loc[mask, "lat"]
        ),
        crs="EPSG:4326"
    )

    rows = len(gdf)

    gdf.to_file(gpkg_path, layer=layer, driver="GPKG")

    print(f"Saved GeoPackage: {gpkg_path} ({rows} rows)")

    return rows

   
def run_merge_only(args):

    from .cli import selected_datasets
    from .merge import merge_dataset_folder

    selected = selected_datasets(args)

    if not selected:
        raise SystemExit("Specify dataset flag(s) to merge")

    base = os.path.join(args.output_dir, args.basin.lower())

    for _, folder in selected.items():

        dataset_dir = os.path.join(base, folder)

        gpkg_path = os.path.join(
            base,
            f"{args.basin}_{folder}.gpkg"
        )

        merge_dataset_folder(dataset_dir, gpkg_path, folder)

    return 0