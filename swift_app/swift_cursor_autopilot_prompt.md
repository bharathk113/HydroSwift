# SWIFT Refactor --- Cursor Autopilot Prompt (Diff‑Patch Mode)

Goal: Introduce namespaced APIs while preserving existing behaviour.

Namespaces:

swift.wris swift.cwc

Path parameters MUST remain:

input_dir output_dir

Do NOT rename them.

------------------------------------------------------------------------

# Step 1 --- Scan Repository

Identify modules:

swift_app/api.py swift_app/**init**.py swift_app/cli.py
swift_app/main.py

Engine modules (do not modify):

wris.py cwc.py merge.py plot.py wris_client.py

------------------------------------------------------------------------

# Step 2 --- Detect API Functions

Inside api.py locate:

download_wris download_cwc get_wris_data get_cwc_data wris_stations
cwc_stations search_stations cwc_station merge plot

Record their signatures.

Do NOT modify their internal logic.

------------------------------------------------------------------------

# Step 3 --- Create Namespace Classes

Add minimal code:

class \_WrisNamespace: pass

class \_CwcNamespace: pass

Generate patch only.

Example:

+class \_WrisNamespace: + pass

+class \_CwcNamespace: + pass

------------------------------------------------------------------------

# Step 4 --- Map Functions

Add wrapper methods.

Example:

class \_WrisNamespace:

    def download(self, *args, **kwargs):
        return download_wris(*args, **kwargs)

    def stations(self, *args, **kwargs):
        return wris_stations(*args, **kwargs)

CWC equivalent.

------------------------------------------------------------------------

# Step 5 --- Export Namespaces

Edit **init**.py:

from .api import \_WrisNamespace, \_CwcNamespace

wris = \_WrisNamespace() cwc = \_CwcNamespace()

------------------------------------------------------------------------

# Step 6 --- Add Compatibility Aliases

download_wris = wris.download download_cwc = cwc.download

get_wris_data = wris.download get_cwc_data = cwc.download

wris_stations = wris.stations cwc_stations = cwc.stations

------------------------------------------------------------------------

# Step 7 --- CLI Plot Support

In main.py after run_wris_download:

if args.plot: run_plot_only(args)

------------------------------------------------------------------------

# Patch Rules

Always generate unified diff patches.

Never rewrite full files.

Preserve formatting.

------------------------------------------------------------------------

# Verification

import swift

swift.wris.download( basin="godavari", variable="discharge",
output_dir="output" )

swift.cwc.download( station="040-CDJAPR" )
