# Examples and Notebooks

HydroSwift ships example notebooks in the repository root rather than inside `docs/`.

## Included examples

### Python API examples

- `hydroswift_python_examples.ipynb` [hydroswift_python_examples.ipynb]

This example demonstrates:

- WRIS basin-table workflows
- WRIS station-table workflows
- `hydroswift.fetch(...)`
- `hydroswift.wris.download(...)`
- CWC basin and station workflows
- `hydroswift.cwc.download(...)`
- `hydroswift.merge_only(...)`
- `hydroswift.plot_only(...)`

### CLI beginner examples

- `SWIFT_CLI_BEGINNER.ipynb`
- `SWIFT_CLI_BEGINNER.html`

This example demonstrates:

- the flag-based CLI model
- WRIS dataset flags
- date range control
- output options
- merge-only mode
- plot-only mode
- CWC station and basin commands

## How to use these examples alongside the docs

- Read [Python API Guide](PYTHON_API_GUIDE.md) before running `hydroswift_python_examples.ipynb`.
- Read [CLI Usage Guide](CLI_USAGE_GUIDE.md) before running `SWIFT_CLI_BEGINNER.ipynb`.
- Use [Public API and CLI Map](PUBLIC_API_AND_CLI.md) when translating a notebook action from Python to CLI or vice versa.

## Important note about older doc references

If you see older references to `CLI_EXAMPLES.ipynb` inside historical docs or configs, the current repository examples are:

- `SWIFT_CLI_BEGINNER.ipynb`
- `PYTHON_API_EXAMPLES.ipynb`

Those are the example sources this documentation now follows.
