import pytest
from app import create_app
from config import Config
from models.db import query_db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_home_page_runs(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hybrid Smart Street Light Fault Monitoring" in response.data
    assert b"SL-203" in response.data
    assert b"Demonstration Data" in response.data

def test_login_page_renders(client):
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Staff Portal Login" in response.data

def test_database_seed_contains_required_fixtures():
    poles = query_db("SELECT * FROM poles")
    assert len(poles) >= 10
    sl_203 = query_db("SELECT * FROM poles WHERE pole_code = 'SL-203'", one=True)
    assert sl_203 is not None
    assert sl_203["zone"] == "Zone A"

    users = query_db("SELECT * FROM users")
    roles = {u["role"] for u in users}
    assert "admin" in roles
    assert "supervisor" in roles
    assert "worker" in roles
    workers = [u for u in users if u["role"] == "worker"]
    assert len(workers) >= 3

def test_csrf_protection(client):
    # POST without CSRF token should return 400
    response = client.post("/auth/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 400

def test_auth_login_success(client):
    # Fetch login page first to acquire CSRF token in session
    get_res = client.get("/auth/login")
    assert get_res.status_code == 200
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]

    post_res = client.post("/auth/login", data={
        "username": "admin",
        "password": Config.ADMIN_DEFAULT_PASSWORD,
        "csrf_token": token
    }, follow_redirects=True)
    assert post_res.status_code == 200
    assert b"System Administrator" in post_res.data
