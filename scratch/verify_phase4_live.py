"""
verify_phase4_live.py
Live HTTP verification of Phase 4 Stock Transactions and Purchase Orders report generation and detail retrieval.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def run_live_verification():
    print("=== LIVE FLASK HTTP VERIFICATION OF PHASE 4 MULTI-REPORT GENERATION & DETAIL RETRIEVAL ===")

    # 1. Authenticate roles
    s = requests.Session()
    def get_token(username):
        resp = s.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": "password123"})
        assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
        return resp.json()["access_token"]

    owner_token = get_token("demo_owner")
    manager_token = get_token("demo_manager")
    employee_token = get_token("demo_employee")
    supplier_token = get_token("demo_supplier")
    print(" [PASS] Logged in: Owner, Manager, Employee, Supplier")

    # 2. Test Invalid Report Type Rejection (HTTP 400)
    for bad_type in ["Quotations", "Shipments", "InvalidType", ""]:
        resp_bad = s.post(
            f"{BASE_URL}/api/reports/generate",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"report_name": "Bad Type Test", "report_type": bad_type}
        )
        assert resp_bad.status_code == 400, f"Expected 400 for {bad_type}, got {resp_bad.status_code}"
    print(" [PASS] Unsupported report types strictly rejected with HTTP 400")

    # 3. Test RBAC on generation endpoint
    for rep_type in ["Stock Transactions", "Purchase Orders"]:
        resp_anon = s.post(f"{BASE_URL}/api/reports/generate", json={"report_name": "Anon", "report_type": rep_type})
        assert resp_anon.status_code == 401, f"Expected 401 for anon, got {resp_anon.status_code}"

        resp_emp = s.post(f"{BASE_URL}/api/reports/generate", headers={"Authorization": f"Bearer {employee_token}"}, json={"report_name": "Emp", "report_type": rep_type})
        assert resp_emp.status_code == 403, f"Expected 403 for emp, got {resp_emp.status_code}"

        resp_sup = s.post(f"{BASE_URL}/api/reports/generate", headers={"Authorization": f"Bearer {supplier_token}"}, json={"report_name": "Sup", "report_type": rep_type})
        assert resp_sup.status_code == 403, f"Expected 403 for sup, got {resp_sup.status_code}"
    print(" [PASS] Generation endpoint rejects anonymous (401), employee (403), supplier (403)")

    # 4. Generate Stock Transactions Report as Manager
    st_resp = s.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {manager_token}"},
        json={
            "report_name": "Live Phase 4 Stock Transactions Snapshot",
            "report_type": "Stock Transactions",
            "generated_by": 999999  # Attempted spoof
        }
    )
    assert st_resp.status_code == 201, f"Generate Stock Transactions failed: {st_resp.text}"
    st_data = st_resp.json()
    st_rep = st_data["report"]
    st_id = st_rep["report_id"]
    assert st_rep["report_type"] == "Stock Transactions"
    assert st_rep["generated_by"] != 999999, "Spoofed ID was not ignored!"
    assert st_rep["has_snapshot"] is True
    print(f" [PASS] Successfully generated Stock Transactions Report #{st_id} (Items count: {len(st_data['data'])})")

    # 5. Retrieve Stock Transactions Report Detail
    st_detail_resp = s.get(f"{BASE_URL}/api/reports/{st_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert st_detail_resp.status_code == 200
    st_detail = st_detail_resp.json()
    assert st_detail["report_type"] == "Stock Transactions"
    assert st_detail["has_snapshot"] is True
    assert isinstance(st_detail["snapshot"], list)
    if len(st_detail["snapshot"]) > 0:
        first_tx = st_detail["snapshot"][0]
        for key in ["transaction_id", "product_id", "product_name", "sku", "transaction_type", "quantity", "transaction_date", "performed_by"]:
            assert key in first_tx, f"Missing key {key} in transaction snapshot"
    print(f" [PASS] Stock Transactions detail verified with valid transaction item contract")

    # 6. Generate Purchase Orders Report as Owner
    po_resp = s.post(
        f"{BASE_URL}/api/reports/generate",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "report_name": "Live Phase 4 Purchase Orders Snapshot",
            "report_type": "Purchase Orders"
        }
    )
    assert po_resp.status_code == 201, f"Generate Purchase Orders failed: {po_resp.text}"
    po_data = po_resp.json()
    po_rep = po_data["report"]
    po_id = po_rep["report_id"]
    assert po_rep["report_type"] == "Purchase Orders"
    assert po_rep["has_snapshot"] is True
    print(f" [PASS] Successfully generated Purchase Orders Report #{po_id} (POs count: {len(po_data['data'])})")

    # 7. Retrieve Purchase Orders Report Detail
    po_detail_resp = s.get(f"{BASE_URL}/api/reports/{po_id}", headers={"Authorization": f"Bearer {manager_token}"})
    assert po_detail_resp.status_code == 200
    po_detail = po_detail_resp.json()
    assert po_detail["report_type"] == "Purchase Orders"
    assert po_detail["has_snapshot"] is True
    assert isinstance(po_detail["snapshot"], list)
    if len(po_detail["snapshot"]) > 0:
        first_po = po_detail["snapshot"][0]
        for key in ["purchase_order_id", "reference_number", "supplier_id", "supplier_name", "order_date", "total_amount", "status", "items"]:
            assert key in first_po, f"Missing key {key} in PO snapshot"
        if len(first_po["items"]) > 0:
            first_poi = first_po["items"][0]
            for key in ["purchase_order_item_id", "product_id", "product_name", "sku", "quantity", "unit_price", "subtotal"]:
                assert key in first_poi, f"Missing key {key} in PO line item"
    print(f" [PASS] Purchase Orders detail verified with valid nested line items contract")

    # 8. Check Legacy Report Detail (ID 1)
    leg_resp = s.get(f"{BASE_URL}/api/reports/1", headers={"Authorization": f"Bearer {owner_token}"})
    assert leg_resp.status_code == 200
    leg_data = leg_resp.json()
    assert leg_data["has_snapshot"] is False
    assert leg_data["snapshot"] is None
    assert "Historical snapshot data is unavailable" in leg_data["message"]
    print(" [PASS] Legacy report detail preserves unavailable-snapshot message")

    # 9. Verify CSV Export (Current balance)
    csv_resp = s.get(f"{BASE_URL}/api/reports/export?report_type=Inventory", headers={"Authorization": f"Bearer {owner_token}"})
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("Content-Type", "")
    print(" [PASS] Current balance CSV export remains functional")

    # 10. Check Frontend Static Server
    fe_resp = requests.get("http://localhost:8000/index.html")
    assert fe_resp.status_code == 200
    assert "js/pages/reports.js?v=40" in fe_resp.text
    reports_js = requests.get("http://localhost:8000/js/pages/reports.js?v=40").text
    assert "Stock Transactions" in reports_js
    assert "Purchase Orders" in reports_js
    assert "openGenerateReportModal" in reports_js
    print(" [PASS] Frontend serves updated reports.js?v=40 with all Phase 4 features")

    print("\n>>> ALL LIVE HTTP PHASE 4 VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_live_verification()
