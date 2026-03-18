# HydroSwift ⚡

HydroSwift is a unified toolkit for hydrological data integration, analysis, and visualization.

Designed for fast, reproducible basin-scale workflows.

HydroSwift currently downloads hydrology data from two sources:

- **India-WRIS** for multiple hydrological variables such as discharge, rainfall, temperature, humidity, sediment, groundwater level, solar radiation, atmospheric pressure, and water level.
- **CWC Flood Forecasting System** for **water-level** station data.

This documentation has been rewritten to match the current codebase and the example workflows shown in:

- `PYTHON_API_EXAMPLES.ipynb` / `PYTHON_API_EXAMPLES.html`
- `SWIFT_CLI_BEGINNER.ipynb` / `SWIFT_CLI_BEGINNER.html`

## How HydroSwift is organized

HydroSwift exposes two main interfaces:

1. **Python API** via `import hydroswift as swift`
2. **CLI** via `swift ...` or `python -m hydroswift ...`

The Python API has two styles:

- **Explicit namespace downloads** for when you already know the basin/station values you want.
- **Table-driven workflows** for when you first discover basins or stations, then pass those tables into `swift.fetch(...)`.

## Recommended reading order

- [Python API Guide](PYTHON_API_GUIDE.md) — concepts, workflows, and examples.
- [CLI Usage Guide](CLI_USAGE_GUIDE.md) — every supported CLI flag and common command patterns.
- [API Functions Reference](API_FUNCTIONS_REFERENCE.md) — signatures, parameter meanings, return shapes, and notes.
- [Public API and CLI Map](PUBLIC_API_AND_CLI.md) — side-by-side mapping between notebook examples, Python, and CLI usage.
- [Examples and Notebooks](EXAMPLES_AND_NOTEBOOKS.md) — where the example notebooks fit and what they demonstrate.

## Quick start

### Python

```python
import hydroswift as swift

stations = swift.wris.stations(basin="Godavari", variable="discharge")
result = swift.fetch(
    stations,
    output_dir="output",
    start_date="2024-01-01",
    end_date="2024-01-10",
    merge=True,
)
```

### CLI

```bash
swift -b Godavari -q --start-date 2024-01-01 --end-date 2024-01-10 --merge
```

## Important usage rules

- Use `swift.wris.download(...)` and `swift.cwc.download(...)` when you want to pass **explicit basin/station values**.
- Use `swift.fetch(table, ...)` when your input comes from `swift.wris.stations(...)`, `swift.wris.basins(...)`, `swift.cwc.stations(...)`, or `swift.cwc.basins(...)`.
- `swift.wris.download(...)` does **not** accept DataFrame inputs.
- `swift.cwc.download(...)` does **not** accept DataFrame inputs.
- CWC downloads are **water-level only**.

## Output model

HydroSwift writes downloaded station files under an output directory, then optionally:

- merges them into GeoPackages with `merge=True` or `swift.merge_only(...)`
- creates plots with `plot=True` or `swift.plot_only(...)`

The post-processing helpers work from existing downloaded files and directory structure rather than requiring basin/station arguments again.
