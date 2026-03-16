# SWIFT — Python functions reference

All callable functions and main methods, grouped by module. Arguments are listed with types and default where relevant.

---

## Public API (`swift_app` package)

Access via `import swift_app`. Only these are part of the stable public API.

Legacy migration:
- Removed: `swift.datasets`
- Removed: `swift.basins()`
- Use: `swift_app.wris.variables()`, `swift_app.wris.basins()`, `swift_app.cwc.basins()`

| Function / method | Description | Arguments |
|-------------------|-------------|-----------|
| **swift_app.wris.download** | Download WRIS time-series data to disk. | `basin` (str\|int), `variable` (str\|list), \*, `station=None`, `start_date="1950-01-01"`, `end_date=None`, `output_dir="output"`, `format="csv"`, `overwrite=False`, `merge=False`, `plot=False`, `delay=0.25`, `quiet=False` |
| **swift_app.wris.stations** | List WRIS stations for one or more basins/variables (returns SwiftTable with per-row `basin` and `variable` columns). | `basin` (str\|int\|list), `variable` (str\|list, required), `delay=0.25` |
| **swift_app.wris.variables** | Return WRIS variable table (`flag`, `dataset_code`, `folder`, `canonical_name`, `aliases`). | (none) |
| **swift_app.wris.basins** | Return WRIS basin id/name table. | (none) |
| **swift_app.cwc.download** | Download CWC water-level time-series to disk. | `station=None`, \*, `basin=None`, `start_date=None`, `end_date=None`, `output_dir="output"`, `format="csv"`, `overwrite=False`, `merge=False`, `plot=False`, `quiet=False`, `refresh=False` |
| **swift_app.cwc.stations** | Return CWC station metadata (SwiftTable). | `station=None`, `basin=None`, `river=None`, `state=None`, `refresh=False` |
| **swift_app.cwc.basins** | Return CWC basin table with station counts from station metadata. | `refresh=False` |
| **swift_app.fetch** | Download using a WRIS/CWC stations table. For multi-basin/variable WRIS tables, groups by `(basin, variable)` and dispatches each combination. | `stations` (DataFrame/SwiftTable from `wris.stations` or `cwc.stations`), \* `output_dir="output"`, `start_date="1950-01-01"`, `end_date=None`, `format="csv"`, `overwrite=False`, `merge=False`, `plot=False`, `quiet=False`, `delay=0.25`, `refresh=False` |
| **swift_app.merge_only** | Merge existing SWIFT station files into GeoPackages. Basins/agencies are auto-discovered from the directory layout. | `input_dir=None`, `output_dir=None`, \*, `mode=None`, `variable=None` |
| **swift_app.plot_only** | Generate hydrograph plots from existing SWIFT output. Basins/agencies are auto-discovered from the directory layout. | `input_dir=None`, `output_dir=None`, `cwc=False`, \*, `mode=None`, `variable=None` |
| **swift_app.merge** | Backward-compatible alias for `swift_app.merge_only`. | `input_dir=None`, `output_dir=None`, \*, `mode=None`, `variable=None` |
| **swift_app.plot** | Backward-compatible alias for `swift_app.plot_only`. | `input_dir=None`, `output_dir=None`, `cwc=False`, \*, `mode=None`, `variable=None` |
| **swift_app.cite** | Print banner and citation text. | (none) |
| **swift_app.coffee** | Easter egg: print coffee-break message. | (none) |

---

## api.py (internal implementation)

Functions used by the public API; not guaranteed stable. Prefer the public API above.

| Function | Description | Arguments |
|----------|-------------|-----------|
| **get_wris_data** | Download WRIS time-series (used by `wris.download`). | `var`, `basin`, \*, `station=None`, `start_date`, `end_date`, `output_dir`, `format`, `overwrite`, `merge`, `plot`, `delay`, `quiet` |
| **get_cwc_data** | Download CWC water-level data (used by `cwc.download`). | `station=None`, \*, `var=None`, `start_date`, `end_date`, `output_dir`, `format`, `overwrite`, `merge`, `plot`, `quiet`, `refresh` |
| **wris_stations** | List WRIS stations for one or more basins/variables (used by `wris.stations`). | `basin` (str\|int\|list), `var` (str\|list), `delay=0.25` |
| **cwc_stations** | CWC station metadata (used by `cwc.stations`). | `station=None`, `basin=None`, `river=None`, `state=None`, `refresh=False` |
| **_normalize_datasets_input** | Turn single str or list into list of dataset names. | `datasets` |
| **_normalize_cwc_station_input** | Normalize CWC station to list or None. | `cwc_station` |
| **_normalize_wris_station_input** | Normalize WRIS station to list or None. | `station` |
| **_normalize_dataset_flags** | Map human names to CLI flags; raise if unknown. | `datasets` |
| **_build_args** | Build a SimpleNamespace of CLI-like args from kwargs. | `**kwargs` |
| **_resolve_basin** | Map basin int/name to canonical basin name. | `basin` |
| **_resolve_variable** | Normalise a variable string to its dataset flag. | `var` |
| **_discover_station_codes** | Discover WRIS station codes and river fallbacks for one (basin, variable). | `client`, `basin_code`, `basin_structure`, `dataset_code` |
| **_resolve_mode_input_dir** | Derive `input_dir` from `mode` (root containing ``wris/`` and ``cwc/``). | `mode`, `output_dir` |

---

## cli.py

| Function | Description | Arguments |
|----------|-------------|-----------|
| **build_parser** | Build the argparse parser for the `swift` CLI. | (none) |
| **selected_datasets** | Map parsed args to dict of dataset_code → folder name. | `args` (argparse.Namespace) |

