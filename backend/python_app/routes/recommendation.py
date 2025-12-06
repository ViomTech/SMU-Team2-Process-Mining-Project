from flask import Blueprint, request, jsonify, session
from services.recommendation_service import *
from services.models import Recommendation, Project
from services.db import db

recommendation_bp = Blueprint("recommendation", __name__)


@recommendation_bp.route("/chat", methods=["POST"])
def chat_route():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.get_json()
    if not data or "messages" not in data:
        return jsonify({"error": "Invalid JSON body, 'messages' key is required"}), 400

    messages = data["messages"]
    
    try:
        answer = get_llm_chat_response(messages)
        return jsonify({"answer": answer}), 200
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500
    
# In case max token limit reached
@recommendation_bp.route("/summarize", methods=["POST"])
def summarize_route():
    data = request.get_json()
    if not data or "messages" not in data:
        return jsonify({"error": "Missing messages to summarize"}), 400

    messages_to_summarize = data["messages"]
    
    summarization_prompt = [
        {"role": "system", "content": "You are a helpful assistant. Summarize the following conversation into a concise, single paragraph, retaining all key facts and decisions."},
        *messages_to_summarize
    ]
    
    try:
        summary = get_llm_chat_response(summarization_prompt)
        return jsonify({"summary": summary}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@recommendation_bp.route("/save", methods=["POST"])
def save_recommendation_route():
    """
    Saves a single, curated AI recommendation to the database.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    required_fields = ["project_id", "content", "bottleneck_activity"]
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required data (project_id, content, bottleneck_activity)"}), 400

    try:
        new_rec = save_recommendation(
            user_id=user_id,
            project_id=data["project_id"],
            content=data["content"],
            bottleneck_activity=data["bottleneck_activity"]
        )
        return jsonify({
            "message": "Recommendation saved successfully",
            "user_id": new_rec.user_id
        }), 201

    except Exception as e:
        print(f"Error saving recommendation: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
    
@recommendation_bp.route("/library", methods=["GET"])
def get_recommendations():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    project_id = request.args.get("project_id", type=int)
    
    try:
        recs = get_all_recommendations(user_id)
        result = [
            {
                "recommendation_id": r.Recommendation.recommendation_id,
                "content": r.Recommendation.content,
                "bottleneck_activity": r.Recommendation.bottleneck_activity,
                "project_id": r.Recommendation.project_id,
                "project_name": r.project_name
            } for r in recs
        ]
        return jsonify(result), 200
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

@recommendation_bp.route("/delete", methods=["POST"])
def delete_recommendation_route():

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    if not data or "recommendation_id" not in data:
        return jsonify({"error": "Missing 'recommendation_id' in request body"}), 400

    recommendation_id = data["recommendation_id"]

    try:
        was_deleted = delete_recommendation(
            recommendation_id=recommendation_id,
            user_id=user_id
        )

        if was_deleted:
            return jsonify({"message": "Recommendation deleted successfully"}), 200
        else:
            return jsonify({"error": "Recommendation not found or you do not have permission"}), 404

    except Exception as e:
        print(f"Error during recommendation deletion: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500