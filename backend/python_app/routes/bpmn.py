from flask import Blueprint, request, jsonify, Response, session
from services.bpmn_service import *
from services.approval_service import *
from services.models import BpmnFile  # make sure this import exists

bpmn_bp = Blueprint("bpmn", __name__)

# Save BPMN to database
@bpmn_bp.route("/save-bpmn", methods=["POST"])
def save_bpmn_route():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    project_id = data.get("project_id")
    filename = data.get("filename")
    xml_content = data.get("bpmn_xml")
    description = data.get("description", "")

    if not filename or not xml_content:
        return jsonify({"error": "Missing filename or bpmn_xml"}), 400

    try:
        new_bpmn = save_bpmn(user_id, project_id, filename, description, xml_content)
        return jsonify({
            "id": new_bpmn.bpmnfile_id,
            "filename": new_bpmn.filename,
            "message": "BPMN saved successfully"
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500

@bpmn_bp.route("/save-edits/<int:bpmn_id>", methods=["PUT"])
def save_new_version_route(bpmn_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    new_xml = data.get("new_bpmn_xml")

    if not new_xml:
        return jsonify({"error": "Missing new_bpmn_xml"}), 400
    
    try:
        bpmn_edit = save_bpmn_edits(bpmn_id, new_xml, user_id)
        return jsonify({
            "id": bpmn_edit.bpmnfile_id,
            "version": bpmn_edit.bpmnfile_id,
            "message": "BPMN edits saved successfully"
        }), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500

# Download BPMN
@bpmn_bp.route("/download/<int:bpmn_id>")
def download_bpmn_route(bpmn_id):
    bpmn = BpmnFile.query.get(bpmn_id)
    if not bpmn or not bpmn.file_data:
        return jsonify({"error": "File not found"}), 404

    xml = bpmn.file_data.decode("utf-8") if isinstance(bpmn.file_data, (bytes, bytearray)) else bpmn.file_data
    filename = (bpmn.filename or f"diagram_{bpmn_id}").rstrip(".bpmn")

    return Response(
        xml,
        mimetype="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}.bpmn"}
    )

@bpmn_bp.route("/export-svg/<int:bpmn_id>")
def export_bpmn_as_svg(bpmn_id):
    bpmn = BpmnFile.query.get(bpmn_id)
    if not bpmn or not bpmn.file_data:
        return jsonify({"error": "File not found"}), 404

    xml = bpmn.file_data.decode("utf-8", errors="ignore") if isinstance(bpmn.file_data, (bytes, bytearray)) else bpmn.file_data
    return jsonify({"xml": xml, "filename": bpmn.filename or f"diagram_{bpmn_id}"}), 200

# View BPMN in browser (return XML for frontend rendering)
@bpmn_bp.route("/view/<int:bpmn_id>")
def view_bpmn_route(bpmn_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    file = get_bpmn(user_id, bpmn_id)
    if not file:
        return jsonify({"error": "File not found"}), 404

    xml_content = file.file_data.decode("utf-8")  # Convert bytes to string
    print(f"XML content preview: {xml_content[:200]}...")

    if not xml_content.strip().startswith("<?xml") and not xml_content.strip().startswith("<bpmn:"):
        print("Warning: XML doesn't look like valid BPMN")

    return xml_content, 200, {"Content-Type": "application/xml"}

# Retrieve the latest 5 BPMN models  ⬅️ now includes project_id
@bpmn_bp.route("/recent")
def recent_bpmn_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    files = get_recent_bpmn(user_id) or []
    
    results = [
        {
            "bpmn_id": file.bpmnfile_id,
            "filename": file.filename,
            "upload_date": file.upload_date,
            "project_id": getattr(file, "project_id", None),  # ensure FE has project context
        } for file in files
    ]
    
    return jsonify(results), 200

# Retrieve all BPMN models
@bpmn_bp.route("/all-bpmn")
def get_all_bpmn_route():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    files = get_all_bpmn(user_id) or []
    
    results = [
        {
            "bpmn_id": file.bpmnfile_id,
            "filename": file.filename,
            "upload_date": file.upload_date,
            "project_id": getattr(file, "project_id", None),
        } for file in files
    ]

    return jsonify(results), 200

@bpmn_bp.route("/get-bpmn-by-project/<int:project_id>")
def get_bpmn_by_project_route(project_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    files = get_bpmn_by_project(user_id, project_id) or []
    
    results = [
        {
            "bpmn_id": file.bpmnfile_id,
            "filename": file.filename,
            "upload_date": file.upload_date,
            "project_id": getattr(file, "project_id", None),
        } for file in files
    ]

    return jsonify(results), 200

# Retrieve name and description from bpmn id  ⬅️ now returns project_id
@bpmn_bp.route("/get-info/<int:bpmn_id>")
def bpmn_info_route(bpmn_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    file = get_bpmn(user_id, bpmn_id)
    if not file:
        return jsonify({"error": "BPMN file not found"}), 404

    return {
        "filename": file.filename,
        "description": file.description,
        "version": file.version,
        "project_id": getattr(file, "project_id", None),
    }

# Updates bpmn filename and description
@bpmn_bp.route("/update-bpmn-info/<int:bpmn_id>", methods=["PUT"])
def update_bpmn_info_route(bpmn_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing filename/description"}), 400
    
    new_filename = data["filename"]
    new_description = data["description"]
    file = update_bpmn_info(bpmn_id, new_filename, new_description)
    if not file:
        return jsonify({"error": f"BPMN file with id {bpmn_id} not found"}), 404
    
    return jsonify({
        "message": "BPMN information updated successfully",
        "id": file.bpmnfile_id,
        "filename": file.filename
    }), 200

@bpmn_bp.route("/update-bpmn/<int:bpmn_id>", methods=["PUT"])
def update_bpmn_route(bpmn_id):
    data = request.get_json()
    if not data or "xml" not in data:
        return jsonify({"error": "Missing XML data"}), 400
    
    new_xml = data["xml"]
    file = update_bpmn(bpmn_id, new_xml)
    if not file:
        return jsonify({"error": f"BPMN file with id {bpmn_id} not found"}), 404
    
    return jsonify({
        "message": "BPMN updated successfully",
        "id": file.bpmnfile_id,
        "filename": file.filename
    }), 200

@bpmn_bp.route("/delete-bpmn/<int:bpmn_id>", methods=["DELETE"])
def delete_bpmn_route(bpmn_id):
    try:
        result = delete_bpmn(bpmn_id)
        return jsonify(result), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except RuntimeError as re:
        return jsonify({"error": str(re)}), 500
    
@bpmn_bp.route("/submit-for-approval", methods=["POST"])
def submit_for_approval_route():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json()
        bpmn_id = data.get("bpmn_id")
        bpo_id = data.get("bpo_id")

        if not bpmn_id or not bpo_id:
            return jsonify({"error": "bpmn_id and bpo_id are required"}), 400

        approval = submit_bpmn_for_approval(bpmn_id=bpmn_id, user_id=user_id, bpo_id=bpo_id)
        return jsonify({
            "approval_id": approval.approval_id,
            "bpmnfile_id": approval.bpmnfile_id,
            "submitted_by": approval.submitted_by,
            "reviewed_by": approval.reviewed_by,
            "status": approval.status,
            "created_at": approval.created_at.isoformat()
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bpmn_bp.route("/review-approval", methods=["PUT"])
def review_approval_route():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json()
        approval_id = data.get("approval_id")
        approved = data.get("approved")  # should be True or False
        comment = data.get("comment")

        if approval_id is None or approved is None:
            return jsonify({"error": "approval_id and approved are required"}), 400

        approval = BpmnApproval.query.get(approval_id)
        if not approval:
            return jsonify({"error": f"Approval with ID {approval_id} not found"}), 404

        if approval.reviewed_by != user_id:
            return jsonify({"error": "You are not authorized to review this approval"}), 403

        approval = review_bpmn(approval_id, approved, comment)
        return jsonify({
            "approval_id": approval.approval_id,
            "bpmnfile_id": approval.bpmnfile_id,
            "status": approval.status,
            "reviewed_by": approval.reviewed_by,
            "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bpmn_bp.route("/get-bpmn-bpo/<int:bpmn_id>", methods=["GET"])
def get_bpmn_bpo_route(bpmn_id):
    try:
        bpo = get_bpmn_bpo_info(bpmn_id)
        if not bpo:
            return jsonify({"error": "No assigned BPO found"}), 404
        return jsonify(bpo), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bpmn_bp.route("/get-approval-status/<int:bpmn_id>", methods=["GET"])
def get_bpmn_approval_status(bpmn_id):
    try:
        approval_status = get_approval_status(bpmn_id)
        return jsonify({"approval_status": approval_status}), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bpmn_bp.route("/get-bpo-approvals", methods=["GET"])
def get_bpo_approvals_route():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        approvals = get_bpo_approvals(user_id)
        return jsonify({"bpmn_files": approvals}), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bpmn_bp.route("/get-bpmn-approval/<int:bpmn_id>", methods=["GET"])
def get_bpmn_approval_route(bpmn_id):
    try: 
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        approval = get_bpmn_approval(bpmn_id)
        return jsonify(approval), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bpmn_bp.route("/<int:project_id>/history", methods=["GET"])
def get_project_approval_history(project_id):
    bpmns = BpmnFile.query.filter_by(project_id=project_id).all()
    result = []
    for b in bpmns:
        for a in b.approvals:
            submitted_user = User.query.get(a.submitted_by)
            reviewed_user = User.query.get(a.reviewed_by) if a.reviewed_by else None

            result.append({
                "approval_id": a.approval_id,
                "bpmnfile_id": b.bpmnfile_id,
                "bpmn_filename": b.filename,
                "from_state": a.from_state,
                "to_state": a.to_state,
                "status": a.status,
                "comment": a.comment,
                "version": a.version,
                "submitted_by": submitted_user.name if submitted_user else str(a.submitted_by),
                "reviewed_by": reviewed_user.name if reviewed_user else None,
                "created_at": a.created_at.isoformat(),
                "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            })
    return jsonify({"history": result})
@bpmn_bp.route("/get-version-history/<int:bpmn_id>", methods=["GET"])
def get_version_history_route(bpmn_id):
    """Get version history for a BPMN file"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        versions = get_version_history(bpmn_id, user_id)
        return jsonify({"versions": versions}), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bpmn_bp.route("/restore-version", methods=["POST"])
def restore_version_route():
    """Restore a previous BPMN version (creates new version as copy)"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    bpmn_id = data.get("bpmn_id")
    audit_id = data.get("audit_id")  # The version to restore from
    
    if not bpmn_id or not audit_id:
        return jsonify({"error": "bpmn_id and audit_id are required"}), 400
    
    try:
        restored_bpmn = restore_bpmn_version(bpmn_id, audit_id, user_id)
        return jsonify({
            "message": "Version restored successfully",
            "bpmnfile_id": restored_bpmn.bpmnfile_id,
            "new_version": restored_bpmn.version,
            "filename": restored_bpmn.filename
        }), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@bpmn_bp.route("/get-project-bpmn-files/<int:project_id>", methods=["GET"])
def get_project_bpmn_files_route(project_id):
    """Get all BPMN files in a project (for cloning)"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        files = get_project_bpmn_files(project_id, user_id)
        return jsonify({"bpmn_files": files}), 200
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bpmn_bp.route("/clone-bpmn", methods=["POST"])
def clone_bpmn_route():
    """Clone a BPMN file in the same project (creates new file)"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    source_bpmn_id = data.get("source_bpmn_id")
    project_id = data.get("project_id")
    
    if not source_bpmn_id or not project_id:
        return jsonify({"error": "source_bpmn_id and project_id are required"}), 400
    
    try:
        new_bpmn = clone_bpmn_file(source_bpmn_id, project_id, user_id)
        return jsonify({
            "message": "BPMN file cloned successfully",
            "bpmnfile_id": new_bpmn.bpmnfile_id,
            "new_version": new_bpmn.version,
            "filename": new_bpmn.filename
        }), 201
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 404
    
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

