import sys
import pytest
import pandas as pd

from swift_app.api import _normalize_dataset_flags


def _get_cwc_engine_module():
    """Return the actual swift_app.cwc *module* (not the namespace object).

    ``swift_app.__init__`` exports ``cwc = _CwcNamespace()``, which shadows
    the ``swift_app.cwc`` submodule as a package attribute.  Tests that need
    to monkeypatch the engine module (e.g. ``PACKAGED_CSV``) must retrieve
    the module object from ``sys.modules`` instead.
    """
    import swift_app  # noqa: F401 – ensure __init__ has been loaded
    return sys.modules["swift_app.cwc"]


def test_dataset_aliases_cover_cli_style_and_python_style_names():
    flags = _normalize_dataset_flags(
        ["discharge", "atm_pressure", "solar_radiation", "groundwater_level"]
    )
    assert flags == ["q", "atm", "solar", "gwl"]


def test_unknown_dataset_error_is_actionable():
    with pytest.raises(ValueError, match="Supported values"):
        _normalize_dataset_flags(["bogus_dataset"])


def test_wris_stations_populates_river_from_discovery_fallback(monkeypatch):
    import swift_app.api as api_mod
    import swift_app.wris as wris_mod

    class DummyClient:
        def __init__(self, delay=0.25):
            self.delay = delay

        def get_basin_code(self, basin):
            return "5"

        def get_tributaries(self, basin_code, dataset_code):
            return [{"tributaryid": "t1", "tributary": "Trib-A"}]

        def get_rivers(self, tributary_id, dataset_code):
            return [{"localriverid": "r1", "riverName": "River-X"}]

        def get_agencies(self, tributary_id, localriver_id, dataset_code):
            return [{"agencyid": "a1"}]

        def get_stations(self, tributary_id, localriver_id, agency_id, dataset_code):
            return [{"stationcode": "S1"}]

        def get_metadata(self, station_code, dataset_code):
            return {
                "station_Name": "Demo Station",
                "latitude": 10.0,
                "longitude": 20.0,
                "riverName": None,
            }

    monkeypatch.setattr(api_mod, "WrisClient", DummyClient)
    monkeypatch.setattr(api_mod, "build_basin_structure", lambda client, basin_code: [("t1", "r1")])
    monkeypatch.setattr(api_mod, "discover_stations", lambda *args, **kwargs: ["S1"])

    out = api_mod.wris.stations("Godavari")

    assert len(out) == 1
    assert out.loc[0, "river"] == "River-X"


def test_cwc_stations_refresh_uses_live_fetch(monkeypatch, tmp_path):
    import swift_app.api as api_mod
    cwc_mod = _get_cwc_engine_module()

    fresh = pd.DataFrame(
        [
            {"code": "AAA001", "name": "Station A"},
            {"code": "BBB001", "name": "Station B"},
        ]
    )

    monkeypatch.setattr(cwc_mod, "fetch_cwc_station_metadata", lambda: fresh)
    monkeypatch.setattr(cwc_mod, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cwc_mod, "CACHE_FILE", tmp_path / "cwc_meta.csv")

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = api_mod.cwc_ns.stations(refresh=True)

    assert list(out["code"]) == ["AAA001", "BBB001"]


def test_cwc_stations_refresh_falls_back_when_live_unavailable(monkeypatch, tmp_path):
    import swift_app.api as api_mod
    cwc_mod = _get_cwc_engine_module()

    monkeypatch.setattr(cwc_mod, "fetch_cwc_station_metadata", lambda: pd.DataFrame())
    monkeypatch.setattr(cwc_mod, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cwc_mod, "CACHE_FILE", tmp_path / "nonexistent_cache.csv")

    fallback = tmp_path / "packaged.csv"
    fallback.write_text("code,name\n040-CDJAPR,Parwan pick-up Weir\n")
    monkeypatch.setattr(cwc_mod, "PACKAGED_CSV", fallback)

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = api_mod.cwc_ns.stations(refresh=True)

    assert len(out) == 1
    assert out.iloc[0]["code"] == "040-CDJAPR"


def test_cwc_stations_default_uses_packaged_csv(monkeypatch, tmp_path):
    import swift_app.api as api_mod
    cwc_mod = _get_cwc_engine_module()

    local_csv = tmp_path / "local.csv"
    local_csv.write_text("code,name\nLOC001,Local Station\n")
    monkeypatch.setattr(cwc_mod, "PACKAGED_CSV", local_csv)
    monkeypatch.setattr(cwc_mod, "CACHE_FILE", tmp_path / "nonexistent.csv")

    out = api_mod.cwc_ns.stations()

    assert len(out) == 1
    assert out.iloc[0]["code"] == "LOC001"


