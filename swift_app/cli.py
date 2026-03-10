"""Command-line parsing for SWIFT."""

from __future__ import annotations

import argparse
import time
from collections import OrderedDict

DATASETS = OrderedDict(
    {
        "q": ("DISCHARG", "discharge"),
        "wl": ("WATERLVL", "water_level"),
        "atm": ("PRESS", "atm_pressure"),
        "rf": ("RAINF", "rainfall"),
        "temp": ("MT_TEMP", "temperature"),
        "rh": ("HUMID", "humidity"),
        "solar": ("SOLAR_RD", "solar_radiation"),
        "sed": ("SEDIM", "sediment"),
        "gwl": ("GWATERLVL", "groundwater_level"),
    }
)


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for SWIFT CLI."""
    parser = argparse.ArgumentParser(
        prog="swift",
        description=(
            "SWIFT — Simple WRIS India Fetch Tool\n\n"
            "Download hydrological datasets from the India WRIS portal without\n"
            "manually clicking through the website."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "-b",
        "--basin",
        required=True,
        help="River basin name (example: Krishna, Godavari)",
    )

    datasets = parser.add_argument_group("Datasets")
    datasets.add_argument("-q", action="store_true", help="River discharge")
    datasets.add_argument("-wl", action="store_true", help="River water level")
    datasets.add_argument("-atm", action="store_true", help="Atmospheric pressure")
    datasets.add_argument("-rf", action="store_true", help="Rainfall")
    datasets.add_argument("-temp", action="store_true", help="Temperature")
    datasets.add_argument("-rh", action="store_true", help="Relative humidity")
    datasets.add_argument("-solar", action="store_true", help="Solar radiation")
    datasets.add_argument("-sed", action="store_true", help="Suspended sediment")
    datasets.add_argument("-gwl", action="store_true", help="Groundwater level")

    download = parser.add_argument_group("Download behaviour")
    download.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing files"
    )
    download.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Delay between API requests (default: 0.25 seconds)",
    )
    download.add_argument(
        "--merge", action="store_true", help="Merge all station files into one dataset"
    )
    download.add_argument(
        "--start-date",
        default="1950-01-01",
        help="Start date for time series download (YYYY-MM-DD)",
    )
    download.add_argument(
        "--end-date",
        default=time.strftime("%Y-%m-%d"),
        help="End date for time series download (YYYY-MM-DD)",
    )

    output = parser.add_argument_group("Output options")
    output.add_argument(
        "--metadata", action="store_true", help="Save station metadata as CSV"
    )
    output.add_argument(
        "--geopackage", action="store_true", help="Export station locations as GeoPackage"
    )
    output.add_argument(
        "--plot",
        action="store_true",
        help="Generate station time series plots after download",
    )
    output.add_argument(
        "--stations", action="store_true", help="Export discovered station list"
    )
    output.add_argument(
        "--output-dir", default="output", help="Custom output directory (default: output)"
    )
    output.add_argument(
    "--format",
    choices=["csv", "xlsx"],
    default="csv",
    help="Output file format (default: csv)",
    )

    misc = parser.add_argument_group("Misc")
    misc.add_argument("--coffee", action="store_true", help="Take a virtual coffee break ☕")
    misc.add_argument(
        "--plot-only",
        action="store_true",
        help="Generate plots from existing SWIFT output (no download)",
    )

    return parser


def selected_datasets(args: argparse.Namespace) -> dict[str, str]:
    """Map selected CLI flags to WRIS dataset code => output folder."""
    selected: dict[str, str] = {}
    for key, (dataset_code, folder_name) in DATASETS.items():
        if getattr(args, key):
            selected[dataset_code] = folder_name
    return selected
