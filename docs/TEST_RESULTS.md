# Official Test Results Report

**Execution Timestamp:** 2026-10-23 19:25:37  
**Environment:** Python SQLite Abstraction (Local Dev)  
**Overall Status:** ALL PASSED

---

## Summary Table

| Test Case | Description | Expected Outcome | Actual Status | Differences |
|---|---|---|---|---|
| **TEST-01** | Feeder-level power failure (Zone A, 0V, 0A) | Group alert, HIGH priority, sensor evidence logged, zero bulb isolation | **PASS** | None (Exact Match) |
| **TEST-02** | Individual pole complaint & duplicate detection (SL-203) | Linked duplicate, worker dispatch, full lifecycle to Resolved, GPS nav link | **PASS** | None (Exact Match) |

---

## Detailed Evidence & Audit Trail

### 1. TEST-01: Feeder-Level Power Failure Evidence
- **Inputs:** `Feeder: FDR-A01`, `Zone: Zone A`, `Voltage: 0.0 V`, `Current: 0.0 A`
- **Reading ID:** `#1`
- **Alert ID:** `#1`
- **Alert Code:** `ALT-ZONEA-202610231925-G0JQ`
- **Priority Assigned:** `HIGH`
- **Status:** `Active`
- **Timestamp:** `2026-10-23 13:55:37`
- **Description Logged:**
  > "Demonstration data: Total electrical blackout detected at feeder FDR-A01 affecting Zone A. Zero supply voltage (0.0 V) and zero circuit current (0.0 A) recorded. Group-level outage; individual bulbs are not isolated."
- **Bulb Isolation Audit:** Passed (Confirms group-level outage without identifying isolated bulbs).

---

### 2. TEST-02: Individual Complaint, Duplicate Detection & Lifecycle Evidence
- **Primary Complaint Reference:** `REF-20261023-AH7I6` (ID: `#1`)
- **Target Pole:** `Pole SL-203`
- **Registered Coordinates:** `12.9732, 77.5962`
- **Assigned Priority:** `MEDIUM`
- **Priority Reason:** "Category 'Light not working' impairs road illumination at night."
- **Google Maps Navigation Link:** [https://www.google.com/maps/dir/?api=1&destination=12.9732,77.5962](https://www.google.com/maps/dir/?api=1&destination=12.9732,77.5962)

#### Duplicate Detection Audit:
- **Second Report Reference:** `REF-20261023-Q6OJ2` (ID: `#2`)
- **Flagged as Duplicate (`is_duplicate`):** `1`
- **Linked Primary Ticket ID (`duplicate_of_id`):** `#1`
- **Primary Work Order Retained:** Yes, primary ticket maintained active state and proceeded through dispatch.

#### Lifecycle Transitions Audit Trail:
| From Status | To Status | Notes | Timestamp |
|---|---|---|---|
| `None` | **`Reported`** | Public report recorded from citizen QR portal. | 2026-10-23 13:55:37 |
| `Reported` | **`Assigned`** | Assigned to field technician Rajesh Kumar (Field Tech) (+91 98765 10001). | 2026-10-23 13:55:37 |
| `Assigned` | **`In Progress`** | Arrived on site with replacement lamp. | 2026-10-23 13:55:38 |
| `In Progress` | **`Resolved`** | Completed bulb fixture replacement. Functional. | 2026-10-23 13:55:38 |

---
*Report generated automatically by `tests/run_official_tests.py`.*
