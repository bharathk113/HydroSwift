import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
import importlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swift_app.cwc import fetch_station_data, download_station


@patch("swift_app.cwc.session.get")
@patch("time.sleep")
def test_cwc_download_retry_logic(mock_sleep, mock_get):
    """Test exponential backoff logic for CWC downloads."""
    
    # Mock sequence: failure, failure, success
    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 500
    
    mock_resp_succ = MagicMock()
    mock_resp_succ.status_code = 200
    mock_resp_succ.json.return_value = [
        {"stationCode": "TestStation", "id": {"dataTime": "2026-03-01"}, "dataValue": 10.5}
    ]
    
    mock_get.side_effect = [mock_resp_fail, mock_resp_fail, mock_resp_succ]
    
    # Ensure it works after failures
    result = fetch_station_data("TestStation")
    assert result is not None
    assert len(result) == 1
    assert result["water_level"].iloc[0] == 10.5
    
    # It should have called get 3 times
    assert mock_get.call_count == 3
    # It should have slept twice
    assert mock_sleep.call_count == 2


def test_download_station_writes_wse_column(monkeypatch, tmp_path):
    """CWC station files should include `wse` for plotting/merge compatibility."""

    station = {
        "code": "040-CDJAPR",
        "name": "Parwan",
        "lat": 24.0,
        "lon": 76.0,
        "rl_zero": 100.0,
    }

    def fake_fetch_station_data(code, start_date=None, end_date=None, retries=3):
        import pandas as pd
        return pd.DataFrame(
            {
                "station_code": [code],
                "time": ["2024-01-01 08:00:00"],
                "water_level": [105.5],
            }
        )

    cwc_mod = importlib.import_module("swift_app.cwc")
    monkeypatch.setattr(cwc_mod, "fetch_station_data", fake_fetch_station_data)

    args = SimpleNamespace(
        format="csv",
        overwrite=True,
        start_date="2024-01-01",
        end_date="2024-01-02",
    )

    result = download_station(station, str(tmp_path), args)
    assert result is True

    out_files = list(tmp_path.glob("040-CDJAPR_*.csv"))
    assert out_files, "Expected station CSV file to be written"

    import pandas as pd
    df = pd.read_csv(out_files[0], comment="#")
    assert "wse" in df.columns
    assert df["wse"].iloc[0] == 105.5
