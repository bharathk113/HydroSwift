"""
Public Python API for SWIFT.

Namespaced access (preferred):
    swift.wris.download(basin, variable, ...)
    swift.wris.stations(basin, ...)
    swift.cwc.download(station, ...)
    swift.cwc.stations(...)

Top-level helpers:
    swift.fetch(source, ...)
    swift.merge(...)
    swift.plot(...)
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import time

from .wris_client import WrisClient
from .cli import DATASETS, WRIS_BASINS
from .wris import run_wris_download, build_basin_structure, discover_stations
from .merge import run_merge_only
from .plot import run_plot_only
from .cwc import run_cwc_download, get_cwc_station_metadata


# ---------------------------------------------------------
# Dataset aliases  (human-friendly → CLI flag)
# ---------------------------------------------------------

DATASET_ALIAS = {
    "discharge": "q",
    "water_level": "wl",
    "atm_pressure": "atm",
    "atmospheric_pressure": "atm",
    "rainfall": "rf",
    "temperature": "temp",
    "humidity": "rh",
    "solar": "solar",
    "solar_radiation": "solar",
    "sediment": "sed",
    "groundwater": "gwl",
    "groundwater_level": "gwl",
}


# ---------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------

def _normalize_datasets_input(datasets):
    if datasets is None:
        return []
    if isinstance(datasets, str):
        datasets = [datasets]
    return list(datasets)


def _normalize_cwc_station_input(cwc_station):
    if cwc_station is None:
        return None
    if isinstance(cwc_station, (str, int)):
        return [str(cwc_station)]
    return [str(x) for x in cwc_station]


def _normalize_wris_station_input(station):
    """Normalise WRIS station input to a list of codes or None."""
    if station is None:
        return None
    if isinstance(station, (str, int)):
        return [str(station)]
    return [str(x) for x in station]


def _normalize_dataset_flags(datasets):
    if not datasets:
        return []
    flags = []
    for d in datasets:
        if d in DATASET_ALIAS:
            flags.append(DATASET_ALIAS[d])
        elif d in DATASET_ALIAS.values():
            flags.append(d)
        else:
            valid = sorted(DATASET_ALIAS.keys()) + sorted(DATASET_ALIAS.values())
            raise ValueError(
                f"Unknown dataset: {d}. Supported values: {', '.join(valid)}"
            )
    return flags


def _build_args(**kwargs):
    args = SimpleNamespace()
    args.basin = kwargs.get("basin")
    args.start_date = kwargs.get("start_date", "1950-01-01")
    args.end_date = kwargs.get("end_date") or time.strftime("%Y-%m-%d")
    args.merge = kwargs.get("merge", False)
    args.merge_only = kwargs.get("merge_only", False)
    args.plot_only = kwargs.get("plot_only", False)
    args.overwrite = kwargs.get("overwrite", False)
    args.output_dir = kwargs.get("output_dir")
    args.input_dir = kwargs.get("input_dir")
    args.delay = kwargs.get("delay", 0.25)
    args.format = kwargs.get("format", "csv")
    args.plot = kwargs.get("plot", False)
    args.metadata = kwargs.get("metadata", False)
    args.quiet = kwargs.get("quiet", False)
    args.cwc = kwargs.get("cwc", False)
    args.cwc_station = kwargs.get("cwc_station")
    args.stations = kwargs.get("stations")
    args.cwc_refresh = kwargs.get("cwc_refresh", False)
    dataset_keys = ["q", "wl", "atm", "rf", "temp", "rh", "solar", "sed", "gwl"]
    for key in dataset_keys:
        setattr(args, key, False)
    for flag in kwargs.get("dataset_flags", []):
        setattr(args, flag, True)
    return args


def _resolve_basin(basin):
    """Normalise basin input (int / number-string / name) to a basin name."""
    if isinstance(basin, int):
        basin = str(basin)
    if basin in WRIS_BASINS:
        return WRIS_BASINS[basin]
    return basin


# ============================================================
# PRIMARY PUBLIC API
# ============================================================


def get_wris_data(
    var,
    basin,
    *,
    station=None,
    start_date="1950-01-01",
    end_date=None,
    output_dir="output",
    format="csv",
    overwrite=False,
    merge=False,
    plot=False,
    delay=0.25,
    quiet=False,
):
    """
    Download WRIS time-series data to files.

    Parameters
    ----------
    var : str or list[str]
        Variable(s) to download.  Accepts human-friendly names
        (``'discharge'``, ``'water_level'``, ``'rainfall'``, etc.)
        or short codes (``'q'``, ``'wl'``, ``'rf'``).
    basin : str or int
        Basin name or number (see ``swift.basins()``).
    station : str or list[str], optional
        Limit to specific station code(s).
    start_date, end_date : str
        ISO date strings (``'YYYY-MM-DD'``).
    output_dir : str
        Root output directory.
    format : ``'csv'`` | ``'xlsx'``
    overwrite : bool
        Re-download existing files.
    merge : bool
        Merge station files into a GeoPackage.
    plot : bool
        Generate hydrograph plots after download.
    delay : float
        Seconds between WRIS API requests.
    quiet : bool
        Suppress progress output.

    Examples
    --------
    >>> swift.get_wris_data('discharge', 'Krishna')
    >>> swift.get_wris_data(['discharge', 'rainfall'], basin=6,
    ...                     start_date='2020-01-01', merge=True)
    """
    datasets = _normalize_datasets_input(var)
    if not datasets:
        raise ValueError("var must specify at least one dataset")

    dataset_flags = _normalize_dataset_flags(datasets)
    if format not in {"csv", "xlsx"}:
        raise ValueError("format must be one of: csv, xlsx")

    basin_name = _resolve_basin(basin)
    stations = _normalize_wris_station_input(station)

    args = _build_args(
        basin=basin_name,
        start_date=start_date,
        end_date=end_date,
        merge=merge,
        overwrite=overwrite,
        output_dir=str(Path(output_dir)),
        delay=delay,
        format=format,
        plot=plot,
        quiet=quiet,
        dataset_flags=dataset_flags,
        stations=stations,
    )

    client = WrisClient(delay=delay)
    if not client.check_api():
        raise RuntimeError("WRIS API unavailable")

    basin_code = client.get_basin_code(args.basin)

    selected = {}
    for flag in dataset_flags:
        dataset_code, folder = DATASETS[flag]
        selected[dataset_code] = folder

    if not selected:
        raise ValueError("No datasets selected")

    run_wris_download(args, selected, client, basin_code)

    if plot:
        plot_args = _build_args(
            basin=args.basin,
            output_dir=str(Path(output_dir)),
            plot_only=True,
            dataset_flags=dataset_flags,
        )
        run_plot_only(plot_args)

    return None


def get_cwc_data(
    station=None,
    *,
    var=None,
    start_date=None,
    end_date=None,
    output_dir="output",
    format="csv",
    overwrite=False,
    merge=False,
    plot=False,
    quiet=False,
    refresh=False,
):
    """
    Download CWC water-level time-series data to files.

    The CWC flood-forecasting network only provides **water level**
    data.  If ``var`` is passed with any other value a warning is
    issued and the argument is ignored.

    Parameters
    ----------
    station : str or list[str], optional
        CWC station code(s).  Downloads all stations when omitted.
    var : ignored
        Accepted for API symmetry with :func:`get_wris_data` but CWC
        only provides water level.  A warning is raised if a non-water-
        level value is supplied.
    start_date, end_date : str, optional
        ISO date strings.
    output_dir : str
        Root output directory.
    format : ``'csv'`` | ``'xlsx'``
    overwrite : bool
        Re-download existing files.
    merge : bool
        Merge station files into a GeoPackage.
    plot : bool
        Generate hydrograph plots after download.
    quiet : bool
        Suppress progress output.
    refresh : bool
        Refresh CWC station metadata from the live API before
        downloading.

    Examples
    --------
    >>> swift.get_cwc_data()
    >>> swift.get_cwc_data(station='032-LGDHYD', start_date='2020-01-01')
    """
    if var is not None:
        allowed = {"water_level", "wl"}
        given = {var} if isinstance(var, str) else set(var)
        bad = given - allowed
        if bad:
            warnings.warn(
                f"CWC only provides water level data. "
                f"Ignoring unsupported variable(s): {', '.join(sorted(bad))}",
                stacklevel=2,
            )

    if format not in {"csv", "xlsx"}:
        raise ValueError("format must be one of: csv, xlsx")

    cwc_station = _normalize_cwc_station_input(station)

    args = _build_args(
        cwc=True,
        cwc_station=cwc_station,
        cwc_refresh=refresh,
        start_date=start_date or "1950-01-01",
        end_date=end_date,
        overwrite=overwrite,
        merge=merge,
        plot=plot,
        output_dir=str(Path(output_dir)),
        format=format,
        quiet=quiet,
    )

    run_cwc_download(args)
    return None


# ---------------------------------------------------------
# Station discovery (internal; use swift.wris.stations / swift.cwc.stations)
# ---------------------------------------------------------

def wris_stations(basin, var="discharge", delay=0.25):
    """
    List available WRIS stations in a basin.

    Parameters
    ----------
    basin : str or int
        Basin name or number.
    var : str
        Dataset variable (default ``'discharge'``).
    delay : float
        Seconds between API requests.

    Returns
    -------
    SwiftTable
    """
    if var in DATASET_ALIAS:
        dataset_flag = DATASET_ALIAS[var]
    else:
        dataset_flag = var

    dataset_code, _ = DATASETS[dataset_flag]
    basin_name = _resolve_basin(basin)

    client = WrisClient(delay=delay)
    basin_code = client.get_basin_code(basin_name)
    basin_structure = build_basin_structure(client, basin_code)

    station_river_fallback: dict[str, str] = {}
    try:
        tributaries = client.get_tributaries(basin_code, dataset_code)
        for trib in tributaries:
            trib_id = trib.get("tributaryid")
            trib_name = (
                trib.get("tributary")
                or trib.get("tributaryName")
                or trib.get("tributaryname")
            )
            rivers = client.get_rivers(trib_id, dataset_code)
            for river in rivers:
                river_id = river.get("localriverid")
                river_name = (
                    river.get("riverName")
                    or river.get("localriver")
                    or river.get("localRiver")
                    or river.get("localrivername")
                    or river.get("river")
                )
                agencies = client.get_agencies(trib_id, river_id, dataset_code)
                for agency in agencies:
                    agency_id = agency.get("agencyid")
                    stations_items = client.get_stations(
                        trib_id, river_id, agency_id, dataset_code,
                    )
                    for s in stations_items:
                        code = s.get("stationcode")
                        if not code:
                            continue
                        label = (
                            river_name
                            or s.get("riverName")
                            or s.get("river")
                            or trib_name
                        )
                        if label and code not in station_river_fallback:
                            station_river_fallback[code] = label
    except Exception:
        pass

    agency_cache: dict = {}
    station_cache: dict = {}

    stations = discover_stations(
        client, basin_structure, dataset_code, agency_cache, station_cache,
    )

    records = []
    for s in stations:
        meta = client.get_metadata(s, dataset_code)
        if not meta:
            continue
        records.append({
            "station_code": s,
            "station_name": meta.get("station_Name"),
            "latitude": meta.get("latitude"),
            "longitude": meta.get("longitude"),
            "river": (
                meta.get("riverName")
                or meta.get("river")
                or station_river_fallback.get(s)
            ),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("station_code").reset_index(drop=True)
    return SwiftTable(df.copy())


def cwc_stations(station=None, basin=None, river=None, refresh=False):
    """
    Return CWC flood-forecast station metadata.

    By default reads the packaged metadata file shipped with SWIFT
    (fast, no network).  Pass ``refresh=True`` to fetch live data from
    the CWC FFS portal.

    Parameters
    ----------
    station : str, optional
        Station code or partial name.
    basin : str, optional
        Basin name filter (substring, case-insensitive).
    river : str, optional
        River name filter (substring, case-insensitive).
    refresh : bool, default False
        If True, fetch fresh metadata from the CWC API (~2 min).
        Metadata is mostly static and only changes when a new HFL is
        recorded, so the packaged file is usually sufficient.

    Returns
    -------
    SwiftTable

    Examples
    --------
    >>> swift.cwc_stations()
    >>> swift.cwc_stations(station="032-LGDHYD")
    >>> swift.cwc_stations(basin="godavari")
    >>> swift.cwc_stations(refresh=True)
    """
    df = get_cwc_station_metadata(
        station=station, basin=basin, river=river, refresh=refresh,
    )
    return SwiftTable(df.copy())


# ============================================================
# NAMESPACED API  (preferred public interface)
# ============================================================

class _WrisNamespace:
    """``swift.wris`` namespace for India-WRIS operations."""

    @staticmethod
    def download(
        basin,
        variable,
        *,
        station=None,
        start_date="1950-01-01",
        end_date=None,
        output_dir="output",
        format="csv",
        overwrite=False,
        merge=False,
        plot=False,
        delay=0.25,
        quiet=False,
    ):
        """Download WRIS time-series data.

        Parameters
        ----------
        basin : str or int
            Basin name or number.
        variable : str or list[str]
            Dataset variable(s) (``'discharge'``, ``'rainfall'``, etc.).
        station : str or list[str], optional
            Limit to specific station code(s).
        start_date, end_date : str
            ISO date strings.
        output_dir : str
            Root output directory.
        format : ``'csv'`` | ``'xlsx'``
        overwrite, merge, plot, quiet : bool
        delay : float
            Seconds between API requests.
        """
        return get_wris_data(
            var=variable,
            basin=basin,
            station=station,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            format=format,
            overwrite=overwrite,
            merge=merge,
            plot=plot,
            delay=delay,
            quiet=quiet,
        )

    @staticmethod
    def stations(basin, variable="discharge", delay=0.25):
        """List available WRIS stations in a basin.

        Returns
        -------
        SwiftTable
        """
        return wris_stations(basin=basin, var=variable, delay=delay)


class _CwcNamespace:
    """``swift.cwc`` namespace for CWC flood-forecast operations."""

    @staticmethod
    def download(
        station=None,
        *,
        start_date=None,
        end_date=None,
        output_dir="output",
        format="csv",
        overwrite=False,
        merge=False,
        plot=False,
        quiet=False,
        refresh=False,
    ):
        """Download CWC water-level time-series data.

        Parameters
        ----------
        station : str or list[str], optional
            CWC station code(s).  Downloads all when omitted.
        start_date, end_date : str, optional
            ISO date strings.
        output_dir : str
            Root output directory.
        format : ``'csv'`` | ``'xlsx'``
        overwrite, merge, plot, quiet : bool
        refresh : bool
            Refresh station metadata before downloading.
        """
        return get_cwc_data(
            station=station,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            format=format,
            overwrite=overwrite,
            merge=merge,
            plot=plot,
            quiet=quiet,
            refresh=refresh,
        )

    @staticmethod
    def stations(station=None, basin=None, river=None, refresh=False):
        """Return CWC flood-forecast station metadata.

        Returns
        -------
        SwiftTable
        """
        return cwc_stations(station=station, basin=basin, river=river,
                            refresh=refresh)


wris = _WrisNamespace()
cwc_ns = _CwcNamespace()


# ============================================================
# UNIFIED FETCH HELPER
# ============================================================

def fetch(
    source,
    basin=None,
    station=None,
    variable=None,
    *,
    output_dir="output",
    start_date="1950-01-01",
    end_date=None,
    merge=False,
    plot=False,
    quiet=False,
    **kwargs,
):
    """Download data from WRIS or CWC with a single entry point.

    Parameters
    ----------
    source : ``'wris'`` | ``'cwc'``
        Data source to fetch from.
    basin : str or int, optional
        Basin (required for WRIS).
    station : str or list[str], optional
        Station code(s).
    variable : str or list[str], optional
        Dataset variable(s) (required for WRIS).
    output_dir : str
        Root output directory.
    start_date, end_date : str
        ISO date strings.
    merge, plot, quiet : bool
    **kwargs
        Forwarded to the underlying download function.
    """
    source = source.lower().strip()
    if source == "wris":
        if variable is None:
            raise ValueError("variable is required for source='wris'")
        if basin is None:
            raise ValueError("basin is required for source='wris'")
        return wris.download(
            basin=basin,
            variable=variable,
            station=station,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            merge=merge,
            plot=plot,
            quiet=quiet,
            **kwargs,
        )
    elif source == "cwc":
        return cwc_ns.download(
            station=station,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            merge=merge,
            plot=plot,
            quiet=quiet,
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unknown source: {source!r}. Use 'wris' or 'cwc'."
        )


# ---------------------------------------------------------
# Merge / Plot
# ---------------------------------------------------------

def _resolve_mode_input_dir(mode, basin, output_dir):
    """Derive ``input_dir`` from *mode* and *basin* using SWIFT conventions."""
    base = Path(output_dir or "output")
    if mode == "wris":
        if basin is None:
            return str(base)
        return str(base / _resolve_basin(basin))
    elif mode == "cwc":
        return str(base)
    raise ValueError(f"Unknown mode: {mode!r}. Use 'wris' or 'cwc'.")


def merge(
    input_dir=None,
    datasets=None,
    output_dir=None,
    *,
    mode=None,
    basin=None,
    variable=None,
):
    """
    Merge existing SWIFT station files into GeoPackages.

    Can be called with an explicit ``input_dir`` (legacy) or with
    ``mode`` / ``basin`` / ``variable`` for a higher-level interface.

    Parameters
    ----------
    input_dir : str or Path, optional
        Root directory containing SWIFT output.  Inferred from *mode*
        and *basin* when not given.
    datasets : str or list[str], optional
        Subset of variables to merge.
    output_dir : str or Path, optional
        Destination for merged GeoPackages (defaults to *input_dir*).
    mode : ``'wris'`` | ``'cwc'``, optional
        Data source mode.  When provided, ``input_dir`` is derived
        automatically from the SWIFT output directory layout.
    basin : str or int, optional
        Basin (used with ``mode='wris'``).
    variable : str or list[str], optional
        Alias for *datasets* (preferred name for new code).
    """
    if variable is not None and datasets is None:
        datasets = variable if isinstance(variable, list) else [variable]
    if mode is not None and input_dir is None:
        input_dir = _resolve_mode_input_dir(mode, basin, output_dir)
    if input_dir is None:
        raise ValueError(
            "input_dir must be specified (or provide mode= to derive it)"
        )
    p = Path(input_dir)
    if not p.exists():
        raise ValueError("input_dir does not exist")
    dataset_flags = _normalize_dataset_flags(datasets)
    args = _build_args(
        input_dir=str(p),
        output_dir=str(output_dir) if output_dir else None,
        merge_only=True,
        dataset_flags=dataset_flags,
        cwc=(mode == "cwc") if mode else False,
    )
    run_merge_only(args)
    return None


def plot(
    input_dir=None,
    datasets=None,
    output_dir=None,
    cwc=False,
    *,
    mode=None,
    basin=None,
    variable=None,
):
    """
    Generate hydrograph plots from existing SWIFT output.

    Can be called with an explicit ``input_dir`` (legacy) or with
    ``mode`` / ``basin`` / ``variable`` for a higher-level interface.

    Parameters
    ----------
    input_dir : str or Path, optional
        Root directory containing SWIFT output.  Inferred from *mode*
        and *basin* when not given.
    datasets : str or list[str], optional
        Subset of variables to plot.
    output_dir : str or Path, optional
        Destination for plot images (defaults to *input_dir*).
    cwc : bool, default False
        Legacy flag -- prefer ``mode='cwc'``.
    mode : ``'wris'`` | ``'cwc'``, optional
        Data source mode.
    basin : str or int, optional
        Basin (used with ``mode='wris'``).
    variable : str or list[str], optional
        Alias for *datasets*.
    """
    if variable is not None and datasets is None:
        datasets = variable if isinstance(variable, list) else [variable]
    if mode is not None:
        if mode == "cwc":
            cwc = True
        if input_dir is None:
            input_dir = _resolve_mode_input_dir(mode, basin, output_dir)
    if input_dir is None:
        raise ValueError(
            "input_dir must be specified (or provide mode= to derive it)"
        )
    p = Path(input_dir)
    if not p.exists():
        raise ValueError("input_dir does not exist")
    dataset_flags = _normalize_dataset_flags(datasets)
    args = _build_args(
        input_dir=str(p),
        output_dir=str(output_dir) if output_dir else None,
        plot_only=True,
        dataset_flags=dataset_flags,
        cwc=cwc,
    )
    run_plot_only(args)
    return None


# ---------------------------------------------------------
# SwiftTable (DataFrame wrapper for nicer notebook display)
# ---------------------------------------------------------

class SwiftTable(pd.DataFrame):
    """DataFrame subclass with a SWIFT header in ``repr``."""

    @property
    def _constructor(self):
        return SwiftTable

    def __repr__(self):
        rows, cols = self.shape
        header = (
            f"SWIFT Table\n"
            f"Rows: {rows:,} | Columns: {cols}\n"
            f"{'-' * 40}\n"
        )
        return header + super().__repr__()


# ---------------------------------------------------------
# Notebook helpers  (tab-completion namespaces)
# ---------------------------------------------------------

class _DatasetNamespace:
    """Provides tab-completion for dataset names in notebooks."""

    discharge = "discharge"
    water_level = "water_level"
    atm_pressure = "atm_pressure"
    rainfall = "rainfall"
    temperature = "temperature"
    humidity = "humidity"
    solar = "solar"
    solar_radiation = "solar_radiation"
    sediment = "sediment"
    groundwater = "groundwater"
    groundwater_level = "groundwater_level"

    def __call__(self):
        return [
            self.discharge, self.water_level, self.atm_pressure,
            self.rainfall, self.temperature, self.humidity,
            self.solar, self.solar_radiation, self.sediment,
            self.groundwater, self.groundwater_level,
        ]


datasets = _DatasetNamespace()


class _BasinNamespace:
    """Tab-completion helper for basin names."""

    def __init__(self, basin_mapping):
        self._mapping = basin_mapping
        for code, name in basin_mapping.items():
            key = name.lower()
            key = re.sub(r"[^\w]+", "_", key)
            key = re.sub(r"_+", "_", key).strip("_")
            setattr(self, key, name)

    def __call__(self):
        records = [{"id": k, "basin": v} for k, v in self._mapping.items()]
        return SwiftTable(pd.DataFrame(records))


basins = _BasinNamespace(WRIS_BASINS)


# ---------------------------------------------------------
# Citation / Easter eggs
# ---------------------------------------------------------

from .banner import print_wish_banner


def cite():
    """Print the banner and citation information."""
    print_wish_banner()
    print(
        """
    If you use SWIFT in your research, please cite:

    Sarat, C., Dash, D., & Kumar, A. (2026).
    SWIFT: Automated Retrieval of Hydrological Station Data
    from India-WRIS and CWC Portals.
    Journal of Open Source Software.

    Repository:
    https://github.com/carbform/swift
    """
    )


def coffee():
    """SWIFT coffee break easter egg for notebooks."""
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
    print(
        "Many kinds of monkeys have a strong taste for tea, "
        "coffee and spirituous liqueurs. - Charles Darwin"
    )
    return None
