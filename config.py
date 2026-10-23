import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-dev-secret-key-32-chars")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 5000))
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")

    # Database
    DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/streetlights.db")

    # Uploads & Media
    UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
    QR_FOLDER = BASE_DIR / "static" / "qr_codes"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max photo upload

    # Incident Rules Config
    OVERDUE_HOURS_THRESHOLD = int(os.getenv("OVERDUE_HOURS_THRESHOLD", 48))
    REPEATED_FAULT_DAYS = int(os.getenv("REPEATED_FAULT_DAYS", 30))
    REPEATED_FAULT_COUNT_THRESHOLD = int(os.getenv("REPEATED_FAULT_COUNT_THRESHOLD", 3))

    # Priority Rules Mapping
    PRIORITY_HIGH_CATEGORIES = [
        "Exposed wire / electrical hazard / pole damage",
        "Sparking / physical shock hazard",
        "Fallen pole / broken arm"
    ]
    PRIORITY_MEDIUM_CATEGORIES = [
        "Light not working",
        "Light off during night hours"
    ]
    PRIORITY_LOW_CATEGORIES = [
        "Flickering / dim",
        "Glass dirty / casing loose",
        "Timer desynchronized"
    ]

    # Feeder Monitoring Thresholds (Nominal 230V AC)
    VOLTAGE_MIN_NORMAL = 200.0  # Volts
    VOLTAGE_MAX_NORMAL = 250.0  # Volts
    CURRENT_MIN_NORMAL = 5.0    # Amps (under normal night load)
    CURRENT_MAX_NORMAL = 35.0   # Amps

    # Demo Seed Credentials from Environment
    ADMIN_DEFAULT_PASSWORD = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin@12345")
    SUPERVISOR_DEFAULT_PASSWORD = os.getenv("SUPERVISOR_DEFAULT_PASSWORD", "Super@12345")
    WORKER_DEFAULT_PASSWORD = os.getenv("WORKER_DEFAULT_PASSWORD", "Worker@12345")
