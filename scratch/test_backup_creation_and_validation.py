import os
import sys
import json
import requests

BASE_URL = "http://127.0.0.1:5000"

def get_token(username, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

def test_backup():
    print("=== 1. RBAC TESTING ON /api/backups/ ===")
    # Anonymous GET & POST
    r_anon_get = requests.get(f"{BASE_URL}/api/backups/")
    print(f"Anon GET -> HTTP {r_anon_get.status_code} (Expected 401)")
    assert r_anon_get.status_code == 401

    r_anon_post = requests.post(f"{BASE_URL}/api/backups/", json={})
    print(f"Anon POST -> HTTP {r_anon_post.status_code} (Expected 401)")
    assert r_anon_post.status_code == 401

    # Supplier GET & POST
    sup_token = get_token("demo_supplier", "password123")
    r_sup_get = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {sup_token}"})
    print(f"Supplier GET -> HTTP {r_sup_get.status_code} (Expected 403)")
    assert r_sup_get.status_code == 403

    r_sup_post = requests.post(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {sup_token}"}, json={})
    print(f"Supplier POST -> HTTP {r_sup_post.status_code} (Expected 403)")
    assert r_sup_post.status_code == 403

    # Employee GET & POST
    emp_token = get_token("demo_employee", "password123")
    r_emp_get = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {emp_token}"})
    print(f"Employee GET -> HTTP {r_emp_get.status_code} (Expected 403)")
    assert r_emp_get.status_code == 403

    # Manager GET & POST
    mgr_token = get_token("demo_manager", "password123")
    r_mgr_get = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {mgr_token}"})
    print(f"Manager GET -> HTTP {r_mgr_get.status_code} (Expected 403)")
    assert r_mgr_get.status_code == 403

    print("RBAC Checks: PASSED\n")

    print("=== 2. OWNER BACKUP CREATION (POST /api/backups/) ===")
    owner_token = get_token("demo_owner", "password123")
    r_create = requests.post(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {owner_token}"}, json={"created_by": 5})
    print(f"Owner POST -> HTTP {r_create.status_code}")
    assert r_create.status_code == 201, f"Expected 201, got {r_create.status_code}: {r_create.text}"
    
    backup_meta = r_create.json()
    print("Backup Response:")
    print(json.dumps(backup_meta, indent=2))

    assert backup_meta.get("status") == "Success"
    assert "file_path" in backup_meta
    assert "backup_id" in backup_meta
    assert "backup_name" in backup_meta

    file_path = backup_meta["file_path"]
    print(f"\nVerifying artifact existence at: {file_path}")
    assert os.path.exists(file_path), f"Backup file does not exist at {file_path}"
    file_size = os.path.getsize(file_path)
    print(f"File size on disk: {file_size} bytes")
    assert file_size > 0, "Backup file is empty"

    print("\n=== 3. BACKUP ARTIFACT INTEGRITY & SCHEMA COVERAGE ===")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict), "Backup content must be a JSON object"
    tables_in_backup = list(data.keys())
    print(f"Tables captured in backup ({len(tables_in_backup)} tables):")
    for t in sorted(tables_in_backup):
        print(f"  - {t}: {len(data[t])} records")

    expected_core_tables = [
        "AuditLogs", "Categories", "Inventory", "Notifications",
        "OrderStatusHistory", "Products", "PurchaseOrderItems",
        "PurchaseOrders", "Reports", "Roles", "Shipments",
        "StockRequestItems", "StockRequests", "StockTransactions",
        "SupplierQuotations", "Suppliers", "SystemStatus", "Users"
    ]
    for ct in expected_core_tables:
        assert ct in data, f"Core table {ct} missing from backup artifact"
    print("Core tables coverage: 100% VERIFIED\n")

    print("=== 4. BACKUP LISTING VERIFICATION (GET /api/backups/) ===")
    r_list = requests.get(f"{BASE_URL}/api/backups/", headers={"Authorization": f"Bearer {owner_token}"})
    assert r_list.status_code == 200
    backups_list = r_list.json()
    print(f"Total backups returned in history: {len(backups_list)}")
    assert len(backups_list) > 0
    latest = backups_list[0]
    print(f"Latest backup in history: {latest}")
    assert latest["backup_id"] == backup_meta["backup_id"]
    assert latest["backup_name"] == backup_meta["backup_name"]
    assert latest["status"] == "Success"
    print("Backup history listing: PASSED\n")

    print("ALL TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_backup()
