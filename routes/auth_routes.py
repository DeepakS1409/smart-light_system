from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.auth import authenticate, login_user, logout_user, get_current_user

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        next_url = request.form.get("next") or url_for("home")

        user = authenticate(username, password)
        if user:
            login_user(user)
            flash(f"Welcome back, {user['full_name']} ({user['role'].title()})!", "success")
            if user["role"] == "worker":
                return redirect(url_for("worker.tasks") if "worker.tasks" in request.url_rule.rule else url_for("home"))
            return redirect(next_url)
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html", current_user=get_current_user())

@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    logout_user()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("auth.login"))
