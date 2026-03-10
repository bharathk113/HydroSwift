"""
CWC Flood Forecasting Station downloader for SWIFT
"""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------
# HTTP session (connection reuse)
# ---------------------------------------------------------

session = requests.Session()

CWC_API = "https://ffs.india-water.gov.in/iam/api/new-entry-data/specification/sorted"


# ---------------------------------------------------------
# Load station table
# ---------------------------------------------------------

def load_station_table():

    station_file = Path(__file__).parent / "cwc_stations.csv"
    location_file = Path(__file__).parent / "station_locations.csv"

    if not station_file.exists():
        raise RuntimeError("CWC station file missing")

    df = pd.read_csv(station_file)
    df.columns = [c.lower().strip() for c in df.columns]

    # ---------------------------------------------------------
    # Load station locations if available
    # ---------------------------------------------------------

    if location_file.exists():

        loc = pd.read_csv(location_file)
        loc.columns = [c.lower().strip() for c in loc.columns]

        # normalize names for matching
        df["name"] = (
            df["name"]
            .astype(str)
            .str.lower()
            .str.replace(r"\(.*?\)", "", regex=True)
            .str.strip()
        )

        loc["name"] = (
            loc["name"]
            .astype(str)
            .str.lower()
            .str.replace(r"\(.*?\)", "", regex=True)
            .str.strip()
        )

        # merge coordinates
        df = df.merge(
            loc[["name", "lat", "lon"]],
            on="name",
            how="left"
        )

    else:
        print("Warning: station_locations.csv not found; Skipping lat/lon entries.")

    return df


# ---------------------------------------------------------
# Fetch CWC station data
# ---------------------------------------------------------

def fetch_station_data(code, retries=2):

    params = {
        "sort-criteria": "%7B%22sortOrderDtos%22:%5B%7B%22sortDirection%22:%22ASC%22,%22field%22:%22id.dataTime%22%7D%5D%7D",
        "specification": (
            "%7B%22where%22:%7B%22expression%22:%7B"
            f"%22fieldName%22:%22id.stationCode%22,%22operator%22:%22eq%22,%22value%22:%22{code}%22"
            "%7D%7D%7D"
        )
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    for _ in range(retries):

        try:

            r = session.get(
                CWC_API,
                params=params,
                headers=headers,
                timeout=120
            )

            if r.status_code != 200:
                return None

            data = r.json()

            if not isinstance(data, list):
                return None

            rows = []

            for j in data:
                try:
                    rows.append([
                        j["stationCode"],
                        j["id"]["dataTime"],
                        j["dataValue"]
                    ])
                except Exception:
                    pass

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=["station_code", "time", "wse"])

            df["time"] = pd.to_datetime(df["time"])

            return df

        except Exception:
            pass

    return None


# ---------------------------------------------------------
# Worker function for parallel downloads
# ---------------------------------------------------------

def download_station(station, output_dir, args):

    code = str(station["code"]).strip()
    name = str(station["name"]).strip()

    lat = station.get("lat")
    lon = station.get("lon")

    safe_name = (
        name.replace("/", "-")
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )

    ext = args.format

    outfile = os.path.join(
        output_dir,
        f"{code}_{safe_name}.{ext}"
    )

    # ---------------------------------------------------------
    # Skip existing file unless overwrite
    # ---------------------------------------------------------

    if os.path.exists(outfile) and not args.overwrite:
        return "skipped"

    # ---------------------------------------------------------
    # Fetch data
    # ---------------------------------------------------------

    df = fetch_station_data(code)

    if df is None or df.empty:
        return False

    # ---------------------------------------------------------
    # Parse timestamps
    # ---------------------------------------------------------

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    # ---------------------------------------------------------
    # Date filtering
    # ---------------------------------------------------------

    try:

        if args.start_date:
            start = pd.to_datetime(args.start_date)
            df = df[df["time"] >= start]

        if args.end_date:
            end = pd.to_datetime(args.end_date)
            df = df[df["time"] <= end]

    except Exception:
        pass

    if df.empty:
        return False

    # ---------------------------------------------------------
    # Attach station metadata
    # ---------------------------------------------------------

    df["station_name"] = name
    df["unit"] = "m"
    df["lat"] = lat
    df["lon"] = lon

    cols = ["station_code", "time", "wse", "unit", "lat", "lon"]
    df = df[[c for c in cols if c in df.columns]]

    # ---------------------------------------------------------
    # Save file
    # ---------------------------------------------------------

    try:

        if args.format == "csv":
            df.to_csv(outfile, index=False)

        elif args.format == "xlsx":
            df.to_excel(outfile, index=False)

    except Exception:
        return False

    return True

