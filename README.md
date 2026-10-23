# Hybrid Smart Street Light Monitoring & Dispatch System

A beginner-friendly, hackathon-ready hybrid IoT and civic fault management system for municipal street lighting.

> **Demonstration Notice:** All feeder telemetry and pole coordinates are synthetic fixtures labeled as **Demonstration data**. No physical power mains or utility switches are controlled.

---

## 1. The Core Problem & Solution
- **The Problem:** Installing individual cellular IoT sensors on every street light pole is financially prohibitive for municipalities ($$$ hardware + monthly SIM fees). As a result, outages are discovered late via random public calls.
- **The Hybrid Solution:**
  1. **One Feeder Monitoring Box per zone** (e.g. Zone A) detects group electrical supply faults (power blackouts, low voltage, surges).
  2. **Unique QR Code per light pole** empowers citizens to report isolated bulb burnouts or physical hazards with instant GPS accuracy.
  3. **Central Dashboard & Worker Mobile Interface** streamlines dispatching with Google Maps GPS navigation links, deduplication, and full audit trails.

---

## 2. Installation & Quick Start

### Prerequisites
- Python 3.10+ installed
- Pip package manager

### Steps
```bash
# 1. Clone or navigate to the project directory
cd street-light-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env configuration (or copy .env.example)
copy .env.example .env

# 4. Start the application
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 3. Running Automated Tests

```bash
# Run the official test runner for TEST-01 and TEST-02
python tests/run_official_tests.py

# Run all unit and integration test suites
python -m pytest tests/ -v
```
Results and evidence logs are automatically exported to [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md).

---

## 4. Hackathon Demo Walkthrough Guide

### Step 1: Citizen QR Fault Report
1. Click **"Public Report (Demo SL-203)"** in the top navigation bar.
2. Select **"Light not working"** and click **"Submit Fault Report"**.
3. Note the generated tracking code (e.g., `REF-20261023-XXXXX`) and priority assigned (Medium).
4. Re-submit the same form for pole `SL-203` to show the **Automated Deduplication Engine** in action.

### Step 2: Feeder IoT Monitoring Simulator (TEST-01)
1. Navigate to **"Feeder IoT Box"** (`/simulator/`).
2. Click the preset button: **"TEST-01: Feeder Blackout (0 V, 0 A)"**.
3. Click **"Transmit Telemetry"**.
4. Observe the immediate **HIGH Priority group alert** generated for Zone A with complete sensor evidence logged. Note that the alert clearly marks a group outage without falsely claiming to isolate an individual bulb.

### Step 3: Field Worker Mobile Interface
1. Sign in as Technician Raj (use the **One-Click Demo Login** button on `/auth/login`).
2. Click **"Worker Portal"** (`/worker/tasks`).
3. Click **"Navigate via Google Maps"** to see exact turn-by-turn routing to the pole's GPS coordinates.
4. Update the ticket status from `Assigned` &rarr; `In Progress` &rarr; `Resolved` and append repair notes.

### Step 4: Citizen Status Tracking
1. Open **"Track Ticket"** (`/complaint/lookup`).
2. Enter the reference number to view the complete timestamped lifecycle audit trail.

---

## 5. Demonstration Credentials
- **Admin:** `admin` / `Admin@12345`
- **Supervisor:** `supervisor` / `Super@12345`
- **Field Technician:** `worker_raj` / `Worker@12345`
*(Clickable demo autofill buttons are provided on the login page for convenience during live demos).*
