import secrets
from functools import wraps
from flask import session, request, redirect, url_for, flash, abort, g
from werkzeug.security import check_password_hash
from models.db import query_db

def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(16)
    return session["_csrf_token"]

def validate_csrf():
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        expected = session.get("_csrf_token")
        if not expected or not token or not secrets.compare_digest(token, expected):
            abort(400, description="Invalid or missing CSRF token.")

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = query_db("SELECT id, username, role, full_name, phone FROM users WHERE id = ?", (user_id,), one=True)
    return user

def login_user(user):
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    session["full_name"] = user["full_name"]
    # Generate fresh CSRF token upon login
    session["_csrf_token"] = secrets.token_hex(16)

def logout_user():
    session.clear()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in first.", "warning")
                return redirect(url_for("auth.login", next=request.url))
            role = session.get("role")
            if role not in allowed_roles:
                flash("Access denied: You do not have permission for this resource.", "danger")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def authenticate(username, password):
    user = query_db("SELECT * FROM users WHERE username = ?", (username.strip(),), one=True)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None
