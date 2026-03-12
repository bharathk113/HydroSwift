"""
Public Python API for SWIFT.

Python equivalents of CLI commands:
    swift.download()
    swift.merge()
    swift.plot()
"""

from types import SimpleNamespace
from pathlib import Path
import time

from .api import WrisClient
from .cli import DATASETS, WRIS_BASINS
from .download import run_download
from .merge import run_merge_only
from .plot import run_plot_only
from .cwc import run_cwc_download


# ---------------------------------------------------------
# Dataset aliases (Python friendly names)
# ---------------------------------------------------------

DATASET_ALIAS = {
    "discharge": "q",
    "water_level": "wl",
    "rainfall": "rf",
    "temperature": "temp",
    "humidity": "rh",
    "solar": "solar",
    "sediment": "sed",
    "groundwater": "gwl",
}

def _normalize_datasets_input(datasets):

    if datasets is None:
        return []

    if isinstance(datasets, str):
        datasets = [datasets]

    return list(datasets)



# ---------------------------------------------------------
# Normalize dataset input
# ---------------------------------------------------------

def _normalize_dataset_flags(datasets):

    if not datasets:
        return []

    flags = []

    for d in datasets:

        if d in DATASET_ALIAS:
            flags.append(DATASET_ALIAS[d])

        elif d in DATASET_ALIAS.values():
            flags.append(d)

        else:
            raise ValueError(f"Unknown dataset: {d}")

    return flags


# ---------------------------------------------------------
# Build CLI-style args object
# ---------------------------------------------------------

def _build_args(**kwargs):

    args = SimpleNamespace()

    args.basin = kwargs.get("basin")

    args.start_date = kwargs.get("start_date", "1950-01-01")
    args.end_date = kwargs.get("end_date") or time.strftime("%Y-%m-%d")

    args.merge = kwargs.get("merge", False)
    args.merge_only = kwargs.get("merge_only", False)
    args.plot_only = kwargs.get("plot_only", False)

    args.overwrite = kwargs.get("overwrite", False)

    args.output_dir = kwargs.get("output_dir")
    args.input_dir = kwargs.get("input_dir")   # ← ADD THIS

    args.delay = kwargs.get("delay", 0.25)
    args.format = kwargs.get("format", "csv")

    args.plot = kwargs.get("plot", False)
    args.metadata = kwargs.get("metadata", False)
    args.quiet = kwargs.get("quiet", False)

    args.cwc = kwargs.get("cwc", False)
    args.cwc_station = kwargs.get("cwc_station")

    dataset_keys = ["q","wl","atm","rf","temp","rh","solar","sed","gwl"]

    for key in dataset_keys:
        setattr(args, key, False)

    for flag in kwargs.get("dataset_flags", []):
        setattr(args, flag, True)

    return args


# ---------------------------------------------------------
# DOWNLOAD (equivalent to CLI main run)
# ---------------------------------------------------------

def download(
    basin=None,
    b=None,
    datasets=None,
    start_date="1950-01-01",
    end_date=None,
    overwrite=False,
    merge=False,
    plot=False,
    metadata=False,
    output_dir=None,
    delay=0.25,
    format="csv",
    quiet=False,
    cwc=False,
    cwc_station=None,
):

    if output_dir is None:
        raise ValueError("output_dir must be specified when using the Python API")

    output_dir = str(Path(output_dir))

    # normalize dataset input
    datasets = _normalize_datasets_input(datasets)

    if not datasets and not cwc:
        raise ValueError("At least one dataset must be specified")

    dataset_flags = _normalize_dataset_flags(datasets)

    # ---------------------------------------------------------
    # Output directory required
    # ---------------------------------------------------------
    if basin is None and not cwc:
        raise ValueError("basin must be specified unless using cwc=True")

    if output_dir is None:
        raise ValueError("output_dir must be specified when using the Python API")

    output_dir = str(Path(output_dir))

    # basin shorthand
    if basin is None and b is not None:
        basin = b

    args = _build_args(
        basin=basin,
        start_date=start_date,
        end_date=end_date,
        merge=merge,
        overwrite=overwrite,
        output_dir=output_dir,
        delay=delay,
        format=format,
        plot=plot,
        metadata=metadata,
        quiet=quiet,
        cwc=cwc,
        cwc_station=cwc_station,
        dataset_flags=dataset_flags,
    )

    # ---------------------------------------------------------
    # CWC mode
    # ---------------------------------------------------------

    if cwc:
        run_cwc_download(args)
        return None

    # ---------------------------------------------------------
    # Basin number → name
    # ---------------------------------------------------------

    if isinstance(basin, int):
        basin = str(basin)

    if basin in WRIS_BASINS:
        args.basin = WRIS_BASINS[basin]
    else:
        args.basin = basin

    # ---------------------------------------------------------
    # Initialize WRIS client
    # ---------------------------------------------------------

    client = WrisClient(delay=delay)

    if not client.check_api():
        raise RuntimeError("WRIS API unavailable")

    basin_code = client.get_basin_code(args.basin)

    # ---------------------------------------------------------
    # Preserve dataset order
    # ---------------------------------------------------------

    selected = {}

    for flag in dataset_flags:
        dataset_code, folder = DATASETS[flag]
        selected[dataset_code] = folder

    if not selected:
        raise ValueError("No datasets selected")

    # ---------------------------------------------------------
    # Run download engine
    # ---------------------------------------------------------

    run_download(args, selected, client, basin_code)

    # ---------------------------------------------------------
    # Plot after download if requested
    # ---------------------------------------------------------

    if plot:

        plot_args = _build_args(
            basin=args.basin,
            output_dir=output_dir,
            plot_only=True,
            dataset_flags=dataset_flags,
        )

        run_plot_only(plot_args)

    # CLI-style behaviour: print output, return silently
    return None


