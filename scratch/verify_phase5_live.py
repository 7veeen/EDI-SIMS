import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def login(username, password):
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": username,
        "password": password
    })
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token"), data.get("user", {})
    return None, None

def verify_live():
    print("=== LIVE FLASK HTTP VERIFICATION OF PHASE 5 (QUOTATIONS & SUPPLIER PERFORMANCE) ===")

    owner_token, owner_user = login("demo_owner", "password123")
    mgr_token, mgr_user = login("demo_manager", "password123")
    emp_token, emp_user = login("demo_employee", "password123")
    sup_token, sup_user = login("demo_supplier", "password123")

    assert owner_token and mgr_token and emp_token and sup_token, "Failed to authenticate test users"
    print(" [PASS] Logged in: Owner, Manager, Employee, Supplier")

    # 1. Test unsupported types rejection
    resp_unsupported = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"report_name": "Invalid Type", "report_type": "Audit Trail"}
    )
    assert resp_unsupported.status_code == 400, f"Expected 400, got {resp_unsupported.status_code}"
    print(" [PASS] Unsupported report types strictly rejected with HTTP 400")

    # 2. Test invalid date format and reversed dates
    resp_bad_date = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"report_name": "Bad Date", "report_type": "Quotations", "start_date": "invalid"}
    )
    assert resp_bad_date.status_code == 400
    resp_rev_date = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"report_name": "Rev Date", "report_type": "Quotations", "start_date": "2026-12-31", "end_date": "2026-01-01"}
    )
    assert resp_rev_date.status_code == 400
    print(" [PASS] Invalid and reversed date ranges strictly rejected with HTTP 400")

    # 3. Test RBAC for generation endpoint
    resp_anon = requests.post(
        f"{BASE_URL}/api/reports/generate",
        json={"report_name": "Anon Quotations", "report_type": "Quotations"}
    )
    assert resp_anon.status_code == 401, f"Expected 401, got {resp_anon.status_code}"

    resp_emp = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {emp_token}"},
        json={"report_name": "Emp Quotations", "report_type": "Quotations"}
    )
    assert resp_emp.status_code == 403, f"Expected 403, got {resp_emp.status_code}"

    resp_sup = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {sup_token}"},
        json={"report_name": "Sup Supplier Perf", "report_type": "Supplier Performance"}
    )
    assert resp_sup.status_code == 403, f"Expected 403, got {resp_sup.status_code}"
    print(" [PASS] Generation endpoint strictly rejects anonymous (401), employee (403), supplier (403)")

    # 4. Generate Quotations Report as Manager
    resp_gen_q = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {mgr_token}"},
        json={"report_name": "Live Verified Quotations Report", "report_type": "Quotations"}
    )
    assert resp_gen_q.status_code == 201, f"Expected 201, got {resp_gen_q.status_code}: {resp_gen_q.text}"
    q_rep = resp_gen_q.json()["report"]
    q_id = q_rep["report_id"]
    assert q_rep["generated_by"] == mgr_user["user_id"], "Identity not derived from JWT"
    print(f" [PASS] Successfully generated Quotations Report #{q_id} as Manager (Items count: {len(resp_gen_q.json().get('data', []))})")

    # 5. Retrieve Quotations Report Detail
    resp_get_q = requests.get(
        f"{BASE_URL}/api/reports/{q_id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp_get_q.status_code == 200
    q_detail = resp_get_q.json()
    assert q_detail["has_snapshot"] is True
    assert isinstance(q_detail["snapshot"], list)
    if len(q_detail["snapshot"]) > 0:
        first_q = q_detail["snapshot"][0]
        assert "quotation_number" in first_q
        assert "supplier_name" in first_q
        assert "items" in first_q
        assert isinstance(first_q["items"], list)
    print(" [PASS] Quotations detail verified with valid nested line items contract")

    # 6. Generate Supplier Performance Report as Owner
    resp_gen_sp = requests.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"report_name": "Live Verified Supplier Performance Report", "report_type": "Supplier Performance"}
    )
    assert resp_gen_sp.status_code == 201, f"Expected 201, got {resp_gen_sp.status_code}: {resp_gen_sp.text}"
    sp_rep = resp_gen_sp.json()["report"]
    sp_id = sp_rep["report_id"]
    assert sp_rep["generated_by"] == owner_user["user_id"]
    print(f" [PASS] Successfully generated Supplier Performance Report #{sp_id} as Owner (Suppliers count: {len(resp_gen_sp.json().get('data', []))})")

    # 7. Retrieve Supplier Performance Detail
    resp_get_sp = requests.get(
        f"{BASE_URL}/api/reports/{sp_id}",
        headers={"Authorization": f"Bearer {mgr_token}"}
    )
    assert resp_get_sp.status_code == 200
    sp_detail = resp_get_sp.json()
    assert sp_detail["has_snapshot"] is True
    assert isinstance(sp_detail["snapshot"], list)
    if len(sp_detail["snapshot"]) > 0:
        first_sup = sp_detail["snapshot"][0]
        assert "supplier_name" in first_sup
        assert "total_purchase_orders" in first_sup
        assert "total_quotations" in first_sup
        assert "metric_definitions" in first_sup
    print(" [PASS] Supplier Performance detail verified with explainable metrics contract")

    # 8. Check Legacy Report Detail Preservation
    resp_legacy = requests.get(
        f"{BASE_URL}/api/reports/1",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp_legacy.status_code == 200
    leg_data = resp_legacy.json()
    assert leg_data["has_snapshot"] is False
    assert leg_data["snapshot"] is None
    assert "Historical snapshot data is unavailable" in leg_data["message"]
    print(" [PASS] Legacy report detail preserves unavailable-snapshot message")

    # 9. Verify CSV balance export
    resp_csv = requests.get(
        f"{BASE_URL}/api/reports/export?report_type=Inventory",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers.get("Content-Type", "")
    print(" [PASS] Current balance CSV export remains functional")

    # 10. Verify Frontend serves reports.js?v=50
    frontend_resp = requests.get("http://localhost:8000/")
    assert "reports.js?v=50" in frontend_resp.text
    print(" [PASS] Frontend serves updated reports.js?v=50 with all Phase 5 features")

    print("\nALL 10 LIVE FLASK HTTP VERIFICATION CHECKS PASSED PERFECTLY!")

if __name__ == '__main__':
    verify_live()
