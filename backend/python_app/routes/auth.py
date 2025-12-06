from flask import Blueprint, jsonify, request, session, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash
from email.message import EmailMessage
import smtplib
import itsdangerous
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError


from services.db import db
from services.models import User, Notification
from datetime import datetime

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# -------------------------
# Helpers
# -------------------------
def _json_error(message: str, status: int):
    return jsonify({"message": message}), status

def _serializer():
    return URLSafeTimedSerializer(
        secret_key=current_app.config["SECRET_KEY"],
        salt=current_app.config["SECURITY_PASSWORD_SALT"],
    )

def generate_reset_token(email: str) -> str:
    return _serializer().dumps({"email": email})

def verify_reset_token(token: str, max_age_seconds: int = 3600) -> str:
    """Return email if token is valid and not expired."""
    data = _serializer().loads(token, max_age=max_age_seconds)
    return data.get("email")

def send_email(to_email: str, subject: str, html: str, text: str = ""):
    """Send email using SMTP settings from config (Gmail-ready)."""
    cfg = current_app.config
    msg = EmailMessage()
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to_email
    msg["Subject"] = subject
    if text:
        msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        if cfg["MAIL_USE_SSL"]:
            with smtplib.SMTP_SSL(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as smtp:
                smtp.ehlo()
                if cfg["MAIL_USERNAME"]:
                    smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as smtp:
                smtp.ehlo()
                if cfg["MAIL_USE_TLS"]:
                    smtp.starttls()
                    smtp.ehlo()
                if cfg["MAIL_USERNAME"]:
                    smtp.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
                smtp.send_message(msg)
    except Exception as e:
        current_app.logger.exception(f"SMTP send failed: {e}")

# -------------------------
# Routes
# -------------------------
@auth_bp.post("/login")
def login():
    """Authenticate user and create session cookie (httpOnly)."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    remember = bool(data.get("remember"))

    if not email or not password:
        return _json_error("Email and password are required", 400)

    user = db.session.query(User).filter_by(email=email).first()

    # --- FAILED AUTH: create a notification and return 401 ---
    if not user or not check_password_hash(user.password_hash, password):
        # best-effort client IP (works behind proxy if X-Forwarded-For is set)
        xff = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        ip = xff or (request.remote_addr or "")

        return _json_error("Incorrect email or password", 401)

    # create session
    session["user_id"] = user.user_id
    session.permanent = bool(remember)

    return jsonify({
        "message": "Logged in",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    }), 200


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

@auth_bp.get("/me")
def me():
    uid = session.get("user_id")
    if not uid:
        return _json_error("Not authenticated", 401)
    user = db.session.get(User, uid)
    if not user:
        session.clear()
        return _json_error("Not authenticated", 401)

    return jsonify({
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }), 200

@auth_bp.post("/register")
def register():
    """Create a new user with role, ensuring unique email; auto-login on success."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role_in = (data.get("role") or "").strip()

    # Basic validations
    if not name:
        return _json_error("Name is required", 400)
    if not email:
        return _json_error("Email is required", 400)
    if "@" not in email:
        return _json_error("Enter a valid email", 400)
    if len(password) < 3:
        return _json_error("Password must be at least 3 characters", 400)

    # Role validation & normalization
    # UI exposes: "BPO" or "Admin"
    # Persist consistently with existing seed row ('business process owner')
    allowed_map = {
        "BPO": "business process owner",
        "ADMIN": "admin",
    }
    role_key = role_in.upper() if role_in else "BPO"  # default to BPO
    if role_key not in allowed_map:
        return _json_error("Invalid role. Choose either 'BPO' or 'Admin'.", 400)
    role_value = allowed_map[role_key]

    # Uniqueness check (case-insensitive)
    existing = db.session.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        return _json_error("An account with this email already exists.", 409)

    # Create & persist
    user = User(name=name, email=email, role=role_value)
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _json_error("An account with this email already exists.", 409)

    # Auto-login
    session.clear()
    session["user_id"] = user.user_id
    session.permanent = True

    return jsonify({
        "message": "Registered successfully.",
        "user": {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        }
    }), 201


@auth_bp.post("/password/forgot")
def password_forgot():
    """Accept an email and (if valid) send a reset link. Always respond 200."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return _json_error("Email is required", 400)

    user = db.session.query(User).filter_by(email=email).first()

    if user:
        token = generate_reset_token(email)
        reset_link = f'{current_app.config["PASSWORD_RESET_URL"]}?token={token}'
        html = f"""
            <p>You requested a password reset.</p>
            <p><a href="{reset_link}">Click here to reset your password</a></p>
            <p>If you didn't request this, you can safely ignore this email.</p>
        """
        send_email(
            to_email=email,
            subject="Reset your password",
            html=html,
            text=f"Reset your password: {reset_link}",
        )

    return jsonify({"message": "If the email is registered, a reset link has been sent."}), 200

@auth_bp.post("/password/reset")
def password_reset():
    """Accept token + new password; update hash; (optionally) login."""
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    new_password = data.get("password") or ""

    if not token or not new_password:
        return _json_error("Token and new password are required", 400)
    if len(new_password) < 3:
        return _json_error("Password must be at least 3 characters", 400)

    try:
        email = verify_reset_token(token, max_age_seconds=3600)
    except SignatureExpired:
        return _json_error("Reset link has expired. Please request a new one.", 400)
    except BadSignature:
        return _json_error("Invalid reset token.", 400)

    user = db.session.query(User).filter_by(email=email).first()
    if not user:
        return _json_error("Invalid reset token.", 400)

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    session.clear()
    session["user_id"] = user.user_id
    session.permanent = True

    return jsonify({"message": "Password updated successfully."}), 200
