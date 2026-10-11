import os
import sys
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def get_token(username, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

def main():
    print("=== TEST 1: Public Liveness Ping ===")
    r1 = requests.get(f"{BASE_URL}/api/status/")
    print(f"GET /api/status/ -> HTTP {r1.status_code}: {r1.text}")
    assert r1.status_code == 200
    assert r1.json().get("status") == "UP"

    r2 = requests.get(f"{BASE_URL}/api/status")
    print(f"GET /api/status -> HTTP {r2.status_code}: {r2.text}")
    assert r2.status_code == 200
    assert r2.json().get("status") == "UP"

    print("\n=== TEST 2: Unauthenticated Health Check (Should be 401) ===")
    r_anon = requests.get(f"{BASE_URL}/api/status/health")
    print(f"GET /api/status/health (No Auth) -> HTTP {r_anon.status_code}: {r_anon.text}")
    assert r_anon.status_code == 401

    print("\n=== TEST 3: Unauthorized Role RBAC Rejection (Should be 403) ===")
    token_sup = get_token("demo_supplier", "password123")
    r_sup = requests.get(f"{BASE_URL}/api/status/health", headers={"Authorization": f"Bearer {token_sup}"})
    print(f"Supplier -> HTTP {r_sup.status_code}: {r_sup.text}")
    assert r_sup.status_code == 403

    token_emp = get_token("demo_employee", "password123")
    r_emp = requests.get(f"{BASE_URL}/api/status/health", headers={"Authorization": f"Bearer {token_emp}"})
    print(f"Employee -> HTTP {r_emp.status_code}: {r_emp.text}")
    assert r_emp.status_code == 403

    print("\n=== TEST 4: Authorized Role Access (Manager - Should be 200) ===")
    token_mgr = get_token("demo_manager", "password123")
    r_mgr = requests.get(f"{BASE_URL}/api/status/health", headers={"Authorization": f"Bearer {token_mgr}"})
    print(f"Manager -> HTTP {r_mgr.status_code}")
    assert r_mgr.status_code == 200
    mgr_data = r_mgr.json()
    print("Manager data keys:", list(mgr_data.keys()))
    print(f"Overall status: {mgr_data.get('overall_status')}")
    print(f"Database: {mgr_data.get('database')}")

    print("\n=== TEST 5: Authorized Role Access (Owner - Should be 200) ===")
    token_owner = get_token("demo_owner", "password123")
    r_owner = requests.get(f"{BASE_URL}/api/status/health", headers={"Authorization": f"Bearer {token_owner}"})
    print(f"Owner -> HTTP {r_owner.status_code}")
    assert r_owner.status_code == 200
    owner_data = r_owner.json()
    print(json.dumps(owner_data, indent=2))
    assert owner_data.get("backend", {}).get("status") == "UP"
    assert owner_data.get("database", {}).get("status") == "CONNECTED"
    assert "latency_ms" in owner_data.get("database", {})
    assert len(owner_data.get("modules", [])) >= 1

    print("\nALL LIVE API & RBAC TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
