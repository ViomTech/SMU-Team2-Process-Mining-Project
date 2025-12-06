from services.db import db
from services.models import AuditLog

def log_audit_event(user_id: int, action: str, details: str = ""):
    """Creates and saves a new audit log entry."""
    try:
        new_log = AuditLog(
            user_id=user_id,
            action=action,
            details=details
        )
        db.session.add(new_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # You should log this failure to your server logs
        print(f"Failed to log audit event: {e}")