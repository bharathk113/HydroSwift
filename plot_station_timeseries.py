#!/usr/bin/env python3

"""
Generate hydrographs from SWIFT output.

Supports:
• single station
• variable folder
• basin folder

Examples
--------

Single station
python plot_station_timeseries.py output/krishna/discharge/station.xlsx

All discharge stations
python plot_station_timeseries.py output/krishna/discharge/

Entire basin
python plot_station_timeseries.py output/krishna/
"""

import sys
import importlib
import pandas as pd

matplotlib = importlib.import_module("matplotlib")

# use non-GUI backend
matplotlib.use("Agg")

plt = importlib.import_module("matplotlib.pyplot")
mdates = importlib.import_module("matplotlib.dates")
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


# ============================================================
# Load SWIFT Excel robustly
# ============================================================

def load_swift_file(file_path):

    if str(file_path).endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    df.columns = [str(c).strip().lower() for c in df.columns]

    # WRIS sometimes shifts header row
    if "time" not in df.columns or "value" not in df.columns:

        df = pd.read_excel(file_path, header=1)
        df.columns = [str(c).strip().lower() for c in df.columns]

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

        variable = file_path.parent.name
        basin = file_path.parent.parent.name

        df = load_swift_excel(file_path)

        if df is None:
            print("Skipping (missing columns):", file_path.name)
            return

        # parse timestamps
        df["time"] = pd.to_datetime(df["time"], errors="coerce")

        df = df.dropna(subset=["time", "value"])

        # remove duplicates
        df = df.drop_duplicates(subset="time")

        # critical: sort chronologically
        df = df.sort_values("time")

        if df.empty:
            print("Skipping (no data):", file_path.name)
            return

        # -------------------------
        # Determine label
        # -------------------------

        if variable == "discharge":
            ylabel = "Discharge (m³/s)"

        elif variable == "water_level":
            ylabel = "Water Level"

        else:
            ylabel = df["unit"].iloc[0] if "unit" in df.columns else "Value"

        # -------------------------
        # Hydrograph plot
        # -------------------------

        fig, ax = plt.subplots(figsize=(12,4.5))

        ax.plot(
            df["time"],
            df["value"],
            color="#1f4e79",
            linewidth=1.8
        )

        ax.set_xlabel("Year")
        ax.set_ylabel(ylabel)

        ax.set_title(file_path.stem.replace("_"," "))

        ax.grid(
            True,
            linestyle="--",
            linewidth=0.5,
            alpha=0.6
        )

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # year ticks
        ax.xaxis.set_major_locator(mdates.YearLocator(5))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        ax.set_xlim(df["time"].min(), df["time"].max())

        fig.tight_layout()

        # -------------------------
        # Output directory
        # -------------------------

        out_dir = Path("images") / basin / variable
        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / (file_path.stem + ".png")

        fig.savefig(str(out_file), dpi=300)

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

    return list(input_path.rglob("*.xlsx"))


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