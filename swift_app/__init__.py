"""SWIFT app package metadata.

Internal implementation package for SWIFT.
Public commands are still exposed through:
- python swift.py ...
- python -m swift ...
- swift ... (if installed)
"""

__version__ = "1.0.0"
__codename__ = "Arctic Amsterdam"

APP_NAME = "HydroSwift"
APP_TAGLINE = "Fast, unified workflows for hydrological data"
APP_ORG = "Carbform • carbform.github.io"

VERSION = f"{__version__}"
VERSION_FULL = f"{VERSION} — {__codename__}"

from .api import (
    wris,
    cwc_ns as cwc,
    help,
    cli_help,
    merge_only,
    plot_only,
    fetch,
    cite,
    coffee,
)
from .base_client import BaseHydrologyClient


_LEGACY_API_REDIRECTS = {
    "datasets": (
        "`swift.datasets` has been removed. "
        "Use `swift.wris.variables()` for WRIS variable definitions."
    ),
    "basins": (
        "`swift.basins()` has been removed. "
        "Use `swift.wris.basins()` for WRIS basins or `swift.cwc.basins()` for CWC basins."
    ),
    "merge": (
        "`swift.merge()` has been removed. Use `swift.merge_only()` instead."
    ),
    "plot": (
        "`swift.plot()` has been removed. Use `swift.plot_only()` instead."
    ),
}


def __getattr__(name: str):
    """Provide clear migration guidance for removed legacy API symbols."""
    if name in _LEGACY_API_REDIRECTS:
        raise AttributeError(_LEGACY_API_REDIRECTS[name])
    raise AttributeError(f"module 'swift_app' has no attribute {name!r}")
