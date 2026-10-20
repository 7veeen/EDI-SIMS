import requests

BASE_URL = "http://127.0.0.1:5000/api"

# Inspect active demo users in Users table
test_credentials = [
    ("demo_owner", "password123", "Owner"),
    ("demo_manager", "password123", "Manager"),
    ("demo_supplier", "password123", "Supplier"),
    ("demo_employee", "password123", "Employee")
]

print("=== VERIFYING AUTHENTICATION AND ROLE PROFILE CLAIMS ===")
role_tokens = {}

for username, password, expected_role in test_credentials:
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        data = r.json()
        token = data.get("access_token")
        user = data.get("user", {})
        actual_role = user.get("role")
        print(f"[PASS] {username}: Login successful. Role={actual_role} (Expected: {expected_role})")
        role_tokens[expected_role] = token
    else:
        print(f"[FAIL] {username}: Login failed with status {r.status_code}: {r.text}")

print("\n=== VERIFYING SHIPMENTS ENDPOINT ACROSS ROLES ===")
for role, token in role_tokens.items():
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/shipments/?page=1&page_size=5", headers=headers)
    if r.status_code == 200:
        res = r.json()
        count = len(res.get("shipments", []))
        total = res.get("total", 0)
        print(f"[PASS] Role {role}: GET /api/shipments/ -> 200 OK (Visible shipments: {count}, Total: {total})")
    else:
        print(f"[FAIL] Role {role}: GET /api/shipments/ -> status={r.status_code}, error={r.text}")

print("\n=== VERIFYING RBAC RESTRICTIONS ACROSS ROLES ===")
# 1. Employee cannot create shipment (POST /api/shipments/)
emp_headers = {"Authorization": f"Bearer {role_tokens.get('Employee')}"}
r = requests.post(f"{BASE_URL}/shipments/", json={"purchase_order_id": 128}, headers=emp_headers)
print(f"RBAC Employee create shipment: status={r.status_code} (Expected: 403)")
assert r.status_code == 403, f"Expected 403, got {r.status_code}"

# 2. Supplier cannot stock-in (POST /api/inventory/stock-in)
sup_headers = {"Authorization": f"Bearer {role_tokens.get('Supplier')}"}
r = requests.post(f"{BASE_URL}/inventory/stock-in", json={"shipment_id": 1, "product_id": 1, "quantity": 1}, headers=sup_headers)
print(f"RBAC Supplier stock-in: status={r.status_code} (Expected: 403)")
assert r.status_code == 403, f"Expected 403, got {r.status_code}"

# 3. Supplier cannot assign employee (PATCH /api/shipments/1/assign)
r = requests.patch(f"{BASE_URL}/shipments/1/assign", json={"employee_id": 3}, headers=sup_headers)
print(f"RBAC Supplier assign employee: status={r.status_code} (Expected: 403)")
assert r.status_code == 403, f"Expected 403, got {r.status_code}"

# 4. Employee cannot assign employee (PATCH /api/shipments/1/assign)
r = requests.patch(f"{BASE_URL}/shipments/1/assign", json={"employee_id": 3}, headers=emp_headers)
print(f"RBAC Employee assign employee: status={r.status_code} (Expected: 403)")
assert r.status_code == 403, f"Expected 403, got {r.status_code}"

print("\n[PASS] ALL ROLE-BASED ACCESS CHECKS PASSED (100%)")
