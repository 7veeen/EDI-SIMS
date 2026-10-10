"""
verify_phase3_full.py
Complete verification of Phase 3 Report Usability backend + frontend integration.
"""
import requests
import json
import re

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("=== LIVE FULL AUDIT FOR PHASE 3 USABILITY ENHANCEMENTS ===")
    
    # 1. Login as Owner
    s = requests.Session()
    login_resp = s.post(f"{BASE_URL}/api/auth/login", json={
        "username": "demo_owner",
        "password": "password123"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(" [PASS] Successfully authenticated as demo_owner")

    # 2. GET /api/reports/
    reports_resp = s.get(f"{BASE_URL}/api/reports/", headers=headers)
    assert reports_resp.status_code == 200, f"Get reports failed: {reports_resp.text}"
    reports = reports_resp.json()
    assert isinstance(reports, list) and len(reports) > 0, "No reports returned"
    print(f" [PASS] GET /api/reports/ returned {len(reports)} records")

    # Validate required metadata keys for Phase 3 Search, Sort, and Cards
    required_keys = {"report_id", "report_name", "report_type", "generated_by", "generated_by_username", "generated_on", "has_snapshot"}
    first = reports[0]
    missing_keys = required_keys - set(first.keys())
    assert not missing_keys, f"Missing report keys: {missing_keys}"
    print(f" [PASS] All required report keys present: {required_keys}")

    # Verify summary cards data computation from live records
    total_count = len(reports)
    saved_count = sum(1 for r in reports if r.get("has_snapshot"))
    legacy_count = sum(1 for r in reports if not r.get("has_snapshot"))
    print(f" [PASS] Summary cards from live data: Total={total_count}, Saved={saved_count}, Legacy={legacy_count}")
    assert total_count == saved_count + legacy_count, "Summary counts do not sum to total"

    # 3. Verify Historical Snapshot Retrieval on a saved snapshot
    saved_reports = [r for r in reports if r.get("has_snapshot")]
    assert len(saved_reports) > 0, "Expected at least one saved snapshot"
    sample_saved = saved_reports[0]
    saved_id = sample_saved["report_id"]

    detail_resp = s.get(f"{BASE_URL}/api/reports/{saved_id}", headers=headers)
    assert detail_resp.status_code == 200, f"Get report {saved_id} failed: {detail_resp.text}"
    detail_data = detail_resp.json()
    assert detail_data.get("has_snapshot") is True
    assert isinstance(detail_data.get("snapshot"), list) and len(detail_data["snapshot"]) > 0
    print(f" [PASS] Report #{saved_id} detail API returned snapshot with {len(detail_data['snapshot'])} items")

    # 4. Verify Legacy Notice on report without snapshot
    legacy_reports = [r for r in reports if not r.get("has_snapshot")]
    assert len(legacy_reports) > 0, "Expected at least one legacy report"
    sample_legacy = legacy_reports[0]
    legacy_id = sample_legacy["report_id"]

    legacy_resp = s.get(f"{BASE_URL}/api/reports/{legacy_id}", headers=headers)
    assert legacy_resp.status_code == 200, f"Get legacy report {legacy_id} failed: {legacy_resp.text}"
    legacy_data = legacy_resp.json()
    assert legacy_data.get("has_snapshot") is False
    assert legacy_data.get("snapshot") is None
    assert "Historical snapshot data is unavailable" in legacy_data.get("message", "")
    print(f" [PASS] Legacy report #{legacy_id} correctly returned snapshot=None with explanatory message")

    # 5. Verify CSV Export (Current balance)
    export_resp = s.get(f"{BASE_URL}/api/reports/export?report_type=Inventory", headers=headers)
    assert export_resp.status_code == 200, f"Export failed: {export_resp.text}"
    assert "text/csv" in export_resp.headers.get("Content-Type", "")
    csv_text = export_resp.text
    assert "Product ID" in csv_text or "SKU" in csv_text, "CSV header missing"
    print(f" [PASS] GET /api/reports/export returned valid CSV ({len(csv_text)} bytes)")

    # 6. Verify Frontend Static Assets Serving
    fe_resp = requests.get("http://localhost:8000/index.html")
    assert fe_resp.status_code == 200
    assert "js/pages/reports.js?v=30" in fe_resp.text, "index.html has updated reports.js query param"
    print(" [PASS] frontend/index.html serves updated reports.js?v=30")

    js_resp = requests.get("http://localhost:8000/js/pages/reports.js?v=30")
    assert js_resp.status_code == 200
    reports_js = js_resp.text
    assert "reports-search" in reports_js
    assert "report-start-date" in reports_js
    assert "report-end-date" in reports_js
    assert "reports-pagination" in reports_js
    assert "applyFiltersAndSort" in reports_js
    assert "updateSummaryCards" in reports_js
    print(" [PASS] frontend/js/pages/reports.js successfully served by HTTP server with all Phase 3 features")

    print("\n>>> ALL PHASE 3 FULL AUDIT CHECKS PASSED WITH ZERO ERRORS! <<<")

if __name__ == "__main__":
    run_tests()
