"""
SWIFT — Main CLI Entrypoint (Modular Core)
-------------------------------------------

Version: 0.4.0 — Delta Delhi

Author
------
Carbform (www.carbform.github.io)

Code structure, formatting and banner art assisted by GPT-5.3.
(Thanks GPT Go! I'm too poor to afford Claude.)

What this is
------------

This is the modular runtime entrypoint used by both:

    python swift.py ...
    swift ...           (if installed)

The legacy top-level script is kept for habit-friendly usage,
while orchestration now lives in this package file.

If you are reading this while debugging at 2 AM:
- drink water
- then coffee
- then inspect `args.plot_only`
"""

from __future__ import annotations

import time

from .api import WrisClient
from .banner import print_wish_banner
from .cli import build_parser, selected_datasets
from .download import run_download
from .plot import run_plot_only


# ============================================================
# SWIFT Version Information (core entrypoint metadata)
# ============================================================

APP_NAME = "SWIFT — Simple WRIS India Fetch Tool"
APP_ORG = "Carbform • carbform.github.io"

VERSION_MAJOR = 0
VERSION_MINOR = 4
VERSION_PATCH = 0

VERSION_CODENAME = "Delta Delhi"

VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
VERSION_FULL = f"{VERSION} — {VERSION_CODENAME}"


def _print_coffee() -> None:
    print(
        r"""
       ( (
        ) )
      ........
      |      |]
      \      /
       `----'

Science runs on coffee ☕
"""
    )


def main() -> int:
    """Main SWIFT execution entry point."""

    from .cli import build_parser, DATASETS
    from .plot import run_plot_only
    from .download import run_download
    from .cwc import run_cwc_download

    parser = build_parser()
    args = parser.parse_args()

    # ---------------------------------------------------------
    # Coffee ☕
    # ---------------------------------------------------------

    if args.coffee:
        print("Buy the developer a coffee ☕")
        print("UPI: carbform@upi\n")
        return 0

    # ---------------------------------------------------------
    # Station listing mode
    # ---------------------------------------------------------

    if args.stations:

        from .api import WRISAPI

        api = WRISAPI()

        print("\nAvailable basins:\n")

        basins = api.get_basin_list()

        for basin in basins:
            print(basin)

        return 0

    # ---------------------------------------------------------
    # Plot-only mode
    # ---------------------------------------------------------

    if args.plot_only:
        return run_plot_only(args)

    # ---------------------------------------------------------
    # Dataset compatibility check
    # ---------------------------------------------------------

    if args.cwc:

        unsupported = []

        if args.q:
            unsupported.append("discharge")

        if args.rf:
            unsupported.append("rainfall")

        if args.temp:
            unsupported.append("temperature")

        if args.rh:
            unsupported.append("humidity")

        if args.solar:
            unsupported.append("solar radiation")

        if args.sed:
            unsupported.append("sediment")

        if args.gwl:
            unsupported.append("groundwater")

        if args.atm:
            unsupported.append("atmospheric pressure")

        if unsupported:

            print("\nWARNING:")
            print("CWC API only supports water level data.")
            print("Ignoring unsupported datasets:", ", ".join(unsupported))
            print()

    # ---------------------------------------------------------
    # CWC mode
    # ---------------------------------------------------------

    if args.cwc or args.cwc_station:
        return run_cwc_download(args)
    # ---------------------------------------------------------
    # Default WRIS download
    # ---------------------------------------------------------

    if not args.basin:
        raise SystemExit("Error: basin required unless using --cwc")

    client = WrisClient(delay=args.delay)

    if not client.check_api():
        raise SystemExit(1)

    basin_code = client.get_basin_code(args.basin)

    selected = selected_datasets(args)

    if not selected:
        raise SystemExit("No dataset selected")

    return run_download(args, selected, client, basin_code)




if __name__ == "__main__":
    try:
        print_wish_banner()
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user.")
        raise SystemExit(130)
    except Exception as exc:
        print("\nERROR: SWIFT encountered an unexpected issue.")
        print("Reason:", str(exc))
        print("Try running again or check network/API status.")
        raise SystemExit(1)
