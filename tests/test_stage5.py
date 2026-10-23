import pytest
from app import create_app
from models.db import query_db, execute_db
from services.incident_service import submit_complaint
from services.workflow_service import assign_worker, update_status, add_repair_note, get_worker_tasks, get_google_maps_nav_url
from services.seed_data import seed_database

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    seed_database(force=True)
    with app.test_client() as client:
        yield client

def test_full_complaint_and_worker_lifecycle():
    """
    Validates end-to-end lifecycle required by TEST-02:
    Reported -> Assigned -> In Progress -> Repair Notes -> Resolved
    with Google Maps navigation links and audit history.
    """
    execute_db("DELETE FROM repair_notes")
    execute_db("DELETE FROM status_history")
    execute_db("DELETE FROM complaints")

    # 1. Citizen reports defect on pole SL-203
    res1 = submit_complaint(
        pole_code="SL-203",
        category="Light not working",
        description="Dark corner near metro entrance"
    )
    complaint_id = res1["complaint_id"]
    ref_no = res1["reference_no"]
    assert res1["priority"] == "MEDIUM"

    c1 = query_db("SELECT * FROM complaints WHERE id = ?", (complaint_id,), one=True)
    assert c1["status"] == "Reported"
    assert c1["assigned_worker_id"] is None

    # 2. Duplicate submission test while active
    res2 = submit_complaint(
        pole_code="SL-203",
        category="Light not working",
        description="Second citizen reporting same blackout"
    )
    assert res2["is_duplicate"] is True
    assert res2["primary_ticket"]["id"] == complaint_id

    # 3. Supervisor assigns ticket to worker_raj
    admin = query_db("SELECT * FROM users WHERE username = 'admin'", one=True)
    worker_raj = query_db("SELECT * FROM users WHERE username = 'worker_raj'", one=True)
    worker_anita = query_db("SELECT * FROM users WHERE username = 'worker_anita'", one=True)

    assign_worker(complaint_id, worker_raj["id"], actor_user=admin)

    c2 = query_db("SELECT * FROM complaints WHERE id = ?", (complaint_id,), one=True)
    assert c2["status"] == "Assigned"
    assert c2["assigned_worker_id"] == worker_raj["id"]

    # Check status history audit entry
    hist = query_db("SELECT * FROM status_history WHERE complaint_id = ? ORDER BY id DESC LIMIT 1", (complaint_id,), one=True)
    assert hist["from_status"] == "Reported"
    assert hist["to_status"] == "Assigned"
    assert hist["changed_by_user_id"] == admin["id"]

    # 4. Verify Google Maps navigation URL uses exact pole coordinates
    pole = query_db("SELECT * FROM poles WHERE pole_code = 'SL-203'", one=True)
    expected_nav_url = f"https://www.google.com/maps/dir/?api=1&destination={pole['latitude']},{pole['longitude']}"
    assert get_google_maps_nav_url(pole["latitude"], pole["longitude"]) == expected_nav_url

    tasks = get_worker_tasks(worker_id=worker_raj["id"])
    assert len(tasks) >= 1
    task = next(t for t in tasks if t["id"] == complaint_id)
    assert task["google_maps_url"] == expected_nav_url

    # 5. Worker starts work: "In Progress"
    update_status(complaint_id, "In Progress", actor_user=worker_raj, notes="Arrived on site; troubleshooting fixture.")
    c3 = query_db("SELECT * FROM complaints WHERE id = ?", (complaint_id,), one=True)
    assert c3["status"] == "In Progress"

    # 6. Unauthorized worker cannot modify another worker's assigned ticket
    with pytest.raises(PermissionError):
        update_status(complaint_id, "Resolved", actor_user=worker_anita, notes="Unauthorized change attempt")

    # 7. Worker adds repair note
    add_repair_note(complaint_id, worker_user=worker_raj, note_text="Replaced 70W LED driver and reset photocell.")
    notes = query_db("SELECT * FROM repair_notes WHERE complaint_id = ?", (complaint_id,))
    assert len(notes) == 1
    assert "LED driver" in notes[0]["note"]

    # 8. Worker resolves ticket: "Resolved"
    update_status(complaint_id, "Resolved", actor_user=worker_raj, notes="Repaired and illumination verified at 100%.")
    c4 = query_db("SELECT * FROM complaints WHERE id = ?", (complaint_id,), one=True)
    assert c4["status"] == "Resolved"
    assert c4["resolved_at"] is not None

    # Full audit history count (Reported, Assigned, In Progress, Resolved)
    all_history = query_db("SELECT * FROM status_history WHERE complaint_id = ? ORDER BY id ASC", (complaint_id,))
    assert len(all_history) == 4
    assert [h["to_status"] for h in all_history] == ["Reported", "Assigned", "In Progress", "Resolved"]
