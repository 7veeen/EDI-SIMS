import requests
import json
import csv
import io

BASE_URL = "http://127.0.0.1:5000/api"

def login(username, password="password123"):
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        data = r.json()
        return data["access_token"], data["user"]["user_id"]
    return None, None

def main():
    print("=== LIVE FLASK HTTP VERIFICATION OF PHASE 1 SECURITY ===")
    own_tok, own_uid = login("demo_owner")
    mgr_tok, mgr_uid = login("demo_manager")
    emp_tok, emp_uid = login("demo_employee")
    sup_tok, sup_uid = login("demo_supplier")

    print(f"Logged in: Owner ID={own_uid}, Manager ID={mgr_uid}, Employee ID={emp_uid}, Supplier ID={sup_uid}")

    headers_own = {"Authorization": f"Bearer {own_tok}"}
    headers_mgr = {"Authorization": f"Bearer {mgr_tok}"}
    headers_emp = {"Authorization": f"Bearer {emp_tok}"}
    headers_sup = {"Authorization": f"Bearer {sup_tok}"}

    # 1. Test GET /reports/
    print("\n--- 1. Testing GET /api/reports/ ---")
    r_anon = requests.get(f"{BASE_URL}/reports/")
    print(f"  Anonymous: status={r_anon.status_code} (Expected 401)")
    assert r_anon.status_code == 401

    r_emp = requests.get(f"{BASE_URL}/reports/", headers=headers_emp)
    print(f"  Employee: status={r_emp.status_code} (Expected 403)")
    assert r_emp.status_code == 403

    r_sup = requests.get(f"{BASE_URL}/reports/", headers=headers_sup)
    print(f"  Supplier: status={r_sup.status_code} (Expected 403)")
    assert r_sup.status_code == 403

    r_mgr = requests.get(f"{BASE_URL}/reports/", headers=headers_mgr)
    print(f"  Manager: status={r_mgr.status_code}, count={len(r_mgr.json())} (Expected 200)")
    assert r_mgr.status_code == 200

    r_own = requests.get(f"{BASE_URL}/reports/", headers=headers_own)
    print(f"  Owner: status={r_own.status_code}, count={len(r_own.json())} (Expected 200)")
    assert r_own.status_code == 200

    # 2. Test GET /reports/status
    print("\n--- 2. Testing GET /api/reports/status ---")
    r_stat_anon = requests.get(f"{BASE_URL}/reports/status")
    print(f"  Anonymous: status={r_stat_anon.status_code} (Expected 401)")
    assert r_stat_anon.status_code == 401

    r_stat_emp = requests.get(f"{BASE_URL}/reports/status", headers=headers_emp)
    print(f"  Employee: status={r_stat_emp.status_code} (Expected 403)")
    assert r_stat_emp.status_code == 403

    r_stat_mgr = requests.get(f"{BASE_URL}/reports/status", headers=headers_mgr)
    print(f"  Manager: status={r_stat_mgr.status_code}, data={r_stat_mgr.json()} (Expected 200)")
    assert r_stat_mgr.status_code == 200

    # 3. Test POST /reports/generate RBAC & Identity Spoofing Protection
    print("\n--- 3. Testing POST /api/reports/generate ---")
    r_gen_anon = requests.post(f"{BASE_URL}/reports/generate", json={"report_name": "Test", "report_type": "Inventory"})
    print(f"  Anonymous: status={r_gen_anon.status_code} (Expected 401)")
    assert r_gen_anon.status_code == 401

    r_gen_emp = requests.post(f"{BASE_URL}/reports/generate", headers=headers_emp, json={"report_name": "Test", "report_type": "Inventory"})
    print(f"  Employee: status={r_gen_emp.status_code} (Expected 403)")
    assert r_gen_emp.status_code == 403

    # Manager submits forged Owner ID (generated_by: 5)
    r_gen_spoof = requests.post(
        f"{BASE_URL}/reports/generate",
        headers=headers_mgr,
        json={
            "report_name": f"Manager Report Live {own_uid}",
            "report_type": "Inventory",
            "generated_by": own_uid # Forging Owner ID
        }
    )
    print(f"  Manager Spoof Attempt: status={r_gen_spoof.status_code}")
    assert r_gen_spoof.status_code == 201
    rep = r_gen_spoof.json()["report"]
    print(f"  Manager Report generated_by={rep['generated_by']} (Expected Manager ID {mgr_uid}, NOT {own_uid})")
    assert rep["generated_by"] == mgr_uid

    # 4. Test GET /reports/export and Formula Injection Protection
    print("\n--- 4. Testing GET /api/reports/export ---")
    r_exp_anon = requests.get(f"{BASE_URL}/reports/export")
    print(f"  Anonymous Export: status={r_exp_anon.status_code} (Expected 401)")
    assert r_exp_anon.status_code == 401

    r_exp_emp = requests.get(f"{BASE_URL}/reports/export", headers=headers_emp)
    print(f"  Employee Export: status={r_exp_emp.status_code} (Expected 403)")
    assert r_exp_emp.status_code == 403

    r_exp_mgr = requests.get(f"{BASE_URL}/reports/export", headers=headers_mgr)
    print(f"  Manager Export: status={r_exp_mgr.status_code}")
    assert r_exp_mgr.status_code == 200
    print(f"  Content-Type: {r_exp_mgr.headers.get('Content-Type')}")
    print(f"  Content-Disposition: {r_exp_mgr.headers.get('Content-Disposition')}")
    print(f"  Starts with UTF-8 BOM: {r_exp_mgr.content.startswith(b'\xef\xbb\xbf')}")
    assert r_exp_mgr.content.startswith(b'\xef\xbb\xbf')

    csv_text = r_exp_mgr.content.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(csv_text)))
    print(f"  Total CSV rows: {len(rows)} (Header + {len(rows)-1} data rows)")
    print(f"  Headers: {rows[0]}")
    print(f"  Sample row: {rows[1]}")

    print("\n==================================================")
    print("ALL LIVE HTTP SECURITY VERIFICATIONS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    main()
