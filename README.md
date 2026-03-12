

# SWIFT

## Simple Water Information Fetch Tool

![Version](https://img.shields.io/badge/version-1.0.0-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Data](https://img.shields.io/badge/data-Hydrological%20Data-blue) ![Field](https://img.shields.io/badge/field-hydrology-lightblue)

---

## Overview

SWIFT is a lightweight tool for downloading hydrological time-series data from the [India WRIS](https://indiawris.gov.in/wris/) and **CWC Flood Forecasting** portals.

WRIS hosts a large number of hydrological datasets, but downloading them through the website GUI becomes painful if you need data for many stations or variables.

Click → download → repeat… hundreds of times.

SWIFT automates the entire workflow by reproducing the API calls used by the WRIS browser interface.

---

## Quickstart

```bash
conda env create -f environment.yml
conda activate carbform

python swift.py -h
```


## Supported Datasets & Flags

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


## Features

1. **Auto-Discovery**: Provide a basin index or name, and SWIFT will locate all active stations from WRIS and fetch all available time-series data. CWC data is available even without specifying a river basin.
2. **GeoPackage Export (`--merge` or `--merge-only`)**: Creates a GeoPackage file (`.gpkg`) for each dataset, combining all station files.
3. **Plotting (`--plot` or `--plot-only`)**: Generate quick time-series plots for every station downloaded.
4. **Resume Support**: Interrupted downloads automatically skip completed stations; use `--overwrite` to force redownload or when updating the database.
5. **Silent & Coffee Modes**: Use `--quiet` or `--coffee` for background/silent scripting.

---


## 1. Basic WRIS Downloads

The `-b` flag is required for WRIS. You can pass the exact basin name (case-insensitive) or use the corresponding basin number (e.g. `6` for Krishna). Use `--list` to see all available basins.

```bash
# Download discharge and water level data for the Krishna Basin (basin #6)
python swift.py -b 6 -q -wl
```


## 2. Using the CWC API

The CWC portal provides real-time flood forecasting telemetry. This data is available under the `--cwc` flag.

```bash
# Download all CWC water level stations across India
python swift.py --cwc -wl
```

You can target specific CWC stations using their exact station codes:
```bash
python swift.py --cwc-station 038-CDJAPR 040-CDJAPR --merge
```

*(Tip: Use the `--list` flag to find the path to the complete catalog of CWC station codes.)*


## 3. Formatting, Merging, and Plotting

**File Formats**
Use `--format xlsx` to generate Excel files instead of standard CSVs.
```bash
python swift.py -b 6 -q --format xlsx
```

**GeoPackage Merging**
Instead of handling hundreds of individual CSVs, combine them into a single GeoPackage:
```bash
python swift.py -b 6 -q -wl --merge
```
*Note:* You can also run `--merge-only` later to build a GeoPackage from existing downloads without hitting the API again.

**Plotting**
Use `--plot` to automatically generate time-series plots for every station downloaded:
```bash
python swift.py -b 6 -q --plot
```


## 4. Scripting and Background Modes

**Silent Scripting (`--quiet`)**
Suppress progress bars and logs for integration with automated scripts.
```bash
python swift.py -b 6 -q --quiet
```

**Coffee Break (`--coffee`)**
Going for a break? The `--coffee` mode starts downloading silently in the background. Check the `swift.log` in your output folder later for results!

```bash
python swift.py --cwc --coffee --merge
```


### Common Flags (WRIS and CWC)

| Flag | Description |
| ---- | ----------- |
| `--plot` | Generate time-series plots after download |
| `--merge` | Merge all station files into a GeoPackage |
| `--merge-only` | Merge existing files into GeoPackage (no download) |
| `--format csv\|xlsx` | Output file format (default: csv) |
| `--output-dir DIR` | Custom output directory (default: output) |
| `--overwrite` | Overwrite existing files |
| `--start-date YYYY-MM-DD` | Filter start date |
| `--end-date YYYY-MM-DD` | Filter end date |
| `--metadata` | Save station metadata as CSV (WRIS only) |
| `--quiet` | Suppress console output |
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

### Output CSV Format

All output files have 6 columns

```csv
station_code,time,{variable},unit,lat,lon
```

Where `{variable}` is `q`, `wl`, `wse`, `rf`, etc. depending on the dataset.

---


## Resume Support

SWIFT automatically skips stations that have already been downloaded. If a download is interrupted, simply re-run the same command.

Use `--overwrite` to force redownload of all stations.

---


## Notes & Troubleshooting

- SWIFT mimics the API calls made by the WRIS browser interface.
- Please avoid running it too aggressively, otherwise the server may temporarily block requests.
- If downloads fail intermittently, simply run the script again. Completed files will be skipped unless `--overwrite` is used.
- CWC API only supports water level data (`-wl`). Other dataset flags are ignored in CWC mode.
- If you see errors about missing basins or stations, use `--list` to check available options.
- For merge or plot-only modes, ensure you have downloaded data in the output directory.

---


---

**Current release:**

`1.0.0 — Arctic Amsterdam`

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
