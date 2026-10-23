from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename
from config import Config
from models.db import query_db, execute_db

VALID_STATUSES = ["Reported", "Assigned", "In Progress", "Resolved"]

def get_google_maps_nav_url(latitude, longitude):
    """Generates direct Google Maps turn-by-turn navigation URL using pole coordinates."""
    return f"https://www.google.com/maps/dir/?api=1&destination={latitude},{longitude}"

def assign_worker(complaint_id, worker_id, actor_user):
    """
    Assigns a technician to a complaint ticket.
    Accessible to 'admin' and 'supervisor' roles.
    Transitions status from 'Reported' to 'Assigned' and logs audit trail.
    """
    if actor_user.get("role") not in ["admin", "supervisor"]:
        raise PermissionError("Only administrators and supervisors can assign technicians.")

    complaint = query_db("SELECT * FROM complaints WHERE id = ?", (complaint_id,), one=True)
    if not complaint:
        raise ValueError(f"Ticket #{complaint_id} not found.")

    worker = query_db("SELECT * FROM users WHERE id = ? AND role = 'worker'", (worker_id,), one=True)
    if not worker:
        raise ValueError(f"Technician with user ID {worker_id} not found.")

    current_status = complaint["status"]
    new_status = "Assigned" if current_status == "Reported" else current_status

    execute_db("""
        UPDATE complaints
        SET assigned_worker_id = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (worker_id, new_status, complaint_id))

    history_note = f"Assigned to field technician {worker['full_name']} ({worker['phone'] or 'No phone'})."
    execute_db("""
        INSERT INTO status_history (complaint_id, from_status, to_status, changed_by_user_id, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (complaint_id, current_status, new_status, actor_user["id"], history_note))

    return True

def update_status(complaint_id, new_status, actor_user, notes=""):
    """
    Transitions the lifecycle status of a complaint.
    Enforces authorization: workers can only update tickets assigned to them;
    admins and supervisors can update any ticket.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Allowed: {', '.join(VALID_STATUSES)}")

    complaint = query_db("SELECT * FROM complaints WHERE id = ?", (complaint_id,), one=True)
    if not complaint:
        raise ValueError(f"Ticket #{complaint_id} not found.")

    # Authorization check
    role = actor_user.get("role")
    if role == "worker" and complaint["assigned_worker_id"] != actor_user["id"]:
        raise PermissionError("Workers can only update tickets explicitly assigned to them.")

    old_status = complaint["status"]
    resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == "Resolved" else None

    if resolved_at:
        execute_db("""
            UPDATE complaints
            SET status = ?, resolved_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, resolved_at, complaint_id))
    else:
        execute_db("""
            UPDATE complaints
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, complaint_id))

    # Audit history entry
    audit_notes = notes.strip() if notes else f"Status transitioned from {old_status} to {new_status}."
    execute_db("""
        INSERT INTO status_history (complaint_id, from_status, to_status, changed_by_user_id, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (complaint_id, old_status, new_status, actor_user["id"], audit_notes))

    return True

def add_repair_note(complaint_id, worker_user, note_text, photo_file=None):
    """Adds a repair work log and optional photo evidence."""
    complaint = query_db("SELECT * FROM complaints WHERE id = ?", (complaint_id,), one=True)
    if not complaint:
        raise ValueError(f"Ticket #{complaint_id} not found.")

    photo_rel_path = None
    if photo_file and photo_file.filename != "":
        filename = secure_filename(photo_file.filename)
        safe_name = f"repair_{complaint_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        upload_dir = Path(Config.UPLOAD_FOLDER)
        upload_dir.mkdir(parents=True, exist_ok=True)
        photo_file.save(str(upload_dir / safe_name))
        photo_rel_path = f"uploads/{safe_name}"

    res = execute_db("""
        INSERT INTO repair_notes (complaint_id, worker_id, note, photo_path)
        VALUES (?, ?, ?, ?)
    """, (complaint_id, worker_user["id"], note_text.strip(), photo_rel_path))

    return res["lastrowid"]

def get_worker_tasks(worker_id=None):
    """Fetches tickets for technician interface with attached pole coordinates and notes."""
    query = """
        SELECT c.*, p.pole_code, p.zone, p.landmark, p.latitude, p.longitude, p.is_high_risk,
               u.full_name as worker_name
        FROM complaints c
        JOIN poles p ON c.pole_id = p.id
        LEFT JOIN users u ON c.assigned_worker_id = u.id
    """
    args = []
    if worker_id is not None:
        query += " WHERE c.assigned_worker_id = ? "
        args.append(worker_id)
    
    query += " ORDER BY CASE c.status WHEN 'In Progress' THEN 1 WHEN 'Assigned' THEN 2 WHEN 'Reported' THEN 3 ELSE 4 END, c.id DESC"
    
    rows = query_db(query, tuple(args))
    # Augment with Google Maps link and notes
    tasks = []
    for r in rows:
        item = dict(r)
        item["google_maps_url"] = get_google_maps_nav_url(item["latitude"], item["longitude"])
        item["notes"] = query_db("""
            SELECT rn.*, u.full_name as author
            FROM repair_notes rn
            JOIN users u ON rn.worker_id = u.id
            WHERE rn.complaint_id = ?
            ORDER BY rn.id ASC
        """, (item["id"],))
        tasks.append(item)
    return tasks
