# HydroSwift ⚡
![Tests](https://github.com/carbform/swift/actions/workflows/tests.yml/badge.svg)

Fast, unified workflows for hydrological data.

HydroSwift is a Python toolkit for integrating, processing, and visualizing hydrological datasets at basin scale. It automates retrieval from the India‑WRIS (https://indiawris.gov.in/) and Central Water Commission (CWC; https://ffs.india-water.gov.in/) portals while preserving reproducible CLI and notebook workflows.

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

HydroSwift automates basin discovery, station enumeration, time‑series downloads, and dataset merging into geospatial formats.

------------------------------------------------------------

## What is HydroSwift?

HydroSwift enables:

- Multi-source hydrology data ingestion across WRIS and CWC workflows
- Dataset merging and harmonization
- Basin-scale workflows
- Visualization and analysis
- Fast, reproducible pipelines for research and teaching

FEATURES

- Automated discovery of hydrological stations list via CLI or Python API
- Parallel download of time‑series observations with exponential backoff
- Support for multiple hydrological variables (Discharge, Rainfall, Groundwater, etc.)
- Extensible Python API for seamless integration into Jupyter Notebooks and custom scripts
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

After installation, verify HydroSwift is working by running:

    python -m hydroswift --help
    swift --version

This should display the HydroSwift command-line interface and available options.

## Documentation

- Python API guide: `docs/PYTHON_API_GUIDE.md`
- CLI usage guide: `docs/CLI_USAGE_GUIDE.md`
- CLI examples notebook: `SWIFT_CLI_BEGINNER.ipynb` / `SWIFT_CLI_BEGINNER.html`
- Python API examples notebook: `PYTHON_API_EXAMPLES.ipynb` / `PYTHON_API_EXAMPLES.html`
- API reference table: `docs/API_FUNCTIONS_REFERENCE.md`
- Web docs build config: `mkdocs.yml` + `.readthedocs.yaml`

## Python API Usage

HydroSwift is primarily designed as a Python module for scripts and Jupyter notebooks.

```python
import hydroswift as swift

# Discover metadata tables
wris_vars = swift.wris.variables()
wris_basins = swift.wris.basins(variable=["discharge", "rainfall"])
cwc_basins = swift.cwc.basins()

# Explicit namespace downloads (direct values only)
swift.wris.download(
    basin=["Krishna", "Godavari"],
    variable=["discharge", "rainfall"],
    start_date="2024-01-01",
    end_date="2024-03-31",
    merge=True,
)

swift.cwc.download(
    station=["040-CDJAPR", "032-LGDHYD"],
    start_date="2024-01-01",
    end_date="2024-01-07",
    merge=True,
)

# Unified table-driven workflow (recommended for station/basin tables)
wris_stations = swift.wris.stations(basin="Krishna", variable="discharge")
swift.fetch(wris_stations, merge=True)

cwc_stations = swift.cwc.stations(basin=["Krishna", "Godavari"])
swift.fetch(cwc_stations, merge=True)

# Basin table -> fetch
swift.fetch(swift.wris.basins(variable="solar"), start_date="2024-01-01")
swift.fetch(swift.cwc.basins().head(2), start_date="2024-01-01")
```

### Public API summary

- `swift.wris.download(...)`: WRIS download using explicit `basin` + `variable` inputs.
- `swift.cwc.download(...)`: CWC download using explicit `station` and/or `basin` inputs.
- `swift.fetch(table, ...)`: generic entry point for WRIS/CWC station or basin tables.
- `swift.wris.stations(...)`, `swift.cwc.stations(...)`: metadata discovery tables.
- `swift.wris.variables()`, `swift.wris.basins(...)`, `swift.cwc.basins(...)`: lookup tables.
- `swift.merge_only(...)`, `swift.plot_only(...)`: post-processing helpers.

> Note: namespace downloads intentionally reject DataFrame/table arguments.
> Pass tables to `swift.fetch(...)` instead.

> Legacy note: `swift.datasets` and `swift.basins()` are removed.

### Metadata behavior

- WRIS metadata is discovered on request during station lookup/download workflows.
- CWC metadata is packaged (and optionally cached/refreshed) to avoid unnecessary API calls, because it is mostly static and usually changes only when station/HFL metadata updates.
- `swift.cwc.stations(..., refresh=True)` first refreshes live metadata and then applies filters such as `basin="Krishna"`.

------------------------------------------------------------

## Command Line Interface (CLI)

HydroSwift can also be used as a standalone command-line tool for rapid data acquisition without writing code.

Download discharge observations for the Krishna basin:

    swift -b krishna -q

This command will:

1. Discover all discharge stations in the basin
2. Download available time series
3. Store the data in the `output/` directory

### CLI Examples

Download multiple datasets (short flags):

    swift -b godavari -q -rf -temp

Same command with Python-like long variable names:

    swift -b godavari --discharge --rainfall --temperature

Download CWC gauge water level data:

    swift --cwc

Download selected CWC stations (aliases: `--cwc-station` or `--station`):

    swift --station 040-CDJAPR 032-LGDHYD

Filter CWC download by basin names:

    swift --cwc-basin Krishna Godavari

Merge downloaded station datasets into a GeoPackage:

    swift -b krishna -q --merge

Generate publication-ready plots from downloaded data:

    swift --plot-only --input-dir output --plot-moving-average-window 30 --plot-svg

Run silently (no console UI):

    swift -b krishna -q --quiet

List WRIS basins and CWC station availability info:

    swift --list

------------------------------------------------------------

OUTPUT STRUCTURE

Downloaded datasets are organized under source-specific folders:

output/
  wris/
    <basin>/
      <variable>/
      *.gpkg
  cwc/
    <basin-or-group>/stations/
    cwc_waterlevel*.gpkg

Exact file names include date windows and dataset labels used during download.

------------------------------------------------------------

DATA SOURCES

HydroSwift retrieves publicly available data from:

- India Water Resources Information System (WRIS)
- Central Water Commission (CWC) Flood Forecasting System

------------------------------------------------------------

CITATION

If you use HydroSwift in your research, please cite:

Sarat, C., Dash, D., & Kumar, A. (2026).
HydroSwift: Automated Retrieval of Hydrological Station Data from India‑WRIS and CWC Portals.
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


### Build docs locally

```bash
pip install -r requirements-docs.txt
mkdocs build --strict
mkdocs serve
```
