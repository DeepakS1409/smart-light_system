import pytest
from app import create_app
from models.db import query_db, execute_db
from services.incident_service import submit_complaint
from services.sensor_integration import process_feeder_telemetry
from services.seed_data import seed_database
from config import Config

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    seed_database(force=True)
    with app.test_client() as client:
        yield client

def test_dashboard_renders_stats_and_content(client):
    # Ensure there's at least one complaint and one feeder alert
    submit_complaint("SL-203", "Light not working", "Testing dashboard stats")
    process_feeder_telemetry("FDR-A01", 0.0, 0.0, is_simulated=True)

    res = client.get("/dashboard/")
    assert res.status_code == 200
    assert b"Municipal Operations Dashboard" in res.data
    assert b"Total Poles" in res.data
    assert b"Active Complaints" in res.data
    assert b"High Priority" in res.data
    assert b"Live Spatial Infrastructure Map" in res.data
    assert b"SL-203" in res.data
    assert b"FDR-A01" in res.data

def test_map_data_api(client):
    res = client.get("/dashboard/api/map-data")
    assert res.status_code == 200
    data = res.get_json()
    assert "feeders" in data
    assert "poles" in data
    assert len(data["feeders"]) >= 3
    assert len(data["poles"]) >= 10

    # Verify feeder structure
    fdr_a = next(f for f in data["feeders"] if f["zone"] == "Zone A")
    assert fdr_a["feeder_code"] == "FDR-A01"
    assert "latitude" in fdr_a and "longitude" in fdr_a

    # Verify pole structure
    sl_203 = next(p for p in data["poles"] if p["pole_code"] == "SL-203")
    assert sl_203["latitude"] == 12.9732
    assert sl_203["longitude"] == 77.5962

def test_role_restricted_assignment(client):
    # Create ticket
    res_c = submit_complaint("SL-201", "Flickering / dim", "Dim pole testing assignment")
    cid = res_c["complaint_id"]
    worker = query_db("SELECT id FROM users WHERE username = 'worker_raj'", one=True)

    # 1. Unauthenticated post without CSRF token is rejected with 400 Bad Request, or with CSRF redirects to login
    anon_res = client.post(f"/dashboard/complaints/{cid}/assign", data={"worker_id": worker["id"]})
    assert anon_res.status_code in [302, 400]

    # With CSRF token, anonymous post redirects to login
    get_res = client.get("/auth/login")
    with client.session_transaction() as sess:
        anon_csrf = sess["_csrf_token"]
    anon_res_csrf = client.post(f"/dashboard/complaints/{cid}/assign", data={
        "worker_id": worker["id"],
        "csrf_token": anon_csrf
    })
    assert anon_res_csrf.status_code == 302
    assert "/auth/login" in anon_res_csrf.headers["Location"]

    # 2. Worker role attempting assignment should be forbidden / redirected
    login_res = client.get("/auth/login")
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]

    client.post("/auth/login", data={
        "username": "worker_raj",
        "password": Config.WORKER_DEFAULT_PASSWORD,
        "csrf_token": token
    })

    # Fetch fresh post-login CSRF token
    with client.session_transaction() as sess:
        post_login_token = sess["_csrf_token"]

    worker_assign_res = client.post(f"/dashboard/complaints/{cid}/assign", data={
        "worker_id": worker["id"],
        "csrf_token": post_login_token
    })
    # Blocked by roles_required
    assert worker_assign_res.status_code == 302
    assert "/auth/login" in worker_assign_res.headers["Location"] or worker_assign_res.headers["Location"] == "/"
