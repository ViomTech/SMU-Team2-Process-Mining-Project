# backend/python_app/services/project_service.py

from services.db import db
# --- Ensure all necessary models are imported ---
from services.models import Project, Notification, BpmnFile, User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload # Optional but helpful
# --- Import your specific service functions ---
from .audit_service import log_audit_event
from .notification_service import create_notification

def create_project(user_id, name, description, assigned_bpo_id):
    """Creates a new project, logs the action, and notifies the assigned BPO."""
    if not name:
        raise ValueError("Project name cannot be empty.")

    if assigned_bpo_id is None: # Explicitly check for None
        raise ValueError("Please assign a BPO before creating a project.")

    # Check for duplicate project name for the *same user*
    existing_project = Project.query.filter_by(user_id=user_id, project_name=name).first()
    if existing_project:
        raise ValueError(f"A project named '{name}' already exists for this user.")

    new_project = Project(
        user_id=user_id,
        project_name=name,
        description=description,
        assigned_bpo_id=assigned_bpo_id
    )

    try:
        db.session.add(new_project)
        # Flush here to get the new_project.project_id before logging/notifying
        db.session.flush()

        # --- Call Audit Service ---
        log_audit_event(
            user_id=user_id,
            action="Process Created",
            details=f"Project '{name}' (ID: {new_project.project_id}) created by user {user_id} and assigned to BPO ID {assigned_bpo_id}."
        )

        # --- Call Notification Service ---
        create_notification(
            user_id=assigned_bpo_id,
            message=f"You have been assigned to the new project: '{name}'.",
            target_url=f"/projects/{new_project.project_id}" # Example URL
        )

        db.session.commit()
        return new_project

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error during project creation: {e}")
        raise RuntimeError(f"Database error while creating project.")
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error during project creation: {e}")
        raise RuntimeError(f"Failed to create project due to an unexpected error.")

