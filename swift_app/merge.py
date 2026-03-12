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

    import os
    from pathlib import Path
    from .cli import DATASETS, selected_datasets
    from .merge import merge_dataset_folder

    if not args.input_dir:
        raise SystemExit("--merge-only requires input_dir")

    root = Path(args.input_dir)

    if not root.exists():
        raise SystemExit("Input directory not found")

    dataset_names = {folder for _, folder in DATASETS.values()}

    # ---------------------------------------------------------
    # Detect basin directories
    # ---------------------------------------------------------

    if any((root / d).is_dir() and d in dataset_names for d in os.listdir(root)):
        basin_dirs = [root]
    else:
        basin_dirs = [d for d in root.iterdir() if d.is_dir()]

    selected = selected_datasets(args)

    output_base = Path(args.output_dir) if args.output_dir else root
    output_base.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # Merge datasets
    # ---------------------------------------------------------

    for basin_dir in basin_dirs:

        basin = basin_dir.name

        if not selected:
            dataset_dirs = [
                d for d in basin_dir.iterdir()
                if d.is_dir()
            ]
        else:
            dataset_dirs = [
                basin_dir / folder
                for _, folder in selected.items()
            ]

        for d in dataset_dirs:

            if not d.exists():
                if selected:
                    print(f"Dataset '{d.name}' not found in basin: {basin}")
                continue

            gpkg_path = output_base / f"{basin}_{d.name}.gpkg"

            merge_dataset_folder(str(d), str(gpkg_path), d.name)

    return 0