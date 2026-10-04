import requests
import json
import sys

BASE_URL = "http://127.0.0.1:5000"

def get_token(username, password="password123"):
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    if res.status_code == 200:
        return res.json().get("access_token")
    return None

def test_all():
    print("=== Testing Owner Dashboard & Security ===")
    
    # 1. Login all roles
    owner_token = get_token("demo_owner")
    manager_token = get_token("demo_manager")
    employee_token = get_token("demo_employee")
    supplier_token = get_token("demo_supplier")
    
    assert owner_token, "Owner login failed"
    assert manager_token, "Manager login failed"
    assert employee_token, "Employee login failed"
    assert supplier_token, "Supplier login failed"
    print("[OK] All test accounts logged in successfully")
    
    # 2. Owner Dashboard RBAC
    # Anon -> 401
    r_anon = requests.get(f"{BASE_URL}/api/dashboard/owner")
    assert r_anon.status_code == 401, f"Expected 401 for anon, got {r_anon.status_code}"
    
    # Manager -> 403
    r_mgr = requests.get(f"{BASE_URL}/api/dashboard/owner", headers={"Authorization": f"Bearer {manager_token}"})
    assert r_mgr.status_code == 403, f"Expected 403 for manager, got {r_mgr.status_code}"
    
    # Employee -> 403
    r_emp = requests.get(f"{BASE_URL}/api/dashboard/owner", headers={"Authorization": f"Bearer {employee_token}"})
    assert r_emp.status_code == 403, f"Expected 403 for employee, got {r_emp.status_code}"
    # Supplier -> 403
    r_sup = requests.get(f"{BASE_URL}/api/dashboard/owner", headers={"Authorization": f"Bearer {supplier_token}"})
    assert r_sup.status_code == 403, f"Expected 403 for supplier, got {r_sup.status_code}"
    
    # Owner -> 200
    r_owner = requests.get(f"{BASE_URL}/api/dashboard/owner", headers={"Authorization": f"Bearer {owner_token}"})
    assert r_owner.status_code == 200, f"Expected 200 for owner, got {r_owner.status_code}"
    print("[OK] Owner Dashboard RBAC verified (Anon=401, Manager=403, Employee=403, Supplier=403, Owner=200)")
    
    resp_json = r_owner.json()
    dashboard_data = resp_json.get("data") if "data" in resp_json and isinstance(resp_json["data"], dict) else resp_json
    
    # Check original keys
    orig_keys = ["total_users", "total_suppliers", "total_products", "total_inventory_value", "recent_audits"]
    for k in orig_keys:
        assert k in dashboard_data, f"Missing original key: {k}"
    print(f"[OK] Original keys preserved: {orig_keys}")
    
    # Check new executive keys
    new_keys = [
        "active_pos_count", "active_pos_value", "total_pos_count",
        "pending_quotations_count", "low_stock_count", "out_of_stock_count",
        "active_users_count", "inactive_users_count", "users_by_role",
        "po_status_breakdown", "recent_orders", "shipment_stats",
        "inventory_health", "attention_items", "latest_backup", "system_status"
    ]
    for k in new_keys:
        assert k in dashboard_data, f"Missing new executive key: {k}"
    print(f"[OK] All new executive keys present: {new_keys}")
    
    print("\n--- Live Data Summary ---")
    print(f"Total Inventory Value: INR {dashboard_data['total_inventory_value']:,.2f}")
    print(f"Active POs: {dashboard_data['active_pos_count']} (Value: INR {dashboard_data['active_pos_value']:,.2f})")
    print(f"Pending Quotations: {dashboard_data['pending_quotations_count']}")
    print(f"Low Stock: {dashboard_data['low_stock_count']}, Out of Stock: {dashboard_data['out_of_stock_count']}")
    print(f"Users: {dashboard_data['total_users']} (Active: {dashboard_data['active_users_count']}, Inactive: {dashboard_data['inactive_users_count']})")
    print(f"Users by role: {dashboard_data['users_by_role']}")
    print(f"Shipment stats: {dashboard_data['shipment_stats']}")
    print(f"Inventory Health: {dashboard_data['inventory_health']}")
    print(f"Needs Attention Items Count: {len(dashboard_data['attention_items'])}")
    print(f"Latest Backup: {dashboard_data['latest_backup']}")
    print(f"Recent Audits Count: {len(dashboard_data['recent_audits'])}")
    
    # 3. Security Check: Audit Logs RBAC
    print("\n--- Testing Audit Logs RBAC ---")
    r = requests.get(f"{BASE_URL}/api/audit-logs/")
    assert r.status_code == 401, f"Audit logs anon expected 401, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {manager_token}"})
    assert r.status_code == 403, f"Audit logs manager expected 403, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {employee_token}"})
    assert r.status_code == 403, f"Audit logs employee expected 403, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {supplier_token}"})
    assert r.status_code == 403, f"Audit logs supplier expected 403, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/audit-logs/", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, f"Audit logs owner expected 200, got {r.status_code}"
    print("[OK] Audit logs RBAC verified (Anon=401, Manager=403, Employee=403, Supplier=403, Owner=200)")
    
    # 4. Security Check: Backups RBAC
    print("\n--- Testing Backups RBAC ---")
    r = requests.get(f"{BASE_URL}/api/backups/")
    assert r.status_code == 401, f"Backups anon expected 401, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {manager_token}"})
    assert r.status_code == 403, f"Backups manager expected 403, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {employee_token}"})
    assert r.status_code == 403, f"Backups employee expected 403, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {supplier_token}"})
    assert r.status_code == 403, f"Backups supplier expected 403, got {r.status_code}"
    r = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {owner_token}"})
    assert r.status_code == 200, f"Backups owner expected 200, got {r.status_code}"
    print("[OK] Backups RBAC verified (Anon=401, Manager=403, Employee=403, Supplier=403, Owner=200)")
    
    # 5. Regression Check: Steps 1-6 Endpoints for Owner
    print("\n--- Testing Steps 1-6 Regression Endpoints ---")
    headers = {"Authorization": f"Bearer {owner_token}"}
    endpoints = [
        ("/api/products/", "Products"),
        ("/api/inventory/", "Inventory"),
        ("/api/suppliers/", "Suppliers"),
        ("/api/stock-requests/", "Stock Requests"),
        ("/api/purchase-orders/", "Purchase Orders"),
        ("/api/quotations/", "Quotations"),
        ("/api/shipments/", "Shipments"),
        ("/api/inventory/transactions", "Stock Transactions"),
        ("/api/status/health", "System Health"),
        ("/api/users/", "Users"),
    ]
    for url, label in endpoints:
        r = requests.get(f"{BASE_URL}{url}", headers=headers)
        assert r.status_code in [200, 201], f"{label} failed with status {r.status_code}: {r.text[:100]}"
        print(f"[OK] {label} ({url}) returned {r.status_code}")
        
    print("\n==========================================")
    print("ALL TESTS PASSED WITH ZERO ERRORS!")
    print("==========================================")

if __name__ == "__main__":
    test_all()
