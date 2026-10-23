# Hackathon Live Demo & Presentation Guide

*Designed for a 1st-Year IT Student presenting to Judges and Technical Mentors.*

---

## 1. The 30-Second Elevator Pitch
> *"Judges, smart cities often spend millions trying to install expensive cellular sensors on every single light pole—or they rely on citizens randomly calling hotlines when lights fail.  
> Our project introduces a **Hybrid Architecture**: We install **one $35 IoT monitoring box per zone substation** to instantly detect electrical blackouts, and pair it with **unique QR codes on each pole** for citizens to crowd-report bulb burnouts with exact GPS coordinates.  
> This eliminates 95% of hardware costs while delivering automated deduplication, real-time dispatch, and Google Maps field navigation."*

---

## 2. The 3-Minute Live Demo Script

| Step | Page / Action | What to Click & Show | What to Say to the Judges |
|---|---|---|---|
| **1. The Problem & Architecture** | Home (`/`) | Scroll over the architecture cards & principles banner. | *"Here is our hybrid architecture: 1 Feeder Substation Monitor per zone + Citizen QR reporting."* |
| **2. Citizen QR Scan (Demo SL-203)** | `/complaint/report/SL-203` | Select **"Light not working"**, type *"Burned out bulb"*, and click **"Submit Fault Report"**. | *"When a citizen scans the physical QR on Pole SL-203, the exact GPS coordinates and landmark are pre-filled. They get an instant tracking reference code (e.g. `REF-20261023-XXXXX`)."* |
| **3. Automated Deduplication Engine** | Re-submit same form for `SL-203` with **"Light not working"**. | Show the yellow **"Duplicate Report Linked"** banner! | *"Watch this: If a second citizen scans the same pole for the same defect while active, our rule engine links the report to the existing work order without creating redundant technician dispatches."* |
| **4. Feeder IoT Outage (TEST-01)** | `/simulator/` | Click **"TEST-01: Feeder Blackout (0 V, 0 A)"** &rarr; **"Transmit Telemetry"**. | *"Now let's simulate the group substation. When an entire zone loses power, the box detects 0V and 0A. Notice: It creates a HIGH-priority group alert without falsely claiming to isolate an individual bulb."* |
| **5. Central Ops Map & Dispatch** | `/dashboard/` | Show the Leaflet map: Point out the red Feeder Outage icon vs circular Pole markers. Use the search bar to filter tickets. | *"On the central dashboard, the Leaflet map clearly distinguishes whole-feeder outages from isolated pole defects. Supervisors can reassign technicians or filter tickets live."* |
| **6. Field Technician Navigation & Repair** | `/auth/login` &rarr; `/worker/tasks` | Click **"Technician Raj"** one-click login &rarr; click **"Navigate via Google Maps"** on ticket. Update status to **Resolved**. | *"The lineman opens their task queue on mobile, taps 'Navigate via Google Maps' for direct GPS routing to the pole, and logs the repair notes."* |
| **7. Analytics & Route Optimizer** | `/dashboard/reports` &amp; `/dashboard/route-optimizer` | Show the Chart.js graphs, average resolution hours, and the Nearest-Neighbour multi-stop sequence. | *"Finally, our reports calculate average resolution velocity, recurrent fault warnings, and compute a multi-stop repair route using nearest-neighbour routing."* |

---

## 3. Tough Judge Questions & Winning Answers

### Q1: *"Why didn't you just put an ESP32 on every single pole?"*
> **Answer:** *"Cost and operational feasibility. Equipping 10,000 poles with an ESP32, GSM modem, solar panel, and monthly SIM card costs over $400,000 upfront plus $30,000 every month in data plans. In our hybrid model, 10,000 poles only need about 20 feeder monitoring boxes at the substations ($1,000 total) and durable weather-proof QR stickers ($500). That's a 99% cost reduction!"*

### Q2: *"Can the feeder box tell me which specific bulb is burned out?"*
> **Answer:** *"No, and that is a deliberate engineering truth in our system! Current transformers at the substation measure aggregate load. If 1 bulb out of 50 burns out, the 0.3A drop is within normal grid fluctuation noise. That's why we use citizen QR crowd-reporting for individual bulbs, while reserving the feeder box for complete blackouts, brownouts, and dangerous voltage surges."*

### Q3: *"Did you use Machine Learning or AI for priority and duplicates?"*
> **Answer:** *"No black-box ML was used because municipal safety dispatches require 100% deterministic, explainable rules. Our incident intelligence evaluates electrical hazards, high-risk locations (like hospitals), and 30-day chronic failure history with plain-language explanations. Recommendations are strictly separated from human-approved decisions."*

### Q4: *"How did you test smartphone QR scanning on localhost?"*
> **Answer:** *"By connecting the laptop and phone to the same local Wi-Fi, running the Flask server on `0.0.0.0`, and setting `APP_BASE_URL` in `.env` to the laptop's Wi-Fi LAN IP (e.g. `http://192.168.1.50:5000`). Our QR Directory page has built-in instructions explaining this limit."*
