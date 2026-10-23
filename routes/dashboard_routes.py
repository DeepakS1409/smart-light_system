from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from models.db import query_db, execute_db
from services.auth import roles_required, get_current_user, login_required
from services.workflow_service import assign_worker, update_status, get_google_maps_nav_url
from config import Config

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/")
def view():
    user = get_current_user()

    # 1. Summary Statistics Counters
    total_poles = query_db("SELECT COUNT(*) as cnt FROM poles", one=True)["cnt"]
    active_complaints = query_db("""
        SELECT COUNT(*) as cnt FROM complaints
        WHERE status IN ('Reported', 'Assigned', 'In Progress') AND is_duplicate = 0
    """, one=True)["cnt"]
    
    high_priority_complaints = query_db("""
        SELECT COUNT(*) as cnt FROM complaints
        WHERE priority = 'HIGH' AND status != 'Resolved' AND is_duplicate = 0
    """, one=True)["cnt"]
    
    active_feeder_alerts = query_db("""
        SELECT COUNT(*) as cnt FROM feeder_alerts
        WHERE status = 'Active'
    """, one=True)["cnt"]
    
    resolved_count = query_db("""
        SELECT COUNT(*) as cnt FROM complaints
        WHERE status = 'Resolved' AND is_duplicate = 0
    """, one=True)["cnt"]

    # 2. Complaints Table with Join Data
    complaints = query_db("""
        SELECT c.*, p.pole_code, p.zone, p.landmark, p.latitude, p.longitude, p.is_high_risk,
               u.full_name as worker_name,
               parent.reference_no as parent_ref
        FROM complaints c
        JOIN poles p ON c.pole_id = p.id
        LEFT JOIN users u ON c.assigned_worker_id = u.id
        LEFT JOIN complaints parent ON c.duplicate_of_id = parent.id
        ORDER BY 
            CASE c.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
            c.id DESC
    """)

    # Augment complaints with Google Maps navigation link
    for c in complaints:
        c["google_maps_url"] = get_google_maps_nav_url(c["latitude"], c["longitude"])

    # 3. Active Feeder Group Alerts
    feeder_alerts = query_db("""
        SELECT fa.*, f.feeder_code, f.name as feeder_name
        FROM feeder_alerts fa
        JOIN feeders f ON fa.feeder_id = f.id
        ORDER BY fa.status ASC, fa.id DESC
    """)

    # 4. Workers list for assignment dropdowns
    workers = query_db("SELECT id, full_name, phone FROM users WHERE role = 'worker'")

    return render_template(
        "dashboard.html",
        stats={
            "total_poles": total_poles,
            "active_complaints": active_complaints,
            "high_priority": high_priority_complaints + active_feeder_alerts,
            "resolved_count": resolved_count,
            "active_feeder_alerts": active_feeder_alerts
        },
        complaints=complaints,
        feeder_alerts=feeder_alerts,
        workers=workers,
        current_user=user
    )

@dashboard_bp.route("/api/map-data")
def map_data():
    """Returns spatial GeoJSON/JSON for Leaflet: separates feeder substations from light poles."""
    # Feeders
    feeders = query_db("""
        SELECT f.*, 
               fa.id as alert_id, fa.alert_code, fa.alert_type, fa.priority as alert_priority,
               fa.voltage as alert_voltage, fa.current as alert_current, fa.status as alert_status,
               fa.description as alert_desc
        FROM feeders f
        LEFT JOIN feeder_alerts fa ON f.id = fa.feeder_id AND fa.status = 'Active'
    """)

    # Poles with latest active complaints
    poles = query_db("""
        SELECT p.*,
               c.id as complaint_id, c.reference_no, c.category, c.priority, c.status,
               c.is_duplicate, c.reported_at,
               u.full_name as worker_name
        FROM poles p
        LEFT JOIN complaints c ON p.id = c.pole_id AND c.status IN ('Reported', 'Assigned', 'In Progress') AND c.is_duplicate = 0
        LEFT JOIN users u ON c.assigned_worker_id = u.id
    """)

    return jsonify({
        "feeders": [dict(f) for f in feeders],
        "poles": [dict(p) for p in poles]
    })

@dashboard_bp.route("/complaints/<int:complaint_id>/assign", methods=["POST"])
@roles_required("admin", "supervisor")
def assign(complaint_id):
    worker_id = request.form.get("worker_id", type=int)
    if not worker_id:
        flash("Please select a valid worker to assign.", "warning")
        return redirect(url_for("dashboard.view"))

    user = get_current_user()
    try:
        assign_worker(complaint_id, worker_id, actor_user=user)
        flash(f"Ticket #{complaint_id} assigned successfully.", "success")
    except Exception as e:
        flash(f"Assignment failed: {str(e)}", "danger")

    return redirect(url_for("dashboard.view"))

@dashboard_bp.route("/complaints/<int:complaint_id>/priority", methods=["POST"])
@roles_required("admin", "supervisor")
def update_priority(complaint_id):
    new_priority = request.form.get("priority")
    reason = request.form.get("reason", "Manual adjustment by supervisor")
    if new_priority in ["LOW", "MEDIUM", "HIGH"]:
        execute_db("""
            UPDATE complaints
            SET priority = ?, priority_reason = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_priority, reason, complaint_id))
        
        user = get_current_user()
        execute_db("""
            INSERT INTO status_history (complaint_id, from_status, to_status, changed_by_user_id, notes)
            VALUES (?, NULL, ?, ?, ?)
        """, (complaint_id, f"Priority Changed to {new_priority}", user["id"], f"Priority manual override: {reason}"))
        flash(f"Priority for ticket #{complaint_id} updated to {new_priority}.", "info")
    return redirect(url_for("dashboard.view"))

from services.reporting_service import (
    get_report_metrics, get_overdue_tickets, get_repeated_fault_poles,
    get_incident_recommendations, export_complaints_csv, compute_nearest_neighbour_route
)
from flask import Response

@dashboard_bp.route("/reports")
def reports():
    metrics = get_report_metrics()
    overdue = get_overdue_tickets()
    repeated = get_repeated_fault_poles()
    recommendations = get_incident_recommendations()

    return render_template(
        "reports.html",
        metrics=metrics,
        overdue=overdue,
        repeated=repeated,
        recommendations=recommendations,
        config=Config
    )

@dashboard_bp.route("/reports/export-csv")
def export_csv():
    csv_data = export_complaints_csv()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=street_light_complaints_report.csv"}
    )

@dashboard_bp.route("/route-optimizer")
def route_optimizer():
    route_data = compute_nearest_neighbour_route()
    return render_template("route_planner.html", route_data=route_data)
