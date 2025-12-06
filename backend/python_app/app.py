# backend/python_app/app.py
from flask import Flask, jsonify, request, session, abort
from flask_cors import CORS
from sqlalchemy import text
from config import Config
from services.db import db
from flask_migrate import Migrate
from services.models import User, File, Notification
from routes.file import file_bp
from routes.project import project_bp
from routes.user import user_bp
from routes.auth import auth_bp
from datetime import timezone
import os
from routes.bpmn import bpmn_bp
from routes.normalization import normalization_bp
from routes.process_mining import process_bp
from routes.dashboard import dashboard_bp
from routes.recommendation import recommendation_bp

# ✅ NEW — import monitoring blueprint
from routes.monitoring import monitoring_bp


def create_app():
    app = Flask(__name__)

    # Load config first so we can read FRONTEND_ORIGINS for CORS
    app.config.from_object(Config)

    # ✅ CORS: allow multiple origins, enable cookies
    CORS(
        app,
        resources={r"/*": {"origins": app.config.get("FRONTEND_ORIGINS", [])}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    db.init_app(app)
    migrate = Migrate(app, db)

    # ✅ Register blueprints (unchanged)
    app.register_blueprint(auth_bp)
    app.register_blueprint(file_bp, url_prefix="/api/file")
    app.register_blueprint(project_bp, url_prefix="/api/project")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(bpmn_bp, url_prefix="/api/bpmn")
    app.register_blueprint(normalization_bp, url_prefix="/api/normalize")
    app.register_blueprint(process_bp, url_prefix="/api/process-mining")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(recommendation_bp, url_prefix="/api/recommendation")
    app.register_blueprint(monitoring_bp, url_prefix="/api/monitoring")

    @app.route("/")
    def home():
        try:
            db.session.execute(text("SELECT 1"))
            return "Database connection is successful."
        except Exception as e:
            return f"Database connection failed: {e}"

    @app.route("/set-user")
    def set_user():
        session["user_id"] = 2
        return "User ID set to 2"

    def _to_iso_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @app.get("/api/notifications")
    def list_notifications():
        uid = session.get("user_id")
        if not uid:
            return jsonify({"message": "Not authenticated"}), 401

        rows = (
            db.session.query(Notification)
            .filter((Notification.user_id == uid) | (Notification.user_id.is_(None)))
            .order_by(Notification.created_at.desc())
            .limit(200)
            .all()
        )

        return jsonify([
            {
                "id": n.id,
                "type": n.type,
                "message": n.message,
                "timestamp": _to_iso_utc(n.created_at),
                "targetUrl": n.target_url,
                "read": n.read,
            }
            for n in rows
        ])

    @app.patch("/api/notifications/<int:notification_id>/read")
    def mark_one_read(notification_id: int):
        uid = session.get("user_id")
        if not uid:
            return jsonify({"message": "Not authenticated"}), 401
        n = db.session.get(Notification, notification_id)
        if not n:
            return jsonify({"message": "Not found"}), 404
        if n.user_id not in (None, uid):
            return jsonify({"message": "Forbidden"}), 403
        n.read = True
        db.session.commit()
        return jsonify({"ok": True})

    @app.patch("/api/notifications/mark-all-read")
    def mark_all_read():
        uid = session.get("user_id")
        if not uid:
            return jsonify({"message": "Not authenticated"}), 401
        (
            db.session.query(Notification)
            .filter((Notification.user_id == uid) | (Notification.user_id.is_(None)))
            .update({Notification.read: True}, synchronize_session=False)
        )
        db.session.commit()
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
