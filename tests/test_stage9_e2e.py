import pytest
from app import create_app
from config import Config
from services.seed_data import seed_database
from models.db import query_db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    seed_database(force=True)
    with app.test_client() as client:
        yield client

def test_all_critical_pages_accessible(client):
    pages = [
        ("/", 200, b"Hybrid Smart Street Light"),
        ("/complaint/report/SL-203", 200, b"Pole SL-203"),
        ("/complaint/qr-directory", 200, b"Pole QR Management"),
        ("/complaint/lookup", 200, b"Track Street Light Repair Status"),
        ("/simulator/", 200, b"IoT Feeder Substation Monitoring Simulator"),
        ("/dashboard/", 200, b"Municipal Operations Dashboard"),
        ("/dashboard/api/map-data", 200, b"feeders"),
        ("/dashboard/reports", 200, b"Municipal Analytics"),
        ("/dashboard/reports/export-csv", 200, b"Reference No"),
        ("/dashboard/route-optimizer", 200, b"Multi-Stop Field Dispatch Route Planner"),
        ("/auth/login", 200, b"Staff Portal Login"),
        ("/non-existent-page-404", 404, b"Page Not Found")
    ]

    for path, expected_status, content_snippet in pages:
        res = client.get(path)
        assert res.status_code == expected_status, f"Failed on {path}: got {res.status_code}"
        assert content_snippet in res.data, f"Snippet missing on {path}"

def test_authenticated_worker_portal(client):
    # Acquire CSRF token from login
    get_res = client.get("/auth/login")
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]

    login_res = client.post("/auth/login", data={
        "username": "worker_raj",
        "password": Config.WORKER_DEFAULT_PASSWORD,
        "csrf_token": token
    }, follow_redirects=True)
    assert login_res.status_code == 200

    # Access worker portal as logged-in technician
    tasks_res = client.get("/worker/tasks")
    assert tasks_res.status_code == 200
    assert b"Field Technician Work Orders" in tasks_res.data
    assert b"Rajesh Kumar" in tasks_res.data