# ---------------------------------------------------------
# MERGE (equivalent to CLI --merge-only)
# ---------------------------------------------------------

def merge(input_dir, datasets=None, output_dir=None):

    from pathlib import Path

    if input_dir is None:
        raise ValueError("input_dir must be specified")

    p = Path(input_dir)

    if not p.exists():
        raise ValueError("input_dir does not exist")

    dataset_flags = _normalize_dataset_flags(datasets)

    args = _build_args(
        input_dir=str(p),
        output_dir=str(output_dir) if output_dir else None,
        merge_only=True,
        dataset_flags=dataset_flags,
    )

    run_merge_only(args)

    return None


# ---------------------------------------------------------
# PLOT (equivalent to CLI --plot-only)
# ---------------------------------------------------------

def plot(input_dir, datasets=None, output_dir=None, cwc=False):

    from pathlib import Path

    if input_dir is None:
        raise ValueError("input_dir must be specified")

    p = Path(input_dir)

    if not p.exists():
        raise ValueError("input_dir does not exist")

    dataset_flags = _normalize_dataset_flags(datasets)

    args = _build_args(
        input_dir=str(p),
        output_dir=str(output_dir) if output_dir else None,
        plot_only=True,
        dataset_flags=dataset_flags,
        cwc=cwc,
    )

    run_plot_only(args)

    return None

import pandas as pd


def search_stations(basin, dataset="discharge", delay=0.25):
    """
    Discover available stations without downloading timeseries.
    """

    from .download import build_basin_structure, discover_stations

    # dataset normalization
    if dataset in DATASET_ALIAS:
        dataset_flag = DATASET_ALIAS[dataset]
    else:
        dataset_flag = dataset

    dataset_code, _ = DATASETS[dataset_flag]

    # basin normalization
    if isinstance(basin, int):
        basin = str(basin)

    if basin in WRIS_BASINS:
        basin = WRIS_BASINS[basin]

    client = WrisClient(delay=delay)

    basin_code = client.get_basin_code(basin)

    basin_structure = build_basin_structure(client, basin_code)

    agency_cache = {}
    station_cache = {}

    stations = discover_stations(
        client,
        basin_structure,
        dataset_code,
        agency_cache,
        station_cache
    )

    records = []

    for s in stations:

        meta = client.get_metadata(s, dataset_code)

        if not meta:
            continue

        records.append({
            "station_code": s,
            "station_name": meta.get("station_Name"),
            "latitude": meta.get("latitude"),
            "longitude": meta.get("longitude"),
            "river": meta.get("riverName"),
        })

    df = pd.DataFrame(records)

    print(f"\nFound {len(df)} stations in basin '{basin}' for dataset '{dataset}'")

    return df

### Classes for notebook completion  and list printing functions
class _DatasetNamespace:
    """Provides tab-completion for dataset names in notebooks."""

    discharge = "discharge"
    water_level = "water_level"
    rainfall = "rainfall"
    temperature = "temperature"
    humidity = "humidity"
    solar = "solar"
    sediment = "sediment"
    groundwater = "groundwater"

    def __call__(self):
        return [
            self.discharge,
            self.water_level,
            self.rainfall,
            self.temperature,
            self.humidity,
            self.solar,
            self.sediment,
            self.groundwater,
        ]


datasets = _DatasetNamespace()

import re


class _BasinNamespace:
    """Tab-completion helper for basin names."""

    def __init__(self, basin_mapping):

        self._mapping = basin_mapping

        for code, name in basin_mapping.items():

            key = name.lower()
            key = re.sub(r"[^\w]+", "_", key)
            key = re.sub(r"_+", "_", key).strip("_")

            setattr(self, key, name)

    def __call__(self):
        """Print clean basin table and return mapping."""

        print("\nAvailable WRIS Basins")
        print("--------------------------------------------")
        print(f"{'ID':<6}{'Basin'}")
        print("--------------------------------------------")

        for code, name in sorted(self._mapping.items(), key=lambda x: int(x[0])):
            print(f"{code:<6}{name}")

        print("--------------------------------------------")

        return self._mapping

basins = _BasinNamespace(WRIS_BASINS)

from .banner import print_wish_banner


def cite():
    """Print the banner and citation information."""

    print_wish_banner()

    print(
    """
    If you use SWIFT in your research, please cite:

    Sarat, C., Dash, D., & Kumar, A. (2026).
    SWIFT: Automated Retrieval of Hydrological Station Data
    from India-WRIS and CWC Portals.
    Journal of Open Source Software.

    Repository:
    https://github.com/carbform/swift
    """
    )
def coffee():
    """SWIFT coffee break easter egg for notebooks."""

    print(
    r"""
        ( (
        ) )
        ........
        |      |]
        \      /
        `----'
        TIME FOR A COFFEE BREAK ☕
    """
        )

    print(
            "Many kinds of monkeys have a strong taste for tea, coffee and spirituous liqueurs. - Charles Darwin"
        )

    return None

