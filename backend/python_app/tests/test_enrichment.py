import pytest
from datetime import datetime, timedelta, timezone
UTC = timezone.utc  # alias for backward compatibility

from services import enrichment_service
from services.models import db, EventLog, User, Project

# --- Test for a simple, successful parent-child match ---
def test_enrich_simple_parent_child_match(app, make_user, make_project, make_file):
    """
    GIVEN an anchor event and an unidentified child event within the time window
    WHEN enrich_case_ids is called
    THEN the child event's case_id should be updated
    """
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_obj = make_file(user, project)
        
        # Arrange: Create events, now with a valid file_id
        anchor_event = EventLog(
            project_id=project.project_id,
            file_id=file_obj.file_id,
            case_id="CASE-101",
            canonical_activity="Application Submitted",
            activity="Raw App Submit",
            timestamp=datetime.now(UTC)
        )
        child_event = EventLog(
            project_id=project.project_id,
            file_id=file_obj.file_id,
            case_id=None,
            canonical_activity="Customer Profile Created",
            activity="Raw Profile Create",
            timestamp=datetime.now(UTC) + timedelta(minutes=5)
        )
        db.session.add_all([anchor_event, child_event])
        db.session.commit()

        # Act
        result = enrichment_service.enrich_case_ids(project.project_id)
        
        # Assert: Check the dictionary result
        assert result["status"] == "SUCCESS"
        assert result["count"] == 1
        
        updated_child = db.session.get(EventLog, child_event.event_id)
        assert updated_child.case_id == "CASE-101"

# --- Test for a failed match when outside the time window ---
def test_enrich_no_match_outside_time_window(app, make_user, make_project, make_file):
    """
    GIVEN an anchor event and a child event outside the time window
    WHEN enrich_case_ids is called
    THEN the child event's case_id should NOT be updated
    """
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_obj = make_file(user, project)
        
        # Arrange
        anchor_event = EventLog(
            project_id=project.project_id,
            file_id=file_obj.file_id,
            case_id="CASE-102",
            canonical_activity="Application Submitted",
            activity="Raw App Submit",
            timestamp=datetime.now(UTC)
        )
        # This event is 2 hours later, but the window for "Customer Profile Created" is 1 hour
        child_event = EventLog(
            project_id=project.project_id,
            file_id=file_obj.file_id,
            case_id=None,
            canonical_activity="Customer Profile Created",
            activity="Raw Profile Create",
            timestamp=datetime.now(UTC) + timedelta(hours=2)
        )
        db.session.add_all([anchor_event, child_event])
        db.session.commit()
        
        # Act
        result = enrichment_service.enrich_case_ids(project.project_id)
        
        # Assert: Check the dictionary result for no matches
        assert result["status"] == "NO_MATCHES"
        assert result["count"] == 0
        
        not_updated_child = db.session.get(EventLog, child_event.event_id)
        assert not_updated_child.case_id is None

# --- Test the confidence check: fail when multiple case_ids are possible ---
def test_enrich_no_match_due_to_conflicting_case_ids(app, make_user, make_project, make_file):
    """
    GIVEN two potential parent events with DIFFERENT case_ids
    WHEN enrich_case_ids is called
    THEN the child event should not be updated due to low confidence
    """
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_obj = make_file(user, project)
        
        parent1 = EventLog(project_id=project.project_id, file_id=file_obj.file_id,
                           case_id="CASE-A", canonical_activity="Application Submitted",
                           activity="a", timestamp=datetime.now(UTC))
        parent2 = EventLog(project_id=project.project_id, file_id=file_obj.file_id,
                           case_id="CASE-B", canonical_activity="Application Submitted",
                           activity="b", timestamp=datetime.now(UTC) + timedelta(minutes=1))
        child = EventLog(project_id=project.project_id, file_id=file_obj.file_id,
                         case_id=None, canonical_activity="Customer Profile Created",
                         activity="c", timestamp=datetime.now(UTC) + timedelta(minutes=5))
        db.session.add_all([parent1, parent2, child])
        db.session.commit()
        
        # Act
        result = enrichment_service.enrich_case_ids(project.project_id)
        
        # Assert: Check the dictionary result for no matches
        assert result["status"] == "NO_MATCHES"
        assert result["count"] == 0
        
        not_updated_child = db.session.get(EventLog, child.event_id)
        assert not_updated_child.case_id is None

# --- Test the "ripple effect" of the while loop ---
def test_enrich_ripple_effect_over_multiple_passes(app, make_user, make_project, make_file):
    """
    GIVEN a chain of events A -> B -> C where only A has a case_id
    WHEN enrich_case_ids is called
    THEN both B and C should be enriched after multiple passes
    """
    with app.app_context():
        user = make_user()
        project = make_project(user)
        file_obj = make_file(user, project)
        
        event_a = EventLog(project_id=project.project_id, file_id=file_obj.file_id,
                           case_id="RIPPLE-EFFECT", canonical_activity="Application Submitted",
                           activity="a", timestamp=datetime.now(UTC))
        event_b = EventLog(project_id=project.project_id, file_id=file_obj.file_id,
                           case_id=None, canonical_activity="Customer Profile Created",
                           activity="b", timestamp=datetime.now(UTC) + timedelta(minutes=10))
        event_c = EventLog(project_id=project.project_id, file_id=file_obj.file_id,
                           case_id=None, canonical_activity="Aadhaar/PAN KYC Check",
                           activity="c", timestamp=datetime.now(UTC) + timedelta(minutes=20))
        db.session.add_all([event_a, event_b, event_c])
        db.session.commit()
        
        # Act
        result = enrichment_service.enrich_case_ids(project.project_id)
        
        # Assert: Check the dictionary result
        assert result["status"] == "SUCCESS"
        assert result["count"] == 2
        
        updated_b = db.session.get(EventLog, event_b.event_id)
        updated_c = db.session.get(EventLog, event_c.event_id)
        assert updated_b.case_id == "RIPPLE-EFFECT"
        assert updated_c.case_id == "RIPPLE-EFFECT"
