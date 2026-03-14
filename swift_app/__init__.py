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

from .api import (
    wris,
    cwc_ns as cwc,
    merge,
    plot,
    fetch,
    datasets,
    basins,
    cite,
    coffee,
)
from .base_client import BaseHydrologyClient
