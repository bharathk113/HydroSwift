
# SWIFT

## Simple WRIS India Fetch Tool

![Version](https://img.shields.io/badge/version-0.4.1-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Data](https://img.shields.io/badge/data-WRIS%20India-blue) ![Field](https://img.shields.io/badge/field-hydrology-lightblue)

---

## Overview

SWIFT is a lightweight Python tool for downloading hydrological time-series data from the **India WRIS portal** and the **CWC Flood Forecasting** API:

> https://indiawris.gov.in

WRIS hosts a large number of hydrological datasets, but downloading them through the website GUI becomes painful if you need data for many stations or variables.

Click → download → repeat… hundreds of times.

SWIFT reproduces the same API calls used by the WRIS browser interface and automates the entire workflow.

This tool is primarily designed for **academic hydrology workflows**.

---

## What SWIFT does

SWIFT automatically:

- Discovers basin information (WRIS) or fetches station data (CWC)
- Maps tributaries and rivers
- Finds monitoring stations
- Retrieves station metadata
- Downloads time-series observations
- Generates time-series plots
- Exports data as CSV or XLSX
- Merges station files into GeoPackage for GIS workflows

---

## Supported datasets

### WRIS Datasets

| Flag    | Dataset                |
| ------- | ---------------------- |
| `-q`    | River Discharge        |
| `-wl`   | River Water Level      |
| `-atm`  | Atmospheric Pressure   |
| `-rf`   | Rainfall               |
| `-temp` | Temperature            |
| `-rh`   | Relative Humidity      |
| `-solar`| Solar Radiation        |
| `-sed`  | Suspended Sediment     |
| `-gwl`  | Groundwater Level      |

### CWC Dataset

| Flag    | Dataset                |
| ------- | ---------------------- |
| `--cwc` | Water Surface Elevation (wse) |

> CWC only provides water level data from 1,500+ flood forecasting stations.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/carbform/swift
cd swift
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run directly:

```bash
python swift.py -h
```

Run as a module:

```bash
python -m swift_app -h
```

Optional: install a `swift` shell command:

```bash
pip install -e .
```

---

## Usage

### List available basins and stations

```bash
python swift.py --list
```

### WRIS Downloads

Download discharge data from the Krishna basin (use name or number):

```bash
python swift.py -b Krishna -q
python swift.py -b 6 -q           # same as above
```

Download multiple datasets together:

```bash
python swift.py -b Krishna -q -wl -rf
```

### CWC Downloads

Download water level data from all CWC stations:

```bash
python swift.py --cwc
```

Download specific CWC stations:

```bash
python swift.py --cwc --cwc-station 040-CDJAPR
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
