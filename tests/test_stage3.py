import pytest
from app import create_app
from config import Config
from models.db import query_db, execute_db
from services.incident_service import generate_pole_qr, submit_complaint, evaluate_priority
from services.seed_data import seed_database
from pathlib import Path

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    seed_database(force=True)
    with app.test_client() as client:
        yield client

def test_qr_generation():
    rel_path = generate_pole_qr("SL-203")
    assert rel_path == "qr_codes/SL-203.png"
    full_path = Config.QR_FOLDER / "SL-203.png"
    assert full_path.exists()
    assert full_path.stat().st_size > 0

def test_priority_rules_evaluation():
    normal_pole = query_db("SELECT * FROM poles WHERE pole_code = 'SL-203'", one=True)
    high_risk_pole = query_db("SELECT * FROM poles WHERE pole_code = 'SL-204'", one=True)
    assert high_risk_pole["is_high_risk"] == 1

    # 1. High hazard category on normal pole -> HIGH
    p1, r1 = evaluate_priority(normal_pole, "Exposed wire / electrical hazard / pole damage")
    assert p1 == "HIGH"
    assert "immediate electrical hazard" in r1

    # 2. Bulb out on normal pole -> MEDIUM
    p2, r2 = evaluate_priority(normal_pole, "Light not working")
    assert p2 == "MEDIUM"

    # 3. Dimming on normal pole -> LOW
    p3, r3 = evaluate_priority(normal_pole, "Flickering / dim")
    assert p3 == "LOW"

    # 4. Normal defect on high-risk pole -> Escalated to HIGH
    p4, r4 = evaluate_priority(high_risk_pole, "Light not working")
    assert p4 == "HIGH"
    assert "high-risk area" in r4

def test_complaint_submission_and_duplicate_detection():
    # Clean previous complaints to test fresh
    execute_db("DELETE FROM status_history")
    execute_db("DELETE FROM complaints")

    # 1. First submission on SL-203
    res1 = submit_complaint(
        pole_code="SL-203",
        category="Light not working",
        description="Bulb went dark yesterday"
    )
    assert res1["reference_no"].startswith("REF-")
    assert res1["is_duplicate"] is False
    assert res1["primary_ticket"] is None
    primary_id = res1["complaint_id"]

    # 2. Second submission on SL-203 with same category while active
    res2 = submit_complaint(
        pole_code="SL-203",
        category="Light not working",
        description="Still not working tonight"
    )
    assert res2["is_duplicate"] is True
    assert res2["primary_ticket"]["id"] == primary_id
    assert res2["primary_ticket"]["reference_no"] == res1["reference_no"]

    # 3. Third submission on different pole in same zone (SL-202) -> NOT a duplicate
    res3 = submit_complaint(
        pole_code="SL-202",
        category="Light not working",
        description="Different pole defect"
    )
    assert res3["is_duplicate"] is False

def test_web_complaint_submission_and_lookup(client):
    # Fetch form to get CSRF token
    get_res = client.get("/complaint/report/SL-203")
    assert get_res.status_code == 200
    with client.session_transaction() as sess:
        token = sess["_csrf_token"]

    # Submit complaint via POST
    post_res = client.post("/complaint/report/SL-203", data={
        "csrf_token": token,
        "category": "Light not working",
        "description": "Integration test web submission"
    })
    assert post_res.status_code == 200
    assert b"Complaint Registered Successfully" in post_res.data or b"Duplicate Report Linked" in post_res.data

    # Fetch reference from database to test lookup
    latest = query_db("SELECT reference_no FROM complaints ORDER BY id DESC LIMIT 1", one=True)
    lookup_res = client.get(f"/complaint/lookup?ref={latest['reference_no']}")
    assert lookup_res.status_code == 200
    assert latest["reference_no"].encode() in lookup_res.data
    assert b"Audit Trail & Lifecycle Transitions" in lookup_res.data
