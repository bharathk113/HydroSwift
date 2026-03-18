# SWIFT CLI Usage Guide (Comprehensive)

Run SWIFT as:

See also: `docs/CLI_EXAMPLES.ipynb` for a runnable notebook set of examples.

```bash
swift ...
# or
python -m swift_app.main ...
```

---

## 1) Source selection

### WRIS mode (default)
Provide basin plus one or more WRIS dataset flags:

```bash
swift -b Godavari -q
swift -b 6 -q -rf -temp
```

### CWC mode
Any of the following routes to CWC download workflow:

```bash
swift --cwc
swift --cwc-station 040-CDJAPR 032-LGDHYD
swift --station 040-CDJAPR 032-LGDHYD
swift --cwc-basin Krishna Godavari
```

---

## 2) WRIS dataset flags

Short and long forms are both supported:

- `-q` / `--discharge`
- `-wl` / `--water-level`
- `-atm` / `--atm-pressure`
- `-rf` / `--rainfall`
- `-temp` / `--temperature`
- `-rh` / `--humidity`
- `-solar` / `--solar-radiation`
- `-sed` / `--sediment`
- `-gwl` / `--groundwater-level`

Examples:

```bash
swift -b Krishna -q -rf
swift -b Krishna --discharge --rainfall
```

---

## 3) Date/output behavior flags

Common download controls:

```bash
--start-date YYYY-MM-DD
--end-date YYYY-MM-DD
--output-dir output
--format csv|xlsx
--overwrite
--merge
--plot
--plot-svg
--plot-moving-average-window N
--quiet
```

Example:

```bash
swift -b Godavari -q --start-date 2024-01-01 --end-date 2024-01-31 --format xlsx --merge
```

---

## 4) CWC-specific flags

- `--cwc` : explicitly enable CWC mode
- `--cwc-station CODE [CODE ...]` or `--station CODE [CODE ...]`
- `--cwc-basin NAME [NAME ...]`
- `--cwc-refresh` : refresh metadata from live API

Examples:

```bash
swift --station 040-CDJAPR --start-date 2024-01-01 --end-date 2024-01-07
swift --cwc-basin Krishna Godavari --cwc-refresh
```

---

## 5) Metadata and utility commands

```bash
swift --list
swift --cite
swift --coffee
swift --version
```

---

## 6) Post-processing without download

### Merge-only mode

```bash
swift --merge-only --input-dir output --output-dir output
```

### Plot-only mode

```bash
swift --plot-only --input-dir output --plot-moving-average-window 30 --plot-svg
```

---

## 7) Python API parity hints

- `swift -b ... -q/-rf/...` maps to `swift.wris.download(...)`.
- `swift --station ...` and `swift --cwc-basin ...` map to `swift.cwc.download(station=..., basin=...)`.
- CLI does not expose full `fetch(table, ...)` table-dispatch semantics; use Python API for table-native workflows.

---

## 8) Troubleshooting

- **No dataset selected in WRIS mode**: pass at least one WRIS variable flag (`-q`, `-rf`, etc.).
- **Basin required error**: in WRIS mode, `-b/--basin` is required.
- **CWC + WRIS flags together**: WRIS-only variables are ignored by CWC mode except water-level semantics.
