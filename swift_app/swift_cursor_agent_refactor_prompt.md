# SWIFT Codebase Refactor -- Agent Execution Prompt

**Optimized for Cursor / Claude Code AI coding agents**

------------------------------------------------------------------------

## Objective

Refactor the SWIFT codebase to create a **clean, consistent, namespaced
Python API** while preserving all existing engine logic and CLI
behavior.

The refactor should improve:

-   API ergonomics
-   Naming consistency
-   CLI ↔ Python symmetry
-   Maintainability

Do **NOT rewrite core engines**. Only update the API layer and CLI
wiring.

Existing architecture reference:

-   API layer → `swift_app/api.py`
-   CLI layer → `swift_app/cli.py`, `swift_app/main.py`
-   Engines:
    -   `wris.py`
    -   `cwc.py`
    -   `merge.py`
    -   `plot.py`
    -   `wris_client.py`

The engines must remain functionally unchanged.

------------------------------------------------------------------------

# Phase 1 --- Introduce Namespaced APIs

Create two namespaces:

    swift.wris
    swift.cwc

Implementation:

Inside `swift_app/api.py` create:

``` python
class _WrisNamespace:
    def download(...)
    def stations(...)

class _CwcNamespace:
    def download(...)
    def stations(...)
```

Expose them in `swift_app/__init__.py`:

``` python
from .api import _WrisNamespace, _CwcNamespace

wris = _WrisNamespace()
cwc = _CwcNamespace()
```

Target public API:

``` python
import swift

swift.wris.download(...)
swift.wris.stations(...)

swift.cwc.download(...)
swift.cwc.stations(...)
```

------------------------------------------------------------------------

# Phase 2 --- Rename Download Functions

Current functions:

-   `download_wris`
-   `download_cwc`
-   `get_wris_data`
-   `get_cwc_data`

Replace canonical interface with:

    swift.wris.download()
    swift.cwc.download()

Add backward compatibility aliases:

``` python
download_wris = wris.download
download_cwc = cwc.download

get_wris_data = wris.download
get_cwc_data = cwc.download
```

Emit deprecation warnings:

``` python
warnings.warn(
    "get_wris_data is deprecated. Use swift.wris.download instead.",
    DeprecationWarning,
)
```

------------------------------------------------------------------------

# Phase 3 --- Standardize Station Metadata APIs

Replace legacy functions:

    wris_stations
    cwc_stations
    search_stations
    cwc_station

Canonical APIs:

    swift.wris.stations()
    swift.cwc.stations()

Backwards compatibility:

    wris_stations = wris.stations
    cwc_stations = cwc.stations
    search_stations = wris.stations
    cwc_station = cwc.stations

------------------------------------------------------------------------

# Phase 4 --- Standardize Parameter Names

Normalize inconsistent parameters across API.

### Dataset parameter

Replace:

    var
    datasets
    dataset_flags

with canonical:

    variable

Allowed canonical dataset names:

    discharge
    water_level
    rainfall
    temperature
    humidity
    solar_radiation
    sediment
    groundwater_level

Maintain internal alias mapping via `DATASET_ALIAS`.

------------------------------------------------------------------------

### Basin parameter

Replace:

    b
    basin_id

with:

    basin

Only allow:

    basin="godavari"

Numeric basin IDs should still be resolved internally via `WRIS_BASINS`.

------------------------------------------------------------------------

### Path parameters

Replace:

    input_dir
    output_dir

with unified:

    root_dir

Meaning:

    root_dir = SWIFT output root directory

Example structure:

    output/
    output/godavari/
    output/cwc/

------------------------------------------------------------------------

# Phase 5 --- Update WRIS Download API

Final API signature:

``` python
swift.wris.download(
    basin,
    variable,
    *,
    station=None,
    start_date="1950-01-01",
    end_date=None,
    root_dir="output",
    format="csv",
    overwrite=False,
    merge=False,
    plot=False,
    delay=0.25,
    quiet=False,
)
```

