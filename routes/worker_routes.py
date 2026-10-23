from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from services.auth import login_required, get_current_user
from services.workflow_service import get_worker_tasks, update_status, add_repair_note
from models.db import query_db

worker_bp = Blueprint("worker", __name__, url_prefix="/worker")

@worker_bp.route("/tasks")
@login_required
def tasks():
    user = get_current_user()
    if user["role"] == "worker":
        tasks_list = get_worker_tasks(worker_id=user["id"])
    else:
        # Admins and supervisors can view all or filter by worker
        filter_worker_id = request.args.get("worker_id", type=int)
        tasks_list = get_worker_tasks(worker_id=filter_worker_id)

    workers = query_db("SELECT id, full_name, phone FROM users WHERE role = 'worker'")
    return render_template("worker_tasks.html", tasks=tasks_list, workers=workers, user=user)

@worker_bp.route("/tasks/<int:complaint_id>/status", methods=["POST"])
@login_required
def change_status(complaint_id):
    user = get_current_user()
    new_status = request.form.get("status")
    notes = request.form.get("notes", "")

    try:
        update_status(complaint_id, new_status, actor_user=user, notes=notes)
        flash(f"Ticket #{complaint_id} status updated to '{new_status}'.", "success")
    except Exception as e:
        flash(f"Unable to update status: {str(e)}", "danger")

    return redirect(url_for("worker.tasks"))

@worker_bp.route("/tasks/<int:complaint_id>/note", methods=["POST"])
@login_required
def submit_note(complaint_id):
    user = get_current_user()
    note_text = request.form.get("note", "").strip()
    photo = request.files.get("photo")

    if not note_text:
        flash("Please enter repair notes before submitting.", "warning")
        return redirect(url_for("worker.tasks"))

    try:
        add_repair_note(complaint_id, worker_user=user, note_text=note_text, photo_file=photo)
        flash("Repair log entry added successfully.", "success")
    except Exception as e:
        flash(f"Error adding note: {str(e)}", "danger")

    return redirect(url_for("worker.tasks"))
