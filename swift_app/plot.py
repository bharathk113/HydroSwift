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

    import os
    from pathlib import Path
    from .cli import DATASETS, selected_datasets
    from .plot_station_timeseries import plot_station

    if not args.input_dir:
        raise SystemExit("--plot-only requires input_dir")

    root = Path(args.input_dir)

    if not root.exists():
        raise SystemExit("Input directory not found")

    # ---------------------------------------------------------
    # Dataset folder names
    # ---------------------------------------------------------

    dataset_names = {folder for _, folder in DATASETS.values()}

    # ---------------------------------------------------------
    # Detect basin directories
    # ---------------------------------------------------------

    if any((root / d).is_dir() and d in dataset_names for d in os.listdir(root)):
        basin_dirs = [root]
    else:
        basin_dirs = [d for d in root.iterdir() if d.is_dir()]

    selected = selected_datasets(args)

    print("\nPlot-only mode enabled.")

    total_plots = 0

    # ---------------------------------------------------------
    # CWC plotting
    # ---------------------------------------------------------

    if args.cwc:

        cwc_dir = root / "cwc" / "stations"

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

    for basin_dir in basin_dirs:

        basin = basin_dir.name

        if not selected:

            files = _collect_files(basin_dir)

            if files:
                print(f"\nScanning WRIS basin folder: {basin_dir}")
                print("Stations found:", len(files))

                for file in files:
                    plot_station(file)
                    total_plots += 1

        else:

            for _, folder in selected.items():

                variable_dir = basin_dir / folder

                if not variable_dir.exists():
                    print(f"Dataset '{folder}' not found in basin: {basin}")
                    continue

                files = _collect_files(variable_dir)

                print(f"\nPlotting {basin} / {folder} ({len(files)} stations)")

                for file in files:
                    plot_station(file)
                    total_plots += 1

    if total_plots == 0:
        print("No station files found.")
        return 1

    print("\nPlots generated:", total_plots)

    return 0