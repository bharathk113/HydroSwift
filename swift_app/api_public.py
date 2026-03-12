from types import SimpleNamespace
import time

from .api import WrisClient
from .cli import selected_datasets
from .download import run_download
from .cwc import run_cwc_download
from .cli import WRIS_BASINS


def run(
    basin=None,
    datasets=None,
    start_date="1950-01-01",
    end_date=None,
    merge=False,
    overwrite=False,
    output_dir="output",
    delay=0.25,
    format="csv",
    plot=False,
    metadata=False,
    quiet=True,
    cwc=False,
    cwc_station=None,
):
    """
    Programmatic interface to SWIFT.

    Parameters
    ----------
    basin : str
        Basin name (e.g. "Krishna", "Godavari").
    datasets : list[str]
        Dataset flags identical to CLI (["q","rf","temp"]).
    start_date : str
    end_date : str
    merge : bool
    overwrite : bool
    output_dir : str
    delay : float
    format : str
    plot : bool
    metadata : bool
    quiet : bool
    cwc : bool
        Download CWC dataset instead of WRIS.
    cwc_station : list[str]
        Optional station filter.
    """

    # Build argument object similar to argparse
    args = SimpleNamespace()

    args.basin = basin
    args.start_date = start_date
    args.end_date = end_date or time.strftime("%Y-%m-%d")
    args.merge = merge
    args.overwrite = overwrite
    args.output_dir = output_dir
    args.delay = delay
    args.format = format
    args.plot = plot
    args.metadata = metadata
    args.quiet = quiet
    args.cwc = cwc
    args.cwc_station = cwc_station
    args.merge_only = False
    args.plot_only = False

    # dataset flags
    dataset_flags = [
        "q", "wl", "atm", "rf", "temp", "rh", "solar", "sed", "gwl"
    ]

    for flag in dataset_flags:
        setattr(args, flag, False)

    if datasets:
        for d in datasets:
            setattr(args, d, True)

    # ---------------------------------------------------------
    # CWC mode
    # ---------------------------------------------------------

    if cwc:
        return run_cwc_download(args)

    # ---------------------------------------------------------
    # WRIS mode
    # ---------------------------------------------------------

    if not basin:
        raise ValueError("basin must be specified for WRIS downloads")

    if basin in WRIS_BASINS:
        args.basin = WRIS_BASINS[basin]

    client = WrisClient(delay=delay)

    if not client.check_api():
        raise RuntimeError("WRIS API unavailable")

    basin_code = client.get_basin_code(args.basin)

    selected = selected_datasets(args)

    if not selected:
        raise ValueError("No dataset selected")

    return run_download(args, selected, client, basin_code)