import csv
import io
import math
from datetime import datetime, timedelta
from config import Config
from models.db import query_db

def get_report_metrics():
    """Calculates aggregated metrics for municipal reporting."""
    # 1. By Zone
    by_zone = query_db("""
        SELECT p.zone, COUNT(c.id) as count
        FROM poles p
        LEFT JOIN complaints c ON p.id = c.pole_id AND c.is_duplicate = 0
        GROUP BY p.zone
        ORDER BY count DESC
    """)

    # 2. By Category
    by_category = query_db("""
        SELECT category, COUNT(id) as count
        FROM complaints
        WHERE is_duplicate = 0
        GROUP BY category
        ORDER BY count DESC
    """)

    # 3. By Status
    by_status = query_db("""
        SELECT status, COUNT(id) as count
        FROM complaints
        WHERE is_duplicate = 0
        GROUP BY status
    """)

    # 4. Average resolution time (in hours)
    resolved_tickets = query_db("""
        SELECT reported_at, resolved_at
        FROM complaints
        WHERE status = 'Resolved' AND resolved_at IS NOT NULL AND is_duplicate = 0
    """)
    
    total_hours = 0.0
    valid_resolved_count = 0
    for r in resolved_tickets:
        try:
            # SQLite default timestamp format %Y-%m-%d %H:%M:%S
            t_rep = datetime.fromisoformat(r["reported_at"])
            t_res = datetime.fromisoformat(r["resolved_at"])
            diff = (t_res - t_rep).total_seconds() / 3600.0
            if diff >= 0:
                total_hours += diff
                valid_resolved_count += 1
        except Exception:
            continue

    avg_resolution_hours = round(total_hours / valid_resolved_count, 1) if valid_resolved_count > 0 else 0.0

    return {
        "by_zone": by_zone,
        "by_category": by_category,
        "by_status": {row["status"]: row["count"] for row in by_status},
        "avg_resolution_hours": avg_resolution_hours,
        "resolved_count": valid_resolved_count
    }

def get_overdue_tickets(threshold_hours=None):
    """Identifies active tickets open longer than configured threshold hours."""
    threshold = threshold_hours or Config.OVERDUE_HOURS_THRESHOLD
    cutoff = (datetime.now() - timedelta(hours=threshold)).strftime("%Y-%m-%d %H:%M:%S")
    
    return query_db("""
        SELECT c.*, p.pole_code, p.zone, p.landmark, u.full_name as worker_name
        FROM complaints c
        JOIN poles p ON c.pole_id = p.id
        LEFT JOIN users u ON c.assigned_worker_id = u.id
        WHERE c.status IN ('Reported', 'Assigned', 'In Progress')
          AND c.reported_at <= ?
          AND c.is_duplicate = 0
        ORDER BY c.reported_at ASC
    """, (cutoff,))

def get_repeated_fault_poles(days=None, threshold=None):
    """Detects poles that have experienced repeated breakdowns (>= N in M days)."""
    days = days or Config.REPEATED_FAULT_DAYS
    threshold = threshold or Config.REPEATED_FAULT_COUNT_THRESHOLD
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    return query_db("""
        SELECT p.id, p.pole_code, p.zone, p.landmark, p.latitude, p.longitude, COUNT(c.id) as fault_count
        FROM poles p
        JOIN complaints c ON p.id = c.pole_id
        WHERE c.reported_at >= ? AND c.is_duplicate = 0
        GROUP BY p.id
        HAVING fault_count >= ?
        ORDER BY fault_count DESC
    """, (cutoff, threshold))

def get_incident_recommendations():
    """Generates plain-language rule-based recommendations for preventative maintenance."""
    recs = []
    # 1. Frequent breakdown check
    repeated = get_repeated_fault_poles()
    for pole in repeated:
        recs.append({
            "type": "RECURRENT_FAULT",
            "level": "WARNING",
            "pole_code": pole["pole_code"],
            "zone": pole["zone"],
            "title": f"Recurrent Failure Pattern: Pole {pole['pole_code']}",
            "description": f"Logged {pole['fault_count']} failures within {Config.REPEATED_FAULT_DAYS} days. "
                           f"Possible underground cable insulation breakdown or chronic driver surge. "
                           f"Recommend full branch megger test and luminaire replacement rather than isolated bulb swaps."
        })

    # 2. Overdue check
    overdue = get_overdue_tickets()
    if overdue:
        recs.append({
            "type": "SLA_BREACH",
            "level": "DANGER",
            "pole_code": ", ".join(t["pole_code"] for t in overdue[:3]),
            "zone": "Multi-Zone",
            "title": f"{len(overdue)} Overdue Tickets Exceeding {Config.OVERDUE_HOURS_THRESHOLD}h SLA",
            "description": f"Target resolution time breached for high-impact tickets. "
                           f"Recommend reassigning field crews or escalating priority to Senior Lineman."
        })

    # 3. Feeder Alert Check
    active_feeders = query_db("SELECT * FROM feeder_alerts WHERE status = 'Active'")
    for fa in active_feeders:
        recs.append({
            "type": "FEEDER_OUTAGE",
            "level": "CRITICAL",
            "pole_code": "Group Feeder",
            "zone": fa["zone"],
            "title": f"Active Substation Supply Disruption in {fa['zone']}",
            "description": f"Group-level {fa['alert_type']} detected ({fa['voltage']}V, {fa['current']}A). "
                           f"Dispatch substation crew to inspect transformer breaker and main phase bus before sending individual pole technicians."
        })

    return recs

