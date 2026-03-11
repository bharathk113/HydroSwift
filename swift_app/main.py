"""
SWIFT — Main CLI Entrypoint (Modular Core)
-------------------------------------------

Version: 0.4.1 — Delta Delhi

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
from .banner import print_wish_banner

import time


def _print_coffee() -> None:
    print(
        r"""
      ( (
       ) )
    ........
    |      |]
    \      /
     `----'
     TIME FOR A COFFEE BREAK
"""
    )


def main() -> int:
    """Main SWIFT execution entry point."""

    from .cli import build_parser, DATASETS, selected_datasets
    from .api import WrisClient
    from .plot import run_plot_only
    from .download import run_download
    from .cwc import run_cwc_download

    parser = build_parser()
    args = parser.parse_args()

    # ---------------------------------------------------------
    # Coffee ☕
    # ---------------------------------------------------------
    if args.coffee:
        _print_coffee()
        print("Many kinds of monkeys have a strong taste for tea, coffee and spirituous liqueurs. - Charles Darwin")

        # If coffee is the only flag → exit
        if not any([args.basin, args.cwc, args.cwc_station, args.plot_only]):
            return 0

        print("\nYour request is running while you enjoy your coffee ☕\n")

    # ---------------------------------------------------------
    # External List Mode
    # ---------------------------------------------------------

    if args.list:
        from .cli import WRIS_BASINS
        print("\nAvailable WRIS Basins:")
        for num, name in WRIS_BASINS.items():
            print(f"  [{num}] {name}")
        
        print("\nAvailable CWC Stations:")
        print("  The CWC dataset covers over 1,500 individual stations.")
        print("  To view the full catalog of station codes and names, please check the local file:")
        print("  →  swift_app/cwc_stations.csv")
        print("\n  If you are browsing the repository, you can find it here:")
        print("  →  https://github.com/carbform/swift/blob/dev/swift_app/cwc_stations.csv\n")
        
        return 0

    # ---------------------------------------------------------
    # Parse numbered basin input (WRIS only)
    # ---------------------------------------------------------
    
    if args.basin:
        from .cli import WRIS_BASINS
        if args.basin in WRIS_BASINS:
            key = str(args.basin).strip()
            if key in WRIS_BASINS:
                args.basin = WRIS_BASINS[key]
    # ---------------------------------------------------------
    # merge-only mode
    # ---------------------------------------------------------
    if args.merge_only:
        from .merge import run_merge_only
        return run_merge_only(args)
    # ---------------------------------------------------------
    # Plot-only mode
    # ---------------------------------------------------------

    if args.plot_only:

        if not args.cwc and not args.basin:
            raise SystemExit("Plot-only requires --basin (or -b) / --cwc")

        if args.basin and args.basin not in WRIS_BASINS:
            raise SystemExit(f"Invalid basin id: {args.basin}")

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
