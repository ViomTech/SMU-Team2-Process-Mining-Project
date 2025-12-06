import math

from services.db import db
from services.models import BpmnFile, User, BpmnFileAudit, Project
import hashlib
from sqlalchemy.exc import SQLAlchemyError

def save_bpmn(user_id, project_id, name, description, xml):
    if not name or not xml:
        raise ValueError("Missing filename or BPMN XML")
    
    try :
        last_bpmn = BpmnFile.query.filter_by(project_id=project_id).order_by(BpmnFile.version.desc()).first()
        next_version = (last_bpmn.version + 1.0) if last_bpmn else 1.0

        xml_bytes = xml.encode("utf-8") if isinstance(xml, str) else xml
        file_hash = hashlib.sha256(xml_bytes).hexdigest()
        
        new_bpmn = BpmnFile(
            user_id=user_id, 
            project_id=project_id,
            filename=name, 
            description=description, 
            file_hash=file_hash,
            file_data=xml_bytes,
            status=0,
            version=next_version
        )

        db.session.add(new_bpmn)
        db.session.commit()
        
        return new_bpmn

    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while saving BPMN: {str(e)}")
    
def save_bpmn_edits(bpmn_id, xml, user_id):
    try:
        bpmn_file = BpmnFile.query.get(bpmn_id)
        if not bpmn_file:
            raise ValueError(f"BPMN with id {bpmn_id} not found")
        
        new_xml_bytes = xml.encode("utf-8") if isinstance(xml, str) else xml
        new_file_hash = hashlib.sha256(new_xml_bytes).hexdigest()
        
        if new_file_hash != bpmn_file.file_hash:
            audit_entry = BpmnFileAudit(
                bpmnfile_id=bpmn_file.bpmnfile_id,
                user_id=bpmn_file.user_id,
                file_hash=bpmn_file.file_hash,
                file_data=bpmn_file.file_data,
                version=bpmn_file.version
            )

            db.session.add(audit_entry)

            bpmn_file.file_hash = new_file_hash
            bpmn_file.file_data = new_xml_bytes
            bpmn_file.approval_status = None
            bpmn_file.version = round(bpmn_file.version + 0.1, 1)
        
        db.session.commit()

        return bpmn_file
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while saving BPMN edits: {str(e)}")

