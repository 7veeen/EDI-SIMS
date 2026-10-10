import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def get_token(username, password="password123"):
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    if res.status_code == 200:
        data = res.json()
        return data.get("access_token") or data.get("token")
    return None

def main():
    print("==================================================", flush=True)
    print("REGRESSION TEST SUITE: STEPS 1 - 6 WORKFLOW VERIFICATION", flush=True)
    print("==================================================", flush=True)

    mgr_token = get_token("demo_manager")
    emp_token = get_token("demo_employee")
    own_token = get_token("demo_owner")
    sup_token = get_token("demo_supplier")

    assert mgr_token and emp_token and own_token and sup_token, "Failed to login test roles"

    headers_mgr = {"Authorization": f"Bearer {mgr_token}"}
    headers_emp = {"Authorization": f"Bearer {emp_token}"}
    headers_own = {"Authorization": f"Bearer {own_token}"}
    headers_sup = {"Authorization": f"Bearer {sup_token}"}

    # Step 1: Products & Inventory
    r_prod = requests.get(f"{BASE_URL}/api/products/", headers=headers_mgr)
    assert r_prod.status_code == 200, f"Step 1 Products failed: {r_prod.status_code}"
    print(f"[PASS] Step 1 - Products API returned 200 ({len(r_prod.json())} products)", flush=True)

    r_inv = requests.get(f"{BASE_URL}/api/inventory/", headers=headers_mgr)
    assert r_inv.status_code == 200, f"Step 1 Inventory failed: {r_inv.status_code}"
    print(f"[PASS] Step 1 - Inventory API returned 200 ({len(r_inv.json())} inventory items)", flush=True)

    # Step 2: Suppliers
    r_sup = requests.get(f"{BASE_URL}/api/suppliers/", headers=headers_mgr)
    assert r_sup.status_code == 200, f"Step 2 Suppliers failed: {r_sup.status_code}"
    print(f"[PASS] Step 2 - Suppliers API returned 200 ({len(r_sup.json())} suppliers)", flush=True)

    # Step 3: Purchase Orders
    r_po = requests.get(f"{BASE_URL}/api/purchase-orders/", headers=headers_mgr)
    assert r_po.status_code == 200, f"Step 3 POs failed: {r_po.status_code}"
    print(f"[PASS] Step 3 - Purchase Orders API returned 200 ({len(r_po.json())} POs)", flush=True)

    # Step 4: Quotations
    r_rfq = requests.get(f"{BASE_URL}/api/quotations/", headers=headers_mgr)
    assert r_rfq.status_code == 200, f"Step 4 Quotations failed: {r_rfq.status_code}"
    print(f"[PASS] Step 4 - Quotations API returned 200 ({len(r_rfq.json())} quotations)", flush=True)

    # Step 5: Shipments
    r_ship = requests.get(f"{BASE_URL}/api/shipments/", headers=headers_mgr)
    assert r_ship.status_code == 200, f"Step 5 Shipments failed: {r_ship.status_code}"
    print(f"[PASS] Step 5 - Shipments API returned 200 ({len(r_ship.json())} shipments)", flush=True)

    # Step 6: Stock Transactions History
    r_tx = requests.get(f"{BASE_URL}/api/inventory/transactions", headers=headers_mgr)
    assert r_tx.status_code == 200, f"Step 6 Stock Transactions failed: {r_tx.status_code}"
    print(f"[PASS] Step 6 - Stock Transactions API returned 200 ({len(r_tx.json())} transactions)", flush=True)

    # Step 6: Stock Requests
    r_sr = requests.get(f"{BASE_URL}/api/stock-requests/", headers=headers_mgr)
    assert r_sr.status_code == 200, f"Step 6 Stock Requests failed: {r_sr.status_code}"
    print(f"[PASS] Step 6 - Stock Requests API returned 200", flush=True)

    # Step 6: Employee Shipments Assigned View
    r_emp_ship = requests.get(f"{BASE_URL}/api/shipments/", headers=headers_emp)
    assert r_emp_ship.status_code == 200, f"Employee Shipments failed: {r_emp_ship.status_code}"
    print(f"[PASS] Step 6 - Employee Assigned Shipments returned 200 ({len(r_emp_ship.json())} items)", flush=True)

    # Step 6: Dashboards check
    r_dash_mgr = requests.get(f"{BASE_URL}/api/dashboard/manager", headers=headers_mgr)
    assert r_dash_mgr.status_code == 200, f"Manager Dashboard failed: {r_dash_mgr.status_code}"
    print("[PASS] Step 1-6 - Manager Dashboard returned 200", flush=True)

    r_dash_own = requests.get(f"{BASE_URL}/api/dashboard/owner", headers=headers_own)
    assert r_dash_own.status_code == 200, f"Owner Dashboard failed: {r_dash_own.status_code}"
    print("[PASS] Step 1-6 - Owner Dashboard returned 200", flush=True)

    print("==================================================", flush=True)
    print("ALL STEPS 1-6 REGRESSION TESTS PASSED CLEANLY!", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()
