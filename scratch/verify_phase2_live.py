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
    print("=== LIVE FLASK HTTP VERIFICATION OF PHASE 2 SNAPSHOT PERSISTENCE & DETAIL RETRIEVAL ===")
    own_tok, own_uid = login("demo_owner")
    mgr_tok, mgr_uid = login("demo_manager")
    emp_tok, emp_uid = login("demo_employee")
    sup_tok, sup_uid = login("demo_supplier")

    print(f"Logged in: Owner ID={own_uid}, Manager ID={mgr_uid}, Employee ID={emp_uid}, Supplier ID={sup_uid}")

    headers_own = {"Authorization": f"Bearer {own_tok}"}
    headers_mgr = {"Authorization": f"Bearer {mgr_tok}"}
    headers_emp = {"Authorization": f"Bearer {emp_tok}"}
    headers_sup = {"Authorization": f"Bearer {sup_tok}"}

    # 1. Test GET /reports/ metadata format
    print("\n--- 1. Testing GET /api/reports/ Metadata ---")
    r_list = requests.get(f"{BASE_URL}/reports/", headers=headers_mgr)
    assert r_list.status_code == 200, f"Expected 200, got {r_list.status_code}"
    reports = r_list.json()
    print(f"  Total reports retrieved: {len(reports)}")
    if reports:
        first = reports[0]
        print(f"  Sample report metadata keys: {list(first.keys())}")
        assert "has_snapshot" in first, "has_snapshot key missing in metadata"
        assert "generated_by_username" in first, "generated_by_username missing in metadata"
        print(f"  Report #{first['report_id']} - has_snapshot: {first['has_snapshot']}, generated_by_username: {first['generated_by_username']}")

    # 2. Test GET /reports/1 (Legacy report without snapshot)
    print("\n--- 2. Testing GET /api/reports/1 (Legacy Report) ---")
    r_legacy = requests.get(f"{BASE_URL}/reports/1", headers=headers_mgr)
    assert r_legacy.status_code == 200, f"Expected 200, got {r_legacy.status_code}"
    legacy_data = r_legacy.json()
    print(f"  Report ID: {legacy_data.get('report_id')}")
    print(f"  Report Name: {legacy_data.get('report_name')}")
    print(f"  Has Snapshot: {legacy_data.get('has_snapshot')}")
    print(f"  Snapshot: {legacy_data.get('snapshot')}")
    print(f"  Message: {legacy_data.get('message')}")
    assert legacy_data.get("has_snapshot") is False, "Legacy report should have has_snapshot=False"
    assert legacy_data.get("snapshot") is None, "Legacy report should have snapshot=None"
    assert legacy_data.get("message") == "Historical snapshot data is unavailable for this report"

    # 3. Test POST /reports/generate and snapshot persistence
    print("\n--- 3. Testing POST /api/reports/generate (Persist Snapshot) ---")
    payload = {
        "report_name": "Live Verification Phase 2 Snapshot",
        "report_type": "Inventory"
    }
    r_gen = requests.post(f"{BASE_URL}/reports/generate", headers=headers_mgr, json=payload)
    assert r_gen.status_code == 201, f"Expected 201, got {r_gen.status_code}: {r_gen.text}"
    gen_data = r_gen.json()
    new_report_id = gen_data["report"]["report_id"]
    print(f"  Created report #{new_report_id}")
    print(f"  Report metadata: {gen_data['report']}")
    print(f"  Snapshot item count: {len(gen_data.get('data', []))}")
    assert gen_data["report"].get("has_snapshot") is True

    # 4. Test GET /reports/<new_report_id> (Retrieve Saved Snapshot)
    print(f"\n--- 4. Testing GET /api/reports/{new_report_id} (Retrieve Snapshot) ---")
    r_detail = requests.get(f"{BASE_URL}/reports/{new_report_id}", headers=headers_mgr)
    assert r_detail.status_code == 200, f"Expected 200, got {r_detail.status_code}"
    detail_data = r_detail.json()
    assert detail_data["report_id"] == new_report_id
    assert detail_data["has_snapshot"] is True
    assert detail_data["message"] is None
    assert isinstance(detail_data["snapshot"], list)
    assert len(detail_data["snapshot"]) == len(gen_data["data"])
    print(f"  Retrieved report #{detail_data['report_id']} by {detail_data['generated_by_username']}")
    print(f"  Saved snapshot items verified: {len(detail_data['snapshot'])} items")
    print(f"  First item SKU: {detail_data['snapshot'][0]['sku']}, Price: {detail_data['snapshot'][0]['unit_price']}")

    # 5. Test Access Control on Detail Endpoint
    print(f"\n--- 5. Testing RBAC on GET /api/reports/{new_report_id} ---")
    r_anon = requests.get(f"{BASE_URL}/reports/{new_report_id}")
    print(f"  Anonymous: status={r_anon.status_code} (Expected 401)")
    assert r_anon.status_code == 401

    r_emp = requests.get(f"{BASE_URL}/reports/{new_report_id}", headers=headers_emp)
    print(f"  Employee: status={r_emp.status_code} (Expected 403)")
    assert r_emp.status_code == 403

    r_sup = requests.get(f"{BASE_URL}/reports/{new_report_id}", headers=headers_sup)
    print(f"  Supplier: status={r_sup.status_code} (Expected 403)")
    assert r_sup.status_code == 403

    r_own = requests.get(f"{BASE_URL}/reports/{new_report_id}", headers=headers_own)
    print(f"  Owner: status={r_own.status_code} (Expected 200)")
    assert r_own.status_code == 200

    # 6. Test Invalid and Non-existent Report IDs
    print("\n--- 6. Testing Invalid & Non-Existent Report IDs ---")
    for bad_id in ["abc", "-5", "0"]:
        r_bad = requests.get(f"{BASE_URL}/reports/{bad_id}", headers=headers_mgr)
        print(f"  ID '{bad_id}': status={r_bad.status_code} (Expected 400)")
        assert r_bad.status_code == 400
        assert r_bad.json().get("error") == "Invalid report ID"

    r_404 = requests.get(f"{BASE_URL}/reports/99999999", headers=headers_mgr)
    print(f"  ID '99999999': status={r_404.status_code} (Expected 404)")
    assert r_404.status_code == 404
    assert r_404.json().get("error") == "Report not found"

    print("\n>>> ALL LIVE HTTP PHASE 2 VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    main()
