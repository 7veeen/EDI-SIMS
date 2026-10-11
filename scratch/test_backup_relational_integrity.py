import os
import sys
import json

def test_relational_integrity():
    backups_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "backups")
    assert os.path.exists(backups_dir), "Backups directory does not exist"
    
    # Get latest backup
    files = sorted([f for f in os.listdir(backups_dir) if f.endswith(".json")])
    assert len(files) > 0, "No backup files found"
    latest_file = os.path.join(backups_dir, files[-1])
    print(f"Validating relational integrity of latest backup: {files[-1]}")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # 1. Categories & Products
    categories = {c["category_id"]: c for c in data.get("Categories", [])}
    products = {p["product_id"]: p for p in data.get("Products", [])}
    print(f"Categories: {len(categories)}, Products: {len(products)}")
    
    for p in data.get("Products", []):
        cat_id = p.get("category_id")
        if cat_id is not None:
            assert cat_id in categories, f"Product #{p.get('product_id')} references missing category #{cat_id}"
    print("PASS: Product -> Category foreign key integrity verified.")

    # 2. Roles & Users
    roles = {r["role_id"]: r for r in data.get("Roles", [])}
    users = {u["user_id"]: u for u in data.get("Users", [])}
    print(f"Roles: {len(roles)}, Users: {len(users)}")
    for u in data.get("Users", []):
        rid = u.get("role_id")
        if rid is not None:
            assert rid in roles, f"User #{u.get('user_id')} references missing role #{rid}"
    print("PASS: User -> Role foreign key integrity verified.")

    # 3. Inventory & Products
    for inv in data.get("Inventory", []):
        pid = inv.get("product_id")
        if pid is not None:
            assert pid in products, f"Inventory item #{inv.get('inventory_id')} references missing product #{pid}"
    print("PASS: Inventory -> Product foreign key integrity verified.")

    # 4. Suppliers & PurchaseOrders
    suppliers = {s["supplier_id"]: s for s in data.get("Suppliers", [])}
    pos = {po["purchase_order_id"]: po for po in data.get("PurchaseOrders", [])}
    print(f"Suppliers: {len(suppliers)}, Purchase Orders: {len(pos)}")

    # 5. PurchaseOrderItems & PurchaseOrders & Products
    for poi in data.get("PurchaseOrderItems", []):
        poid = poi.get("purchase_order_id")
        pid = poi.get("product_id")
        if poid is not None:
            assert poid in pos, f"PO Item #{poi.get('purchase_order_item_id')} references missing PO #{poid}"
        if pid is not None:
            assert pid in products, f"PO Item #{poi.get('purchase_order_item_id')} references missing Product #{pid}"
    print("PASS: PurchaseOrderItem -> PurchaseOrder & Product integrity verified.")

    # 6. Shipments & PurchaseOrders
    for shp in data.get("Shipments", []):
        poid = shp.get("purchase_order_id")
        if poid is not None:
            assert poid in pos, f"Shipment #{shp.get('shipment_id')} references missing PO #{poid}"
    print("PASS: Shipment -> PurchaseOrder integrity verified.")

    print("\nALL RELATIONAL INTEGRITY CHECKS PASSED FOR BACKUP ARTIFACT!")

if __name__ == "__main__":
    test_relational_integrity()
