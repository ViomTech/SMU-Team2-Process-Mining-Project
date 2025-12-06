# file.py
from datetime import datetime
from services.db import db
from services.models import File  # Make sure you have a File model matching your files table
import hashlib
import os

# --- Function to store file in db ---
def store_file(user_id, project_id, file_data, filename):
    """
    Checks for duplicate. Stores file if unique. Returns status message.
    """
    try:
        if is_file_duplicate(user_id, project_id, file_data, filename):
            return f"File '{filename}' already exists. Not stored."

        file_hash = hashlib.sha256(file_data).hexdigest()
        new_file = File(
            user_id=user_id,
            project_id=project_id,
            filename=filename,
            file_hash=file_hash,
            file_data=file_data, # Stored in raw bytes
            upload_date=datetime.now(),
            status=0  # 0: uploaded, 1: processed, 2: failed
        )
        db.session.add(new_file)
        db.session.commit()
        return f"File '{filename}' stored successfully."
    except Exception as e:
        return f"Error storing file '{filename}': {e}"

# --- Helper Function to check for duplicate files ---
def is_file_duplicate(user_id, project_id, file_data, filename=None):
    """
    Checks if a file already exists for a user based on a specific project.
    """
    file_hash = hashlib.sha256(file_data).hexdigest()
    existing_file = File.query.filter_by(
        user_id=user_id,
        project_id=project_id,
        file_hash=file_hash
    ).first()
    return bool(existing_file) # Return true if file exist, false otherwise

#  --- Function to get file info by user ---
def get_file_info_by_user(user_id):
    """
    Returns file metadata for a specific user.
    This version is more robust and handles potential bad data in individual files.
    """
    files = File.query.filter_by(user_id=user_id).all()
    file_list = []

    for f in files:
        try:
            # Attempt to build the file dictionary
            file_info = {
                "file_id": f.file_id,
                "filename": f.filename,
                "file_type": os.path.splitext(f.filename)[1][1:] if f.filename else "unknown",
                "size_bytes": len(f.file_data) if f.file_data else 0,
                "status": f.status,
                "upload_date": f.upload_date.strftime("%Y-%m-%d %H:%M:%S") if f.upload_date else None
            }
            file_list.append(file_info)
        except Exception as e:
            # If an error occurs for one file (e.g., bad date format),
            # print it to the server logs and skip that file.
            print(f"Could not process file_id {f.file_id} for user_id {user_id}. Error: {e}")
            continue # Move to the next file

    return file_list

def get_file_by_project(project_id):
    return File.query.filter_by(project_id=project_id).all()