def test_cwc_stations_prefers_cache_over_packaged(monkeypatch, tmp_path):
    import swift_app.api as api_mod
    cwc_mod = _get_cwc_engine_module()

    cache_csv = tmp_path / "cwc_meta.csv"
    cache_csv.write_text("code,name\nCACHE01,Cached Station\n")
    monkeypatch.setattr(cwc_mod, "CACHE_FILE", cache_csv)

    packaged = tmp_path / "packaged.csv"
    packaged.write_text("code,name\nPKG001,Packaged Station\n")
    monkeypatch.setattr(cwc_mod, "PACKAGED_CSV", packaged)

    out = api_mod.cwc_ns.stations()

    assert len(out) == 1
    assert out.iloc[0]["code"] == "CACHE01"


def test_cwc_stations_station_filter(monkeypatch, tmp_path):
    import swift_app.api as api_mod
    cwc_mod = _get_cwc_engine_module()

    csv = tmp_path / "meta.csv"
    csv.write_text(
        "code,name\n001-AAA,Alpha\n002-BBB,Beta\n003-CCC,Gamma\n"
    )
    monkeypatch.setattr(cwc_mod, "PACKAGED_CSV", csv)
    monkeypatch.setattr(cwc_mod, "CACHE_FILE", tmp_path / "nonexistent.csv")

    out = api_mod.cwc_ns.stations(station="002-BBB")
    assert len(out) == 1
    assert out.iloc[0]["code"] == "002-BBB"


# ============================================================
# Namespace API tests
# ============================================================


def test_wris_namespace_download_dispatches(monkeypatch, tmp_path):
    """swift.wris.download() should delegate to the WRIS engine."""
    import swift_app.api as api_mod

    class DummyClient:
        def __init__(self, delay=0.25):
            self.delay = delay

        def check_api(self):
            return True

        def get_basin_code(self, basin):
            return "6"

    calls = {}

    def fake_run_wris_download(args, selected, client, basin_code):
        calls["selected"] = selected
        calls["basin_code"] = basin_code
        calls["stations"] = getattr(args, "stations", None)

    monkeypatch.setattr(api_mod, "WrisClient", DummyClient)
    monkeypatch.setattr(api_mod, "run_wris_download", fake_run_wris_download)

    api_mod.wris.download(
        basin="Krishna",
        variable=["discharge", "rainfall"],
        output_dir=tmp_path,
        quiet=True,
    )

    assert calls["basin_code"] == "6"
    assert calls["selected"] == {
        "DISCHARG": "discharge",
        "RAINF": "rainfall",
    }
    assert calls["stations"] is None


def test_wris_namespace_download_with_station_filter(monkeypatch, tmp_path):
    import swift_app.api as api_mod

    class DummyClient:
        def __init__(self, delay=0.25):
            self.delay = delay

        def check_api(self):
            return True

        def get_basin_code(self, basin):
            return "6"

    calls = {}

    def fake_run_wris_download(args, selected, client, basin_code):
        calls["stations"] = getattr(args, "stations", None)

    monkeypatch.setattr(api_mod, "WrisClient", DummyClient)
    monkeypatch.setattr(api_mod, "run_wris_download", fake_run_wris_download)

    api_mod.wris.download(
        basin="Krishna",
        variable="discharge",
        station=["ST001", "ST002"],
        output_dir=tmp_path,
        quiet=True,
    )

    assert calls["stations"] == ["ST001", "ST002"]


def test_cwc_namespace_download_dispatches(monkeypatch):
    """swift.cwc.download() should delegate to the CWC engine."""
    import swift_app.api as api_mod

    calls = {}

    def fake_run_cwc_download(args):
        calls["cwc"] = args.cwc
        calls["stations"] = args.cwc_station

    monkeypatch.setattr(api_mod, "run_cwc_download", fake_run_cwc_download)

    api_mod.cwc_ns.download(station=["040-CDJAPR"], quiet=True)

    assert calls["cwc"] is True
    assert calls["stations"] == ["040-CDJAPR"]


def test_wris_namespace_stations(monkeypatch):
    import swift_app.api as api_mod

    class DummyClient:
        def __init__(self, delay=0.25):
            self.delay = delay

        def get_basin_code(self, basin):
            return "5"

        def get_tributaries(self, basin_code, dataset_code):
            return []

        def get_rivers(self, tributary_id, dataset_code):
            return []

        def get_agencies(self, tributary_id, localriver_id, dataset_code):
            return []

        def get_stations(self, tributary_id, localriver_id, agency_id, dataset_code):
            return []

        def get_metadata(self, station_code, dataset_code):
            return {"station_Name": "X", "latitude": 0, "longitude": 0}

    monkeypatch.setattr(api_mod, "WrisClient", DummyClient)
    monkeypatch.setattr(api_mod, "build_basin_structure", lambda c, bc: [("t1", "r1")])
    monkeypatch.setattr(api_mod, "discover_stations", lambda *a, **k: ["S1"])

    out = api_mod.wris.stations("Godavari")
    assert len(out) == 1


