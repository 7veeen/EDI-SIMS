import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def login(username, password):
    url = f"{BASE_URL}/api/auth/login"
    payload = json.dumps({"username": username, "password": password}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('access_token') or data.get('token')
    except Exception as e:
        print(f"Login failed for {username}: {e}")
        return None

def api_get(endpoint, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 500, str(e)

def run_tests():
    print("==================================================")
    print("TEST SUITE: MANAGER DASHBOARD ENHANCEMENTS")
    print("==================================================")

    # 1. Login as Manager
    print("\n[TEST 1] Manager Authentication & Dashboard Data Retrieval")
    manager_token = login("demo_manager", "password123")
    if not manager_token:
        # try manager1
        manager_token = login("manager1", "password123")
    assert manager_token, "Could not obtain Manager token"
    print("[OK] Manager authentication successful.")

    status, data = api_get("/api/dashboard/manager", manager_token)
    assert status == 200, f"Expected 200, got {status}: {data}"
    print("[OK] GET /api/dashboard/manager returned HTTP 200")

    # 2. Assert all required fields
    required_fields = [
        "active_pos",
        "pending_po_value",
        "low_stock_count",
        "pending_quotations",
        "pending_deliveries",
        "shipment_stats",
        "attention_items",
        "recent_orders",
        "critical_low_stock",
        "stock_requests_overview",
        "recent_stock_requests",
        "recent_stock_movement",
        "recent_transactions",
        "recent_activity"
    ]

    print("\n[TEST 2] Verifying All 14 Manager Dashboard Fields & Schema")
    for field in required_fields:
        assert field in data, f"Missing field in response: {field}"
        val = data[field]
        print(f"  - {field}: {type(val).__name__} = {repr(val)[:60]}...")
    print("[OK] All 14 required dashboard fields are present.")

    # 3. Check specific values & structures
    print("\n[TEST 3] Validating Live Data Types and Values")
    assert isinstance(data["active_pos"], int) and data["active_pos"] >= 0
    assert isinstance(data["pending_po_value"], (int, float)) and data["pending_po_value"] >= 0
    assert isinstance(data["low_stock_count"], int) and data["low_stock_count"] >= 0
    assert isinstance(data["pending_quotations"], int) and data["pending_quotations"] >= 0
    assert isinstance(data["pending_deliveries"], int) and data["pending_deliveries"] >= 0
    
    # shipment_stats
    ship_stats = data["shipment_stats"]
    assert "ready_for_shipment" in ship_stats
    assert "dispatched" in ship_stats
    assert "in_transit" in ship_stats
    assert "delayed" in ship_stats
    assert "delivered" in ship_stats
    assert "total" in ship_stats
    print("[OK] shipment_stats structure validated.")

    # attention_items
    assert isinstance(data["attention_items"], list)
    for item in data["attention_items"]:
        assert "type" in item
        assert "title" in item
        assert "description" in item
        assert "status" in item
        assert "action_label" in item
        assert "target_page" in item
    print(f"[OK] attention_items validated ({len(data['attention_items'])} items).")

    # recent_orders
    assert isinstance(data["recent_orders"], list)
    assert len(data["recent_orders"]) <= 5
    print(f"[OK] recent_orders validated ({len(data['recent_orders'])} items).")

    # critical_low_stock
    assert isinstance(data["critical_low_stock"], list)
    for p in data["critical_low_stock"]:
        assert "product_name" in p
        assert "quantity_available" in p
        assert "reorder_level" in p
    print(f"[OK] critical_low_stock validated ({len(data['critical_low_stock'])} items).")

    # stock_requests_overview
    sr_overview = data["stock_requests_overview"]
    assert "pending" in sr_overview
    assert "quoted" in sr_overview
    assert "rejected" in sr_overview
    print("[OK] stock_requests_overview validated.")

    # recent_activity
    assert isinstance(data["recent_activity"], list)
    print(f"[OK] recent_activity validated ({len(data['recent_activity'])} audit events).")

    # 4. RBAC Verification
    print("\n[TEST 4] Manager RBAC Enforcement")
    # Unauthenticated
    status_unauth, _ = api_get("/api/dashboard/manager", None)
    assert status_unauth == 401, f"Expected 401 for unauthenticated, got {status_unauth}"
    print("[OK] Unauthenticated request rejected with 401.")

    # Supplier token
    supplier_token = login("demo_supplier", "password123")
    if not supplier_token:
        supplier_token = login("supplier1", "password123")
    if supplier_token:
        status_sup, _ = api_get("/api/dashboard/manager", supplier_token)
        assert status_sup == 403, f"Expected 403 for Supplier role, got {status_sup}"
        print("[OK] Supplier role rejected with 403 Forbidden.")
    else:
        print("[SKIP] Skipped supplier login check (user not found).")

    # Employee token
    emp_token = login("demo_employee", "password123")
    if not emp_token:
        emp_token = login("employee1", "password123")
    if emp_token:
        status_emp, _ = api_get("/api/dashboard/manager", emp_token)
        assert status_emp == 403, f"Expected 403 for Employee role, got {status_emp}"
        print("[OK] Employee role rejected with 403 Forbidden.")
    else:
        print("[SKIP] Skipped employee login check (user not found).")

    # 5. Regression Check for Steps 1-6 APIs for Manager
    print("\n[TEST 5] Steps 1–6 Regression Verification for Manager")
    endpoints_to_check = [
        ("Step 1 (Inventory/Products)", "/api/inventory/"),
        ("Step 2 (Purchase Orders)", "/api/purchase-orders"),
        ("Step 3 (Quotations)", "/api/quotations"),
        ("Step 4 (Shipments)", "/api/shipments"),
        ("Step 5 (Stock Requests)", "/api/stock-requests/"),
        ("Step 6 (Stock Transactions)", "/api/inventory/transactions")
    ]

    for step_name, ep in endpoints_to_check:
        st, res = api_get(ep, manager_token)
        assert st in [200, 201], f"Regression failure in {step_name} ({ep}): HTTP {st}"
        count = len(res) if isinstance(res, list) else (len(res.get('items', [])) if isinstance(res, dict) else 'OK')
        print(f"[OK] {step_name}: HTTP {st} (records: {count})")

    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! (100% PASS RATE)")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