Requirements:

-   Rename `var → variable`
-   Rename `output_dir → root_dir`
-   Ensure station filtering works
-   Preserve dataset alias resolution

Internally still call:

    run_wris_download()

------------------------------------------------------------------------

# Phase 6 --- Update CWC Download API

Final signature:

``` python
swift.cwc.download(
    station=None,
    *,
    start_date="1950-01-01",
    end_date=None,
    root_dir="output",
    format="csv",
    overwrite=False,
    merge=False,
    plot=False,
    quiet=False,
    refresh=False,
)
```

Remove dataset argument completely since CWC only supports water level.

Internally call:

    run_cwc_download()

------------------------------------------------------------------------

# Phase 7 --- Redesign Merge API

Replace existing API:

    swift.merge(input_dir, datasets=None, output_dir=None)

with:

``` python
swift.merge(
    mode="wris",
    basin=None,
    variable=None,
    root_dir="output",
)
```

Modes:

    mode="wris"
    mode="cwc"

Internally map to:

    run_merge_only()

------------------------------------------------------------------------

# Phase 8 --- Redesign Plot API

Replace:

    swift.plot(input_dir, datasets=None, output_dir=None, cwc=False)

with:

``` python
swift.plot(
    mode="wris",
    basin=None,
    variable=None,
    root_dir="output",
)
```

Internally call:

    run_plot_only()

------------------------------------------------------------------------

# Phase 9 --- Create Unified Fetch Helper

Replace legacy `download()` dispatcher with:

``` python
swift.fetch(
    source,
    basin=None,
    station=None,
    variable=None,
    root_dir="output",
    start_date="1950-01-01",
    end_date=None,
    merge=False,
    plot=False,
)
```

Behavior:

    if source == "wris":
        swift.wris.download(...)
    elif source == "cwc":
        swift.cwc.download(...)

------------------------------------------------------------------------

# Phase 10 --- CLI Improvements

Modify `swift_app/main.py`.

Enable WRIS plotting after download.

Current behavior:

    --plot only works for CWC

New behavior:

    swift -b godavari -q --plot

Implementation:

After `run_wris_download()`:

    if args.plot:
        run_plot_only(args)

------------------------------------------------------------------------

# Phase 11 --- Dataset Naming Consistency

Canonical names:

    discharge
    water_level
    rainfall
    temperature
    humidity
    solar_radiation
    sediment
    groundwater_level

CLI flags remain unchanged:

    -q
    -rf
    -wl

Mapping handled via:

    DATASET_ALIAS
    DATASETS

------------------------------------------------------------------------

# Phase 12 --- Preserve Engine Modules

DO NOT modify engine logic in:

    wris.py
    cwc.py
    merge.py
    plot.py
    wris_client.py

These modules must remain untouched except for required parameter name
compatibility.

------------------------------------------------------------------------

# Phase 13 --- Update Public API Exports

Final `swift/__init__.py` exports:

    wris
    cwc

    merge
    plot
    fetch

    datasets
    basins

    cite
    coffee

Legacy functions should not be publicly exposed except as compatibility
aliases.

------------------------------------------------------------------------

# Phase 14 --- Verification Tests

Confirm the following work:

### WRIS download

    swift.wris.download(
        basin="godavari",
        variable="discharge"
    )

### CWC download

    swift.cwc.download(
        station="040-CDJAPR"
    )

### Merge

    swift.merge(mode="wris", basin="godavari")

### Plot

    swift.plot(mode="wris", basin="godavari")

### CLI

    swift -b godavari -q --merge --plot

------------------------------------------------------------------------

# Final Expected API Example

``` python
import swift

swift.wris.download(
    basin="godavari",
    variable="discharge",
    merge=True,
    plot=True,
)

swift.wris.stations(basin="godavari")

swift.cwc.download(station="040-CDJAPR")

swift.merge(mode="wris", basin="godavari")

swift.plot(mode="wris", basin="godavari")
```
