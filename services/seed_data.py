import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash
from config import Config
from models.db import get_db_connection, init_db, query_db

def seed_database(force=False):
    """Populates the database with required demonstration seed data."""
    init_db(force_recreate=force)
    
    conn = get_db_connection()
    cur = conn.cursor()

    # Check if users already exist
    existing_users = cur.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
    if existing_users > 0 and not force:
        conn.close()
        return False

    # 1. Seed Users (1 Admin, 1 Supervisor, 3 Workers) with hashed passwords from env
    admin_pw_hash = generate_password_hash(Config.ADMIN_DEFAULT_PASSWORD)
    super_pw_hash = generate_password_hash(Config.SUPERVISOR_DEFAULT_PASSWORD)
    worker_pw_hash = generate_password_hash(Config.WORKER_DEFAULT_PASSWORD)

    users = [
        ("admin", admin_pw_hash, "admin", "System Administrator", "+91 98765 00001"),
        ("supervisor", super_pw_hash, "supervisor", "Zone Operations Supervisor", "+91 98765 00002"),
        ("worker_raj", worker_pw_hash, "worker", "Rajesh Kumar (Field Tech)", "+91 98765 10001"),
        ("worker_anita", worker_pw_hash, "worker", "Anita Sharma (Senior Lineman)", "+91 98765 10002"),
        ("worker_vikram", worker_pw_hash, "worker", "Vikram Singh (Electrician)", "+91 98765 10003")
    ]
    cur.executemany("""
        INSERT INTO users (username, password_hash, role, full_name, phone)
        VALUES (?, ?, ?, ?, ?)
    """, users)

    # 2. Seed Feeders (Group-Level Monitoring Units for Zone A, Zone B, Zone C)
    feeders = [
        ("FDR-A01", "Feeder Substation Alpha", "Zone A", 12.9716, 77.5946, 230.0),
        ("FDR-B01", "Feeder Substation Bravo", "Zone B", 12.9780, 77.6010, 230.0),
        ("FDR-C01", "Feeder Substation Charlie", "Zone C", 12.9650, 77.5850, 230.0)
    ]
    cur.executemany("""
        INSERT INTO feeders (feeder_code, name, zone, latitude, longitude, nominal_voltage)
        VALUES (?, ?, ?, ?, ?, ?)
    """, feeders)

    # Fetch feeder IDs
    feeder_map = {row["zone"]: row["id"] for row in cur.execute("SELECT id, zone FROM feeders").fetchall()}

    # 3. Seed >=10 Poles across Zone A, B, C including SL-203
    # Demonstrating normal vs high-risk locations (e.g. hospital crossing / accident zone)
    poles = [
        # Zone A (includes required SL-203)
        ("SL-201", "Zone A", feeder_map["Zone A"], 12.9720, 77.5950, "Demonstration data - Near North Gate", 0, None),
        ("SL-202", "Zone A", feeder_map["Zone A"], 12.9725, 77.5955, "Demonstration data - Central Circle", 0, None),
        ("SL-203", "Zone A", feeder_map["Zone A"], 12.9732, 77.5962, "Demonstration data - Metro Station Entry Road", 0, None),
        ("SL-204", "Zone A", feeder_map["Zone A"], 12.9740, 77.5970, "Demonstration data - General Hospital Emergency Lane", 1, "Hospital Emergency Route"),
        
        # Zone B
        ("SL-301", "Zone B", feeder_map["Zone B"], 12.9785, 77.6015, "Demonstration data - Tech Park Avenue 1", 0, None),
        ("SL-302", "Zone B", feeder_map["Zone B"], 12.9792, 77.6022, "Demonstration data - Market Road Crossing", 1, "High pedestrian traffic junction"),
        ("SL-303", "Zone B", feeder_map["Zone B"], 12.9800, 77.6030, "Demonstration data - East Bus Terminal", 0, None),
        ("SL-304", "Zone B", feeder_map["Zone B"], 12.9810, 77.6040, "Demonstration data - Residential Ring 4", 0, None),
        
        # Zone C
        ("SL-401", "Zone C", feeder_map["Zone C"], 12.9645, 77.5845, "Demonstration data - Old Bridge Approach", 1, "Narrow bridge accident zone"),
        ("SL-402", "Zone C", feeder_map["Zone C"], 12.9638, 77.5838, "Demonstration data - West Park Joggers Path", 0, None),
        ("SL-403", "Zone C", feeder_map["Zone C"], 12.9630, 77.5830, "Demonstration data - Industrial Spur Road", 0, None),
        ("SL-404", "Zone C", feeder_map["Zone C"], 12.9622, 77.5822, "Demonstration data - Freight Rail Crossing", 1, "Railway Level Crossing")
    ]

    cur.executemany("""
        INSERT INTO poles (pole_code, zone, feeder_id, latitude, longitude, landmark, is_high_risk, high_risk_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, poles)

    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    success = seed_database(force=True)
    print("Database initialized and seeded successfully:", success)
