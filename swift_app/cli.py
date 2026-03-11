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

WRIS_BASINS = OrderedDict({
    "1": "Brahmani and Baitarni",
    "2": "Cauvery",
    "3": "East flowing rivers between Mahanadi and Pennar",
    "4": "East flowing rivers between Pennar and Kanyakumari",
    "5": "Godavari",
    "6": "Krishna",
    "7": "Mahanadi",
    "8": "Mahi",
    "9": "Minor rivers draining into Myanmar and Bangladesh",
    "10": "Narmada",
    "11": "Pennar",
    "12": "Sabarmati",
    "13": "Subernarekha",
    "14": "Tapi",
    "15": "West flowing rivers from Tadri to Kanyakumari",
    "16": "West flowing rivers from Tapi to Tadri",
    "17": "West flowing rivers of Kutch and Saurashtra including Luni"
})

# Map dataset codes to short column names for the value column
DATASET_COLUMNS = {
    "DISCHARG": "q",
    "WATERLVL": "wl",
    "PRESS": "atm",
    "RAINF": "rf",
    "MT_TEMP": "temp",
    "HUMID": "rh",
    "SOLAR_RD": "solar",
    "SEDIM": "sed",
    "GWATERLVL": "gwl",
}


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for SWIFT CLI."""
    parser = argparse.ArgumentParser(
        prog="swift",
        description=(
            "SWIFT — Simple Water Information Fetch Tool\n\n"
            "Download hydrological datasets from the India WRIS portal without\n"
            "manually clicking through the website."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    basin_help = "River basin name or corresponding number:\n"
    for num, name in WRIS_BASINS.items():
        basin_help += f"  [{num}] {name}\n"

    required = parser.add_argument_group("Required arguments")
    required.add_argument(
        "-b",
        "--basin",
        help=basin_help,
    )

    datasets = parser.add_argument_group(
    "Datasets (WRIS or CWC depending on --cwc)")
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
    "--merge-only",
    action="store_true",
    help="Merge existing station files into a GeoPackage without downloading",
    )
    parser.add_argument(
    "--cwc",
    action="store_true",
    help="Download CWC real-time gauge data for all stations",
    )

    parser.add_argument(
    "--cwc-station",
    nargs="+",
    help="Download CWC data for specific station codes (see --list for details)",
    )
    download.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Delay between API requests (default: 0.25 seconds)",
    )
    download.add_argument(
        "--merge", action="store_true", help="Merge all station files into a GeoPackage"
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
        "--plot",
        action="store_true",
        help="Generate station time series plots after download",
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
    misc.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output (progress bars, banners) and run silently",
    )
    misc.add_argument("--list", action="store_true", help="List available WRIS basins and CWC station info")
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
