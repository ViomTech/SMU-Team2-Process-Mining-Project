import pytest
import pandas as pd
from io import BytesIO

# --- IMPORTS ---
# This pattern imports the entire file as a module.
from services import normalization_service
from services import models
from services.db import db


# --- Test Data ---
VALID_EVENT_log_CSV = (
    b"case_id,activity,timestamp\n"
    b"1,Start,2023-01-01T10:00:00Z\n"
    b"1,End,2023-01-01T11:00:00Z\n"
)
VALID_DB_LOG_CSV = (
    b"query,timestamp,user\n"
    b"SELECT * FROM users,2023-02-01T12:00:00Z,admin\n"
    b"UPDATE products SET price=10,2023-02-01T13:00:00Z,admin\n"
)
INVALID_CSV_FORMAT = b"this,is,not,a,valid,csv"
MISSING_DB_COLUMN_CSV = b"activity,timestamp\nSomeActivity,2023-01-01T10:00:00Z"


@pytest.fixture
def mock_canonicalize(monkeypatch):
    """Mocks the 'canonicalize' function inside the 'normalization' module."""
    # We tell monkeypatch to find the 'canonicalize' function inside the imported 'normalization' module.
    monkeypatch.setattr(normalization_service, "canonicalize", lambda s, source=None: f"canon_{s}")


# --- Test Suite for normalize_event_log ---

def test_normalize_event_log_success(app, make_user, make_project, make_file, mock_canonicalize):
    """Tests the successful normalization of an event log."""
    with app.app_context():
        # ARRANGE
        user = make_user()
        project = make_project(user)
        file_record = make_file(user, project, filename="events.csv", file_data=VALID_EVENT_log_CSV)
        
        # ACT
        result = normalization_service.normalize_event_log(file_record.file_id)

        # ASSERT
        assert "Successfully stored 2 log events" in result
        updated_file = db.session.get(models.File, file_record.file_id)
        assert updated_file.status == 1
        stored_events = models.EventLog.query.filter_by(file_id=file_record.file_id).all()
        assert len(stored_events) == 2


def test_normalize_event_log_file_not_found(app):
    """Tests handling of a non-existent file ID."""
    with app.app_context():
        # ACT & ASSERT
        result = normalization_service.normalize_event_log(9999)
        assert result == "File not found"


def test_normalize_event_log_processing_error(app, make_user, make_project, make_file):
    """Tests failure on malformed CSV data."""
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_record = make_file(user, project, filename="bad.csv", file_data=INVALID_CSV_FORMAT)

        # ACT & ASSERT
        result = normalization_service.normalize_event_log(file_record.file_id)

        assert "Error processing Event Log" in result
        updated_file = db.session.get(models.File, file_record.file_id)
        assert updated_file.status == 2


# --- Test Suite for normalize_database_log ---

def test_normalize_database_log_success(app, make_user, make_project, make_file, mock_canonicalize):
    """Tests the successful normalization of a database log."""
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_record = make_file(user, project, filename="db.csv", file_data=VALID_DB_LOG_CSV)
        
        # ACT & ASSERT
        result = normalization_service.normalize_database_log(file_record.file_id)
        
        assert "Successfully stored 2 log events" in result
        updated_file = db.session.get(models.File, file_record.file_id)
        assert updated_file.status == 1


def test_normalize_database_log_missing_query_column(app, make_user, make_project, make_file):
    """Tests failure when 'query' column is missing."""
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_record = make_file(user, project, filename="bad_db.csv", file_data=MISSING_DB_COLUMN_CSV)
        
        # ACT & ASSERT
        result = normalization_service.normalize_database_log(file_record.file_id)
        
        assert "Error processing Database Log" in result
        updated_file = db.session.get(models.File, file_record.file_id)
        assert updated_file.status == 2


# --- Test Suite for store_events ---

def test_store_events_clears_old_data(app, make_user, make_project, make_file):
    """Tests that re-processing a file clears old data."""
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_record = make_file(user, project)
        
        # First pass
        df1 = pd.DataFrame({'case_id': [1], 'activity': ['Old'], 'timestamp': [pd.Timestamp("2023-01-01T10:00:00Z")]})
        # ACT & ASSERT
        normalization_service.store_events(df1, file_record.file_id)
        assert models.EventLog.query.count() == 1
        
        # Second pass
        df2 = pd.DataFrame({'case_id': [2, 3], 'activity': ['New1', 'New2'], 'timestamp': [pd.Timestamp("2023-01-02T10:00:00Z")]*2})
        # ACT & ASSERT
        normalization_service.store_events(df2, file_record.file_id)
        
        assert models.EventLog.query.count() == 2
        assert models.EventLog.query.filter_by(activity='Old').count() == 0

