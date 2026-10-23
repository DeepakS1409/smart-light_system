# Architecture: Hybrid Smart Street Light System

## 1. System Overview
The system combines low-cost group electrical sensing with distributed citizen reporting to eliminate the cost of per-pole telemetry hardware.

```
                      +---------------------------------------+
                      |           Street Light System         |
                      +---------------------------------------+
                                     |
             +-----------------------+-----------------------+
             |                                               |
  [Group-Level IoT Feeder]                       [Individual Pole Level]
  - 1 Box per Zone/Feeder                        - Unique QR Code per Pole
  - Telemetry: Voltage (V), Current (A)          - Citizen Scan -> Web Form
  - Detects: Outages, Surges, Low Voltage         - Reports: Outages, Hazards, Damage
  - Output: Feeder Group Alert                   - Output: Individual Ticket with Geolocation
             |                                               |
             +-----------------------+-----------------------+
                                     |
                                     v
                        [Flask Application Server]
                        - Rule-based Incident Intelligence
                          * Duplicate Linking (Pole + Category + Active)
                          * Priority Assessment (Hazard/Location/History)
                        - Role-Based Access Control (Admin, Supervisor, Worker)
                        - SQLite Storage Abstraction
                                     |
             +-----------------------+-----------------------+
             |                                               |
             v                                               v
     [Admin Dashboard]                             [Technician Interface]
     - Interactive Leaflet Map                      - Assigned Work Orders
       (Feeder Alerts vs Pole Markers)             - Google Maps GPS Navigation Link
     - Dispatching & Route Optimizer               - Repair Notes & Photo Evidence
     - CSV Reports & Resolution Analytics          - Lifecycle Transition Updates
```

---

## 2. Technology Stack
- **Backend**: Python 3 (Flask), SQLite with custom lightweight database abstraction layer.
- **Frontend**: Responsive HTML5, Vanilla CSS, Bootstrap 5, JavaScript (ES6).
- **Mapping**: Leaflet.js with OpenStreetMap tiles; dynamic Google Maps navigation URLs (`https://www.google.com/maps/dir/?api=1&destination=lat,lng`).
- **QR Engine**: `qrcode` (Python) generating pole-specific complaint URLs.
- **Charts**: Chart.js for fault distribution and resolution metrics.
- **IoT Interface**: `services/sensor_integration.py` for simulated MQTT/HTTP payload handling, ready for ESP32.

---

## 3. Data Schema Concept
- `poles`: `id`, `pole_code` (e.g. SL-203), `zone_id`, `latitude`, `longitude`, `landmark`, `is_high_risk`, `created_at`
- `feeders`: `id`, `feeder_code`, `zone_id`, `normal_voltage_min`, `normal_voltage_max`, `normal_current_min`, `normal_current_max`
- `sensor_readings`: `id`, `feeder_id`, `voltage`, `current`, `status`, `timestamp`, `is_simulated`
- `complaints`: `id`, `reference_no`, `pole_id`, `category`, `description`, `photo_filename`, `priority`, `priority_reason`, `status`, `assigned_to`, `is_duplicate_of`, `created_at`, `updated_at`
- `status_history`: `id`, `complaint_id`, `from_status`, `to_status`, `changed_by`, `notes`, `timestamp`
- `users`: `id`, `username`, `password_hash`, `role` (admin/supervisor/worker), `full_name`, `phone`
