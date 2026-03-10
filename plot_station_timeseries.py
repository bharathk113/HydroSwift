#!/usr/bin/env python3

"""
Generate hydrographs from SWIFT output.

Supports:
• WRIS datasets
• CWC gauge datasets
• CSV and XLSX files

Examples
--------

Single station
python plot_station_timeseries.py output/krishna/discharge/station.csv

All stations in folder
python plot_station_timeseries.py output/krishna/discharge/

Entire basin
python plot_station_timeseries.py output/krishna/
"""

import sys
import importlib
import pandas as pd

matplotlib = importlib.import_module("matplotlib")
matplotlib.use("Agg")

plt = importlib.import_module("matplotlib.pyplot")
mdates = importlib.import_module("matplotlib.dates")

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


# ============================================================
# Load SWIFT file robustly
# ============================================================

def load_swift_file(file_path):

    file_path = str(file_path)

    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)

    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)

    else:
        return None

    df.columns = [str(c).strip().lower() for c in df.columns]

    # ------------------------------------------------
    # Normalize column names
    # ------------------------------------------------

    known_vars = ["wse", "q", "wl", "atm", "rf", "temp", "rh", "solar", "sed", "gwl"]
    for var in known_vars:
        if var in df.columns and "value" not in df.columns:
            df["value"] = df[var]
            break

    # WRIS sometimes shifts header row
    if "time" not in df.columns or "value" not in df.columns:

        try:
            df = pd.read_excel(file_path, header=1)
            df.columns = [str(c).strip().lower() for c in df.columns]
        except Exception:
            return None

        if "time" not in df.columns or "value" not in df.columns:
            return None

    cols = [c for c in ["time", "value", "unit"] if c in df.columns]

    return df[cols]


# ============================================================
# Plot single station
# ============================================================

def plot_station(file_path):

    file_path = Path(file_path)

    try:

        df = load_swift_file(file_path)

        if df is None:
            print("Skipping (missing columns):", file_path.name)
            return

        df["time"] = pd.to_datetime(df["time"], errors="coerce")

        df = df.dropna(subset=["time", "value"])
        df = df.drop_duplicates(subset="time")
        df = df.sort_values("time")

        if df.empty:
            print("Skipping (no data):", file_path.name)
            return

        # ----------------------------------------------------
        # Determine dataset type
        # ----------------------------------------------------

        parts = file_path.parts

        if "cwc" in parts:

            dataset = "cwc"
            ylabel = "Water Level (m)"

            out_dir = Path("images") / "cwc"
            prefix = "CWC_"

        else:

            dataset = "wris"

            variable = file_path.parent.name
            basin = file_path.parent.parent.name

            if variable == "discharge":
                ylabel = "Discharge (m³/s)"

            elif variable == "water_level":
                ylabel = "Water Level (m)"

            else:
                ylabel = df["unit"].iloc[0] if "unit" in df.columns else "Value"

            out_dir = Path("images") / "wris" / basin / variable
            prefix = ""

        # ----------------------------------------------------
        # Plot hydrograph
        # ----------------------------------------------------

        fig, ax = plt.subplots(figsize=(12, 4.5))

        ax.plot(
            df["time"],
            df["value"],
            color="#1f4e79",
            linewidth=1.8
        )

        ax.set_xlabel("Year")
        ax.set_ylabel(ylabel)

        title = file_path.stem.replace("_", " ")

        ax.set_title(title)

        ax.grid(
            True,
            linestyle="--",
            linewidth=0.5,
            alpha=0.6
        )

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.xaxis.set_major_locator(mdates.YearLocator(5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        ax.set_xlim(df["time"].min(), df["time"].max())

        fig.tight_layout()

        # ----------------------------------------------------
        # Output
        # ----------------------------------------------------

        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"{prefix}{file_path.stem}.png"

        fig.savefig(out_file, dpi=300)

        plt.close(fig)

        print("Saved:", out_file)

    except Exception as e:

        print("Failed:", file_path.name, "|", str(e))


# ============================================================
# Collect files
# ============================================================

def collect_files(input_path):

    input_path = Path(input_path)

    if input_path.is_file():
        return [input_path]

    files = list(input_path.rglob("*.csv"))
    files.extend(input_path.rglob("*.xlsx"))

    return files


# ============================================================
# Main
# ============================================================

def main():

    if len(sys.argv) < 2:
        print("\nUsage:")
        print("python plot_station_timeseries.py <file | folder>\n")
        sys.exit()

    input_path = sys.argv[1]

    files = collect_files(input_path)

    if not files:
        print("No station files found.")
        return

    print("Stations found:", len(files))

    workers = min(8, len(files))

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(plot_station, files))


if __name__ == "__main__":
    main()