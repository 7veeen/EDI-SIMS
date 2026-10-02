import time
from datetime import datetime, timezone
from app.extensions import get_db_connection

# Record process startup time to calculate uptime
PROCESS_START_TIME = time.time()

# Documented performance warning threshold for cloud PostgreSQL latency: 500.0 ms
LATENCY_WARNING_THRESHOLD_MS = 500.0


def get_liveness():
    """
    Returns minimal backend liveness status for public ping checks.
    """
    return {
        "status": "UP"
    }


def get_detailed_health():
    """
    Gathers detailed system telemetry:
      - Backend availability & uptime
      - Database connectivity (CONNECTED vs DISCONNECTED)
      - Database query round-trip latency in milliseconds
      - Database performance evaluation (NORMAL vs ELEVATED) against documented threshold (500 ms)
      - Module readiness states from SystemStatus table
      - Overall health determination:
          HEALTHY: Database CONNECTED, Inventory module READY, and Database performance NORMAL (<= 500ms).
          DEGRADED: Database DISCONNECTED, Inventory NOT READY, or Database latency ELEVATED (> 500ms).
    Returns:
        (health_dict, http_status_code)
    """
    checked_at = datetime.now(timezone.utc).isoformat()
    uptime_seconds = int(time.time() - PROCESS_START_TIME)

    conn = None
    cursor = None
    db_connected = False
    latency_ms = None
    modules = []

    try:
        # Measure database round-trip query latency using high-resolution monotonic timer
        t_start = time.perf_counter()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        db_connected = True

        # Read actual module readiness from SystemStatus table
        cursor.execute('''
            SELECT module_name, status, progress, message, updated_at
            FROM public."SystemStatus"
            ORDER BY module_name ASC
        ''')
        rows = cursor.fetchall()
        for row in rows:
            updated_str = row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4])
            modules.append({
                "name": row[0],
                "status": row[1],
                "progress": row[2],
                "message": row[3],
                "updated_at": updated_str
            })

    except Exception:
        db_connected = False
        latency_ms = None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # Determine Inventory module readiness
    inventory_ready = False
    for mod in modules:
        if mod.get("name") == "Inventory" and mod.get("status") == "READY":
            inventory_ready = True
            break

    # Evaluate database performance separately from connectivity status
    if not db_connected:
        db_performance = "UNAVAILABLE"
        performance_warning = False
    elif latency_ms is not None and latency_ms > LATENCY_WARNING_THRESHOLD_MS:
        db_performance = "ELEVATED"
        performance_warning = True
    else:
        db_performance = "NORMAL"
        performance_warning = False

    # Consistent overall health calculation:
    # All components must be connected, ready, and performing within thresholds
    if db_connected and inventory_ready and not performance_warning:
        overall_status = "HEALTHY"
    else:
        overall_status = "DEGRADED"

    response_data = {
        "overall_status": overall_status,
        "backend": {
            "status": "UP"
        },
        "database": {
            "status": "CONNECTED" if db_connected else "DISCONNECTED",
            "latency_ms": latency_ms,
            "performance": db_performance,
            "performance_warning": performance_warning,
            "latency_threshold_ms": LATENCY_WARNING_THRESHOLD_MS
        },
        "performance_warning": performance_warning,
        "modules": modules,
        "uptime_seconds": uptime_seconds,
        "checked_at": checked_at
    }

    # If database check fails completely, return 503 Service Unavailable
    http_status = 200 if db_connected else 503
    return response_data, http_status
