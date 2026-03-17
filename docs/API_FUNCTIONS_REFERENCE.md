# SWIFT — API functions reference

All public functions in `swift_app` with the current supported signatures.

See also: [Python API Guide](./PYTHON_API_GUIDE.md) and [CLI Usage Guide](./CLI_USAGE_GUIDE.md).

---

## Public API (`import swift_app as swift`)

> Legacy migration:
> - Removed: `swift.datasets`
> - Removed: `swift.basins()`
> - Use: `swift.wris.variables()`, `swift.wris.basins()`, `swift.cwc.basins()`

| Function / method | Description | Arguments |
|---|---|---|
| `swift.wris.download` | Download WRIS time-series data (explicit args only). | `basin` (str\|int\|list), `variable` (str\|list), `station=None`, `stations=None`, `start_date="1950-01-01"`, `end_date=None`, `output_dir="output"`, `format="csv"`, `overwrite=False`, `merge=False`, `plot=False`, `delay=0.25`, `quiet=False` |
| `swift.wris.stations` | Discover WRIS stations table for basin/variable combinations. | `basin` (str\|int\|list), `variable` (required str\|list), `delay=0.25`, `state=None` |
| `swift.wris.variables` | WRIS variable/alias lookup table. | (none) |
| `swift.wris.basins` | WRIS basin table; optional variable expansion for fetch-ready rows. | `variable=None` |
| `swift.cwc.download` | Download CWC water-level data (explicit args only). | `station=None`, `basin=None`, `start_date=None`, `end_date=None`, `output_dir="output"`, `format="csv"`, `overwrite=False`, `merge=False`, `plot=False`, `quiet=False`, `refresh=False` |
| `swift.cwc.stations` | CWC station metadata table. | `station=None`, `basin=None`, `river=None`, `state=None`, `refresh=False` |
| `swift.cwc.basins` | CWC basin summary table with station counts. | `refresh=False` |
| `swift.cwc.reconcile_metadata` | Reconcile packaged CWC metadata using `name-code.csv` and live lookups. | `write=False` |
| `swift.fetch` | Generic table-driven downloader for WRIS/CWC station or basin tables. | `stations` (DataFrame/SwiftTable), `output_dir="output"`, `start_date="1950-01-01"`, `end_date=None`, `format="csv"`, `overwrite=False`, `merge=False`, `plot=False`, `quiet=False`, `delay=0.25`, `refresh=False` |
| `swift.merge_only` | Merge downloaded station files into GeoPackages. | `input_dir=None`, `output_dir=None`, `mode=None`, `variable=None` |
| `swift.plot_only` | Plot from existing downloaded files. | `input_dir=None`, `output_dir=None`, `cwc=False`, `mode=None`, `variable=None`, `plot_svg=False`, `plot_trend_window=None` |
| `swift.help` / `swift.cli_help` | Print CLI help text from Python. | (none) |
| `swift.cite` | Print citation text. | (none) |
| `swift.coffee` | Print coffee-break banner. | (none) |

---

## Usage notes

- WRIS station metadata is fetched on request.
- CWC station metadata defaults to packaged/cached data; use `refresh=True` to fetch live metadata before filters are applied.

1. `swift.wris.download(...)` and `swift.cwc.download(...)` are **explicit-input APIs**.
2. Table objects from `swift.wris.stations()`, `swift.wris.basins()`, `swift.cwc.stations()`, and `swift.cwc.basins()` should be passed to `swift.fetch(...)`.
3. `merge=True` returns concatenated GeoDataFrame results when optional geo dependencies are available; otherwise downloads still complete on disk.
