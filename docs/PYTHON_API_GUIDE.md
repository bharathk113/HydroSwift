# SWIFT Python API Guide (Comprehensive)

This guide documents the stable Python API exposed by:

```python
import swift_app as swift
```

---

## 1) API design in one minute

SWIFT intentionally uses **two complementary download styles**:

1. **Explicit namespace downloads**
   - `swift.wris.download(...)`
   - `swift.cwc.download(...)`
   - Best when you already know basin/station/variables.

2. **Table-driven generic downloads**
   - `swift.fetch(table, ...)`
   - Best when you discover stations/basins first and then download from those tables.

> Important: namespace download methods accept explicit values only; DataFrame/SwiftTable inputs should be passed to `swift.fetch(...)`.

---

## 2) WRIS API

### `swift.wris.variables()`
Returns a table of supported WRIS variables and aliases.

```python
vars_df = swift.wris.variables()
```

### `swift.wris.basins(variable=None)`
Returns WRIS basin table.

```python
basins = swift.wris.basins()
basin_var_pairs = swift.wris.basins(variable=["discharge", "rainfall"])
```

If `variable` is provided, the table is fetch-ready for basin-level dispatch.

### `swift.wris.stations(basin, variable, delay=0.25)`
Discovers station metadata for one or multiple basin/variable combinations.

```python
stations = swift.wris.stations(
    basin=["Godavari", "Krishna"],
    variable=["discharge", "solar"],
)
```

### `swift.wris.download(...)`
Explicit WRIS download.

```python
gdf = swift.wris.download(
    basin="Krishna",
    variable=["discharge", "rainfall"],
    station=None,
    start_date="2024-01-01",
    end_date="2024-03-31",
    output_dir="output",
    format="csv",
    overwrite=False,
    merge=True,
    plot=False,
    delay=0.25,
    quiet=False,
)
```

Parameters:
- `basin`: str|int|list
- `variable`: str|list
- `station` / `stations`: optional station code(s)
- common controls: `start_date`, `end_date`, `output_dir`, `format`, `overwrite`, `merge`, `plot`, `quiet`

---

## 3) CWC API

### `swift.cwc.stations(...)`
Returns CWC station metadata table with optional filters.

```python
cwc_stns = swift.cwc.stations(basin=["Krishna", "Godavari"], state="Telangana")
```

### `swift.cwc.basins(refresh=False)`
Returns basin summary from CWC station metadata.

```python
cwc_basins = swift.cwc.basins()
```

### `swift.cwc.download(...)`
Explicit CWC download.

```python
gdf = swift.cwc.download(
    station=["040-CDJAPR", "032-LGDHYD"],
    basin=["Krishna"],
    start_date="2024-01-01",
    end_date="2024-01-07",
    output_dir="output",
    format="csv",
    overwrite=False,
    merge=True,
    plot=False,
    quiet=False,
    refresh=False,
)
```

Notes:
- CWC provides water-level data.
- If both `station` and `basin` are provided, SWIFT uses intersection behavior.

### `swift.cwc.reconcile_metadata(write=False)`
Reconciles missing station codes from `name-code.csv` via live lookups.

---

## Metadata behavior (WRIS vs CWC)

- **WRIS metadata is fetched on request** during station discovery/download workflows.
- **CWC metadata is packaged by default** (and optionally cached/refreshed) to reduce API calls because station metadata is mostly static and typically changes only when HFL-related metadata updates occur.
- For CWC, `refresh=True` fetches fresh metadata first and then applies filters (for example `basin="Krishna"`) on that refreshed dataset.

---

## 4) Unified download: `swift.fetch(table, ...)`

Use this when input is a station/basin table from SWIFT helper methods.

```python
# WRIS station table -> download
wris_tbl = swift.wris.stations(basin="Krishna", variable="discharge")
swift.fetch(wris_tbl, start_date="2024-01-01", end_date="2024-01-10", merge=True)

# CWC basin table -> dispatch by basin
cwc_basin_tbl = swift.cwc.basins().head(2)
swift.fetch(cwc_basin_tbl, start_date="2024-01-01", end_date="2024-01-10")
```

`fetch(...)` auto-detects WRIS vs CWC and station-vs-basin table shapes.

---

## 5) Post-processing helpers

### `swift.merge_only(...)`
Merge previously downloaded station files into GeoPackage outputs.

### `swift.plot_only(...)`
Generate publication-ready hydrograph plots from existing output directories.

Optional quality controls:
- `plot_trend_window`: overlay moving-average trendline
- `plot_svg=True`: export vector SVG alongside PNG

---

## 6) Utilities

- `swift.help()` / `swift.cli_help()` → print CLI help in Python context.
- `swift.cite()` → print citation text.
- `swift.coffee()` → utility banner/easter egg.

---

## 7) Recommended workflows

### Workflow A: direct known request
1. Call `swift.wris.download(...)` or `swift.cwc.download(...)`
2. Set `merge=True` when you want in-memory merged results.

### Workflow B: discover then fetch
1. Use `wris.stations`, `wris.basins`, `cwc.stations`, or `cwc.basins`
2. Pass resulting table to `swift.fetch(...)`

This pattern is best for reproducible notebook pipelines.