def get_projects_by_user(user_id):
    """Gets all projects created by OR assigned to the user."""
    projects = (
        Project.query.filter(
            (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
        )
        .order_by(Project.created_at.desc())
        .all()
    )

    results = []
    for p in projects:
        # Get latest BPMN file by version
        latest_bpmn = (
            sorted(p.bpmn_files, key=lambda b: b.version, reverse=True)[0]
            if p.bpmn_files else None
        )

        # Get latest approval (if any) for that BPMN
        latest_approval = (
            sorted(latest_bpmn.approvals, key=lambda a: a.created_at, reverse=True)[0]
            if latest_bpmn and latest_bpmn.approvals else None
        )

        results.append({
            "project_id": p.project_id,
            "project_name": p.project_name,
            "assigned_bpo": p.assigned_bpo.name if p.assigned_bpo else None,
            "description": p.description,
            "created_at": p.created_at.isoformat(),
            "version": latest_bpmn.version if latest_bpmn else None,
            "last_modified": latest_bpmn.last_modified.isoformat() if latest_bpmn else None,
            "approval_status": latest_approval.status if latest_approval else "Not Submitted"
        })

    return results

def get_project_by_id(project_id, user_id):
    """Gets a specific project if the user created it OR is assigned to it."""
    return Project.query.filter(
        Project.project_id == project_id,
        (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
    ).first()

def get_recent_projects_by_user(user_id):
    """Gets recent projects created by OR assigned to the user, 
    including latest BPMN and approval information.
    """
    projects = (
        Project.query.filter(
            (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
        )
        .order_by(Project.created_at.desc())
        .limit(6)
        .all()
    )

    results = []
    for p in projects:
        # Get latest BPMN file by version
        latest_bpmn = (
            sorted(p.bpmn_files, key=lambda b: b.version, reverse=True)[0]
            if p.bpmn_files else None
        )

        # Get latest approval (if any) for that BPMN
        latest_approval = (
            sorted(latest_bpmn.approvals, key=lambda a: a.created_at, reverse=True)[0]
            if latest_bpmn and latest_bpmn.approvals else None
        )

        results.append({
            "project_id": p.project_id,
            "project_name": p.project_name,
            "assigned_bpo": p.assigned_bpo.name if p.assigned_bpo else None,
            "description": p.description,
            "created_at": p.created_at.isoformat(),
            "version": latest_bpmn.version if latest_bpmn else None,
            "last_modified": latest_bpmn.last_modified.isoformat() if latest_bpmn else None,
            "approval_status": latest_approval.status if latest_approval else "Not Submitted",
            "submitted_by": latest_approval.submitted_by if latest_approval else None,
            "reviewed_by": latest_approval.reviewed_by if latest_approval else None,
            "reviewed_at": latest_approval.reviewed_at.isoformat() if latest_approval and latest_approval.reviewed_at else None,
        })

    return results

# --- ADDED FUNCTION ---
def submit_project_for_approval(project_id: int, submitter_user_id: int):
    """
    Handles the logic for submitting a project for approval.
    Notifies the assigned BPO.
    """
    try:
        # Find the project and eager-load related data needed
        project = Project.query.options(
            joinedload(Project.assigned_bpo), # Load BPO details
            # joinedload(Project.bpmn_files) # Load associated BPMN files (optional here)
        ).filter_by(project_id=project_id).first()

        if not project:
            raise ValueError("Project not found.")

        # Optional: Add permission check here if needed (e.g., only admin can submit)
        # submitter = User.query.get(submitter_user_id)
        # if not submitter or submitter.role != 'admin':
        #     raise PermissionError("Only admins can submit projects for approval.")

        if not project.assigned_bpo_id:
            raise ValueError("Project has no assigned BPO. Cannot submit for approval.")

        # Find the relevant BPMN file (e.g., latest version) to mention in notification
        bpmn_to_approve = BpmnFile.query.filter_by(project_id=project_id)\
                                     .order_by(BpmnFile.version.desc())\
                                     .first()

        if not bpmn_to_approve:
            # Decide if this is an error or just proceed without BPMN details
            # For now, let's proceed but adjust the message
            notification_message = f"Approval required for project '{project.project_name}'. (No BPMN found)"
            # raise ValueError("No BPMN diagram found for this project to approve.")
        else:
            notification_message = f"Approval required for '{bpmn_to_approve.filename}' (v{bpmn_to_approve.version}) in project '{project.project_name}'."

        # Optional: Update project status if you have one
        # project.status = 'pending_approval' # Example status update
        # db.session.add(project)

        # Create Notification for Assigned BPO
        target_url = f"/approvals" # Link to the approvals page (or project page)

        create_notification(
            user_id=project.assigned_bpo_id,
            message=notification_message,
            target_url=target_url
            # Assuming type='ApprovalRequest' or similar is handled in create_notification
        )

        # Optional: Log this action to the audit trail
        # log_audit_event(
        #     user_id=submitter_user_id,
        #     action="Submitted for Approval",
        #     details=f"Project '{project.project_name}' (ID: {project_id}) submitted.",
        #     project_id=project_id
        # )

        db.session.commit() # Commit status update and notification
        return project # Return the project

    except (ValueError, PermissionError) as e:
        db.session.rollback()
        raise e # Re-raise specific known errors
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error during submit for approval: {e}")
        raise RuntimeError(f"Database error while submitting project for approval.")
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error during submit for approval: {e}")
        raise RuntimeError(f"Failed to submit project due to an unexpected error.")
# --- END ADDED FUNCTION ---
    
def update_project_info(project_id, name, description):
    try:
        project = Project.query.filter_by(project_id=project_id).first()

        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        
        project.project_name = name
        project.description = description

        db.session.commit()
        return project
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while updating project {project_id} information: {str(e)}")
    
def delete_project(project_id):
    try:
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        
        db.session.delete(project)
        db.session.commit()
        return {"message": f"Project {project_id} deleted successfully"}
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while deleting project {project_id} information: {str(e)}")
