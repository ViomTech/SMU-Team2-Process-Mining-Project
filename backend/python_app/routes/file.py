# backend/python_app/routes/file.py

from flask import Blueprint, request, jsonify, Response, session
from services.db import db
from services.models import File
from services.file_service import *

file_bp = Blueprint("file", __name__)

# --- Route to upload file --- 
@file_bp.route("/upload-file", methods=["POST"])
def upload_file():
    uploaded_file = request.files.get("file")
    user_id = session.get("user_id")

    if not uploaded_file:
        return {"message": "No file provided"}, 400

    file_data = uploaded_file.read()
    filename = uploaded_file.filename
    project_id = request.form.get('project_id')

    message = store_file(user_id, project_id, file_data, filename)

    # print(message)
    if "already exists" in message:
        return jsonify({"message": message}), 409  # conflict - duplicate file
    elif "Error" in message:
        return jsonify({"message": message}), 500  # error
    else:
        return jsonify({"message": message}), 201  # created
    
# --- Route to retrieve file metadata ---
@file_bp.route("/get-file-info", methods=["GET"])
def get_files():
    try:
        user_id = session.get("user_id")
        print(f"--- SESSION CHECK ---")
        print(f"User ID found in session: {user_id}")
        print(f"Type of User ID: {type(user_id)}")
        print(f"---------------------")
        
        # 1. Check for authentication first
        if not user_id:
            return jsonify({"error": "User authentication required. Please log in."}), 401

        # 2. Safely convert user_id to integer
        try:
            user_id = int(user_id)
        except ValueError:
            return jsonify({"message": "user_id must be an integer"}), 400

        # 3. Call your now-robust function to get file data
        result = get_file_info_by_user(user_id)
        
        # 4. Return the data (even if it's an empty list, which is valid JSON)
        return jsonify(result)

    except Exception as e:
        # 5. If any unexpected error occurs, log it and send a clean JSON error.
        print(f"A critical error occurred in /get-file-info: {e}") 
        return jsonify({"error": "An internal server error occurred."}), 500

@file_bp.route("/get-file-by-project", methods=["GET"])
def get_project_files(project_id):
    try:
        project_id = request.args.get("project_id", type=int)
        if not project_id:
            return jsonify({"error": "Missing project_id"}), 400
        
        files = get_file_by_project(project_id)

        files_data = [
            {
                "id": f.id,
                "name": f.name,
                "project_id": f.project_id,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in files
        ]
    
    except Exception as e:
        return jsonify({"error": "Failed to fetch project files."}), 500
