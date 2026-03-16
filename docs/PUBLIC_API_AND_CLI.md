# SWIFT — Public API and CLI

User-facing Python API and the equivalent command-line usage.

---

## Python API

```python
import swift_app
```

> Legacy note: `swift.datasets` and `swift.basins()` were removed.
> Use `swift_app.wris.variables()` and `swift_app.wris.basins()`.
> For CWC basin listing, use `swift_app.cwc.basins()`.

| Python API | What it does |
|------------|----------------|
| **swift_app.wris.download**(basin, variable, ...) | Download WRIS time-series to files |
| **swift_app.wris.stations**(basin, variable=..., delay=...) | List WRIS stations in a basin |
| **swift_app.cwc.download**(station=..., ...) | Download CWC water-level data to files |
| **swift_app.cwc.stations**(station=..., basin=..., river=..., state=..., refresh=...) | List CWC station metadata (supports optional state filter for CWC only) |
| **swift_app.wris.variables**() | List supported WRIS variables, flags, and aliases |
| **swift_app.wris.basins**() | List WRIS basin id/name table |
| **swift_app.cwc.basins**(refresh=False) | List CWC basins with station counts from metadata |
| **swift_app.fetch**(stations_df, ...) | Download data for stations listed in a WRIS/CWC stations table |
| **swift_app.merge_only**(input_dir=..., mode=..., variable=..., ...) | Merge existing station files into GeoPackages (preferred) |
| **swift_app.plot_only**(input_dir=..., mode=..., variable=..., cwc=..., ...) | Generate hydrograph plots from existing output (preferred) |
| **swift_app.merge**(...) | Backward-compatible alias of `merge_only` |
| **swift_app.plot**(...) | Backward-compatible alias of `plot_only` |
| **swift_app.cite**() | Print citation |
| **swift_app.coffee**() | Print coffee-break message |

---

## CLI (equivalent commands)

Run: `swift` or `python -m swift_app.main`.

| Python | CLI equivalent |
|--------|------------------|
| **wris.download**(basin="Godavari", variable="discharge") | `swift -b Godavari -q` |
| **wris.download**(..., station=["S1","S2"]) | No direct CLI filter; download then filter files manually |
| **wris.download**(..., start_date="2020-01-01", end_date="2020-12-31") | `swift -b Godavari -q --start-date 2020-01-01 --end-date 2020-12-31` |
| **wris.download**(..., output_dir="data") | `swift -b Godavari -q --output-dir data` |
| **wris.download**(..., format="xlsx") | `swift -b Godavari -q --format xlsx` |
| **wris.download**(..., overwrite=True) | `swift -b Godavari -q --overwrite` |
| **wris.download**(..., merge=True) | `swift -b Godavari -q --merge` |
| **wris.download**(..., plot=True) | `swift -b Godavari -q --plot` |
| **wris.download**(..., quiet=True) | `swift -b Godavari -q --quiet` |
| **wris.stations**("Godavari") | No direct CLI; use Python or download then inspect output |
| **wris.variables**() | No direct CLI equivalent |
| **wris.basins**() | `swift --list` (WRIS basin section) |
| **cwc.download**() | `swift --cwc` |
| **cwc.download**(station=["040-CDJAPR"]) | `swift --cwc-station 040-CDJAPR` |
| **cwc.download**(..., start_date=..., end_date=...) | `swift --cwc --start-date ... --end-date ...` |
| **cwc.download**(..., refresh=True) | `swift --cwc --cwc-refresh` |
| **cwc.download**(..., output_dir="data") | `swift --cwc --output-dir data` |
| **cwc.stations**() | `swift --list` (shows count); full table only via Python |
| **cwc.basins**() | No direct CLI equivalent |
| **fetch**(swift_app.wris.stations(...), ...) | No direct single CLI equivalent; compose via `swift -b ...` and dataset flags |
| **fetch**(swift_app.cwc.stations(...), ...) | No direct single CLI equivalent; compose via `swift --cwc-station ...` |
| **merge_only**(mode="wris", output_dir="output") | `swift --merge-only --input-dir output --output-dir output -q` (with dataset flags as needed) |
| **merge_only**(input_dir="output") | `swift --merge-only --input-dir output` |
| **plot_only**(mode="wris", output_dir="output") | `swift --plot-only --input-dir output -q` |
| **plot_only**(mode="cwc", output_dir="output") | `swift --plot-only --input-dir output --cwc` |
| **cite**() | `swift --cite` |
| **coffee**() | `swift --coffee` |

---

## Dataset flags (CLI)

| Variable (Python) | CLI flag |
|------------------|----------|
| discharge | `-q` |
| water_level | `-wl` |
| atm_pressure | `-atm` |
| rainfall | `-rf` |
| temperature | `-temp` |
| humidity | `-rh` |
| solar_radiation | `-solar` |
| sediment | `-sed` |
| groundwater_level | `-gwl` |

Example: discharge + rainfall → `swift -b Krishna -q -rf`

---

## Common CLI options

| Option | Meaning |
|--------|--------|
| `-b`, `--basin` | Basin name or number (WRIS) |
| `--cwc` | Use CWC instead of WRIS |
| `--cwc-station CODE [CODE ...]` | CWC station code(s) |
| `--cwc-refresh` | Refresh CWC metadata from API before download |
| `--start-date`, `--end-date` | Date range (YYYY-MM-DD) |
| `--output-dir` | Output directory (default: `output`) |
| `--input-dir` | Input dir for `--merge-only` / `--plot-only` |
| `--format csv` \| `xlsx` | Output file format |
| `--overwrite` | Re-download existing files |
| `--merge` | Merge to GeoPackage after download |
| `--merge-only` | Only merge; no download |
| `--plot` | Plot after download |
| `--plot-only` | Only plot; no download |
| `--quiet` | Less output |
| `--list` | List basins and CWC station count |
| `--delay` | Delay between WRIS requests (seconds) |