def export_complaints_csv():
    """Generates a downloadable CSV string of all complaint records."""
    rows = query_db("""
        SELECT c.id, c.reference_no, p.pole_code, p.zone, p.landmark, p.latitude, p.longitude,
               c.category, c.priority, c.priority_reason, c.status,
               u.full_name as assigned_worker, c.is_duplicate, parent.reference_no as duplicate_of,
               c.reported_at, c.resolved_at
        FROM complaints c
        JOIN poles p ON c.pole_id = p.id
        LEFT JOIN users u ON c.assigned_worker_id = u.id
        LEFT JOIN complaints parent ON c.duplicate_of_id = parent.id
        ORDER BY c.id DESC
    """)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Reference No", "Pole Code", "Zone", "Landmark", "Latitude", "Longitude",
        "Category", "Priority", "Priority Reason", "Status", "Assigned Worker",
        "Is Duplicate", "Duplicate Of", "Reported At", "Resolved At", "Data Type"
    ])

    for r in rows:
        writer.writerow([
            r["reference_no"], r["pole_code"], r["zone"], r["landmark"],
            r["latitude"], r["longitude"], r["category"], r["priority"],
            r["priority_reason"], r["status"], r["assigned_worker"] or "Unassigned",
            "YES" if r["is_duplicate"] else "NO", r["duplicate_of"] or "N/A",
            r["reported_at"], r["resolved_at"] or "N/A", "Demonstration data"
        ])

    return output.getvalue()

def calculate_distance(lat1, lon1, lat2, lon2):
    """Approximates Euclidean distance in kilometers between two lat/lon coordinates."""
    # 1 deg lat ~ 111 km, 1 deg lon ~ 111 km * cos(lat)
    d_lat = (lat2 - lat1) * 111.0
    d_lon = (lon2 - lon1) * 111.0 * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.sqrt(d_lat**2 + d_lon**2)

def compute_nearest_neighbour_route(start_coords=None):
    """
    Computes an optimized multi-stop sequence for active tickets using the
    Nearest-Neighbour greedy heuristic.
    """
    # Start at central substation Alpha if no start coords supplied
    start_lat = start_coords[0] if start_coords else 12.9716
    start_lon = start_coords[1] if start_coords else 77.5946

    # Fetch active uncompleted complaints
    unvisited = query_db("""
        SELECT c.id as complaint_id, c.reference_no, c.category, c.priority, c.status,
               p.id as pole_id, p.pole_code, p.zone, p.landmark, p.latitude, p.longitude
        FROM complaints c
        JOIN poles p ON c.pole_id = p.id
        WHERE c.status IN ('Reported', 'Assigned', 'In Progress') AND c.is_duplicate = 0
    """)

    if not unvisited:
        return {"route": [], "total_distance_km": 0.0, "google_maps_multi_url": None}

    unvisited = [dict(row) for row in unvisited]
    route = []
    current_lat, current_lon = start_lat, start_lon
    total_km = 0.0

    while unvisited:
        # Find nearest pole to current location
        nearest_idx = 0
        min_dist = calculate_distance(current_lat, current_lon, unvisited[0]["latitude"], unvisited[0]["longitude"])

        for i in range(1, len(unvisited)):
            dist = calculate_distance(current_lat, current_lon, unvisited[i]["latitude"], unvisited[i]["longitude"])
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        chosen = unvisited.pop(nearest_idx)
        chosen["leg_distance_km"] = round(min_dist, 2)
        total_km += min_dist
        current_lat, current_lon = chosen["latitude"], chosen["longitude"]
        route.append(chosen)

    # Build Google Maps multi-stop URL
    # Format: https://www.google.com/maps/dir/lat1,lon1/lat2,lon2/lat3,lon3
    waypoints = [f"{start_lat},{start_lon}"] + [f"{stop['latitude']},{stop['longitude']}" for stop in route]
    gmaps_multi_url = "https://www.google.com/maps/dir/" + "/".join(waypoints)

    return {
        "route": route,
        "total_distance_km": round(total_km, 2),
        "stops_count": len(route),
        "google_maps_multi_url": gmaps_multi_url
    }
