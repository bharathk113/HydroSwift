import pytest
import pandas as pd

from swift_app.api_public import _normalize_dataset_flags


def test_dataset_aliases_cover_cli_style_and_python_style_names():
    flags = _normalize_dataset_flags(
        ["discharge", "atm_pressure", "solar_radiation", "groundwater_level"]
    )
    assert flags == ["q", "atm", "solar", "gwl"]


def test_download_supports_legacy_dataset_flags_kwarg(monkeypatch, tmp_path):
    import swift_app.api_public as api_public

    class DummyClient:
        def __init__(self, delay=0.25):
            self.delay = delay

        def check_api(self):
            return True

        def get_basin_code(self, basin):
            return "6"

    calls = {}

    def fake_run_download(args, selected, client, basin_code):
        calls["selected"] = selected
        calls["basin_code"] = basin_code

    monkeypatch.setattr(api_public, "WrisClient", DummyClient)
    monkeypatch.setattr(api_public, "run_download", fake_run_download)

    api_public.download(
        basin="Krishna",
        dataset_flags=["q", "rf"],
        output_dir=tmp_path,
        quiet=True,
    )

    assert calls["basin_code"] == "6"
    assert calls["selected"] == {
        "DISCHARG": "discharge",
        "RAINF": "rainfall",
    }


def test_unknown_dataset_error_is_actionable():
    with pytest.raises(ValueError, match="Supported values"):
        _normalize_dataset_flags(["bogus_dataset"])


def test_download_allows_cwc_station_without_cwc_flag(monkeypatch):
    import swift_app.api_public as api_public

    calls = {}

    def fake_run_cwc_download(args):
        calls["cwc"] = args.cwc
        calls["stations"] = args.cwc_station

    monkeypatch.setattr(api_public, "run_cwc_download", fake_run_cwc_download)

    api_public.download(
        cwc_station=["040-CDJAPR"],
        quiet=True,
    )

    assert calls["cwc"] is True
    assert calls["stations"] == ["040-CDJAPR"]


def test_download_defaults_output_dir_to_output(monkeypatch):
    import swift_app.api_public as api_public

    class DummyClient:
        def __init__(self, delay=0.25):
            self.delay = delay

        def check_api(self):
            return True

        def get_basin_code(self, basin):
            return "6"

    calls = {}

    def fake_run_download(args, selected, client, basin_code):
        calls["output_dir"] = args.output_dir

    monkeypatch.setattr(api_public, "WrisClient", DummyClient)
    monkeypatch.setattr(api_public, "run_download", fake_run_download)

    api_public.download(
        basin="Krishna",
        datasets=["discharge"],
        quiet=True,
    )

    assert calls["output_dir"].endswith("output")


def test_search_stations_populates_river_from_discovery_fallback(monkeypatch):
    import swift_app.api_public as api_public
    import importlib

    download_mod = importlib.import_module("swift_app.download")

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

    monkeypatch.setattr(api_public, "WrisClient", DummyClient)
    monkeypatch.setattr(download_mod, "build_basin_structure", lambda client, basin_code: [("t1", "r1")])
    monkeypatch.setattr(download_mod, "discover_stations", lambda *args, **kwargs: ["S1"])

    out = api_public.search_stations("Godavari")

    assert len(out) == 1
    assert out.loc[0, "river"] == "River-X"


def test_cwc_stations_refresh_uses_live_fetch(monkeypatch, tmp_path):
    import swift_app.api_public as api_public

    fresh = pd.DataFrame(
        [
            {"code": "AAA001", "name": "Station A"},
            {"code": "BBB001", "name": "Station B"},
        ]
    )

    monkeypatch.setattr(api_public.Path, "home", classmethod(lambda cls: tmp_path))

    import swift_app.cwc as cwc_mod

    monkeypatch.setattr(cwc_mod, "fetch_cwc_station_metadata", lambda: fresh)

    out = api_public.cwc_stations(list=True, refresh=True)

    assert list(out["code"]) == ["AAA001", "BBB001"]


def test_cwc_stations_refresh_falls_back_when_live_unavailable(monkeypatch):
    import swift_app.api_public as api_public
    import swift_app.cwc as cwc_mod

    monkeypatch.setattr(cwc_mod, "fetch_cwc_station_metadata", lambda: pd.DataFrame())
    monkeypatch.setattr(
        cwc_mod,
        "load_station_table",
        lambda: pd.DataFrame([{"code": "040-CDJAPR", "name": "Parwan pick-up Weir"}]),
    )

    out = api_public.cwc_stations(list=True, refresh=True)

    assert len(out) == 1
    assert out.iloc[0]["code"] == "040-CDJAPR"
