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

    # ---------------------------------------------------------
    # WRIS basin directory
    # ---------------------------------------------------------

    basin_dir = None
    if args.basin:
        basin_dir = Path(args.output_dir) / args.basin.lower()

    # ---------------------------------------------------------
    # CWC directory
    # ---------------------------------------------------------

    cwc_dir = Path(args.output_dir) / "cwc" / "stations"

    selected_variables = [
        folder_name for key, (_, folder_name) in DATASETS.items()
        if getattr(args, key)
    ]

    print("\nPlot-only mode enabled.")

    total_plots = 0

    # ---------------------------------------------------------
    # CWC plotting
    # ---------------------------------------------------------

    if args.cwc:

        if not cwc_dir.exists():
            print("No CWC output found.")
            return 1

        files = _collect_files(cwc_dir)

        if not files:
            print("No CWC station files found.")
            return 1

        print("\nScanning CWC stations:", len(files))

        for file in files:
            plot_station(file)
            total_plots += 1

        print("\nPlots generated:", total_plots)
        return 0

    # ---------------------------------------------------------
    # WRIS plotting
    # ---------------------------------------------------------

    if basin_dir and basin_dir.exists():

        if not selected_variables:

            files = _collect_files(basin_dir)

            if files:
                print("Scanning WRIS basin folder:", basin_dir)
                print("Stations found:", len(files))

                for file in files:
                    plot_station(file)
                    total_plots += 1

        else:

            for variable in selected_variables:

                variable_dir = basin_dir / variable

                if not variable_dir.exists():
                    continue

                files = _collect_files(variable_dir)

                print(f"Plotting {variable} ({len(files)} stations)")

                for file in files:
                    plot_station(file)
                    total_plots += 1

    if total_plots == 0:
        print("No station files found.")
        return 1

    print("\nPlots generated:", total_plots)

    return 0