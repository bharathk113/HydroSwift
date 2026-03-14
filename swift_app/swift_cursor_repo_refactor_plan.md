# SWIFT Refactor --- Repo‑Aware Cursor Agent Plan (input_dir / output_dir preserved)

This document guides a Cursor/Claude Code agent to safely refactor the
SWIFT repository.

IMPORTANT RULE: Do NOT rename path arguments. Keep:

input_dir output_dir

These names must remain unchanged across the API and CLI.

------------------------------------------------------------------------

# Repository Layout

swift_app/ **init**.py api.py cli.py main.py wris.py cwc.py merge.py
plot.py wris_client.py

Engine modules that must NOT be modified:

wris.py cwc.py merge.py plot.py wris_client.py

Only modify:

api.py **init**.py cli.py main.py

------------------------------------------------------------------------

# Commit 1 --- Namespace Skeleton

Open:

swift_app/api.py swift_app/**init**.py

Add namespace classes in api.py:

class \_WrisNamespace: pass

class \_CwcNamespace: pass

Expose them in **init**.py:

from .api import \_WrisNamespace, \_CwcNamespace

wris = \_WrisNamespace() cwc = \_CwcNamespace()

Commit message: feat(api): introduce wris and cwc namespace skeleton

------------------------------------------------------------------------

# Commit 2 --- Move Download APIs

Open:

swift_app/api.py

Wrap existing functions inside namespaces:

class \_WrisNamespace:

    def download(self, *args, **kwargs):
        return download_wris(*args, **kwargs)

class \_CwcNamespace:

    def download(self, *args, **kwargs):
        return download_cwc(*args, **kwargs)

Add compatibility aliases:

download_wris = wris.download download_cwc = cwc.download

get_wris_data = wris.download get_cwc_data = cwc.download

Emit DeprecationWarning for legacy names.

Commit message: refactor(api): move download APIs into namespaces

------------------------------------------------------------------------

# Commit 3 --- Move Station APIs

Move functions:

wris_stations cwc_stations

into namespace methods:

\_WrisNamespace.stations \_CwcNamespace.stations

Aliases:

wris_stations = wris.stations cwc_stations = cwc.stations
search_stations = wris.stations cwc_station = cwc.stations

Commit message: refactor(api): move station APIs into namespaces

------------------------------------------------------------------------

# Commit 4 --- CLI Compatibility

Open:

swift_app/cli.py swift_app/main.py

Ensure CLI arguments remain:

--input-dir --output-dir

Do NOT rename them.

Verify these modes still work:

--merge-only --plot-only

Commit message: refactor(cli): ensure namespace refactor keeps CLI
arguments stable

------------------------------------------------------------------------

# Commit 5 --- WRIS Plot Support

Modify main.py so WRIS downloads can plot immediately.

After:

run_wris_download(...)

add:

if args.plot: run_plot_only(args)

Commit message: feat(cli): enable WRIS plotting after download

------------------------------------------------------------------------

# Final API

import swift

swift.wris.download( basin="godavari", variable="discharge",
output_dir="output" )

swift.wris.stations(basin="godavari")

swift.cwc.download( station="040-CDJAPR" )
