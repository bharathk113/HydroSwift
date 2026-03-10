"""Plot helpers for SWIFT."""

from __future__ import annotations

import os
from pathlib import Path

from .cli import DATASETS


def _collect_files(path: Path):
    """Collect CSV and XLSX station files recursively."""
    files = list(path.rglob("*.csv"))
    files.extend(path.rglob("*.xlsx"))
    return files


def run_plot_only(args) -> int:
    """Generate plots from existing SWIFT output folders without downloading."""

    from plot_station_timeseries import plot_station

    basin_dir = Path(args.output_dir) / args.basin.lower()

    if not basin_dir.exists():
        print(f"No SWIFT output found for basin: {args.basin}")
        return 1

    selected_variables = [
        folder_name for key, (_, folder_name) in DATASETS.items()
        if getattr(args, key)
    ]

    # ---------------------------------------------------------
    # Plot entire basin
    # ---------------------------------------------------------

    if not selected_variables:

        print("\nPlot-only mode enabled.")
        print("Scanning basin folder:", basin_dir)

        files = _collect_files(basin_dir)

        if not files:
            print("No station files found.")
            return 1

        print("Stations found:", len(files))

        for file in files:
            plot_station(file)

        return 0

    # ---------------------------------------------------------
    # Plot selected datasets only
    # ---------------------------------------------------------

    print("\nPlot-only mode enabled.")

    for variable in selected_variables:

        variable_dir = basin_dir / variable

        if not os.path.exists(variable_dir):
            print(f"No data found for: {variable}")
            continue

        files = _collect_files(variable_dir)

        if not files:
            print(f"No station files found for: {variable}")
            continue

        print(f"Plotting {variable} ({len(files)} stations)")

        for file in files:
            plot_station(file)

    return 0