---

## main.py

| Function | Description | Arguments |
|----------|-------------|-----------|
| **main** | CLI entry point: parse args, dispatch download/merge/plot/list/cite. | (none) → returns int exit code |
| **_print_coffee** | Print the coffee ASCII art. | (none) |

---

## wris_client.py — WrisClient (class)

Thin client for India-WRIS HTTP API.

| Method | Description | Arguments |
|--------|-------------|-----------|
| **__init__** | Create session and set delay between requests. | `delay=0.25` |
| **post** | POST with retries and delay. | `url`, `payload`, `retries=3` |
| **check_api** | Probe WRIS API availability. | (none) → bool |
| **get_basin_code** | Resolve basin name to basin code. | `basin_name` |
| **get_tributaries** | Get tributaries for basin + dataset. | `basin_code`, `dataset_code` |
| **get_rivers** | Get rivers for a tributary. | `tributary_id`, `dataset_code` |
| **get_agencies** | Get agencies for tributary + river. | `tributary_id`, `localriver_id`, `dataset_code` |
| **get_stations** | Get telemetric + manual stations. | `tributary_id`, `localriver_id`, `agency_id`, `dataset_code` |
| **get_metadata** | Get single-station metadata. | `station_code`, `dataset_code` |
| **get_timeseries** | Fetch station timeseries; normalize columns. | `station_code`, `dataset_code`, `start_date`, `end_date` |

---

## wris.py (WRIS engine)

| Function | Description | Arguments |
|----------|-------------|-----------|
| **build_metadata** | Build standard metadata dict from WRIS/CWC raw meta. | `meta`, `dataset`, `source` ("WRIS"\|"CWC") |
| **_save_timeseries** | Write one station’s timeseries to CSV or XLSX. | `args`, `base_output`, `folder`, `meta`, `station`, `dataset`, `df`, `var_col` |
| **build_basin_structure** | List (tributary_id, river_id) for a basin. | `client`, `basin_code` |
| **discover_stations** | Collect all station codes for a basin/dataset (uses caches). | `client`, `basin_structure`, `dataset_code`, `agency_cache`, `station_cache` |
| **filter_existing_stations** | Keep only stations that don’t already have files. | `stations`, `dataset_dir`, `ext` |
| **run_wris_download** | Full WRIS download: discover stations, fetch TS, save, optional merge/plot. | `args`, `selected` (dict dataset_code→folder), `client`, `basin_code` |

---

## cwc.py (CWC engine)

| Function | Description | Arguments |
|----------|-------------|-----------|
| **_read_csv_safe** | Read CSV, normalize columns; return DataFrame or None. | `path` |
| **_write_cache** | Write DataFrame to CWC cache file. | `df` |
| **load_station_table** | Load CWC station table (packaged or cache); optional refresh from API. | `refresh=False` |
| **_fetch_lookup_sorted** | Fetch one lookup table via CWC sorted API. | `entity`, `sort_field="name"` |
| **_fetch_lookup_paged** | Fetch one lookup table with pagination. | `entity`, `sort_field="name"`, `page_size=5000` |
| **_fetch_all_lookups** | Fetch all CWC lookup tables in parallel. | (none) |
| **fetch_cwc_station_metadata** | Fetch full CWC station metadata from FFS API (bulk). | (none) |
| **fetch_station_data** | Fetch one station’s water-level timeseries (with retries). | `code`, `start_date=None`, `end_date=None`, `retries=3` |
| **get_cwc_station_metadata** | Filter/query CWC station table by station/basin/river/state. | `station=None`, `basin=None`, `river=None`, `state=None`, `refresh=False` |
| **download_station** | Download one CWC station to a single file. | `station` (dict with code, name, lat, lon, …), `output_dir`, `args` |
| **run_cwc_download** | Full CWC download: load stations, download each, optional merge/plot. | `args` |

---

## merge.py

| Function | Description | Arguments |
|----------|-------------|-----------|
| **merge_dataset_folder** | Merge all CSV/XLSX in a folder to one GeoPackage layer. | `dataset_dir`, `gpkg_path`, `layer` |
| **run_merge_only** | CLI merge: find basin dirs, call merge_dataset_folder per dataset. | `args` |

---

## plot.py

| Function | Description | Arguments |
|----------|-------------|-----------|
| **_collect_files** | Recursively collect CSV and XLSX under a path. | `path` (Path) |
| **run_plot_only** | Plot-only mode: find basin/CWC dirs, call plot_station per file. | `args` |

---

## plot_station_timeseries.py

| Function | Description | Arguments |
|----------|-------------|-----------|
| **load_swift_file** | Load one SWIFT CSV/XLSX and return normalized DataFrame (time, value, unit). | `file_path` |
| **plot_station** | Plot one station file and save figure (images/…). | `file_path` |
| **collect_files** | List CSV/XLSX under path (file or dir). | `input_path` |
| **main** | Script entry: plot one file or all under a directory. | (none; uses sys.argv) |

---

## banner.py

| Function | Description | Arguments |
|----------|-------------|-----------|
| **print_wish_banner** | Print SWIFT ASCII banner (rich if available). | (none) |

---

## Variable names (datasets)

Canonical names used for `variable` / datasets:  
`discharge`, `water_level`, `atm_pressure`, `rainfall`, `temperature`, `humidity`, `solar_radiation`, `sediment`, `groundwater_level`.  
Short codes (e.g. `q`, `wl`, `rf`) are accepted and mapped via `DATASET_ALIAS` in api.py.
