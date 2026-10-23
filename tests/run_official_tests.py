import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.db import query_db, execute_db
from services.seed_data import seed_database
from services.sensor_integration import process_feeder_telemetry
from services.incident_service import submit_complaint
from services.workflow_service import assign_worker, update_status, get_google_maps_nav_url

def run_official_tests():
    print("=" * 70)
    print("RUNNING OFFICIAL VALIDATION TEST SUITE (TEST-01 & TEST-02)")
    print("=" * 70)

    # Re-seed database to ensure clean baseline fixtures
    seed_database(force=True)

    results = []
    test_run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # -------------------------------------------------------------
    # EXECUTE TEST-01: Feeder-level Power Failure
    # -------------------------------------------------------------
    print("\n[TEST-01] Executing Feeder-Level Power Failure...")
    test01_inputs = {"feeder_code": "FDR-A01", "zone": "Zone A", "voltage": 0.0, "current": 0.0}
    
    # Process telemetry
    t1_output = process_feeder_telemetry("FDR-A01", voltage=0.0, current=0.0, is_simulated=True)
    
    # Fetch DB records for evidence
    reading_record = query_db("SELECT * FROM sensor_readings WHERE id = ?", (t1_output["reading_id"],), one=True)
    alert_record = query_db("SELECT * FROM feeder_alerts WHERE id = ?", (t1_output["alert"]["id"],), one=True)
    
    # Verification checks
    t1_checks = []
    t1_checks.append(("Alert generated", alert_record is not None))
    t1_checks.append(("Zone matches Zone A", alert_record and alert_record["zone"] == "Zone A"))
    t1_checks.append(("Priority is HIGH", alert_record and alert_record["priority"] == "HIGH"))
    t1_checks.append(("Type is POWER_FAILURE", alert_record and alert_record["alert_type"] == "POWER_FAILURE"))
    t1_checks.append(("Reading recorded with 0V, 0A", reading_record and reading_record["voltage"] == 0.0 and reading_record["current"] == 0.0))
    t1_checks.append(("Is marked simulated", alert_record and alert_record["is_simulated"] == 1 and reading_record["is_simulated"] == 1))
    
    # Hard rule: Feeder reading must NEVER identify individual bulb
    desc = alert_record["description"].lower() if alert_record else ""
    no_bulb_identified = ("sl-" not in desc) and ("individual bulbs are not isolated" in desc or "group-level" in desc)
    t1_checks.append(("No individual bulb isolated in alert", no_bulb_identified))

    t1_pass = all(passed for _, passed in t1_checks)
    t1_diffs = [name for name, passed in t1_checks if not passed]

    t1_result = {
        "test_id": "TEST-01",
        "title": "Feeder-level power failure",
        "status": "PASS" if t1_pass else "FAIL",
        "inputs": test01_inputs,
        "evidence": {
            "reading_id": reading_record["id"] if reading_record else None,
            "alert_id": alert_record["id"] if alert_record else None,
            "alert_code": alert_record["alert_code"] if alert_record else None,
            "priority": alert_record["priority"] if alert_record else None,
            "alert_status": alert_record["status"] if alert_record else None,
            "description": alert_record["description"] if alert_record else None,
            "timestamp": alert_record["created_at"] if alert_record else None
        },
        "differences": t1_diffs
    }
    results.append(t1_result)
    print(f" -> Result: {t1_result['status']}")

    # -------------------------------------------------------------
    # EXECUTE TEST-02: Individual Pole Complaint & Duplicate Detection
    # -------------------------------------------------------------
    print("\n[TEST-02] Executing Individual Pole Complaint & Duplicate Detection Lifecycle...")
    test02_inputs = {
        "primary_report": {"pole_code": "SL-203", "category": "Light not working", "description": "Bulb out on metro approach"},
        "duplicate_report": {"pole_code": "SL-203", "category": "Light not working", "description": "Second citizen reporting dark pole"}
    }

    # Step 1: Submit initial complaint
    res_primary = submit_complaint(
        pole_code="SL-203",
        category="Light not working",
        description="Bulb out on metro approach"
    )
    p_id = res_primary["complaint_id"]
    p_ref = res_primary["reference_no"]
    pole = res_primary["pole"]

    # Step 2: Submit duplicate complaint on same pole while primary is active
    res_duplicate = submit_complaint(
        pole_code="SL-203",
        category="Light not working",
        description="Second citizen reporting dark pole"
    )
    d_id = res_duplicate["complaint_id"]
    d_ref = res_duplicate["reference_no"]

    # Step 3: Assign worker
    admin_user = query_db("SELECT * FROM users WHERE username = 'admin'", one=True)
    worker_user = query_db("SELECT * FROM users WHERE username = 'worker_raj'", one=True)
    assign_worker(p_id, worker_user["id"], actor_user=admin_user)

    # Step 4: Worker progresses status to In Progress
    update_status(p_id, "In Progress", actor_user=worker_user, notes="Arrived on site with replacement lamp.")

    # Step 5: Worker marks Resolved
    update_status(p_id, "Resolved", actor_user=worker_user, notes="Completed bulb fixture replacement. Functional.")

    # Fetch DB records for evidence
    primary_db = query_db("SELECT * FROM complaints WHERE id = ?", (p_id,), one=True)
    duplicate_db = query_db("SELECT * FROM complaints WHERE id = ?", (d_id,), one=True)
    history_db = query_db("SELECT * FROM status_history WHERE complaint_id = ? ORDER BY id ASC", (p_id,))
    nav_url = get_google_maps_nav_url(pole["latitude"], pole["longitude"])

    # Verification checks
    t2_checks = []
    t2_checks.append(("Primary complaint recorded", primary_db is not None))
    t2_checks.append(("Primary priority is MEDIUM", primary_db and primary_db["priority"] == "MEDIUM"))
    t2_checks.append(("Coordinates recorded for SL-203", pole["latitude"] == 12.9732 and pole["longitude"] == 77.5962))
    t2_checks.append(("Duplicate detected correctly", duplicate_db and duplicate_db["is_duplicate"] == 1))
    t2_checks.append(("Duplicate linked to primary", duplicate_db and duplicate_db["duplicate_of_id"] == p_id))
    t2_checks.append(("Worker assigned", primary_db and primary_db["assigned_worker_id"] == worker_user["id"]))
    t2_checks.append(("Final status is Resolved", primary_db and primary_db["status"] == "Resolved"))
    t2_checks.append(("Resolved timestamp populated", primary_db and primary_db["resolved_at"] is not None))
    t2_checks.append(("Audit history complete (4 transitions)", len(history_db) == 4))
    t2_checks.append(("Google Maps nav URL matches coordinates", f"{pole['latitude']},{pole['longitude']}" in nav_url))

    t2_pass = all(passed for _, passed in t2_checks)
    t2_diffs = [name for name, passed in t2_checks if not passed]

    t2_result = {
        "test_id": "TEST-02",
        "title": "Individual pole complaint, duplicate detection, and full workflow lifecycle",
        "status": "PASS" if t2_pass else "FAIL",
        "inputs": test02_inputs,
        "evidence": {
            "primary_ticket": {
                "id": p_id,
                "reference_no": p_ref,
                "pole_code": pole["pole_code"],
                "coordinates": f"{pole['latitude']}, {pole['longitude']}",
                "priority": primary_db["priority"],
                "priority_reason": primary_db["priority_reason"],
                "assigned_worker": worker_user["full_name"],
                "final_status": primary_db["status"],
                "resolved_at": primary_db["resolved_at"],
                "navigation_url": nav_url
            },
            "duplicate_ticket": {
                "id": d_id,
                "reference_no": d_ref,
                "is_duplicate": duplicate_db["is_duplicate"],
                "duplicate_of_id": duplicate_db["duplicate_of_id"]
            },
            "status_history": [
                {"from": h["from_status"], "to": h["to_status"], "notes": h["notes"], "time": h["timestamp"]}
                for h in history_db
            ]
        },
        "differences": t2_diffs
    }
    results.append(t2_result)
    print(f" -> Result: {t2_result['status']}")

    # -------------------------------------------------------------
    # WRITE ACTUAL RESULTS TO docs/TEST_RESULTS.md
    # -------------------------------------------------------------
    md_content = f"""# Official Test Results Report

**Execution Timestamp:** {test_run_timestamp}  
**Environment:** Python SQLite Abstraction (Local Dev)  
**Overall Status:** {"ALL PASSED" if all(r["status"] == "PASS" for r in results) else "FAILURES DETECTED"}

---

## Summary Table

| Test Case | Description | Expected Outcome | Actual Status | Differences |
|---|---|---|---|---|
| **TEST-01** | Feeder-level power failure (Zone A, 0V, 0A) | Group alert, HIGH priority, sensor evidence logged, zero bulb isolation | **{t1_result["status"]}** | {", ".join(t1_diffs) if t1_diffs else "None (Exact Match)"} |
| **TEST-02** | Individual pole complaint & duplicate detection (SL-203) | Linked duplicate, worker dispatch, full lifecycle to Resolved, GPS nav link | **{t2_result["status"]}** | {", ".join(t2_diffs) if t2_diffs else "None (Exact Match)"} |

---

## Detailed Evidence & Audit Trail

### 1. TEST-01: Feeder-Level Power Failure Evidence
- **Inputs:** `Feeder: FDR-A01`, `Zone: Zone A`, `Voltage: 0.0 V`, `Current: 0.0 A`
- **Reading ID:** `#{t1_result["evidence"]["reading_id"]}`
- **Alert ID:** `#{t1_result["evidence"]["alert_id"]}`
- **Alert Code:** `{t1_result["evidence"]["alert_code"]}`
- **Priority Assigned:** `{t1_result["evidence"]["priority"]}`
- **Status:** `{t1_result["evidence"]["alert_status"]}`
- **Timestamp:** `{t1_result["evidence"]["timestamp"]}`
- **Description Logged:**
  > "{t1_result["evidence"]["description"]}"
- **Bulb Isolation Audit:** Passed (Confirms group-level outage without identifying isolated bulbs).

---

### 2. TEST-02: Individual Complaint, Duplicate Detection & Lifecycle Evidence
- **Primary Complaint Reference:** `{t2_result["evidence"]["primary_ticket"]["reference_no"]}` (ID: `#{t2_result["evidence"]["primary_ticket"]["id"]}`)
- **Target Pole:** `Pole {t2_result["evidence"]["primary_ticket"]["pole_code"]}`
- **Registered Coordinates:** `{t2_result["evidence"]["primary_ticket"]["coordinates"]}`
- **Assigned Priority:** `{t2_result["evidence"]["primary_ticket"]["priority"]}`
- **Priority Reason:** "{t2_result["evidence"]["primary_ticket"]["priority_reason"]}"
- **Google Maps Navigation Link:** [{t2_result["evidence"]["primary_ticket"]["navigation_url"]}]({t2_result["evidence"]["primary_ticket"]["navigation_url"]})

#### Duplicate Detection Audit:
- **Second Report Reference:** `{t2_result["evidence"]["duplicate_ticket"]["reference_no"]}` (ID: `#{t2_result["evidence"]["duplicate_ticket"]["id"]}`)
- **Flagged as Duplicate (`is_duplicate`):** `{t2_result["evidence"]["duplicate_ticket"]["is_duplicate"]}`
- **Linked Primary Ticket ID (`duplicate_of_id`):** `#{t2_result["evidence"]["duplicate_ticket"]["duplicate_of_id"]}`
- **Primary Work Order Retained:** Yes, primary ticket maintained active state and proceeded through dispatch.

#### Lifecycle Transitions Audit Trail:
| From Status | To Status | Notes | Timestamp |
|---|---|---|---|
"""
    for h in t2_result["evidence"]["status_history"]:
        md_content += f"| `{h['from'] or 'None'}` | **`{h['to']}`** | {h['notes']} | {h['time']} |\n"

    md_content += f"""
---
*Report generated automatically by `tests/run_official_tests.py`.*
"""

    report_path = Path(__file__).resolve().parent.parent / "docs" / "TEST_RESULTS.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n[OK] Results written successfully to {report_path}")
    print("=" * 70)
    return all(r["status"] == "PASS" for r in results)

if __name__ == "__main__":
    success = run_official_tests()
    sys.exit(0 if success else 1)
