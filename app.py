import os
from flask import Flask, render_template, request
from config import Config
from models.db import init_db
from services.seed_data import seed_database
from services.auth import generate_csrf_token, validate_csrf, get_current_user

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload and QR directories exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["QR_FOLDER"], exist_ok=True)
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)

    # Auto-initialize database & seed data on startup if not yet seeded
    seed_database(force=False)

    # CSRF Protection Hook
    @app.before_request
    def apply_csrf_protection():
        # Exempt static assets, API endpoints, and safe HTTP methods
        if request.endpoint == "static" or request.path.startswith("/simulator/api/"):
            return
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return
        validate_csrf()

    # Context processors for templates
    @app.context_processor
    def inject_template_globals():
        return {
            "csrf_token": generate_csrf_token,
            "current_user": get_current_user()
        }

    # Register Blueprints
    from routes.auth_routes import auth_bp
    from routes.complaint_routes import complaint_bp
    from routes.simulator_routes import simulator_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.worker_routes import worker_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(complaint_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(worker_bp)

    @app.route("/")
    def home():
        return render_template("index.html")

    # Friendly, safe error handlers (no sensitive stack traces exposed)
    @app.errorhandler(400)
    def bad_request(error):
        message = getattr(error, "description", "Bad Request")
        return render_template("error.html", code=400, title="Bad Request", message=message), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", code=403, title="Forbidden", message="You do not have permission to view this resource."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, title="Page Not Found", message="The requested page could not be located."), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("error.html", code=500, title="Internal Server Error", message="An unexpected error occurred. The technical team has been alerted."), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.FLASK_DEBUG)
