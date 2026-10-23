import pytest
from app import create_app
from models.db import query_db, execute_db
from services.sensor_integration import process_feeder_telemetry
from services.seed_data import seed_database

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    seed_database(force=True)
    with app.test_client() as client:
        yield client

def test_stage4_test01_feeder_power_failure():
    """
    OFFICIAL TEST-01: Feeder-level power failure
    Input: Zone A (feeder FDR-A01), 0 V, 0 A, Power failure.
    Expected: Group-level alert for Zone A; HIGH priority; saved with sensor inputs + timestamp;
              no individual bulb identified.
    """
    # Clear alerts and readings
    execute_db("DELETE FROM feeder_alerts")
    execute_db("DELETE FROM sensor_readings")

    result = process_feeder_telemetry("FDR-A01", voltage=0.0, current=0.0, is_simulated=True)

    # 1. Telemetry evaluation assertions
    assert result["supply_status"] == "FAILURE"
    assert result["alert_created"] is True
    assert result["voltage"] == 0.0
    assert result["current"] == 0.0

    # 2. Check sensor_readings table for evidence
    reading = query_db("SELECT * FROM sensor_readings WHERE id = ?", (result["reading_id"],), one=True)
    assert reading is not None
    assert reading["voltage"] == 0.0
    assert reading["current"] == 0.0
    assert reading["supply_status"] == "FAILURE"
    assert reading["is_simulated"] == 1

    # 3. Check feeder_alerts table for group alert
    alert = result["alert"]
    assert alert is not None
    assert alert["zone"] == "Zone A"
    assert alert["priority"] == "HIGH"
    assert alert["alert_type"] == "POWER_FAILURE"
    assert alert["status"] == "Active"

    # 4. CRITICAL HARD RULE: Verify no individual bulb or pole is identified
    desc = alert["description"].lower()
    assert "pole sl-" not in desc
    assert "individual bulbs are not isolated" in desc or "group-level" in desc
    assert "zone a" in desc

def test_normal_telemetry():
    """Tests normal operating conditions (230 V, 18.0 A) producing no alerts."""
    res = process_feeder_telemetry("FDR-A01", voltage=230.0, current=18.0, is_simulated=True)
    assert res["supply_status"] == "NORMAL"
    assert res["alert_created"] is False
    assert res["alert"] is None

    # Reading is recorded as evidence
    reading = query_db("SELECT * FROM sensor_readings WHERE id = ?", (res["reading_id"],), one=True)
    assert reading["voltage"] == 230.0
    assert reading["current"] == 18.0
    assert reading["supply_status"] == "NORMAL"

def test_api_telemetry_endpoint(client):
    """Tests ESP32 compatible JSON API endpoint."""
    res = client.post("/simulator/api/telemetry", json={
        "feeder_code": "FDR-B01",
        "voltage": 160.0,
        "current": 9.0
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["supply_status"] == "UNDER_VOLTAGE"
    assert data["alert_created"] is True
    assert data["alert"]["zone"] == "Zone B"
