import pytest

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
