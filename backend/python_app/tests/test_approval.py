import pytest
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from services import approval_service
from services.models import BpmnFile, BpmnApproval, Project, User
from services.db import db


# ------------------------
# submit_bpmn_for_approval
# ------------------------
@patch("services.approval_service.create_notification")
def test_submit_bpmn_for_approval_success(mock_notify, app, make_user, make_project, make_file):
    user = make_user()
    bpo_user = make_user(email="bpo@example.com")
    project = make_project(user, project_name="Test Project", description="Desc")
    bpmn_file = BpmnFile(
        user_id=user.user_id,
        project_id=project.project_id,
        filename="process.bpmn",
        file_hash="hash123",
        file_data=b"<xml></xml>",
        version=1
    )
    db.session.add(bpmn_file)
    db.session.commit()

    approval = approval_service.submit_bpmn_for_approval(bpmn_file.bpmnfile_id, user.user_id, bpo_user.user_id)
    assert approval.status == "Pending"
    mock_notify.assert_called_once()

def test_submit_bpmn_for_approval_file_not_found(app):
    with pytest.raises(ValueError, match="BPMN file with ID 999 not found"):
        approval_service.submit_bpmn_for_approval(999, 1, 2)

# ------------------------
# review_bpmn
# ------------------------
@patch("services.approval_service.create_notification")
def test_review_bpmn_approve(mock_notify, app, make_user, make_project):
    user = make_user()
    bpo_user = make_user(email="bpo@example.com")
    project = make_project(user)
    bpmn_file = BpmnFile(user_id=user.user_id, project_id=project.project_id, filename="f.bpmn", file_hash="h", file_data=b"x")
    db.session.add(bpmn_file)
    db.session.commit()
    approval = BpmnApproval(
        bpmnfile_id=bpmn_file.bpmnfile_id,
        submitted_by=user.user_id,
        reviewed_by=bpo_user.user_id,
        status="Pending",
        from_state="None",
        to_state="Pending",
        comment="Submitted",
        version=1
    )
    db.session.add(approval)
    db.session.commit()

    updated = approval_service.review_bpmn(approval.approval_id, approved=True, comment="Looks good")
    assert updated.status == "Approved"
    mock_notify.assert_called_once()

@patch("services.approval_service.create_notification")
def test_review_bpmn_reject(mock_notify, app, make_user, make_project):
    user = make_user()
    bpo_user = make_user(email="bpo@example.com")
    project = make_project(user)
    bpmn_file = BpmnFile(user_id=user.user_id, project_id=project.project_id, filename="f.bpmn", file_hash="h", file_data=b"x")
    db.session.add(bpmn_file)
    db.session.commit()
    approval = BpmnApproval(
        bpmnfile_id=bpmn_file.bpmnfile_id,
        submitted_by=user.user_id,
        reviewed_by=bpo_user.user_id,
        status="Pending",
        from_state="None",
        to_state="Pending",
        comment="Submitted",
        version=1
    )
    db.session.add(approval)
    db.session.commit()

    updated = approval_service.review_bpmn(approval.approval_id, approved=False, comment="Needs changes")
    assert updated.status == "Rejected"
    mock_notify.assert_called_once()

# ------------------------
# get_bpo_approvals
# ------------------------
def test_get_bpo_approvals_returns_list(app, make_user, make_project):
    user = make_user()
    bpo_user = make_user(email="bpo@example.com")
    project = make_project(user)
    bpmn_file = BpmnFile(user_id=user.user_id, project_id=project.project_id, filename="f.bpmn", file_hash="h", file_data=b"x")
    db.session.add(bpmn_file)
    db.session.commit()
    approval = BpmnApproval(
        bpmnfile_id=bpmn_file.bpmnfile_id,
        submitted_by=user.user_id,
        reviewed_by=bpo_user.user_id,
        status="Pending",
        from_state="None",
        to_state="Pending",
        comment="Submitted",
        version=1
    )
    db.session.add(approval)
    db.session.commit()

    results = approval_service.get_bpo_approvals(bpo_user.user_id)
    assert len(results) == 1
    assert results[0]["status"] == "pending"


# ------------------------
# get_bpmn_approval
# ------------------------
def test_get_bpmn_approval_success(app, make_user, make_project):
    user = make_user()
    project = make_project(user)
    bpmn_file = BpmnFile(user_id=user.user_id, project_id=project.project_id, filename="f.bpmn", file_hash="h", file_data=b"x")
    db.session.add(bpmn_file)
    db.session.commit()
    approval = BpmnApproval(
        bpmnfile_id=bpmn_file.bpmnfile_id,
        submitted_by=user.user_id,
        reviewed_by=None,
        status="Pending",
        from_state="None",
        to_state="Pending",
        comment="Submitted",
        version=1
    )
    db.session.add(approval)
    db.session.commit()

    data = approval_service.get_bpmn_approval(bpmn_file.bpmnfile_id)
    assert data["bpmnfile_id"] == bpmn_file.bpmnfile_id

def test_get_bpmn_approval_not_found(app):
    with pytest.raises(ValueError):
        approval_service.get_bpmn_approval(999)


# ------------------------
# get_approval_status
# ------------------------
def test_get_approval_status_success(app, make_user, make_project):
    user = make_user()
    project = make_project(user)
    bpmn_file = BpmnFile(user_id=user.user_id, project_id=project.project_id, filename="f.bpmn", file_hash="h", file_data=b"x")
    db.session.add(bpmn_file)
    db.session.commit()
    approval = BpmnApproval(
        bpmnfile_id=bpmn_file.bpmnfile_id,
        submitted_by=user.user_id,
        reviewed_by=None,
        status="Pending",
        from_state="None",
        to_state="Pending",
        comment="Submitted",
        version=1
    )
    db.session.add(approval)
    db.session.commit()

    status = approval_service.get_approval_status(bpmn_file.bpmnfile_id)
    assert status == "Pending"

def test_get_approval_status_not_found(app):
    with pytest.raises(ValueError):
        approval_service.get_approval_status(999)
