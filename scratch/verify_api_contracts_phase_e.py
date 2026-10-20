import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

def get_token(username, password):
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None

def test_api_safeguards():
    print("=== NON-DESTRUCTIVE API CONTRACT & SAFEGUARD VERIFICATION ===")
    
    # 1. Auth Tokens
    owner_token = get_token("demo_owner", "password123")
    supplier_token = get_token("demo_supplier", "password123")
    employee_token = get_token("demo_employee", "password123")
    
    assert owner_token, "Failed to authenticate demo_owner"
    assert supplier_token, "Failed to authenticate demo_supplier"
    assert employee_token, "Failed to authenticate demo_employee"
    print("[PASS] Tokens retrieved for Owner, Supplier, and Employee.")

    # 2. RBAC check: Employee cannot create shipment (Role required: Supplier, Owner, Manager)
    emp_headers = {"Authorization": f"Bearer {employee_token}"}
    r = requests.post(f"{BASE_URL}/shipments/", json={"purchase_order_id": 99999}, headers=emp_headers)
    print(f"RBAC 1: Employee POST /api/shipments/ -> status={r.status_code} (Expected: 403)")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    # 3. RBAC check: Supplier cannot perform Stock-In (Role required: Owner, Manager, Employee)
    sup_headers = {"Authorization": f"Bearer {supplier_token}"}
    r = requests.post(f"{BASE_URL}/inventory/stock-in", json={"shipment_id": 1, "product_id": 1, "quantity": 1}, headers=sup_headers)
    print(f"RBAC 2: Supplier POST /api/inventory/stock-in -> status={r.status_code} (Expected: 403)")
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    # 4. Backend validation: Missing purchase_order_id
    own_headers = {"Authorization": f"Bearer {owner_token}"}
    r = requests.post(f"{BASE_URL}/shipments/", json={"carrier": "DHL"}, headers=own_headers)
    print(f"Validation 1: Missing PO ID -> status={r.status_code}, error={r.json().get('error')}")
    assert r.status_code == 400 and "purchase_order_id is required" in r.json().get("error", "")

    # 5. Backend validation: Non-existent purchase order
    r = requests.post(f"{BASE_URL}/shipments/", json={"purchase_order_id": 99999999}, headers=own_headers)
    print(f"Validation 2: Non-existent PO ID -> status={r.status_code}, error={r.json().get('error')}")
    assert r.status_code in (400, 404) and "not found" in r.json().get("error", "").lower()

    # 6. Backend validation: Empty items array
    r = requests.post(f"{BASE_URL}/shipments/", json={"purchase_order_id": 128, "items": []}, headers=own_headers)
    print(f"Validation 3: Empty items array -> status={r.status_code}, error={r.json().get('error')}")
    assert r.status_code == 400 and "non-empty list" in r.json().get("error", "")

    # 7. Backend validation: Items with zero/negative quantity
    r = requests.post(f"{BASE_URL}/shipments/", json={"purchase_order_id": 128, "items": [{"product_id": 1, "quantity": 0}]}, headers=own_headers)
    print(f"Validation 4: Zero quantity item -> status={r.status_code}, error={r.json().get('error')}")
    assert r.status_code == 400 and "greater than zero" in r.json().get("error", "")

    r = requests.post(f"{BASE_URL}/shipments/", json={"purchase_order_id": 128, "items": [{"product_id": 1, "quantity": -5}]}, headers=own_headers)
    print(f"Validation 5: Negative quantity item -> status={r.status_code}, error={r.json().get('error')}")
    assert r.status_code == 400 and "greater than zero" in r.json().get("error", "")

    # 8. Backend validation: Duplicate product IDs in items array
    r = requests.post(f"{BASE_URL}/shipments/", json={"purchase_order_id": 128, "items": [{"product_id": 1, "quantity": 5}, {"product_id": 1, "quantity": 5}]}, headers=own_headers)
    print(f"Validation 6: Duplicate product IDs -> status={r.status_code}, error={r.json().get('error')}")
    assert r.status_code == 400 and "Duplicate product ID" in r.json().get("error", "")

    # 9. Read-only check: Existing shipment details structure
    r = requests.get(f"{BASE_URL}/shipments/1", headers=own_headers)
    print(f"Read-only Shipment Details (shipment_id=1): status={r.status_code}")
    if r.status_code == 200:
        shp = r.json().get("shipment", {})
        print(f"  Shipment Number: {shp.get('shipment_number')}")
        print(f"  Receiving Status: {shp.get('receiving_status')}")
        po_items = (shp.get("purchase_order") or {}).get("items", [])
        print(f"  Joined items count: {len(po_items)}")
        if po_items:
            print(f"  Sample item keys: {list(po_items[0].keys())}")

    # 10. Read-only check: PO line items calculation for allocated and remaining
    r = requests.get(f"{BASE_URL}/purchase-orders/128", headers=own_headers)
    print(f"Read-only PO Details (purchase_order_id=128): status={r.status_code}")
    if r.status_code == 200:
        po = r.json().get("purchase_order", {})
        po_items = po.get("items", [])
        print(f"  PO items count: {len(po_items)}")
        for it in po_items:
            print(f"  Item product_id={it.get('product_id')}, quantity={it.get('quantity')}, allocated={it.get('allocated_quantity')}, remaining={it.get('remaining_quantity')}")

    print("\n[PASS] ALL NON-DESTRUCTIVE SAFEGUARD AND VALIDATION CHECKS PASSED (100%)")

if __name__ == "__main__":
    test_api_safeguards()
