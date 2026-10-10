import sys
import os
from decimal import Decimal
sys.path.insert(0, os.path.abspath('backend'))
from app.extensions import get_db_connection
from app.services.team3.report_service import fetch_inventory_report_data

def main():
    conn = get_db_connection()
    c = conn.cursor()

    print("=== 1. INVENTORY TABLE COLUMNS ===")
    c.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'Inventory'
        ORDER BY ordinal_position
    """)
    for r in c.fetchall():
        print(f"  {r[0]}: {r[1]} (nullable: {r[2]})")

    print("\n=== 2. PRODUCTS TABLE COLUMNS ===")
    c.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'Products'
        ORDER BY ordinal_position
    """)
    for r in c.fetchall():
        print(f"  {r[0]}: {r[1]} (nullable: {r[2]})")

    print("\n=== 3. LIVE REPORT DATA VS RAW DB DATA ===")
    report_items, error, status = fetch_inventory_report_data()
    print(f"fetch_inventory_report_data returned {len(report_items or [])} items (status {status})")

    c.execute('SELECT COUNT(*) FROM "Products"')
    prod_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM "Inventory"')
    inv_count = c.fetchone()[0]
    print(f"DB Products count: {prod_count}, DB Inventory count: {inv_count}")

    print("\nSample Report Items:")
    for item in (report_items or [])[:5]:
        print(f"  Product #{item['product_id']}: '{item['product_name']}', Qty: {item['quantity_available']}, Reorder: {item['reorder_level']}, Price: {item['unit_price']}, Value: {item['inventory_value']}, Status: {item['stock_status']}")

    print("\n=== 4. CHECK STOCK STATUS CONSISTENCY WITH ZERO QUANTITY ===")
    zero_items = [it for it in (report_items or []) if it['quantity_available'] == 0]
    print(f"Products with quantity_available == 0: {len(zero_items)}")
    for z in zero_items:
        print(f"  #{z['product_id']} {z['product_name']}: qty=0, stock_status='{z['stock_status']}'")

    print("\n=== 5. CHECK OTHER MODULES' DATA AVAILABLE FOR REPORTING ===")
    tables = [
        "Products", "Categories", "Inventory", "PurchaseOrders", "PurchaseOrderItems",
        "SupplierQuotations", "Shipments", "StockTransactions",
        "StockRequests", "StockRequestItems", "Suppliers", "Users", "AuditLogs",
        "Notifications", "SystemStatus", "Reports"
    ]
    for tbl in tables:
        try:
            c.execute(f'SELECT COUNT(*) FROM "{tbl}"')
            cnt = c.fetchone()[0]
            print(f"  Table '{tbl}': {cnt} records")
        except Exception as ex:
            conn.rollback()
            print(f"  Table '{tbl}': Error {ex}")

    conn.close()

if __name__ == '__main__':
    main()
