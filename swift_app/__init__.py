"""SWIFT app package metadata.

Internal implementation package for SWIFT.
Public commands are still exposed through:
- python swift.py ...
- python -m swift ...
- swift ... (if installed)
"""

__version__ = "1.0.0"
__codename__ = "Arctic Amsterdam"

APP_NAME = "SWIFT — Simple Water Information Fetch Tool"
APP_ORG = "Carbform • carbform.github.io"

VERSION = f"{__version__}"
VERSION_FULL = f"{VERSION} — {__codename__}"

from .api_public import (
    download,
    merge,
    plot,
    datasets,
    basins,
    search_stations,
    cite,
    coffee,
)
