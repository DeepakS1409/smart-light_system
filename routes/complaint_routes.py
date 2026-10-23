from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, current_app
from models.db import query_db
from services.incident_service import submit_complaint, generate_pole_qr
from config import Config
from pathlib import Path

complaint_bp = Blueprint("complaint", __name__, url_prefix="/complaint")

@complaint_bp.route("/citizen", methods=["GET"])
def citizen_portal():
    sample_poles = query_db("SELECT pole_code, landmark, zone FROM poles LIMIT 4")
    return render_template("citizen_portal.html", sample_poles=sample_poles)

@complaint_bp.route("/report/<pole_code>", methods=["GET", "POST"])
def new_complaint(pole_code="SL-203"):
    pole = query_db("SELECT * FROM poles WHERE pole_code = ?", (pole_code,), one=True)
    if not pole:
        flash(f"Pole '{pole_code}' was not found in registered demonstration assets.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        photo = request.files.get("photo")

        if not category:
            flash("Please select a fault category.", "warning")
            return render_template("complaint_form.html", pole=pole)

        try:
            result = submit_complaint(
                pole_code=pole_code,
                category=category,
                description=description,
                photo_file=photo
            )
            return render_template("complaint_success.html", result=result)
        except Exception as e:
            flash(f"Error submitting report: {str(e)}", "danger")
            return render_template("complaint_form.html", pole=pole)

    return render_template("complaint_form.html", pole=pole)

@complaint_bp.route("/lookup", methods=["GET", "POST"])
def lookup():
    ref_no = request.values.get("ref", "").strip()
    ticket = None
    pole = None
    history = []

    if ref_no:
        ticket = query_db("""
            SELECT c.*, p.pole_code, p.zone, p.landmark, p.latitude, p.longitude, p.is_high_risk,
                   u.full_name as worker_name, u.phone as worker_phone
            FROM complaints c
            JOIN poles p ON c.pole_id = p.id
            LEFT JOIN users u ON c.assigned_worker_id = u.id
            WHERE c.reference_no = ?
        """, (ref_no,), one=True)

        if ticket:
            history = query_db("""
                SELECT sh.*, u.full_name as actor_name, u.role as actor_role
                FROM status_history sh
                LEFT JOIN users u ON sh.changed_by_user_id = u.id
                WHERE sh.complaint_id = ?
                ORDER BY sh.id ASC
            """, (ticket["id"],))
        else:
            flash(f"No ticket found matching reference '{ref_no}'. Please verify the code.", "warning")

    return render_template("complaint_lookup.html", ref_no=ref_no, ticket=ticket, history=history)

@complaint_bp.route("/qr/<pole_code>")
def get_qr(pole_code):
    pole = query_db("SELECT * FROM poles WHERE pole_code = ?", (pole_code,), one=True)
    if not pole:
        return "Pole not found", 404

    import io
    import qrcode
    # Dynamically resolve public host URL (e.g. https://your-app.vercel.app or http://127.0.0.1:5000)
    base_url = request.host_url.rstrip("/")
    report_url = f"{base_url}/complaint/report/{pole_code}"

    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(report_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@complaint_bp.route("/qr-directory")
def qr_directory():
    poles = query_db("SELECT * FROM poles ORDER BY pole_code ASC")
    return render_template("qr_directory.html", poles=poles, base_url=request.host_url.rstrip("/"))
