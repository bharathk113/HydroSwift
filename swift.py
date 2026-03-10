"""
SWIFT — Simple WRIS India Fetch Tool
Legacy launcher for the modular SWIFT package.

Allows execution without installation:

    python swift.py -b Krishna -q
"""

from swift_app import APP_NAME, APP_ORG, __version__, __codename__
from swift_app.banner import print_wish_banner
from swift_app.main import main


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


