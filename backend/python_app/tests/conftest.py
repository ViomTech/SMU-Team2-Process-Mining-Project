import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ...existing code...

import pytest
import datetime as dt
import hashlib
from sqlalchemy.pool import StaticPool

import app as app_module
from app import create_app

from services.db import db
from services.models import User, Project, File, BpmnFile

class TestConfig:
    TESTING = True
    # Use a throwaway in-memory DB for speed and isolation
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }

    # Security / tokens (required by helpers)
    SECRET_KEY = "testing-secret"
    SECURITY_PASSWORD_SALT = "testing-salt"

    # Frontend/CORS-related (used to build PASSWORD_RESET_URL in prod Config)
    FRONTEND_ORIGIN = "http://localhost:5173"
    PASSWORD_RESET_URL = "http://frontend/reset"  # explicit for tests

    # Sessions / remember-me (mirror your Config.py contract)
    REMEMBER_ME_DAYS = 9  # test a non-default to validate lifetime wiring
    PERMANENT_SESSION_LIFETIME = dt.timedelta(days=REMEMBER_ME_DAYS)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"  # avoid 'None' + Secure combo issues in tests
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_NAME = "session"

    # Mail (we mock send, but fields must exist)
    MAIL_FROM = "noreply@example.com"
    MAIL_SERVER = "localhost"
    MAIL_PORT = 25
    MAIL_USERNAME = ""
    MAIL_PASSWORD = ""
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False

    JSON_SORT_KEYS = False

@pytest.fixture()
def app(monkeypatch):
    # Force the application factory to use TestConfig instead of real Config
    monkeypatch.setattr(app_module, "Config", TestConfig, raising=True)
    application = create_app()
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def make_user(app):
    def _make_user(email="user@example.com", password="pw123", name="User", role="analyst"):
        u = User(name=name, email=email.lower())
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        return u
    return _make_user

@pytest.fixture()
def email_outbox(monkeypatch):
    """
    Capture calls to auth.send_email(...) without hitting SMTP.
    """
    import routes.auth as auth_module
    outbox = []

    def fake_send(to_email, subject, html, text=""):
        outbox.append({"to": to_email, "subject": subject, "html": html, "text": text})
        return True

    monkeypatch.setattr(auth_module, "send_email", fake_send, raising=True)
    return outbox

@pytest.fixture()
def make_project(app):
    """
    Create a Project for a given user, and auto-assign a different BPO user
    (ensures unique email per project).
    """
    from services.models import Project

    def _make_project(user, project_name="Test Project", description="A test project", **_ignore):
        # Generate a unique BPO email each time
        unique_suffix = os.urandom(4).hex()
        assigned_bpo = User(name=f"BPO {unique_suffix}", email=f"bpo_{unique_suffix}@example.com")
        assigned_bpo.set_password("bpopass")
        db.session.add_all([user, assigned_bpo])
        db.session.flush()  # assign IDs

        p = Project(
            user_id=user.user_id,
            project_name=project_name,
            description=description,
            assigned_bpo_id=assigned_bpo.user_id,
        )
        db.session.add(p)
        db.session.commit()
        return p
    return _make_project

@pytest.fixture()
def make_file(app):
    """A fixture to create a File for a given user and project."""
    def _make_file(user, project, filename="test.csv", file_data=b"data"):
        # Create a simple unique hash for testing purposes
        file_hash = hashlib.sha256(file_data + filename.encode()).hexdigest()
        
        f = File(
            user_id=user.user_id,
            project_id=project.project_id,
            filename=filename,
            file_data=file_data,
            file_hash=file_hash
        )
        db.session.add(f)
        db.session.commit()
        return f
    return _make_file