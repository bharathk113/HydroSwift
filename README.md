
# SWIFT

## Simple Water Information Fetch Tool

![Version](https://img.shields.io/badge/version-0.4.1-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Data](https://img.shields.io/badge/data-WRIS%20India-blue) ![Field](https://img.shields.io/badge/field-hydrology-lightblue)

---

## Overview

SWIFT is a lightweight Python tool for downloading hydrological time-series data from the **India WRIS portal** and the **CWC Flood Forecasting** API:

> https://indiawris.gov.in

WRIS hosts a large number of hydrological datasets, but downloading them through the website GUI becomes painful if you need data for many stations or variables.

Click → download → repeat… hundreds of times.

SWIFT reproduces the same API calls used by the WRIS browser interface and automates the entire workflow.

This tool is primarily designed for **academic hydrology workflows**.

<div align="center">
  <h1>SWIFT (Simple Water Information Fetch Tool)</h1>
  <p><strong>Version 1.0.0 — Echo Edinburgh</strong></p>
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg">
  <img src="https://img.shields.io/badge/python-3.9+-brightgreen.svg">
</div>

---

SWIFT is a lightweight, dependency-minimal CLI tool designed to batch downoad hydrological time-series data from the [India WRIS](https://indiawris.gov.in/wris/) and **CWC Flood Forecasting** portals.

## Quickstart

```bash
conda env create -f environment.yml
conda activate carbform

python -m swift_app -h
```

## Supported Datasets

**WRIS API**
- `-q` : River discharge
- `-wl` : Water level
- `-atm` : Atmospheric pressure
- `-rf` : Rainfall
- `-temp` : Temperature
- `-rh` : Relative humidity
- `-solar` : Solar radiation
- `-sed` : Suspended sediment
- `-gwl` : Groundwater level

**CWC API (`--cwc`)**
- `-wl` : Real-time water level (WSE)

## Key Features

1.  **Dual APIs**: Fetch historical data from WRIS or real-time data from CWC.
2.  **Auto-Discovery**: Provide a basin index, and SWIFT will spider the tributary tree, locate all operational agencies, and discover every active station.
3.  **Smart Resume**: Automatically skips previously downloaded station files.
4.  **GeoPackage Export (`--merge`)**: Aggregates hundreds of CSVs into a single QGIS-ready `.gpkg` file.
5.  **Background Logging**: Every download generates a `swift.log` file tracking success/failures.
6.  **Scripting Mode**: Use `--quiet` to suppress progress bars and ASCII art when running headless scripts.

---

## 1. Basic WRIS Downloads

The `-b` flag is required. You can pass the exact basin name (in quotes) or use the corresponding basin number (e.g. `6` for Krishna). Use `--list` to see all available basins.

```bash
# Download discharge and water level data for the Krishna Basin (basin #6)
python -m swift_app -b 6 -q -wl
```

## 2. Using the CWC API

The CWC portal provides real-time flood forecasting telemetry. This data is available under the `--cwc` flag.

```bash
# Download all CWC water level stations across India
python -m swift_app --cwc -wl
```

You can target specific CWC stations using their exact station codes:
```bash
python -m swift_app --cwc-station 038-CDJAPR 040-CDJAPR --merge
```

*(Note: Use the `--list` flag to find the path to the complete catalog of CWC station codes).*

## 3. Formatting, Merging, and Plotting

**File Formats**
Use `--format xlsx` to generate Excel files instead of standard CSVs.
```bash
python -m swift_app -b 6 -q --format xlsx
```

**GeoPackage Merging**
Instead of handling 500 individual CSVs, combine them into a single GeoPackage.
```bash
python -m swift_app -b 6 -q -wl --merge
```
*Note:* You can also run `--merge-only` later to build a GeoPackage from existing downloads without hitting the API again.

**Plotting**
Use `--plot` to automatically generate high-contrast matplotlib time-series graphs for every station downloaded.
```bash
python -m swift_app -b 6 -q --plot
```

## 4. Scripting and Background Modes

**Silent Scripting (`--quiet`)**
Suppress progress bars and logs for integration with automated scripts.
```bash
python -m swift_app -b 6 -q --quiet
```

**Coffee Break (`--coffee`)**
Going for a break? The `--coffee` flag shows a nice ASCII banner and forces quiet mode, downloading silently in the background while keeping a clean console. Check the `swift.log` in your output folder later for results!
```bash
python -m swift_app --cwc --coffee --merge
```

### Common Flags (WRIS and CWC)

| Flag | Description |
| ---- | ----------- |
| `--plot` | Generate time-series plots after download |
| `--merge` | Merge all station files into a GeoPackage |
| `--format csv\|xlsx` | Output file format (default: csv) |
| `--output-dir DIR` | Custom output directory (default: output) |
| `--overwrite` | Overwrite existing files |
| `--start-date YYYY-MM-DD` | Filter start date |
| `--end-date YYYY-MM-DD` | Filter end date |
| `--metadata` | Save station metadata as CSV (WRIS only) |
| `--coffee` | Take a coffee break ☕ |
| `--list` | List available basins and CWC station info |
| `--plot-only` | Generate plots from existing output (no download) |

### Examples

Download Krishna discharge with plots and GeoPackage merge:

```bash
python swift.py -b 6 -q --plot --merge
```

Download CWC data with XLSX format and merge:

```bash
python swift.py --cwc --format xlsx --merge
```

Custom date range for CWC:

```bash
python swift.py --cwc --start-date 2020-01-01 --end-date 2024-12-31
```

---

## Output Structure

### WRIS

```text
output/
    krishna/
        discharge/
            002-UKDPUNE_Warunji_DISCHARG.csv
        Krishna_discharge.gpkg          # if --merge is used

images/
    wris/
        krishna/
            discharge/
                station_plot.png
```

### CWC

```text
output/
    cwc/
        stations/
            040-CDJAPR_parwan_pick-up_weir.csv
        cwc_timeseries.gpkg             # if --merge is used

images/
    cwc/
        CWC_040-CDJAPR_parwan_pick-up_weir.png
```

### Standardized CSV Schema

All output files follow a consistent 6-column schema:

```csv
station_code,time,{variable},unit,lat,lon
```

Where `{variable}` is `q`, `wl`, `wse`, `rf`, etc. depending on the dataset.

---

## Resume Support

SWIFT automatically skips stations that have already been downloaded. If a download is interrupted, simply re-run the same command — only missing stations will be fetched.

Use `--overwrite` to force redownload of all stations.

---

## Notes

- SWIFT mimics the API calls made by the WRIS browser interface.
- Please avoid running it too aggressively, otherwise the server may temporarily block requests.
- If downloads fail intermittently, simply run the script again. Completed files will be skipped unless `--overwrite` is used.

---

**Current release:**

`0.4.1 — Delta Delhi`

---

## License

MIT License.

---

## Acknowledgement

Hydrological data are provided by the India WRIS portal and CWC Flood Forecasting System.

If you use the downloaded datasets in publications, please cite the data sources appropriately.

---

## Contributing

Suggestions, improvements, and bug reports are welcome.
