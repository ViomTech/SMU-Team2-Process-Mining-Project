# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from services.process_mining_service import get_csv, mine_process_from_csv
from app import create_app

# ---------------------------
# Test get_csv
# ---------------------------
@patch("services.process_mining_service.ConsolidatedEvent")
def test_get_csv_returns_events(mock_event_class):
    # Create mock objects with attributes
    event1 = MagicMock()
    event1.id = 1
    event1.merge_run_id = 101
    event1.project_id = 1
    event1.case_id = "C1"
    event1.activity = "Start"
    event1.canonical_activity = "Start"
    event1.timestamp = datetime(2025, 10, 1, 10, 0)
    event1.source = "system"

    event2 = MagicMock()
    event2.id = 2
    event2.merge_run_id = 101
    event2.project_id = 1
    event2.case_id = "C1"
    event2.activity = "End"
    event2.canonical_activity = "End"
    event2.timestamp = datetime(2025, 10, 1, 10, 5)
    event2.source = "system"

    mock_query = MagicMock()
    mock_query.filter_by.return_value.all.return_value = [event1, event2]
    mock_event_class.query = mock_query

    events = get_csv(project_id=1)
    assert isinstance(events, list)
    assert len(events) == 2
    assert events[0]["case_id"] == "C1"
    assert events[1]["activity"] == "End"


@patch("services.process_mining_service.ConsolidatedEvent")
def test_get_csv_no_events(mock_event_class):
    mock_query = MagicMock()
    mock_query.filter_by.return_value.all.return_value = []
    mock_event_class.query = mock_query

    events = get_csv(project_id=999)
    assert events == []


# ---------------------------
# Test mine_process_from_csv
# ---------------------------
@patch("services.process_mining_service.pm4py.discover_bpmn_inductive")
@patch("services.process_mining_service.pm4py.format_dataframe")
@patch("services.process_mining_service.get_csv")
@patch("services.process_mining_service.db.session")
@patch("services.process_mining_service.hashlib.sha256")
@patch("services.process_mining_service.bpmn_exporter.apply")
def test_mine_process_from_csv_success(
    mock_bpmn_apply, mock_hash, mock_db_session, mock_get_csv, mock_format_df, mock_discover
):
    app = create_app()

    # Flask app context
    with app.app_context():
        # Mock CSV data
        mock_get_csv.return_value = [
            {"case_id": "C1", "activity": "Start", "timestamp": datetime.now()},
            {"case_id": "C1", "activity": "End", "timestamp": datetime.now()}
        ]

        # Mock PM4Py dataframe formatting
        mock_format_df.return_value = "formatted_df"

        # Mock PM4Py BPMN discovery
        mock_bpmn_diagram = MagicMock()
        mock_discover.return_value = mock_bpmn_diagram

        # Mock file hash
        mock_hash.return_value.hexdigest.return_value = "fakehash"

        # Call function
        result = mine_process_from_csv(user_id=1, project_id=1, name="Test BPMN", description="Desc")

        assert result.filename == "Test BPMN"
        assert result.file_hash == "fakehash"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@patch("services.process_mining_service.get_csv")
def test_mine_process_from_csv_no_events(mock_get_csv):
    mock_get_csv.return_value = []
    app = create_app()

    # Flask app context
    with app.app_context():
        with pytest.raises(RuntimeError) as excinfo:
            mine_process_from_csv(user_id=1, project_id=999)

        # Accept either error message
        assert "No BPMN data available" in str(excinfo.value) or "Process mining failed" in str(excinfo.value)