# ---------------------------------------------------------
# Main CWC downloader
# ---------------------------------------------------------

def run_cwc_download(args):

    from pathlib import Path
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm

    print("\nCWC downloader starting...")

    base_output = os.path.join(
        args.output_dir,
        "cwc",
        "stations"
    )

    os.makedirs(base_output, exist_ok=True)

    print("Output directory:", base_output)

    stations = load_station_table()

    # ---------------------------------------------------------
    # Station filter
    # ---------------------------------------------------------

    if args.cwc_station:

        stations = stations[
            stations["code"].isin(args.cwc_station)
        ]

        if stations.empty:
            raise SystemExit("No matching CWC stations found")

    # ---------------------------------------------------------
    # Execution summary
    # ---------------------------------------------------------

    n_stations = len(stations)

    start_year = str(args.start_date)[:4] if args.start_date else "1950"
    end_year = str(args.end_date)[:4] if args.end_date else "2026"

    fmt = args.format.upper()

    print(
        f"Mode: CWC download | Stations: {n_stations} | "
        f"Format: {fmt} | Time range: {start_year}–{end_year}"
    )

    print("Total stations available:", n_stations)

    downloaded = 0
    skipped = 0
    workers = 4

    # ---------------------------------------------------------
    # Parallel downloads
    # ---------------------------------------------------------

    with ThreadPoolExecutor(max_workers=workers) as executor:

        futures = [
            executor.submit(download_station, station, base_output, args)
            for _, station in stations.iterrows()
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Downloading CWC station data",
            ncols=100
        ):

            try:
                result = future.result()

                if result is True:
                    downloaded += 1

                elif result == "skipped":
                    skipped += 1

            except Exception:
                pass

    # ---------------------------------------------------------
    # Plotting
    # ---------------------------------------------------------

    if args.plot:

        try:

            from plot_station_timeseries import plot_station

            print("\nGenerating hydrographs...")

            files = list(Path(base_output).glob("*.csv"))
            files.extend(Path(base_output).glob("*.xlsx"))

            if not files:
                print("No station files found for plotting")

            else:

                for f in tqdm(files, desc="Plotting", ncols=100):
                    plot_station(f)

                print("Plots generated:", len(files))

        except Exception as e:
            print("Plotting failed:", str(e))

    if args.merge:

        try:

            import geopandas as gpd

            print("\nMerging CWC stations into GeoPackage...")

            files = list(Path(base_output).glob("*.csv"))
            files.extend(Path(base_output).glob("*.xlsx"))

            if not files:
                print("No station files found for merging")

            else:

                frames = []

                for f in files:

                    try:

                        if f.suffix == ".csv":
                            df = pd.read_csv(f)
                        else:
                            df = pd.read_excel(f)

                        # Only merge files that have lat/lon for geometry
                        if {"lat", "lon"}.issubset(df.columns):
                            frames.append(df)

                    except Exception:
                        continue

                if frames:

                    data = pd.concat(frames, ignore_index=True)

                    data["time"] = pd.to_datetime(
                        data["time"],
                        errors="coerce"
                    )

                    data["lat"] = pd.to_numeric(data["lat"], errors="coerce")
                    data["lon"] = pd.to_numeric(data["lon"], errors="coerce")

                    has_coords = data["lat"].notna() & data["lon"].notna()

                    if has_coords.any():

                        gdf = gpd.GeoDataFrame(
                            data[has_coords],
                            geometry=gpd.points_from_xy(
                                data.loc[has_coords, "lon"],
                                data.loc[has_coords, "lat"]
                            ),
                            crs="EPSG:4326"
                        )

                        gpkg_path = os.path.join(
                            args.output_dir,
                            "cwc",
                            "cwc_timeseries.gpkg"
                        )

                        gdf.to_file(
                            gpkg_path,
                            layer="cwc_timeseries",
                            driver="GPKG"
                        )

                        print(f"Saved merged GeoPackage: {gpkg_path} ({len(gdf)} rows)")

                    else:
                        print("No valid coordinates found — skipping GeoPackage merge")

        except Exception as e:
            print("GeoPackage merge failed:", str(e))

    # ---------------------------------------------------------
    # Final summary
    # ---------------------------------------------------------

    print(
f"""
----------------------------------------------------
Done!
----------------------------------------------------
Dataset: CWC gauges
Stations processed: {n_stations}
Downloaded: {downloaded}
Skipped (already exist): {skipped}
Output directory: {base_output}
----------------------------------------------------
"""
    )

    if skipped and not args.overwrite:
        print("Tip: use --overwrite to force re-download\n")

    return 0
