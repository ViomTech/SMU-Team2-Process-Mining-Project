def test_home_route_success(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "database connection is successful" in resp.get_data(as_text=True).lower()

def test_session_lifetime_config(client):
    # Validate our test config made it into the app and is respected
    app = client.application
    assert app.config["REMEMBER_ME_DAYS"] == 9
    assert app.permanent_session_lifetime.days == 9
