import itsdangerous
import pytest
from sqlalchemy.exc import IntegrityError

from services.db import db
from services.models import User
import routes.auth as auth_module

# -------- Register --------
def test_register_success(client):
    r = client.post("/auth/register", json={
        "name": "Bob", "email": "bob@example.com", "password": "pw123"
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["user"]["email"] == "bob@example.com"
    with client.session_transaction() as sess:
        assert "user_id" in sess
        # register endpoint sets session.permanent = True by design
        assert sess.permanent is True

def test_register_validations(client):
    cases = [
        ({"name": "", "email": "a@b.com", "password": "123"}, 400, "Name is required"),
        ({"name": "A", "email": "", "password": "123"}, 400, "Email is required"),
        ({"name": "A", "email": "bademail", "password": "123"}, 400, "valid email"),
        ({"name": "A", "email": "a@b.com", "password": "12"}, 400, "at least 3"),
    ]
    for payload, code, msg in cases:
        r = client.post("/auth/register", json=payload)
        assert r.status_code == code
        assert msg.lower() in r.get_json()["message"].lower()

def test_register_duplicate_case_insensitive(client, make_user):
    make_user(email="DUPE@EXAMPLE.COM")
    r = client.post("/auth/register", json={
        "name": "X", "email": "dupe@example.com", "password": "pw123"
    })
    assert r.status_code == 409
    assert "already exists" in r.get_json()["message"].lower()

def test_register_integrityerror_branch(client, monkeypatch):
    def boom():
        raise IntegrityError("stmt", params=None, orig=None)
    monkeypatch.setattr(db.session, "commit", boom, raising=True)
    r = client.post("/auth/register", json={
        "name": "Z", "email": "z@example.com", "password": "pw123"
    })
    assert r.status_code == 409
    assert "already exists" in r.get_json()["message"].lower()

# -------- Login / Logout / Me --------
@pytest.mark.parametrize("remember,expected_perm", [(True, True), (False, False)])
def test_login_success_and_remember(client, make_user, remember, expected_perm):
    u = make_user(email="login@example.com", password="pw123")
    r = client.post("/auth/login", json={
        "email": "login@example.com", "password": "pw123", "remember": remember
    })
    assert r.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("user_id") == u.user_id
        assert sess.permanent is expected_perm

def test_login_missing_fields(client):
    r = client.post("/auth/login", json={"email": "", "password": ""})
    assert r.status_code == 400
    assert "required" in r.get_json()["message"].lower()

def test_login_bad_credentials(client, make_user):
    make_user(email="wrong@example.com", password="goodpw")
    r = client.post("/auth/login", json={"email": "wrong@example.com", "password": "bad"})
    assert r.status_code == 401
    assert "incorrect" in r.get_json()["message"].lower()

def test_logout_and_me_requirements(client, make_user):
    make_user(email="me@example.com", password="pw")
    client.post("/auth/login", json={"email": "me@example.com", "password": "pw"})
    r1 = client.get("/auth/me")
    assert r1.status_code == 200
    client.post("/auth/logout")
    r2 = client.get("/auth/me")
    assert r2.status_code == 401

def test_me_stale_session_clears(client, make_user):
    # Log in a real user first (so we have a normal session)
    make_user(email="del@example.com", password="pw")
    client.post("/auth/login", json={"email": "del@example.com", "password": "pw"})

    # Now corrupt the session: set user_id to a non-existent id
    with client.session_transaction() as sess:
        sess["user_id"] = 999_999_999  # guaranteed to not exist

    # /auth/me should detect that user does not exist, clear session, and return 401
    r = client.get("/auth/me")
    assert r.status_code == 401

    # Session must be cleared by the route
    with client.session_transaction() as sess:
        assert "user_id" not in sess


# -------- Forgot / Reset password --------
def test_password_forgot_requires_email(client):
    r = client.post("/auth/password/forgot", json={"email": ""})
    assert r.status_code == 400
    assert "email is required" in r.get_json()["message"].lower()

def test_password_forgot_existing_user_sends(client, make_user, email_outbox):
    make_user(email="f@example.com")
    r = client.post("/auth/password/forgot", json={"email": "f@example.com"})
    assert r.status_code == 200
    assert email_outbox and "reset your password" in email_outbox[0]["subject"].lower()

def test_password_forgot_unknown_is_noop(client, email_outbox):
    r = client.post("/auth/password/forgot", json={"email": "ghost@example.com"})
    assert r.status_code == 200
    assert email_outbox == []

def test_password_reset_validations(client):
    r1 = client.post("/auth/password/reset", json={"token": "", "password": ""})
    assert r1.status_code == 400
    r2 = client.post("/auth/password/reset", json={"token": "t", "password": "12"})
    assert r2.status_code == 400
    assert "at least 3" in r2.get_json()["message"].lower()

def test_password_reset_expired_token(monkeypatch, client):
    def raise_expired(*_a, **_k):
        raise itsdangerous.SignatureExpired("expired")
    monkeypatch.setattr(auth_module, "verify_reset_token", raise_expired, raising=True)
    r = client.post("/auth/password/reset", json={"token": "X", "password": "abc"})
    assert r.status_code == 400
    assert "expired" in r.get_json()["message"].lower()

def test_password_reset_bad_token(monkeypatch, client):
    def raise_bad(*_a, **_k):
        raise itsdangerous.BadSignature("bad")
    monkeypatch.setattr(auth_module, "verify_reset_token", raise_bad, raising=True)
    r = client.post("/auth/password/reset", json={"token": "X", "password": "abc"})
    assert r.status_code == 400
    assert "invalid" in r.get_json()["message"].lower()

def test_password_reset_user_not_found(monkeypatch, client):
    monkeypatch.setattr(auth_module, "verify_reset_token", lambda t, max_age_seconds=3600: "ghost@example.com", raising=True)
    r = client.post("/auth/password/reset", json={"token": "ok", "password": "abc123"})
    assert r.status_code == 400
    assert "invalid reset token" in r.get_json()["message"].lower()

def test_password_reset_success_roundtrip(client, make_user, app):
    u = make_user(email="reset@example.com", password="oldpw")
    with app.app_context():
        token = auth_module.generate_reset_token("reset@example.com")
    r = client.post("/auth/password/reset", json={"token": token, "password": "newpw"})
    assert r.status_code == 200
    with app.app_context():
        updated = db.session.get(User, u.user_id)
        assert updated.check_password("newpw")
    with client.session_transaction() as sess:
        assert "user_id" in sess
        assert sess.permanent is True  # route sets permanent True on reset

def test_token_helpers_roundtrip(app):
    with app.app_context():
        token = auth_module.generate_reset_token("x@example.com")
        email = auth_module.verify_reset_token(token, max_age_seconds=3600)
        assert email == "x@example.com"
