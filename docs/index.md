# SWIFT 🌊
### Simple Water Information Fetch Tool

**SWIFT** provides a unified Python API and CLI for accessing
Indian hydrology datasets from **WRIS** and **CWC**.

<div class="grid cards" markdown>

- :material-language-python: **Python API**

  Discover stations, query basins, and download time-series data
  using a clean Python interface.

  [Python API Guide](PYTHON_API_GUIDE.md)

- :material-console: **Command Line Interface**

  Reproducible data downloads directly from the terminal.

  [CLI Usage Guide](CLI_USAGE_GUIDE.md)

- :material-function: **API Reference**

  Complete reference of all public SWIFT functions.

  [API Functions Reference](API_FUNCTIONS_REFERENCE.md)

- :material-notebook-outline: **Interactive Examples**

  Run SWIFT workflows in Jupyter notebooks.

  [Python API Examples](PYTHON_API_EXAMPLES.ipynb)

</div>

---

## Quick example

=== "Python"

    ```python
    import swift_app as swift

    df = swift.wris.download(
        basin="Godavari",
        variable="discharge",
        start_date="2024-01-01",
        end_date="2024-01-10",
    )
    ```

=== "CLI"

    ```bash
    swift -b Godavari -q \
        --start-date 2024-01-01 \
        --end-date 2024-01-10
    ```

---

## Documentation structure

| Guide | Description |
|------|-------------|
| **Python API Guide** | Complete Python usage documentation |
| **CLI Usage Guide** | All command line options |
| **API Functions Reference** | Function signatures and arguments |
| **Public API and CLI Map** | Cross-reference of CLI ↔ Python |

---

## Notebook examples

- [CLI Examples Notebook](CLI_EXAMPLES.ipynb)
- [Python API Examples Notebook](PYTHON_API_EXAMPLES.ipynb)

---

## About SWIFT

SWIFT provides:

- programmatic access to **WRIS hydrology datasets**
- automated downloads for **CWC water-level data**
- reproducible CLI workflows
- built-in plotting and merge utilities