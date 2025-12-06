# backend/python_app/routes/dashboard.py

from flask import Blueprint, jsonify, session
from services.models import Project, File
from services.db import db
from services.file_service import *
from services.bpmn_service import *

dashboard_bp = Blueprint('dashboard', __name__)

# --- Route to get main dashboard data --- 
@dashboard_bp.route('/dashboard-data')
def get_dashboard_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    files = get_file_info_by_user(user_id)  
    bpmn_diagram_count = get_bpmn_count_by_user(user_id)
    latest_bpmn = get_latest_bpmn(user_id)
    last_discovery_run_date = latest_bpmn.upload_date.isoformat() if latest_bpmn else None

    return jsonify({
        "files": files,
        "bpmnDiagramCount": bpmn_diagram_count,
        "lastDiscoveryRun": last_discovery_run_date
    })