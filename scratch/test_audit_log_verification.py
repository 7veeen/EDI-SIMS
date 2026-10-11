import os
import sys
import requests
import json

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.team3.audit_service import get_all_audit_logs
from app.services.team3.report_service import fetch_audit_trail_report_data
from app.extensions import get_db_connection

BASE_URL = "http://127.0.0.1:5000"

def get_token(username, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

def run_tests():
    print("=== 1. VERIFY get_all_audit_logs() SERVICE FUNCTION ===")
    logs, err = get_all_audit_logs(limit=10)
    assert err is None, f"get_all_audit_logs returned error: {err}"
    assert isinstance(logs, list), "Expected list of logs"
    assert len(logs) > 0, "Expected at least 1 log"
    
    first = logs[0]
    expected_keys = {"log_id", "user_id", "action", "table_name", "record_id", "action_time", "ip_address", "username"}
    assert expected_keys.issubset(first.keys()), f"Missing keys in record: {first.keys()}"
    print(f"Sample log: {json.dumps(first, indent=2)}")
    print("Service function check: PASSED\n")

    print("=== 2. VERIFY RBAC & API ENDPOINT /api/audit-logs/ ===")
    # Anonymous
    r_anon = requests.get(f"{BASE_URL}/api/audit-logs/")
    print(f"Anonymous status: {r_anon.status_code} (Expected 401)")
    assert r_anon.status_code == 401, f"Expected 401 for anonymous, got {r_anon.status_code}"

    # Supplier
    sup_token = get_token("demo_supplier", "password123")
    r_sup = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {sup_token}"})
    print(f"Supplier status: {r_sup.status_code} (Expected 403)")
    assert r_sup.status_code == 403, f"Expected 403 for supplier, got {r_sup.status_code}"

    # Employee
    emp_token = get_token("demo_employee", "password123")
    r_emp = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {emp_token}"})
    print(f"Employee status: {r_emp.status_code} (Expected 403)")
    assert r_emp.status_code == 403, f"Expected 403 for employee, got {r_emp.status_code}"

    # Manager
    mgr_token = get_token("demo_manager", "password123")
    r_mgr = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {mgr_token}"})
    print(f"Manager status: {r_mgr.status_code} (Expected 403)")
    assert r_mgr.status_code == 403, f"Expected 403 for manager, got {r_mgr.status_code}"

    # Owner
    owner_token = get_token("demo_owner", "password123")
    r_owner = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {owner_token}"})
    print(f"Owner status: {r_owner.status_code} (Expected 200)")
    assert r_owner.status_code == 200, f"Expected 200 for owner, got {r_owner.status_code}"

    owner_data = r_owner.json()
    assert isinstance(owner_data, list), "Expected list response"
    print(f"Owner retrieved {len(owner_data)} audit records successfully.")
    assert len(owner_data) > 0, "Expected at least 1 record"
    assert "username" in owner_data[0], "Owner response records must include username"
    print("RBAC & API check: PASSED\n")

    print("=== 3. VERIFY DATA CONSISTENCY WITH SUPABASE POSTGRESQL ===")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT log_id, user_id, action, table_name, record_id, action_time, ip_address FROM public."AuditLogs" WHERE log_id = %s', (owner_data[0]["log_id"],))
    db_row = cur.fetchone()
    cur.close()
    conn.close()

    assert db_row is not None, "Record not found in database"
    assert db_row[0] == owner_data[0]["log_id"]
    assert db_row[1] == owner_data[0]["user_id"]
    assert db_row[2] == owner_data[0]["action"]
    assert db_row[3] == owner_data[0]["table_name"]
    print(f"Verified API record #{owner_data[0]['log_id']} matches exact database row.")
    print("Database consistency check: PASSED\n")

    print("=== 4. VERIFY REPORTS MODULE AUDIT TRAIL COMPATIBILITY ===")
    report_data, err_resp, code = fetch_audit_trail_report_data()
    assert code == 200, f"Audit trail report data returned code {code}: {err_resp}"
    assert isinstance(report_data, list), "Expected list of report records"
    print(f"Audit Trail report retrieved {len(report_data)} records successfully.")
    print("Reports module compatibility check: PASSED\n")

    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
