import os
import sys
import requests

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extensions import get_db_connection

def test_no_side_effects():
    # Login as owner
    resp = requests.post("http://127.0.0.1:5000/api/auth/login", json={"username": "demo_owner", "password": "password123"})
    token = resp.json().get("access_token")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM public."AuditLogs"')
    count_before = cur.fetchone()[0]

    # Repeated health check calls
    for _ in range(5):
        r1 = requests.get("http://127.0.0.1:5000/api/status/")
        assert r1.status_code == 200
        r2 = requests.get("http://127.0.0.1:5000/api/status/health", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200

    cur.execute('SELECT COUNT(*) FROM public."AuditLogs"')
    count_after = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"Audit count before health calls: {count_before}, after 5 health calls: {count_after}")
    assert count_before == count_after, f"AuditLogs was polluted by health check: before={count_before}, after={count_after}"
    print("PASS: System health endpoints produce zero audit logs or database side-effects.")

if __name__ == "__main__":
    test_no_side_effects()
