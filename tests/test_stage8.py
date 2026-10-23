import pytest
from datetime import datetime, timedelta
from app import create_app
from models.db import query_db, execute_db
from services.incident_service import submit_complaint
from services.workflow_service import assign_worker, update_status
from services.reporting_service import (
    get_report_metrics, get_overdue_tickets, get_repeated_fault_poles,
    get_incident_recommendations, export_complaints_csv, compute_nearest_neighbour_route
)
from services.seed_data import seed_database

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    seed_database(force=True)
    with app.test_client() as client:
        yield client

def test_reporting_metrics_and_csv_export(client):
    # Ensure fresh baseline
    execute_db("DELETE FROM repair_notes")
    execute_db("DELETE FROM status_history")
    execute_db("DELETE FROM complaints")

    # 1. Create and resolve a complaint to test resolution velocity
    res1 = submit_complaint("SL-203", "Light not working", "Bulb burnt out")
    cid = res1["complaint_id"]
    admin = query_db("SELECT * FROM users WHERE username = 'admin'", one=True)
    worker = query_db("SELECT * FROM users WHERE role = 'worker'", one=True)
    assign_worker(cid, worker["id"], actor_user=admin)
    
    # Backdate reported_at by 4 hours to verify average resolution calculation
    four_hours_ago = (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
    execute_db("UPDATE complaints SET reported_at = ? WHERE id = ?", (four_hours_ago, cid))
    
    update_status(cid, "Resolved", actor_user=admin, notes="Fixed")

    metrics = get_report_metrics()
    assert metrics["resolved_count"] == 1
    assert metrics["avg_resolution_hours"] >= 3.9

    # 2. Test CSV export
    csv_text = export_complaints_csv()
    assert "Reference No" in csv_text
    assert "Pole Code" in csv_text
    assert "Demonstration data" in csv_text
    assert res1["reference_no"] in csv_text

    # 3. Test HTTP CSV endpoint
    res_http = client.get("/dashboard/reports/export-csv")
    assert res_http.status_code == 200
    assert "text/csv" in res_http.headers["Content-Type"]
    assert b"Reference No" in res_http.data

def test_repeated_faults_and_overdue_detection():
    # 1. Simulate 3 separate complaints on pole SL-201 over recent days
    for i in range(3):
        # We vary category or mark resolved so each is an independent historical failure
        c = submit_complaint("SL-201", f"Flickering / dim {i}", f"Occurrence #{i}")
        # Resolve earlier ones
        execute_db("UPDATE complaints SET status = 'Resolved', is_duplicate = 0 WHERE id = ?", (c["complaint_id"],))

    repeated = get_repeated_fault_poles(days=30, threshold=3)
    assert len(repeated) >= 1
    assert any(p["pole_code"] == "SL-201" for p in repeated)

    # 2. Simulate an overdue complaint (>48 hours old)
    c_overdue = submit_complaint("SL-301", "Light not working", "Old unassigned issue")
    old_time = (datetime.now() - timedelta(hours=55)).strftime("%Y-%m-%d %H:%M:%S")
    execute_db("UPDATE complaints SET reported_at = ? WHERE id = ?", (old_time, c_overdue["complaint_id"]))

    overdue = get_overdue_tickets(threshold_hours=48)
    assert len(overdue) >= 1
    assert any(o["pole_code"] == "SL-301" for o in overdue)

    # 3. Recommendations engine generates insights
    recs = get_incident_recommendations()
    assert len(recs) >= 1
    rec_types = {r["type"] for r in recs}
    assert "RECURRENT_FAULT" in rec_types or "SLA_BREACH" in rec_types

def test_nearest_neighbour_route_computation(client):
    # Ensure active complaints exist on at least 3 distinct poles
    submit_complaint("SL-201", "Light not working", "Stop A")
    submit_complaint("SL-202", "Flickering / dim", "Stop B")
    submit_complaint("SL-301", "Light off during night hours", "Stop C")

    route_res = compute_nearest_neighbour_route(start_coords=(12.9716, 77.5946))
    assert route_res["stops_count"] >= 3
    assert route_res["total_distance_km"] > 0
    assert len(route_res["route"]) == route_res["stops_count"]
    assert "https://www.google.com/maps/dir/" in route_res["google_maps_multi_url"]

    # Test Web endpoint
    web_res = client.get("/dashboard/route-optimizer")
    assert web_res.status_code == 200
    assert b"Multi-Stop Field Dispatch Route Planner" in web_res.data
    assert b"Nearest-Neighbour Optimization Model" in web_res.data
