import sqlite3
import os
from pathlib import Path
from config import Config

def get_db_path():
    db_path = Config.DATABASE_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return str(db_path)

def get_db_connection():
    conn = sqlite3.connect(get_db_path(), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def query_db(query, args=(), one=False):
    """Convenience helper to query database returning dictionaries."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return (dict(rv[0]) if rv else None) if one else [dict(r) for r in rv]
    finally:
        conn.close()

def execute_db(query, args=(), commit=True):
    """Convenience helper to execute insert/update/delete returning lastrowid."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        if commit:
            conn.commit()
        last_id = cur.lastrowid
        row_count = cur.rowcount
        cur.close()
        return {"lastrowid": last_id, "rowcount": row_count}
    finally:
        conn.close()

def init_db(force_recreate=False):
    """Initializes the database schema."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if force_recreate:
            cur.executescript("""
                DROP TABLE IF EXISTS repair_notes;
                DROP TABLE IF EXISTS status_history;
                DROP TABLE IF EXISTS complaints;
                DROP TABLE IF EXISTS feeder_alerts;
                DROP TABLE IF EXISTS sensor_readings;
                DROP TABLE IF EXISTS poles;
                DROP TABLE IF EXISTS feeders;
                DROP TABLE IF EXISTS users;
            """)

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'supervisor', 'worker')),
                full_name TEXT NOT NULL,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feeders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feeder_code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                zone TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                nominal_voltage REAL DEFAULT 230.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS poles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pole_code TEXT UNIQUE NOT NULL,
                zone TEXT NOT NULL,
                feeder_id INTEGER,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                landmark TEXT NOT NULL,
                is_high_risk INTEGER DEFAULT 0,
                high_risk_reason TEXT,
                qr_code_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feeder_id) REFERENCES feeders(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feeder_id INTEGER NOT NULL,
                voltage REAL NOT NULL,
                current REAL NOT NULL,
                supply_status TEXT NOT NULL,
                alert_created INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_simulated INTEGER DEFAULT 1,
                FOREIGN KEY (feeder_id) REFERENCES feeders(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS feeder_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_code TEXT UNIQUE NOT NULL,
                feeder_id INTEGER NOT NULL,
                zone TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'HIGH',
                description TEXT NOT NULL,
                voltage REAL NOT NULL,
                current REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Acknowledged', 'Resolved')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                is_simulated INTEGER DEFAULT 1,
                FOREIGN KEY (feeder_id) REFERENCES feeders(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference_no TEXT UNIQUE NOT NULL,
                pole_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                photo_path TEXT,
                priority TEXT NOT NULL CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH')),
                priority_reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Reported' CHECK(status IN ('Reported', 'Assigned', 'In Progress', 'Resolved')),
                assigned_worker_id INTEGER,
                is_duplicate INTEGER DEFAULT 0,
                duplicate_of_id INTEGER,
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (pole_id) REFERENCES poles(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_worker_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (duplicate_of_id) REFERENCES complaints(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                changed_by_user_id INTEGER,
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
                FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS repair_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                worker_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                photo_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
                FOREIGN KEY (worker_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
    finally:
        conn.close()
