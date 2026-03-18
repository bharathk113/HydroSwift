# Public API and CLI Map

This page connects the current Python API, the CLI, and the example notebooks.

## 1. Which interface should you use?

### Use the Python API when you need:

- station or basin discovery tables
- DataFrame subsetting before download
- `swift.fetch(...)`
- notebook workflows
- merge/plot pipelines controlled in code

### Use the CLI when you need:

- quick direct downloads
- reproducible shell commands
- a simple flag-based workflow

---

## 2. Notebook-backed usage map

The repository currently includes two example notebook pairs:

- `PYTHON_API_EXAMPLES.ipynb` / `PYTHON_API_EXAMPLES.html`
- `SWIFT_CLI_BEGINNER.ipynb` / `SWIFT_CLI_BEGINNER.html`

The Python notebook emphasizes:

- `swift.wris.basins(variable=...)`
- `swift.wris.stations(...)`
- `swift.cwc.basins()`
- `swift.cwc.stations(...)`
- `swift.fetch(...)`
- `swift.wris.download(...)`
- `swift.cwc.download(...)`
- `swift.merge_only(...)`
- `swift.plot_only(...)`

The CLI notebook emphasizes:

- `swift -b ... -q/-rf/-temp/...`
- `swift --merge-only --input-dir ...`
- `swift --plot-only --input-dir ...`
- `swift --cwc`
- `swift --cwc-station ...`
- `swift --cwc-basin ...`

---

## 3. Direct mapping table

| Task | Python API | CLI |
|---|---|---|
| Download WRIS discharge for a basin | `swift.wris.download(basin='Godavari', variable='discharge')` | `swift -b Godavari -q` |
| Download multiple WRIS variables | `swift.wris.download(basin='Krishna', variable=['discharge', 'rainfall', 'temperature'])` | `swift -b Krishna -q -rf -temp` |
| Discover WRIS stations before downloading | `swift.wris.stations(basin='Godavari', variable='discharge')` | not directly exposed as a table workflow |
| Download from a WRIS station table | `swift.fetch(wris_table, ...)` | not directly exposed |
| Download all CWC stations in a basin | `swift.cwc.download(basin=['Krishna'])` | `swift --cwc-basin Krishna` |
| Download selected CWC stations | `swift.cwc.download(station=['032-LGDHYD'])` | `swift --cwc-station 032-LGDHYD` |
| Discover CWC station metadata | `swift.cwc.stations(...)` | `swift --list` gives only a summary, not the full table |
| Merge existing output | `swift.merge_only(input_dir='output')` | `swift --merge-only --input-dir output` |
| Plot existing output | `swift.plot_only(input_dir='output')` | `swift --plot-only --input-dir output` |
| Show help | `swift.help()` / `swift.cli_help()` | `swift -h` |
| Show citation | `swift.cite()` | `swift --cite` |
| Coffee easter egg | `swift.coffee()` | `swift --coffee` |

---

## 4. Key conceptual differences

### Python API supports table-native workflows

The Python API can pass rich tables between discovery and download:

```python
stations = swift.wris.stations(basin="Godavari", variable="discharge")
subset = stations.head(5)
result = swift.fetch(subset, merge=True)
```

That pattern does not have an equivalent CLI table object.

### CLI is optimized for direct commands

The CLI is best when you already know:

- the WRIS basin and dataset flags, or
- the CWC station/basin filters

---

## 5. Rules that apply across both interfaces

- WRIS supports multiple variables.
- CWC is a water-level workflow.
- Explicit namespace download methods use explicit values, not DataFrames.
- `fetch(...)` is the bridge for HydroSwift-generated tables.
- `merge_only(...)` and `plot_only(...)` work from existing output directories.
