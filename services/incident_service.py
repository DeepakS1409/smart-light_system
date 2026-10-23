import os
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
import qrcode
from werkzeug.utils import secure_filename
from config import Config
from models.db import query_db, execute_db

def generate_reference_number():
    date_str = datetime.now().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"REF-{date_str}-{suffix}"

def generate_pole_qr(pole_code, base_url=None):
    """Generates and saves a QR code for a given pole code pointing to the complaint URL."""
    base_url = base_url or Config.APP_BASE_URL
    report_url = f"{base_url.rstrip('/')}/complaint/report/{pole_code}"

    qr_dir = Path(Config.QR_FOLDER)
    qr_dir.mkdir(parents=True, exist_ok=True)
    file_path = qr_dir / f"{pole_code}.png"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(report_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(file_path))

    # Update relative path in database
    rel_path = f"qr_codes/{pole_code}.png"
    execute_db("UPDATE poles SET qr_code_path = ? WHERE pole_code = ?", (rel_path, pole_code))
    return rel_path

def get_recent_fault_count(pole_id, days=None):
    """Counts non-duplicate complaints on this pole in the past N days."""
    days = days or Config.REPEATED_FAULT_DAYS
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    res = query_db("""
        SELECT COUNT(*) as cnt FROM complaints
        WHERE pole_id = ? AND reported_at >= ? AND is_duplicate = 0
    """, (pole_id, cutoff), one=True)
    return res["cnt"] if res else 0

def evaluate_priority(pole, category):
    """
    Evaluates incident priority with plain-language explanation based on configurable rules:
    - HIGH: Electrical hazard / exposed wire / pole damage, OR pole marked as high-risk location.
    - MEDIUM: 'Light not working' at normal location.
    - LOW: 'Flickering / dim' or other minor cosmetic/timing issues.
    - Repeated fault rule: >= 3 prior faults in 30 days escalates priority by one level.
    """
    reasons = []
    base_priority = "LOW"

    # Category matching
    if any(h.lower() in category.lower() for h in Config.PRIORITY_HIGH_CATEGORIES):
        base_priority = "HIGH"
        reasons.append(f"Category '{category}' involves immediate electrical hazard or physical damage.")
    elif any(m.lower() in category.lower() for m in Config.PRIORITY_MEDIUM_CATEGORIES):
        base_priority = "MEDIUM"
        reasons.append(f"Category '{category}' impairs road illumination at night.")
    else:
        base_priority = "LOW"
        reasons.append(f"Category '{category}' is a partial or cosmetic defect.")

    # High-risk location escalation
    if pole.get("is_high_risk"):
        hr_reason = pole.get("high_risk_reason") or "Critical roadway / high traffic zone"
        reasons.append(f"Pole {pole['pole_code']} is registered in a designated high-risk area ({hr_reason}).")
        if base_priority != "HIGH":
            base_priority = "HIGH"
            reasons.append("Escalated to HIGH due to high-risk location classification.")

    # Repeated fault history escalation
    recent_faults = get_recent_fault_count(pole["id"])
    if recent_faults >= Config.REPEATED_FAULT_COUNT_THRESHOLD:
        reasons.append(f"Frequent breakdown pattern: {recent_faults} tickets logged on this pole in past {Config.REPEATED_FAULT_DAYS} days.")
        if base_priority == "LOW":
            base_priority = "MEDIUM"
            reasons.append("Elevated from LOW to MEDIUM due to recurrent failure history.")
        elif base_priority == "MEDIUM":
            base_priority = "HIGH"
            reasons.append("Elevated from MEDIUM to HIGH due to recurrent failure history.")

    explanation = " ".join(reasons)
    return base_priority, explanation

def find_active_duplicate(pole_id, category):
    """
    Rule-based duplicate check:
    Same pole + same category + active ticket in ('Reported', 'Assigned', 'In Progress').
    Never merges different poles even if in same zone.
    """
    active_statuses = ("Reported", "Assigned", "In Progress")
    placeholders = ",".join("?" for _ in active_statuses)
    query = f"""
        SELECT * FROM complaints
        WHERE pole_id = ? AND category = ? AND status IN ({placeholders}) AND is_duplicate = 0
        ORDER BY id ASC LIMIT 1
    """
    return query_db(query, (pole_id, category, *active_statuses), one=True)

def submit_complaint(pole_code, category, description, photo_file=None):
    """Records a public complaint, processes duplicate detection, and assigns priority."""
    pole = query_db("SELECT * FROM poles WHERE pole_code = ?", (pole_code,), one=True)
    if not pole:
        raise ValueError(f"Unknown pole identifier: '{pole_code}'")

    # Photo validation and saving
    photo_rel_path = None
    if photo_file and photo_file.filename != "":
        filename = secure_filename(photo_file.filename)
        ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        if ext not in Config.ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid photo format '{ext}'. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}")
        
        # Unique safe filename
        safe_name = f"pole_{pole_code}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        upload_dir = Path(Config.UPLOAD_FOLDER)
        upload_dir.mkdir(parents=True, exist_ok=True)
        photo_path = upload_dir / safe_name
        photo_file.save(str(photo_path))
        photo_rel_path = f"uploads/{safe_name}"

    # Calculate priority
    priority, reason = evaluate_priority(pole, category)

    # Check for active duplicate on this pole
    existing = find_active_duplicate(pole["id"], category)
    is_duplicate = 1 if existing else 0
    duplicate_of_id = existing["id"] if existing else None

    ref_no = generate_reference_number()

    # Save complaint
    res = execute_db("""
        INSERT INTO complaints (
            reference_no, pole_id, category, description, photo_path,
            priority, priority_reason, status, is_duplicate, duplicate_of_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Reported', ?, ?)
    """, (ref_no, pole["id"], category, description, photo_rel_path, priority, reason, is_duplicate, duplicate_of_id))

    complaint_id = res["lastrowid"]

    # Record initial transition in status history
    history_note = (
        f"Public report submitted. Linked as duplicate to active ticket {existing['reference_no']}."
        if existing else "Public report recorded from citizen QR portal."
    )
    execute_db("""
        INSERT INTO status_history (complaint_id, from_status, to_status, changed_by_user_id, notes)
        VALUES (?, NULL, 'Reported', NULL, ?)
    """, (complaint_id, history_note))

    return {
        "complaint_id": complaint_id,
        "reference_no": ref_no,
        "pole": pole,
        "category": category,
        "priority": priority,
        "priority_reason": reason,
        "is_duplicate": bool(is_duplicate),
        "primary_ticket": existing
    }
