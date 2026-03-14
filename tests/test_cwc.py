import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swift_app.cwc import fetch_station_data


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
