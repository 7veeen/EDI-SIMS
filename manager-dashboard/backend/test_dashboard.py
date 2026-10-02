"""
SMART INVENTORY MANAGEMENT SYSTEM - MANAGER DASHBOARD
API Test Suite (Team 2)
Verifies all 10 endpoints against real Supabase database.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_dashboard_app

def run_tests():
    app = create_dashboard_app()
    app.config["TESTING"] = True
    client = app.test_client()

    print("=" * 65)
    print("RUNNING MANAGER DASHBOARD API TEST SUITE (REAL SUPABASE)")
    print("=" * 65)

    endpoints = [
        ("Health Check", "/api/manager/dashboard/health", "GET"),
        ("Summary Metrics", "/api/manager/dashboard/summary", "GET"),
        ("Inventory Overview", "/api/manager/dashboard/inventory-overview", "GET"),
        ("Procurement Overview", "/api/manager/dashboard/procurement-overview", "GET"),
        ("Pending Actions", "/api/manager/dashboard/pending-actions", "GET"),
        ("Low Stock Products", "/api/manager/dashboard/low-stock", "GET"),
        ("Recent Purchase Orders", "/api/manager/dashboard/recent-purchase-orders", "GET"),
        ("Recent Stock Transactions", "/api/manager/dashboard/recent-transactions", "GET"),
        ("Employee Overview", "/api/manager/dashboard/employees", "GET"),
        ("Supplier Overview", "/api/manager/dashboard/suppliers", "GET"),
        ("Notifications", "/api/manager/dashboard/notifications", "GET"),
    ]

    all_passed = True

    for name, path, method in endpoints:
        print(f"\n[TEST] {name} ({method} {path})")
        if method == "GET":
            res = client.get(path)
        
        status = res.status_code
        try:
            data = res.get_json()
        except Exception:
            data = res.data.decode('utf-8')

        success = (status == 200) and isinstance(data, dict) and data.get("success", False)

        if success:
            print(f"  --> PASS (HTTP {status})")
            if "data" in data:
                d = data["data"]
                if isinstance(d, dict):
                    keys = list(d.keys())
                    print(f"      Keys returned: {keys}")
                elif isinstance(d, list):
                    print(f"      Items returned: {len(d)}")
        else:
            print(f"  --> FAIL (HTTP {status}): {data}")
            all_passed = False

    print("\n" + "=" * 65)
    if all_passed:
        print("ALL MANAGER DASHBOARD APIS PASSED WITH REAL DATABASE DATA!")
    else:
        print("SOME TESTS FAILED - PLEASE REVIEW LOGS")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