def get_bpmn(user_id, bpmn_id):
    try:
        bpmn_file = BpmnFile.query.get(bpmn_id)
        if bpmn_file.project_id is None:
            return bpmn_file
        
        bpmn_file = BpmnFile.query.join(Project).filter(
            BpmnFile.bpmnfile_id == bpmn_id,
            (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
        ).first()
        
        return bpmn_file
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching BPMN: {str(e)}")

def get_recent_bpmn(user_id):
    try:
        bpmn_files = (
            BpmnFile.query.outerjoin(Project)
            .filter(
                (BpmnFile.project_id == None) |
                (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
            )
            .order_by(BpmnFile.upload_date.desc())
            .limit(5)
            .all()
        )
        return bpmn_files

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching recent BPMNs: {str(e)}")

def get_all_bpmn(user_id):
    try:
        bpmn_files = (
            BpmnFile.query.outerjoin(Project)
            .filter(
                (BpmnFile.project_id == None) |
                (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
            )
            .order_by(BpmnFile.upload_date.desc())
            .all()
        )
        return bpmn_files

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching all BPMNs: {str(e)}")
    
def get_bpmn_by_project(user_id, project_id):
    try:
        project = Project.query.filter(
            Project.project_id == project_id,
            (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
        ).first()

        if not project:
            return []
        
        return BpmnFile.query.filter_by(project_id=project_id).order_by(BpmnFile.upload_date.desc()).all()
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching project BPMNs: {str(e)}")

def update_bpmn(bpmn_id, new_xml):
    try:
        bpmn_file = BpmnFile.query.filter_by(bpmnfile_id=bpmn_id).first()

        if not bpmn_file:
            raise ValueError(f"BPMN with id {bpmn_id} not found")
        
        xml_bytes = new_xml.encode("utf-8") if isinstance(new_xml, str) else new_xml
        bpmn_file.file_data = xml_bytes

        db.session.commit()
        return bpmn_file
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while updating BPMN {bpmn_id}: {str(e)}")
    
def update_bpmn_info(bpmn_id, filename, description):
    try:
        bpmn_file = BpmnFile.query.filter_by(bpmnfile_id=bpmn_id).first()

        if not bpmn_file:
            raise ValueError(f"BPMN with id {bpmn_id} not found")
        
        bpmn_file.filename = filename
        bpmn_file.description = description

        db.session.commit()
        return bpmn_file
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while updating BPMN {bpmn_id} information: {str(e)}")
    
def delete_bpmn(bpmn_id):
    try:
        bpmn_file = BpmnFile.query.get(bpmn_id)
        if not bpmn_file:
            raise ValueError(f"BPMN with id {bpmn_id} not found")
        
        db.session.delete(bpmn_file)
        db.session.commit()
        return {"message": f"BPMN {bpmn_id} deleted successfully"}
    
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while deleting BPMN {bpmn_id}: {str(e)}")
    
def get_bpmn_count_by_user(user_id):
    try:
        return BpmnFile.query.join(Project).filter(
            (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
        ).count()
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while counting BPMNs for user {user_id}: {str(e)}")

def get_latest_bpmn(user_id):
    try:
        return BpmnFile.query.join(Project).filter(
            (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
        ).order_by(BpmnFile.upload_date.desc()).first()
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching latest BPMN: {str(e)}")

def get_bpmn_bpo_info(bpmn_id):
    try:
        bpmn = BpmnFile.query.get(bpmn_id)
        if not bpmn or not bpmn.project:
            raise ValueError(f"BPMN or associated project not found for id {bpmn_id}")

        assigned_bpo = User.query.filter_by(user_id=bpmn.project.assigned_bpo_id).first()
        if not assigned_bpo:
            return None  # no BPO assigned

        return {"id": assigned_bpo.user_id, "email": assigned_bpo.email}

    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching assigned BPO: {str(e)}")
    
def get_version_history(bpmn_id, user_id):
    """
    Get all historical versions of a BPMN file from the audit table.
    Returns list of versions with metadata.
    """
    try:
        # First verify user has access to this BPMN
        bpmn_file = get_bpmn(user_id, bpmn_id)
        if not bpmn_file:
            raise ValueError(f"BPMN with id {bpmn_id} not found or access denied")
        
        # Get all audit entries for this BPMN, ordered by version desc
        audit_entries = (
            BpmnFileAudit.query
            .filter_by(bpmnfile_id=bpmn_id)
            .order_by(BpmnFileAudit.version.desc())
            .all()
        )
        
        # Format the response
        versions = []
        for audit in audit_entries:
            versions.append({
                "audit_id": audit.audit_id,
                "version": audit.version,
                "saved_date": audit.save_date.isoformat(),
                "user_id": audit.user_id,
                "approval_status": audit.approval_status
            })
        
        return versions
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching version history: {str(e)}")


def restore_bpmn_version(bpmn_id, audit_id, user_id):
    """
    Restore a previous BPMN version by creating a new version with the old content.
    Only BPO can restore versions.
    
    Args:
        bpmn_id: ID of the current BPMN file
        audit_id: ID of the audit entry to restore from
        user_id: User performing the restoration (must be BPO)
    
    Returns:
        The newly created BPMN file with incremented version
    """
    try:
        # 1. Verify user has access and is BPO
        bpmn_file = BpmnFile.query.get(bpmn_id)
        if not bpmn_file:
            raise ValueError(f"BPMN with id {bpmn_id} not found")
        
        # Check if project exists and user is BPO
        if not bpmn_file.project:
            raise ValueError("BPMN has no associated project")
        
        if bpmn_file.project.assigned_bpo_id != user_id:
            raise PermissionError("Only the assigned BPO can restore versions")
        
        # 2. Get the audit entry to restore from
        audit_entry = BpmnFileAudit.query.get(audit_id)
        if not audit_entry:
            raise ValueError(f"Version history entry with id {audit_id} not found")
        
        if audit_entry.bpmnfile_id != bpmn_id:
            raise ValueError("Version history does not belong to this BPMN")
        
        # 3. Save current version to audit before restoration
        current_audit = BpmnFileAudit(
            bpmnfile_id=bpmn_file.bpmnfile_id,
            user_id=bpmn_file.user_id,
            file_hash=bpmn_file.file_hash,
            file_data=bpmn_file.file_data,
            version=bpmn_file.version,
            approval_status=None  # Reset approval status for restored version
        )
        db.session.add(current_audit)
        
        # 4. Calculate new version number (increment from current)
        new_version = bpmn_file.version + 0.1
        
        # 5. Update the BPMN file with restored content
        bpmn_file.file_data = audit_entry.file_data
        bpmn_file.file_hash = audit_entry.file_hash
        bpmn_file.version = new_version
        bpmn_file.approval_status = "Not Submitted"
        
        # 6. Log the restoration to audit log
        from .audit_service import log_audit_event
        log_audit_event(
            user_id=user_id,
            action="Version Restored",
            details=f"BPMN '{bpmn_file.filename}' (ID: {bpmn_id}) restored from version {audit_entry.version} to new version {new_version}",
        )
        
        # 7. Create notification for project creator
        from .notification_service import create_notification
        create_notification(
            user_id=bpmn_file.project.user_id,
            message=f"Version {audit_entry.version} of '{bpmn_file.filename}' has been restored as version {new_version}",
            target_url=f"/bpmn/view/{bpmn_id}"
        )
        
        db.session.commit()
        return bpmn_file
    
    except (ValueError, PermissionError) as e:
        db.session.rollback()
        raise e
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while restoring version: {str(e)}")
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Unexpected error while restoring version: {str(e)}")
    
def get_project_bpmn_files(project_id, user_id):
    """
    Get all BPMN files in a project (for cloning/restoring from other files).
    Returns only the latest version of each file.
    """
    try:
        # Verify user has access to this project
        project = Project.query.filter(
            Project.project_id == project_id,
            (Project.user_id == user_id) | (Project.assigned_bpo_id == user_id)
        ).first()
        
        if not project:
            raise ValueError(f"Project with id {project_id} not found or access denied")
        
        # Get all BPMN files in project
        bpmn_files = BpmnFile.query.filter_by(project_id=project_id).all()
        
        # Format response with latest version info
        files = []
        for bpmn in bpmn_files:
            files.append({
                "bpmn_id": bpmn.bpmnfile_id,
                "filename": bpmn.filename,
                "version": bpmn.version,
                "upload_date": bpmn.upload_date.isoformat(),
                "last_modified": bpmn.last_modified.isoformat(),
                "description": bpmn.description
            })
        
        return files
    
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database error while fetching project BPMN files: {str(e)}")


def clone_bpmn_file(source_bpmn_id, project_id, user_id):
    """
    Clone another BPMN file in the same project, creating a new file with incremented version.
    Only BPO can clone files.
    
    Args:
        source_bpmn_id: ID of the BPMN file to clone
        project_id: Project ID where new file will be created
        user_id: User performing the clone (must be BPO)
    
    Returns:
        The newly created BPMN file
    """
    try:
        # Verify user is BPO for this project
        project = Project.query.get(project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        
        if project.assigned_bpo_id != user_id:
            raise PermissionError("Only the assigned BPO can clone BPMN files")
        
        # Get the source BPMN file to clone
        source_bpmn = BpmnFile.query.get(source_bpmn_id)
        if not source_bpmn:
            raise ValueError(f"Source BPMN file with id {source_bpmn_id} not found")
        
        if source_bpmn.project_id != project_id:
            raise ValueError("Source BPMN does not belong to this project")
        
        # Calculate next version number (max version in project + 1.0)
        max_version_result = db.session.query(
            db.func.max(BpmnFile.version)
        ).filter_by(project_id=project_id).scalar()

        # Round down to integer, then add 1.0 to get next whole version
        # e.g., max 3.2 → floor(3.2) = 3 → 3 + 1 = 4.0
        next_version = (math.floor(max_version_result) + 1.0) if max_version_result else 1.0
        
        # Create new BPMN file with cloned content
        new_bpmn = BpmnFile(
            user_id=source_bpmn.user_id,  # Keep original creator
            project_id=project_id,
            filename=source_bpmn.filename,
            description=f"Cloned from v{source_bpmn.version}",
            file_hash=source_bpmn.file_hash,
            file_data=source_bpmn.file_data,
            version=next_version,
            status=0
        )
        
        db.session.add(new_bpmn)
        
        # Log the clone action
        from .audit_service import log_audit_event
        log_audit_event(
            user_id=user_id,
            action="BPMN Cloned",
            details=f"BPMN '{source_bpmn.filename}' (v{source_bpmn.version}) cloned as new file with version {next_version}",
        )
        
        # Notify project creator
        from .notification_service import create_notification
        create_notification(
            user_id=project.user_id,
            message=f"BPMN '{source_bpmn.filename}' (v{source_bpmn.version}) has been cloned as v{next_version}",
            target_url=f"/bpmn/view/{new_bpmn.bpmnfile_id}"
        )
        
        db.session.commit()
        return new_bpmn
    
    except (ValueError, PermissionError) as e:
        db.session.rollback()
        raise e
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError(f"Database error while cloning BPMN: {str(e)}")
    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Unexpected error while cloning BPMN: {str(e)}")

