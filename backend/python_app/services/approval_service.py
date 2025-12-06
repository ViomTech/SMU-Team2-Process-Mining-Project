from services.db import db
from services.models import BpmnFile, Project, BpmnApproval, User
from services.notification_service import create_notification
from sqlalchemy.exc import SQLAlchemyError

def submit_bpmn_for_approval(bpmn_id, user_id, bpo_id):
    """
    Submit a BPMN file for approval.
    Each submission creates a new approval row starting from None -> Pending.
    """
    try:
        bpmn_file = BpmnFile.query.get(bpmn_id)
        if not bpmn_file:
            raise ValueError(f"BPMN file with ID {bpmn_id} not found")

        version = bpmn_file.version

        # New approval row: from_state is None, to_state is Pending
        approval = BpmnApproval(
            bpmnfile_id=bpmn_id,
            submitted_by=user_id,
            reviewed_by=bpo_id,
            status="Pending",
            from_state="None",          # fresh submission
            to_state="Pending",
            comment="Submitted for approval",
            version=version
        )

        db.session.add(approval)
        db.session.commit()

        # Notify BPO
        project = bpmn_file.project
        message = f"Approval required for {bpmn_file.filename} BPMN in process {project.project_name}."
        target_url = f"/bpmn/view/{bpmn_id}"
        create_notification(bpo_id, message, target_url)

        return approval

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while submitting BPMN approval: {str(e)}")
    
def review_bpmn(approval_id, approved: bool, comment):
    """
    Review a BPMN approval request.
    Sets from_state to Pending and to_state to Approved/Rejected.
    """
    try:
        approval = BpmnApproval.query.get(approval_id)
        if not approval:
            raise ValueError(f"Approval with ID {approval_id} not found")

        # The decision always transitions from Pending -> Approved/Rejected
        approval.from_state = "Pending"
        approval.to_state = "Approved" if approved else "Rejected"
        approval.status = approval.to_state
        approval.comment = comment

        db.session.commit()

        # Notify submitter
        bpmn_file = approval.bpmn_file
        bpo = approval.reviewer
        if approved:
            message = f"BPMN {bpmn_file.filename} has been approved by {bpo.name}."
        else:
            message = f"BPMN {bpmn_file.filename} has been rejected by {bpo.name}. Please make the changes and submit again for approval."
        
        target_url = f"/bpmn/view/{bpmn_file.bpmnfile_id}"
        create_notification(approval.submitted_by, message, target_url)

        return approval

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while reviewing BPMN approval: {str(e)}")
    
def get_bpo_approvals(user_id):
    try:
        approvals = (
            BpmnApproval.query
            .join(BpmnFile, BpmnApproval.bpmnfile_id == BpmnFile.bpmnfile_id)
            .join(Project, BpmnFile.project_id == Project.project_id)
            .join(User, BpmnApproval.submitted_by == User.user_id)  # join User table
            .filter(BpmnApproval.reviewed_by == user_id)
            .order_by(BpmnApproval.created_at.desc())
            .all()
        )
        
        bpmn_files = [
            {
                "approval_id": a.approval_id,
                "bpmnfile_id": a.bpmnfile_id,
                "processname": a.bpmn_file.project.project_name,
                "filename": a.bpmn_file.filename,
                "version": a.version,
                "submitted_by": a.submitted_by,
                "submitted_by_name": a.submitter.name,  # add name here
                "status": a.status.lower() if a.status else "pending",
                "created_at": a.created_at.isoformat(),
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None
            }
            for a in approvals
        ]
        
        return bpmn_files
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching assigned BPO ID: {str(e)}")
    
def get_bpmn_approval(bpmn_id):
    try:
        approval = BpmnApproval.query.filter_by(bpmnfile_id=bpmn_id).first()
        if not approval:
            raise ValueError(f"BPMN approval for BPMN with id {bpmn_id} not found")
        
        approval_data = {
            "approval_id": approval.approval_id,
            "bpmnfile_id": approval.bpmnfile_id,
            "filename": approval.bpmn_file.filename,
            "version": approval.bpmn_file.version,
            "submitted_by": approval.submitted_by,
            "status": approval.status.lower() if approval.status else "pending",
            "created_at": approval.created_at.isoformat(),
            "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None
        }

        return approval_data
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching BPMN approval info: {str(e)}")

def get_approval_status(bpmn_id):
    try:
        approval = (
            BpmnApproval.query
            .filter_by(bpmnfile_id=bpmn_id)
            .order_by(BpmnApproval.version.desc())  # to get latest approval status
            .first()
        )
        if not approval:
            raise ValueError(f"BPMN approval for BPMN with id {bpmn_id} not found")
        
        return approval.status
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching BPMN approval status: {str(e)}")