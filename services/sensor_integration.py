import random
import string
from datetime import datetime
from config import Config
from models.db import query_db, execute_db

def generate_alert_code(zone):
    clean_zone = zone.replace(" ", "").upper()
    ts = datetime.now().strftime("%Y%m%d%H%M")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ALT-{clean_zone}-{ts}-{rand}"

def process_feeder_telemetry(feeder_id_or_code, voltage, current, is_simulated=True):
    """
    Ingests and evaluates electrical telemetry from a group-level feeder monitoring box.
    Compatible with both simulated UI injection and direct ESP32 IoT HTTP/MQTT payloads.

    CRITICAL ARCHITECTURAL RULE:
    Feeder-level readings monitor aggregate substation current and voltage.
    They identify group-level grid conditions (e.g. blackout, brownout, overload).
    They NEVER identify or claim to identify individual light poles or bulbs.
    """
    # Resolve feeder
    if isinstance(feeder_id_or_code, int) or (isinstance(feeder_id_or_code, str) and feeder_id_or_code.isdigit()):
        feeder = query_db("SELECT * FROM feeders WHERE id = ?", (int(feeder_id_or_code),), one=True)
    else:
        feeder = query_db("SELECT * FROM feeders WHERE feeder_code = ?", (str(feeder_id_or_code),), one=True)

    if not feeder:
        raise ValueError(f"Feeder monitoring unit '{feeder_id_or_code}' not found.")

    feeder_id = feeder["id"]
    zone = feeder["zone"]
    voltage = float(voltage)
    current = float(current)

    # Threshold evaluation
    alert_type = None
    alert_priority = "HIGH"
    supply_status = "NORMAL"
    description = ""

    if voltage <= 5.0 and current <= 0.5:
        # TEST-01 Condition: Complete Feeder Power Loss
        supply_status = "FAILURE"
        alert_type = "POWER_FAILURE"
        description = (
            f"Demonstration data: Total electrical blackout detected at feeder {feeder['feeder_code']} "
            f"affecting {zone}. Zero supply voltage (0.0 V) and zero circuit current (0.0 A) recorded. "
            f"Group-level outage; individual bulbs are not isolated."
        )
    elif voltage < Config.VOLTAGE_MIN_NORMAL:
        supply_status = "UNDER_VOLTAGE"
        alert_type = "UNDER_VOLTAGE"
        description = (
            f"Demonstration data: Feeder {feeder['feeder_code']} ({zone}) under-voltage condition: "
            f"{voltage:.1f} V (threshold normal min: {Config.VOLTAGE_MIN_NORMAL:.1f} V). Risk of ballast/driver damage."
        )
    elif voltage > Config.VOLTAGE_MAX_NORMAL:
        supply_status = "SURGE"
        alert_type = "SURGE"
        description = (
            f"Demonstration data: Voltage surge detected at {feeder['feeder_code']} ({zone}): "
            f"{voltage:.1f} V (threshold normal max: {Config.VOLTAGE_MAX_NORMAL:.1f} V). High risk of electrical stress."
        )
    elif current > Config.CURRENT_MAX_NORMAL:
        supply_status = "OVERLOAD"
        alert_type = "OVERLOAD"
        description = (
            f"Demonstration data: Feeder circuit overload at {feeder['feeder_code']} ({zone}): "
            f"{current:.1f} A exceeds safety threshold ({Config.CURRENT_MAX_NORMAL:.1f} A)."
        )
    elif voltage >= Config.VOLTAGE_MIN_NORMAL and current <= 0.5:
        supply_status = "OPEN_CIRCUIT"
        alert_type = "OPEN_CIRCUIT"
        description = (
            f"Demonstration data: Feeder {feeder['feeder_code']} ({zone}) displays normal voltage ({voltage:.1f} V) "
            f"but no current flow (0.0 A). Feeder main switch open or group branch disconnected."
        )
    else:
        supply_status = "NORMAL"

    alert_created = 1 if alert_type else 0

    # 1. Log sensor evidence in sensor_readings
    res_sensor = execute_db("""
        INSERT INTO sensor_readings (feeder_id, voltage, current, supply_status, alert_created, is_simulated)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (feeder_id, voltage, current, supply_status, alert_created, 1 if is_simulated else 0))

    reading_id = res_sensor["lastrowid"]
    alert_record = None

    # 2. If abnormal, create group-level alert in feeder_alerts
    if alert_type:
        # Check if an Active alert of this type already exists for this feeder to avoid duplicate spamming
        existing_alert = query_db("""
            SELECT * FROM feeder_alerts
            WHERE feeder_id = ? AND alert_type = ? AND status = 'Active'
            ORDER BY id DESC LIMIT 1
        """, (feeder_id, alert_type), one=True)

        if not existing_alert:
            alert_code = generate_alert_code(zone)
            res_alert = execute_db("""
                INSERT INTO feeder_alerts (
                    alert_code, feeder_id, zone, alert_type, priority,
                    description, voltage, current, status, is_simulated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Active', ?)
            """, (alert_code, feeder_id, zone, alert_type, alert_priority, description, voltage, current, 1 if is_simulated else 0))

            alert_record = query_db("SELECT * FROM feeder_alerts WHERE id = ?", (res_alert["lastrowid"],), one=True)
        else:
            alert_record = existing_alert

    return {
        "reading_id": reading_id,
        "feeder": feeder,
        "voltage": voltage,
        "current": current,
        "supply_status": supply_status,
        "alert_created": bool(alert_created),
        "alert": alert_record,
        "timestamp": datetime.now().isoformat()
    }
