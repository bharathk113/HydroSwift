# SWIFT
![Tests](https://github.com/carbform/swift/actions/workflows/tests.yml/badge.svg)

SWIFT — Simple Water Information Fetch Tool

SWIFT is an open‑source Python command‑line tool for automated retrieval of hydrological station data from the India‑WRIS (https://indiawris.gov.in/) and Central Water Commission (CWC; https://ffs.india-water.gov.in/) portals.

The software enables reproducible access to hydrological observations such as:

- River discharge
- Water level
- Rainfall
- Atmospheric pressure
- Temperature
- Relative humidity
- Solar radiation
- Groundwater levels
- Suspended sediment

SWIFT automates basin discovery, station enumeration, time‑series downloads, and dataset merging into geospatial formats.

------------------------------------------------------------

FEATURES

- Automated discovery of hydrological stations
- Parallel download of time‑series observations
- Support for multiple hydrological variables
- Integration with WRIS and CWC data services
- GeoPackage export for GIS workflows
- Hydrograph / Time Series plotting utilities
- Resume capability for interrupted downloads
- Command‑line interface for reproducible workflows

------------------------------------------------------------

INSTALLATION

From source:

    git clone https://github.com/carbform/swift.git
    cd swift
    pip install -e .

Using pip (future release):

    pip install swift

------------------------------------------------------------
## Quick Test

After installation, verify SWIFT is working by running:

    python -m swift_app --help
    python swift.py --version

This should display the SWIFT command-line interface and available options.

## Minimal Example

Download discharge observations for the Krishna basin:

    swift -b krishna -q

This command will:

1. Discover all discharge stations in the basin
2. Download available time series
3. Store the data in the `output/` directory

EXAMPLE USAGE

Download discharge observations for the Krishna basin:

    swift -b krishna -q

Download multiple datasets:

    swift -b godavari -q -rf -temp

Download CWC gauge water level data:

    swift --cwc

Merge downloaded station datasets into a GeoPackage:

    swift -b krishna -q --merge

Generate time series plots from downloaded data:

    swift --plot-only -b krishna

------------------------------------------------------------

OUTPUT STRUCTURE

Downloaded datasets are organized by basin and variable:

output/
  krishna/
    discharge/
      station1.csv
      station2.csv
    rainfall/
    temperature/

Merged geospatial datasets are stored as GeoPackage files in the basin level folder.

------------------------------------------------------------

DATA SOURCES

SWIFT retrieves publicly available data from:

- India Water Resources Information System (WRIS)
- Central Water Commission (CWC) Flood Forecasting System

------------------------------------------------------------

CITATION

If you use SWIFT in your research, please cite:

C.Sarat. (2026).
SWIFT: Automated Retrieval of Hydrological Station Data
from India‑WRIS and CWC Portals.
Journal of Open Source Software.

------------------------------------------------------------

LICENSE

MIT License

------------------------------------------------------------

ACKNOWLEDGEMENTS

- India Water Resources Information System (India-WRIS)
- Central Water Commission (CWC)

The software uses several open‑source Python libraries including:

- pandas
- geopandas
- matplotlib
- requests