def test_cwc_namespace_stations(monkeypatch, tmp_path):
    import swift_app.api as api_mod
    cwc_mod = _get_cwc_engine_module()

    csv = tmp_path / "meta.csv"
    csv.write_text("code,name\n040-CDJAPR,Parwan pick-up Weir\n")
    monkeypatch.setattr(cwc_mod, "PACKAGED_CSV", csv)
    monkeypatch.setattr(cwc_mod, "CACHE_FILE", tmp_path / "nonexistent.csv")

    out = api_mod.cwc_ns.stations(station="040-CDJAPR")
    assert len(out) == 1
    assert out.iloc[0]["code"] == "040-CDJAPR"


# ============================================================
# fetch() tests
# ============================================================


def test_fetch_dispatches_to_wris(monkeypatch, tmp_path):
    import swift_app.api as api_mod

    class DummyClient:
        def __init__(self, delay=0.25):
            self.delay = delay

        def check_api(self):
            return True

        def get_basin_code(self, basin):
            return "6"

    calls = {}

    def fake_run_wris_download(args, selected, client, basin_code):
        calls["selected"] = selected
        calls["basin_code"] = basin_code

    monkeypatch.setattr(api_mod, "WrisClient", DummyClient)
    monkeypatch.setattr(api_mod, "run_wris_download", fake_run_wris_download)

    api_mod.fetch(
        "wris",
        basin="Krishna",
        variable="discharge",
        output_dir=tmp_path,
        quiet=True,
    )

    assert calls["basin_code"] == "6"
    assert "DISCHARG" in calls["selected"]


def test_fetch_dispatches_to_cwc(monkeypatch):
    import swift_app.api as api_mod

    calls = {}

    def fake_run_cwc_download(args):
        calls["cwc"] = args.cwc
        calls["stations"] = args.cwc_station

    monkeypatch.setattr(api_mod, "run_cwc_download", fake_run_cwc_download)

    api_mod.fetch("cwc", station=["040-CDJAPR"], quiet=True)

    assert calls["cwc"] is True
    assert calls["stations"] == ["040-CDJAPR"]


def test_fetch_unknown_source_raises():
    import swift_app.api as api_mod

    with pytest.raises(ValueError, match="Unknown source"):
        api_mod.fetch("invalid_source")


def test_fetch_wris_missing_variable_raises():
    import swift_app.api as api_mod

    with pytest.raises(ValueError, match="variable is required"):
        api_mod.fetch("wris", basin="Krishna")


def test_fetch_wris_missing_basin_raises():
    import swift_app.api as api_mod

    with pytest.raises(ValueError, match="basin is required"):
        api_mod.fetch("wris", variable="discharge")


# ============================================================
# Merge/Plot with mode parameter
# ============================================================


def test_merge_with_mode_derives_input_dir(monkeypatch, tmp_path):
    import swift_app.api as api_mod

    basin_dir = tmp_path / "Krishna"
    basin_dir.mkdir()

    calls = {}

    def fake_run_merge_only(args):
        calls["input_dir"] = args.input_dir

    monkeypatch.setattr(api_mod, "run_merge_only", fake_run_merge_only)

    api_mod.merge(mode="wris", basin="Krishna", output_dir=str(tmp_path))

    assert calls["input_dir"] == str(basin_dir)


def test_plot_with_mode_derives_input_dir(monkeypatch, tmp_path):
    import swift_app.api as api_mod

    basin_dir = tmp_path / "Krishna"
    basin_dir.mkdir()

    calls = {}

    def fake_run_plot_only(args):
        calls["input_dir"] = args.input_dir
        calls["cwc"] = args.cwc

    monkeypatch.setattr(api_mod, "run_plot_only", fake_run_plot_only)

    api_mod.plot(mode="wris", basin="Krishna", output_dir=str(tmp_path))

    assert calls["input_dir"] == str(basin_dir)
    assert calls["cwc"] is False


def test_plot_cwc_mode_sets_cwc_flag(monkeypatch, tmp_path):
    import swift_app.api as api_mod

    calls = {}

    def fake_run_plot_only(args):
        calls["cwc"] = args.cwc

    monkeypatch.setattr(api_mod, "run_plot_only", fake_run_plot_only)

    api_mod.plot(mode="cwc", output_dir=str(tmp_path))

    assert calls["cwc"] is True


# ============================================================
# Package-level namespace access
# ============================================================


def test_package_exposes_wris_namespace():
    import swift_app

    assert hasattr(swift_app, "wris")
    assert hasattr(swift_app.wris, "download")
    assert hasattr(swift_app.wris, "stations")


def test_package_exposes_cwc_namespace():
    import swift_app

    assert hasattr(swift_app, "cwc")
    assert hasattr(swift_app.cwc, "download")
    assert hasattr(swift_app.cwc, "stations")


def test_package_exposes_fetch():
    import swift_app

    assert hasattr(swift_app, "fetch")
    assert callable(swift_app.fetch)
