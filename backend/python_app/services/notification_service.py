from services.db import db
from services.models import Notification

def create_notification(user_id: int, message: str, target_url: str):
    """Creates a notification for a specific user."""
    try:
        # Assuming 'Assignment' is a valid type. You can change this.
        new_notification = Notification(
            user_id=user_id,
            type="Assignment",
            message=message,
            target_url=target_url,
            read=False
        )
        db.session.add(new_notification)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # You should log this failure to your server logs
        print(f"Failed to create notification: {e}")