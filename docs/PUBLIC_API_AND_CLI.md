# SWIFT Documentation Map

This file is kept as a lightweight index to the detailed guides.

## Primary guides

- **Python API (comprehensive):** [`PYTHON_API_GUIDE.md`](./PYTHON_API_GUIDE.md)
- **CLI usage (comprehensive):** [`CLI_USAGE_GUIDE.md`](./CLI_USAGE_GUIDE.md)
- **CLI examples notebook:** [`CLI_EXAMPLES.ipynb`](./CLI_EXAMPLES.ipynb)
- **Python API examples notebook:** [`PYTHON_API_EXAMPLES.ipynb`](./PYTHON_API_EXAMPLES.ipynb)

## Quick parity map

| Python API | CLI equivalent |
|---|---|
| `swift.wris.download(basin="Godavari", variable="discharge")` | `swift -b Godavari -q` |
| `swift.wris.download(..., variable=["discharge","rainfall"])` | `swift -b Godavari -q -rf` |
| `swift.cwc.download(station=["040-CDJAPR"])` | `swift --station 040-CDJAPR` |
| `swift.cwc.download(basin=["Krishna"])` | `swift --cwc-basin Krishna` |
| `swift.merge_only(input_dir="output")` | `swift --merge-only --input-dir output` |
| `swift.plot_only(input_dir="output")` | `swift --plot-only --input-dir output` |
