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
    """CLI main function."""
    parser = build_parser()
    args = parser.parse_args()

    if args.coffee:
        _print_coffee()

    if args.plot_only:
        return run_plot_only(args)

    selected = selected_datasets(args)
    if not selected:
        raise SystemExit("No dataset selected")

    client = WrisClient(delay=args.delay)
    if not client.check_api():
        return 1

    basin_code = client.get_basin_code(args.basin)
    result = run_download(args=args, selected=selected, client=client, basin_code=basin_code)

    print("\nDone!")
    print(f"Downloaded Data for {args.start_date} → {args.end_date}")
    print("Total stations downloaded:", result["downloaded_count"])
    print("Files saved in:", result["base_output"])
    print(time.strftime("%Y-%m-%d %H:%M:%S"))
    return 0


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
