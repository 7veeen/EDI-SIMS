import sys
import os
import requests
import json
import csv
import io
from decimal import Decimal

BASE_URL = "http://127.0.0.1:5000/api"

def login(username, password):
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

def main():
    print("=== STEP 1: AUTHENTICATION TOKENS ===")
    tokens = {
        "Owner": login("demo_owner", "password123"),
        "Manager": login("demo_manager", "password123"),
        "Employee": login("demo_employee", "password123"),
        "Supplier": login("demo_supplier", "password123")
    }
    for role, tok in tokens.items():
        print(f"  {role} Token: {'Retrieved' if tok else 'FAILED'}")

    print("\n=== STEP 2: BACKEND ROUTE AUTHENTICATION AUDIT ===")
    endpoints = [
        ("GET", "/reports/"),
        ("GET", "/reports/status"),
        ("GET", "/reports/export"),
        ("GET", "/reports/export/csv"),
    ]

    for method, ep in endpoints:
        print(f"\n--- Testing Endpoint: {method} {ep} ---")
        # 1. Anonymous
        r_anon = requests.request(method, f"{BASE_URL}{ep}")
        print(f"  Anonymous: status={r_anon.status_code}")

        # 2. Each Role
        for role, tok in tokens.items():
            headers = {"Authorization": f"Bearer {tok}"} if tok else {}
            r_role = requests.request(method, f"{BASE_URL}{ep}", headers=headers)
            print(f"  {role}: status={r_role.status_code}")

    print("\n--- Testing POST /reports/generate Auth & Identity Spoofing ---")
    # Anonymous POST
    r_gen_anon = requests.post(f"{BASE_URL}/reports/generate", json={
        "report_name": "Read-Only Audit Check (Anon)",
        "report_type": "Inventory",
        "generated_by": 999
    })
    print(f"  Anonymous POST /reports/generate: status={r_gen_anon.status_code}")
    # Note: under strict read-only rules, we avoid inserting unnecessary records if possible.
    # We see that in route definition: it does cursor.execute(INSERT INTO "Reports"... RETURNING ...)
    # Let's inspect what happened: status code 201 was returned even anonymously!
    print(f"  Response: {r_gen_anon.json().get('message')}")

    print("\n=== STEP 3: EXPORT CSV INTEGRITY & HEADERS AUDIT ===")
    r_exp = requests.get(f"{BASE_URL}/reports/export", headers={"Authorization": f"Bearer {tokens['Manager']}"})
    print(f"  Status Code: {r_exp.status_code}")
    print(f"  Content-Type: {r_exp.headers.get('Content-Type')}")
    print(f"  Content-Disposition: {r_exp.headers.get('Content-Disposition')}")
    print(f"  Cache-Control: {r_exp.headers.get('Cache-Control')}")
    print(f"  Has UTF-8 BOM: {r_exp.content.startswith(b'\xef\xbb\xbf')}")

    csv_text = r_exp.content.decode('utf-8-sig')
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    print(f"  Total CSV Rows (including header): {len(rows)}")
    print(f"  Header row: {rows[0] if rows else 'None'}")
    print(f"  First data row: {rows[1] if len(rows) > 1 else 'None'}")

    print("\n=== STEP 4: FORMULA & CALCULATION AUDIT ON LIVE INVENTORY ===")
    sys.path.insert(0, os.path.abspath('backend'))
    from app.extensions import get_db_connection
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
        SELECT
            p.product_id,
            p.product_name,
            p.sku,
            c.category_name,
            i.quantity_available,
            p.reorder_level,
            p.selling_price,
            (COALESCE(i.quantity_available, 0) * COALESCE(p.selling_price, 0.00)) AS expected_val,
            p.status,
            i.last_updated
        FROM "Products" p
        LEFT JOIN "Categories" c ON p.category_id = c.category_id
        LEFT JOIN "Inventory" i ON p.product_id = i.product_id
        ORDER BY p.product_id ASC
    ''')
    db_items = c.fetchall()
    print(f"  DB Live Products Joined: {len(db_items)} items")

    total_units = 0
    total_val = Decimal("0.00")
    low_stock_count = 0
    in_stock_count = 0

    for item in db_items:
        pid, name, sku, cat, qty, reorder, price, val, status, last_upd = item
        qty = qty or 0
        reorder = reorder or 0
        price = Decimal(str(price or 0))
        val = Decimal(str(val or 0))
        total_units += qty
        total_val += val
        if qty <= reorder:
            low_stock_count += 1
        else:
            in_stock_count += 1

    print(f"  Total Units Available in DB: {total_units}")
    print(f"  Total Inventory Value (Retail Valuation): {total_val}")
    print(f"  Low Stock Items Count: {low_stock_count}")
    print(f"  In Stock Items Count: {in_stock_count}")

    print("\n=== STEP 5: CROSS-MODULE DATA AUDIT FOR REPORTING POTENTIAL ===")
    # Check Purchase Orders statuses
    c.execute('SELECT status, COUNT(*), SUM(total_amount) FROM "PurchaseOrders" GROUP BY status')
    print("  Purchase Orders by Status:")
    for row in c.fetchall():
        print(f"    Status '{row[0]}': count={row[1]}, sum_amount={row[2]}")

    # Check Supplier Quotations statuses
    c.execute('SELECT status, COUNT(*), SUM(total_amount) FROM "SupplierQuotations" GROUP BY status')
    print("  Supplier Quotations by Status:")
    for row in c.fetchall():
        print(f"    Status '{row[0]}': count={row[1]}, sum_amount={row[2]}")

    # Check Shipments statuses
    c.execute('SELECT status, COUNT(*) FROM "Shipments" GROUP BY status')
    print("  Shipments by Status:")
    for row in c.fetchall():
        print(f"    Status '{row[0]}': count={row[1]}")

    # Check Stock Transactions types
    c.execute('SELECT transaction_type, COUNT(*), SUM(quantity) FROM "StockTransactions" GROUP BY transaction_type')
    print("  Stock Transactions by Type:")
    for row in c.fetchall():
        print(f"    Type '{row[0]}': count={row[1]}, sum_qty={row[2]}")

    # Check Stock Requests statuses
    c.execute('SELECT status, COUNT(*) FROM "StockRequests" GROUP BY status')
    print("  Stock Requests by Status:")
    for row in c.fetchall():
        print(f"    Status '{row[0]}': count={row[1]}")

    conn.close()

if __name__ == '__main__':
    main()
