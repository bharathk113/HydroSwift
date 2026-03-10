"""SWIFT app package metadata.

Internal implementation package for SWIFT.
Public commands are still exposed through:
- python swift.py ...
- python -m swift ...
- swift ... (if installed)
"""

__version__ = "0.4.0"
__codename__ = "Delta Delhi"

APP_NAME = "SWIFT — Simple WRIS India Fetch Tool"
APP_ORG = "Carbform • carbform.github.io"

VERSION = f"{__version__}"
VERSION_FULL = f"{VERSION} — {__codename__}"
