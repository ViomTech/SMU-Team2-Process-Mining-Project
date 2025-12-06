from services.models import User

def test_password_helpers(app):
    u = User(name="A", email="a@example.com")
    u.set_password("secret123")
    assert u.password_hash and u.password_hash != "secret123"
    assert u.check_password("secret123")
    assert not u.check_password("wrong")
