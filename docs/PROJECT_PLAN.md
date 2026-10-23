# Project Plan: Hybrid Smart Street Light System

## 1. Project Overview
A beginner-friendly, hackathon-ready hybrid street light fault monitoring and complaint management system.
- **Group (Feeder) Level**: 1 simulated IoT monitoring box per zone/feeder detects electrical supply abnormalities (voltage/current/blackouts).
- **Pole Level**: Unique QR code per light pole allowing citizens to report individual defects (e.g., bulb failure, physical damage) with exact geolocation.
- **Central Management**: Admin dashboard, role-based workflows, Leaflet maps, Google Maps navigation for technicians, automated duplicate detection, and nearest-neighbour route planning.

---

## 2. Feature Checklist & Implementation Stages

- [x] **Stage 1: Documentation & Blueprinting** (Plan, Architecture, Progress Tracker, Known Limitations)
- [ ] **Stage 2: Foundation & Core Setup** (Flask, SQLite DB abstraction, Config, Auth & Roles, CSRF, Seed Data with >=10 poles including SL-203)
- [ ] **Stage 3: Public Complaint & QR Management** (QR generation, Complaint submission, Duplicate detection, Reference lookup)
- [ ] **Stage 4: IoT Monitoring-Box Simulator** (Zone telemetry, Threshold evaluation, Group alert generation, Evidence store)
- [ ] **Stage 5: Worker Interface & Lifecycle Tracking** (Assignment, Status progression, Technician portal, Google Maps links, Notes)
- [ ] **Stage 6: Core Checkpoint & Official Test Suite** (`tests/run_official_tests.py` running TEST-01 and TEST-02, `docs/TEST_RESULTS.md`, `README.md`)
- [ ] **Stage 7: Admin Dashboard & Spatial Visualization** (Stats counters, Leaflet map with distinct markers, Filterable data table)
- [ ] **Stage 8: Analytics, Route Planning & Export** (CSV export, Overdue/repeated fault alerts, Nearest-neighbour dispatch routing)
- [ ] **Stage 9: Verification, Polish & Demo Presentation** (End-to-end audit, Demo script for hackathon presentation)

---

## 3. Official Test Matrix
- **TEST-01: Feeder-Level Power Failure**
  - *Trigger*: Zone A, 0V, 0A.
  - *Expectation*: High-priority group alert; logged sensor evidence; no individual bulb blamed.
- **TEST-02: Individual Complaint & Duplicate Lifecycle**
  - *Trigger*: Pole SL-203 issue reported, followed by duplicate report while active.
  - *Expectation*: Linked duplicate, intact primary ticket, technician assignment, status progression to Resolved with navigation.
