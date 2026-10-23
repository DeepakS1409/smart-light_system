from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from models.db import query_db, execute_db
from services.sensor_integration import process_feeder_telemetry
from config import Config

simulator_bp = Blueprint("simulator", __name__, url_prefix="/simulator")

@simulator_bp.route("/", methods=["GET"])
def view():
    feeders = query_db("SELECT * FROM feeders ORDER BY zone ASC")
    recent_readings = query_db("""
        SELECT sr.*, f.feeder_code, f.name as feeder_name, f.zone
        FROM sensor_readings sr
        JOIN feeders f ON sr.feeder_id = f.id
        ORDER BY sr.id DESC LIMIT 15
    """)
    active_alerts = query_db("""
        SELECT fa.*, f.feeder_code, f.name as feeder_name
        FROM feeder_alerts fa
        JOIN feeders f ON fa.feeder_id = f.id
        WHERE fa.status = 'Active'
        ORDER BY fa.id DESC
    """)
    return render_template(
        "simulator.html",
        feeders=feeders,
        recent_readings=recent_readings,
        active_alerts=active_alerts,
        config=Config
    )

@simulator_bp.route("/inject", methods=["POST"])
def inject():
    feeder_id = request.form.get("feeder_id")
    voltage = request.form.get("voltage")
    current = request.form.get("current")

    if not feeder_id or voltage is None or current is None:
        flash("All telemetry fields (Feeder, Voltage, Current) are required.", "warning")
        return redirect(url_for("simulator.view"))

    try:
        result = process_feeder_telemetry(feeder_id, float(voltage), float(current), is_simulated=True)
        if result["alert_created"]:
            flash(
                f"[SIMULATED GROUP ALERT] {result['alert']['alert_type']} detected for {result['feeder']['zone']} "
                f"({result['voltage']}V, {result['current']}A). High Priority Alert {result['alert']['alert_code']} logged.",
                "danger"
            )
        else:
            flash(
                f"[SIMULATED READING] Normal grid supply recorded for {result['feeder']['zone']} "
                f"({result['voltage']}V, {result['current']}A). No alerts generated.",
                "success"
            )
    except Exception as e:
        flash(f"Error processing telemetry: {str(e)}", "danger")

    return redirect(url_for("simulator.view"))

@simulator_bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    execute_db("""
        UPDATE feeder_alerts
        SET status = 'Resolved', resolved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (alert_id,))
    flash("Feeder group alert marked as Resolved.", "info")
    return redirect(url_for("simulator.view"))

@simulator_bp.route("/api/telemetry", methods=["POST"])
def api_telemetry():
    """
    ESP32 / IoT Hardware Telemetry Ingestion Endpoint.
    Accepts JSON: {"feeder_code": "FDR-A01", "voltage": 228.4, "current": 16.2}
    """
    data = request.get_json(silent=True) or request.form
    feeder_code = data.get("feeder_code") or data.get("feeder_id")
    voltage = data.get("voltage")
    current = data.get("current")

    if not feeder_code or voltage is None or current is None:
        return jsonify({"error": "Missing required fields: feeder_code, voltage, current"}), 400

    try:
        result = process_feeder_telemetry(feeder_code, float(voltage), float(current), is_simulated=True)
        return jsonify({
            "status": "success",
            "reading_id": result["reading_id"],
            "supply_status": result["supply_status"],
            "alert_created": result["alert_created"],
            "alert": dict(result["alert"]) if result["alert"] else None,
            "timestamp": result["timestamp"]
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
