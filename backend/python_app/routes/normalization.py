# backend/python_app/routes/normalization.py

from flask import Blueprint, request, jsonify, Response, session
from werkzeug.utils import secure_filename
from services.models import Project, File
import tempfile
import os

# Import the service that contains the business logic
from services.normalization_service import normalize_logs
from services.normalization_service import *
from services.enrichment_service import *

# Create a Blueprint for normalization routes
normalization_bp = Blueprint('normalization_bp', __name__)

@normalization_bp.route('/start-mining', methods=['POST'])
def start_mining_route():
    """
    API endpoint to upload log files, normalize them, and return an event log.
    """
    if 'files[]' not in request.files:
        return jsonify({"error": "No files part in the request"}), 400

    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({"error": "No files selected for upload"}), 400

    # Use a secure temporary directory to handle file uploads
    with tempfile.TemporaryDirectory() as temp_dir:
        file_paths = []
        for file in files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(temp_dir, filename)
            file.save(file_path)
            file_paths.append(file_path)

        # Call the service layer to perform the normalization
        try:
            normalized_df, invalid_entries = normalize_logs(file_paths)
            
            # Convert the resulting DataFrame to JSON for the API response
            # Using 'iso' format for dates is a web standard.
            result_json = normalized_df.to_json(orient='records', date_format='iso')

            return jsonify({
                "message": "Normalization successful!",
                "event_log": result_json,
                "invalid_entries_count": len(invalid_entries),
                "invalid_entries_preview": invalid_entries[:20] # Send a preview of flagged entries
            }), 200

        except Exception as e:
            # Catch potential errors during the normalization process
            return jsonify({"error": f"An error occurred during processing: {str(e)}"}), 500

# # --- ROUTE for structured logs ---
# @normalization_bp.route("/<int:project_id>/normalize-structured", methods=["POST"])
# def normalize_structured_route(project_id):
#     user_id = session.get("user_id")
#     if not user_id:
#         return jsonify({"error": "Authentication required"}), 401
    
#     project = Project.query.filter_by(project_id=project_id, user_id=user_id).first()
#     if not project:
#         return jsonify({"error": "Project not found or access denied"}), 404

#     processed_count = 0
#     failed_files = []

#     # Loop through all unprocessed files in the project
#     for file in project.files:
#         try:
#             result_message = ""
#             if 'event' in file.filename.lower():
#                 result_message = normalize_event_log(file.file_id)
#             elif file.filename == 'db_logs.csv':
#                 result_message = normalize_database_log(file.file_id)
#             else:
#                 continue
#             # Add new log types here as you create their functions
            
#             if "Error" in result_message:
#                 failed_files.append(f"{file.filename}: {result_message}")
#             else:
#                 processed_count += 1
#         except Exception as e:
#             failed_files.append(f"{file.filename}: An unexpected error occurred - {e}")

#     if not failed_files:
#         return jsonify({"message": f"Normalized {processed_count} file."}), 200
#     else:
#         return jsonify({
#             "message": f"Completed with errors. Processed {processed_count} files.",
#             "errors": failed_files
#         }), 207 # 207 Multi-Status
    

# # ROUTE FOR ACTIVITY MAPPING
# @normalization_bp.route("/<int:project_id>/map-activities", methods=["POST"])
# def map_activities_route(project_id):
#     """
#     Maps all activity into its canon activity.
#     """
#     user_id = session.get("user_id")
#     if not user_id:
#         return jsonify({"error": "Authentication required"}), 401
    
#     try:
#         mapped_count = map_project_activities(project_id)
#         return jsonify({
#             "message": f"mapped {mapped_count} activities"
#         }), 200
#     except Exception as e:
#         return jsonify({"error": f"An error occurred: {str(e)}"}), 500


# # ROUTE FOR CASE ID ENRICHMENT
# @normalization_bp.route("/<int:project_id>/enrich-case-ids", methods=["POST"])
# def enrich_case_ids_route(project_id):
#     """
#     Enriches events that are missing a case_id.
#     """
#     user_id = session.get("user_id")
#     if not user_id:
#         return jsonify({"error": "Authentication required"}), 401

#     try:
#         enriched_count = enrich_case_ids(project_id)
        
#         if enriched_count > 0:
#             message = "Case ID enrichment complete."
#         else:
#             message = "No confident case ID matches were found."

#         return jsonify({
#             "message": message,
#             "events_enriched": enriched_count
#         }), 200
#     except Exception as e:
#         return jsonify({"error": f"An error occurred: {str(e)}"}), 500