
# SWIFT

## Simple WRIS India Fetch Tool

![Version](https://img.shields.io/badge/version-0.4.0-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Data](https://img.shields.io/badge/data-WRIS%20India-blue) ![Field](https://img.shields.io/badge/field-hydrology-lightblue)

---

## Overview

SWIFT is a lightweight Python tool for downloading hydrological time-series data from the **India WRIS portal**:

> https://indiawris.gov.in

WRIS hosts a large number of hydrological datasets, but downloading them through the website GUI becomes painful if you need data for many stations or variables.

Click → download → repeat… hundreds of times.

SWIFT reproduces the same API calls used by the WRIS browser interface and automates the entire workflow.

This tool is primarily designed for **academic hydrology workflows**.

---

## What SWIFT does

SWIFT automatically:

- Discovers basin information
- Maps tributaries and rivers
- Finds monitoring stations
- Retrieves station metadata
- Downloads time-series observations
- Generates time-series plots of the downloaded data

---

## Supported datasets

| Flag    | Dataset                |
| ------- | ---------------------- |
| `-q`    | River Water Discharge  |
| `-wl`   | River Water Level      |
| `-atm`  | Atmospheric Pressure   |
| `-rf`   | Rainfall               |
| `-temp` | Temperature            |
| `-rh`   | Relative Humidity      |
| `-solar`| Solar Radiation        |
| `-sed`  | Suspended Sediment     |
| `-gwl`  | Groundwater Level      |

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

SWIFT can directly be run with Python or installed as a module:


```bash
python swift.py -h
```

Run as a module:

```bash
python -m swift_app -h
```

Optional: install a `swift` shell command (only if you want it):

```bash
pip install -e .
```

```bash
swift -b Krishna -h
```

---

## Usage

Download discharge data from the Krishna basin:

```bash
python swift.py -b Krishna -q
```

You can run the equivalent module command as well:

```bash
python -m swift_app -b Krishna -q
```

Download water level data:

```bash
python swift.py -b Krishna -wl
```

Download multiple datasets together:

```bash
python swift.py -b Krishna -q -wl -rf
```

Overwrite existing files (useful for testing):

```bash
python swift.py -b Krishna -q --overwrite
```

Save station metadata:

```bash
python swift.py -b Krishna -q --metadata
```

Export station geometry:

```bash
python swift.py -b Krishna -q --geopackage
```

Export station list:

```bash
python swift.py -b Krishna -q --stations
```

Merge downloaded stations into one dataset:

```bash
python swift.py -b Krishna -q --merge
```

Custom output directory:

```bash
python swift.py -b Krishna -q --output-dir data
```

Take a virtual coffee break:

```bash
python swift.py -b Krishna -q --coffee
```

---

## Example Output

Downloaded data are automatically organised by basin and dataset:

```text
output/
    krishna/
        discharge/
            029-LKDHYD_Suddakal_DISCHARG.csv
```

Plotting

SWIFT can generate station time series plots automatically.

During download:

```bash
python swift.py -b Krishna -q --plot
```

Or generate plots later using existing data:

```bash
python swift.py -b Krishna --plot-only
```

Plots are saved in:
```text
images/
    krishna/
        discharge/
            station_plot.png

output/
    krishna/
        discharge/
        water_level/
        rainfall/

images/
    krishna/
        discharge/
        rainfall/
```

## Notes

- SWIFT mimics the API calls made by the WRIS browser interface.
- Please avoid running it too aggressively, otherwise the server may temporarily block requests.
- If downloads fail intermittently, simply run the script again. Completed files will be skipped unless `--overwrite` is used.

---

<!-- ## Version Naming

Each major SWIFT release receives a city-themed codename:

- Analog Amsterdam
- Bravo Boston
- Cryo Copenhagen
- Delta Delhi
- Echo Edinburgh
- Flux Florence
- Glacier Geneva -->

**Current release:**

`0.4.0 — Delta Delhi`

---

## License

MIT License.

---

## Acknowledgement

Hydrological data are provided by the India WRIS portal.

If you use the downloaded datasets in publications, please cite the WRIS data source appropriately.

---

## Contributing

Suggestions, improvements, and bug reports are welcome.
