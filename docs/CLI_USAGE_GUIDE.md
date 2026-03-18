# CLI Usage Guide

HydroSwift provides a flag-based CLI.

Run it as:

```bash
swift ...
```

or, if the console script is not on your path:

```bash
python -m hydroswift ...
```

This guide reflects the current parser in `hydroswift.cli` and the examples shown in `SWIFT_CLI_BEGINNER.ipynb`.

## 1. Important mental model

The CLI is **flag-based**, not subcommand-based.

You compose a command from:

- a source selection (`-b/--basin` for WRIS, or `--cwc` / `--station` / `--cwc-basin` for CWC)
- one or more WRIS dataset flags if you are using WRIS
- optional output/date/plot/merge flags

Example:

```bash
swift -b Krishna -q -rf -temp
```

---

## 2. WRIS mode

WRIS is the default mode when you provide a basin and at least one WRIS dataset flag.

### Required pieces

- `-b` / `--basin`
- one or more dataset flags such as `-q`, `-wl`, `-rf`, etc.

### Basin values

You can pass either:

- a basin name, such as `Krishna`
- a WRIS basin number, such as `6`

Examples:

```bash
swift -b 5 -q
swift -b Krishna -q -rf -temp
swift -b Godavari --discharge --rainfall --temperature
```

---

## 3. WRIS dataset flags

Current WRIS variable flags are:

- `-q`, `--discharge`
- `-wl`, `--water-level`
- `-atm`, `--atm-pressure`
- `-rf`, `--rainfall`
- `-temp`, `--temperature`
- `-rh`, `--humidity`
- `-solar`, `--solar-radiation`
- `-sed`, `--sediment`
- `-gwl`, `--groundwater-level`

Examples:

```bash
swift -b Godavari -q
swift -b Krishna -q -rf -temp
swift -b Krishna --discharge --rainfall
```

---

## 4. CWC mode

CWC downloads target water-level data.

You can enter CWC mode with any of the following:

```bash
swift --cwc
swift --cwc-station 040-CDJAPR 032-LGDHYD
swift --station 040-CDJAPR 032-LGDHYD
swift --cwc-basin Krishna Godavari
```

### CWC flags

- `--cwc`
- `--cwc-station CODE [CODE ...]`
- `--station CODE [CODE ...]` (alias of `--cwc-station`)
- `--cwc-basin NAME [NAME ...]`
- `--cwc-refresh`

Examples aligned with the notebook:

```bash
swift --cwc
swift --cwc-station 032-LGDHYD
swift --cwc-basin Krishna
```

Behavior notes:

- CWC mode does not support WRIS multi-variable downloads.
- If you pass both station codes and basin filters, HydroSwift uses the matching intersection.

---

## 5. Date and output controls

Common download controls include:

- `--start-date YYYY-MM-DD`
- `--end-date YYYY-MM-DD`
- `--output-dir PATH`
- `--format csv|xlsx`
- `--overwrite`
- `--merge`
- `--plot`
- `--plot-svg`
- `--plot-moving-average-window N`
- `--quiet`
- `--metadata`

Examples:

```bash
swift -b 6 -q --start-date 2020-01-01 --end-date 2022-01-01
```

```bash
swift -b 5 -q --output-dir data --format csv --overwrite
```

```bash
swift -b 5 -q --plot
```

---

## 6. Post-processing modes

### Merge only

Use existing downloaded files to generate GeoPackages.

```bash
swift --merge-only --input-dir output
```

You may also control the output location:

```bash
swift --merge-only --input-dir output --output-dir merged_output
```

### Plot only

Use existing downloaded files to generate plots.

```bash
swift --plot-only --input-dir output
```

With quality options:

```bash
swift --plot-only --input-dir output --plot-svg --plot-moving-average-window 30
```

---

## 7. Metadata and utility commands

### List mode

```bash
swift --list
```

This prints:

- the WRIS basin list
- the total number of known CWC stations

### Other utility flags

```bash
swift --version
swift --cite
swift --coffee
```

---

## 8. CLI to Python equivalence

The beginner notebook explicitly maps many CLI commands to Python API calls.

Examples:

| CLI | Python API |
|---|---|
| `swift -b 5 -q` | `swift.wris.download(basin=5, variable='discharge')` |
| `swift -b Krishna -q -rf -temp` | `swift.wris.download(basin='Krishna', variable=['discharge', 'rainfall', 'temperature'])` |
| `swift --merge-only --input-dir output` | `swift.merge_only(input_dir='output')` |
| `swift --plot-only --input-dir output` | `swift.plot_only(input_dir='output')` |
| `swift --cwc-station 032-LGDHYD` | `swift.cwc.download(station=['032-LGDHYD'])` |
| `swift --cwc-basin Krishna` | `swift.cwc.download(basin=['Krishna'])` |

---

## 9. Troubleshooting and common mistakes

### "No dataset selected" in WRIS mode

You must provide at least one WRIS dataset flag like `-q` or `-rf`.

### `--merge-only` or `--plot-only` fails

These modes require:

- `--input-dir`
- an input directory that already contains HydroSwift outputs

### Mixing WRIS expectations into CWC mode

CWC is a water-level workflow. If you need multiple WRIS variables, use WRIS mode with `-b` plus WRIS dataset flags.

### Want table-driven workflows from the terminal

The CLI does not expose the same table-native dispatch model as `swift.fetch(...)`. For discover → subset → fetch workflows, prefer the Python API.
