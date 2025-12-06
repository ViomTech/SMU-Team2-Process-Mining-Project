# backend/python_app/routes/project.py

from flask import Blueprint, request, jsonify, session
from services.models import Project, EventLog
from services.project_service import *
from services.merge_service import consolidate_project_event_logs_snapshot_and_artifact
from services.enrichment_service import *
from services.normalization_service import (
    normalize_event_log,
    normalize_database_log,
    normalize_unstructured_file,
)
from services.project_service import submit_project_for_approval, get_project_by_id 

project_bp = Blueprint('project', __name__)

# --- Route to create project folder ---
@project_bp.route('/create-project', methods=['POST'])
def create_project_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    # Get the assigned BPO's ID from the request body
    assigned_bpo_id = data.get('assigned_bpo_id')
    
    try:
        # Pass the new ID to the service function
        project = create_project(user_id, name, description, assigned_bpo_id)
        return jsonify({
            'message': 'Project created successfully!',
            'project_id': project.project_id,
            'project_name': project.project_name
        }), 201
    except ValueError as e:
        # Handle errors, like a duplicate name or missing BPO
        return jsonify({'error': str(e)}), 400

# --- Route to get all of a user's projects ---
@project_bp.route('/get-projects', methods=['GET'])
def get_projects_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
            
    try:
        projects = get_recent_projects_by_user(user_id)
        return jsonify(projects), 200
    except Exception as e:
        print(f"Error fetching recent projects: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

# --- Route to get a single project by its ID, including all its files ---
@project_bp.route('/<int:project_id>', methods=['GET'])
def get_project_route(project_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    project = get_project_by_id(project_id, user_id)
    
    if not project:
        return jsonify({'error': 'Project not found or access denied'}), 404
        
    files_in_project = [{
        'file_id': file.file_id,
        'filename': file.filename,
        'status': file.status,
        'upload_date': file.upload_date.isoformat()
    } for file in project.files]
    
    return jsonify({
        'project_id': project.project_id,
        'project_name': project.project_name,
        'description': project.description,
        'created_at': project.created_at.isoformat(),
        'files': files_in_project
    })

@project_bp.route('/<int:project_id>/merge', methods=['POST'])
def merge_project_sources(project_id):
    """
    One-click: normalise all uploaded files, store events, enrich,
    then merge into consolidated_event_log.csv.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    project = get_project_by_id(project_id, user_id)
    if not project:
        return jsonify({'error': 'Project not found or access denied'}), 404

    processed = 0
    failed = []

    for f in project.files:
        try:
            name = (f.filename or '').strip().lower()
            result_message = None

            if name.endswith('.csv'):
                if name == 'db_logs.csv':
                    result_message = normalize_database_log(f.file_id)
                elif name == 'event_logs.csv':
                    result_message = normalize_event_log(f.file_id)
                else:
                    result_message = normalize_event_log(f.file_id)
            elif name.endswith('.log') or name.endswith('.txt'):
                result_message = normalize_unstructured_file(f.file_id)
            else:
                continue

            if isinstance(result_message, str) and result_message.startswith("Error"):
                failed.append(f"{f.filename}: {result_message}")
            else:
                processed += 1
        except Exception as e:
            failed.append(f"{f.filename}: Unexpected error - {e}")
    
    try:
        enriched = enrich_case_ids(project_id)
    except Exception as e:
        return jsonify({"error": f"Enrichment failed: {e}"}), 500

    try:
        consolidated = consolidate_project_event_logs_snapshot_and_artifact(project_id)
        preview = consolidated.head(30).to_dict(orient="records")
        return jsonify({
            "message": "Merge complete.",
            "normalised_files": processed,
            "normalisation_errors": failed,
            "merged_events": int(consolidated.shape[0]),
            "enriched_events": enriched,
            "preview": preview
        }), 200
    except Exception as e:
        return jsonify({
            "error": f"Merge failed: {e}",
            "normalised_files": processed,
            "normalisation_errors": failed
        }), 500

@project_bp.route("/get-recent-projects", methods=["GET"])
def get_recent_projects_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    projects = get_recent_projects_by_user(user_id)

    try:
        projects = get_recent_projects_by_user(user_id)
        return jsonify(projects), 200
    except Exception as e:
        print(f"Error fetching recent projects: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@project_bp.route('/<int:project_id>/submit-for-approval', methods=['POST'])
def submit_for_approval_route(project_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        # Call the service function to handle the logic
        project = submit_project_for_approval(project_id, user_id) 
        
        # Return a success response
        return jsonify({
            'message': f'Project {project.project_name} submitted for approval.',
            # You might want to return the updated status if your model has one
            # 'project_status': project.status 
        }), 200
        
    except ValueError as e:
        # Handle specific errors from the service layer (e.g., "Project not found")
        return jsonify({'error': str(e)}), 400 
    except PermissionError as e:
        # Handle permission errors if you implemented them (e.g., "Only admins can submit")
        return jsonify({'error': str(e)}), 403
    except RuntimeError as e:
        # Handle database or other unexpected errors from the service layer
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        # Generic fallback error handler
        print(f"Unexpected error in submit_for_approval_route for project {project_id}: {e}") # Log the error
        return jsonify({'error': 'An unexpected server error occurred.'}), 500
    
@project_bp.route("/update-project-info/<int:project_id>", methods=["PUT"])
def update_project_info_route(project_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing filename/description"}), 400
    
    new_projectname = data["project_name"]
    new_description = data["description"]
    project = update_project_info(project_id, new_projectname, new_description)
    if not project:
        return jsonify({"error": f"Project file with id {project_id} not found"}), 404
    
    return jsonify({
        "message": "Project information updated successfully",
        "id": project.project_id,
        "project_name": project.project_name
    }), 200

@project_bp.route("/delete-project/<int:project_id>", methods=["DELETE"])
def delete_project_route(project_id):
    try:
        result = delete_project(project_id)
        return jsonify(result), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 500
