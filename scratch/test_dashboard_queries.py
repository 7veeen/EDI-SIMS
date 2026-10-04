import os, psycopg2
from dotenv import load_dotenv

load_dotenv('backend/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

supplier_id = 5

# 1. Pending deliveries
cur.execute("""
    SELECT COUNT(*)
    FROM "Shipments"
    WHERE supplier_id = %s AND status NOT IN ('Delivered', 'Cancelled')
""", (supplier_id,))
pending_deliveries = cur.fetchone()[0]
print("Pending Deliveries:", pending_deliveries)

# 2. Shipment breakdown
cur.execute("""
    SELECT status, COUNT(*)
    FROM "Shipments"
    WHERE supplier_id = %s
    GROUP BY status
""", (supplier_id,))
ship_breakdown = dict(cur.fetchall())
print("Shipment breakdown:", ship_breakdown)

# Delayed count
cur.execute("""
    SELECT COUNT(*)
    FROM "Shipments"
    WHERE supplier_id = %s AND status NOT IN ('Delivered', 'Cancelled') AND expected_delivery < CURRENT_DATE
""", (supplier_id,))
delayed_count = cur.fetchone()[0]
print("Delayed Shipments:", delayed_count)

# 3. Attention items
attention = []

# Stock requests
cur.execute("""
    SELECT sr.stock_request_id, sr.request_number, sr.priority, sr.required_date, sr.created_at,
           COALESCE((
               SELECT p.product_name 
               FROM "StockRequestItems" sri 
               JOIN "Products" p ON sri.product_id = p.product_id 
               WHERE sri.stock_request_id = sr.stock_request_id 
               LIMIT 1
           ), 'General Restock') as prod_name
    FROM "StockRequests" sr
    WHERE sr.supplier_id = %s AND sr.status IN ('Pending', 'Open')
    ORDER BY CASE WHEN sr.priority = 'Urgent' THEN 1 WHEN sr.priority = 'High' THEN 2 ELSE 3 END, sr.created_at DESC
    LIMIT 5
""", (supplier_id,))
for sr in cur.fetchall():
    attention.append({
        "type": "stock_request",
        "id": sr[0],
        "ref": sr[1],
        "title": f"Stock Request {sr[1]} requires response",
        "description": f"Priority: {sr[2]} • Item: {sr[5]}",
        "date": sr[3].isoformat() if sr[3] else None,
        "status": "Pending",
        "priority": sr[2],
        "target": "stock-requests"
    })

# POs awaiting response
cur.execute("""
    SELECT po.purchase_order_id, po.order_date, po.total_amount, po.status, po.supplier_response
    FROM "PurchaseOrders" po
    WHERE po.supplier_id = %s AND (po.supplier_response = 'Pending' OR po.supplier_response IS NULL) AND po.status NOT IN ('Cancelled', 'Rejected', 'Delivered')
    ORDER BY po.order_date DESC
    LIMIT 5
""", (supplier_id,))
for po in cur.fetchall():
    attention.append({
        "type": "purchase_order",
        "id": po[0],
        "ref": f"PO-{po[0]}",
        "title": f"PO #{po[0]} is awaiting your acceptance",
        "description": f"Order value: ₹{float(po[2]):,.2f} • Date: {po[1]}",
        "date": po[1].isoformat() if po[1] else None,
        "status": "Awaiting Response",
        "priority": "High",
        "target": "purchase-orders"
    })

# Delayed shipments
cur.execute("""
    SELECT s.shipment_id, s.shipment_number, s.expected_delivery, s.status, s.purchase_order_id
    FROM "Shipments" s
    WHERE s.supplier_id = %s AND s.status NOT IN ('Delivered', 'Cancelled') AND s.expected_delivery < CURRENT_DATE
    ORDER BY s.expected_delivery ASC
    LIMIT 5
""", (supplier_id,))
for s in cur.fetchall():
    attention.append({
        "type": "shipment_delayed",
        "id": s[0],
        "ref": s[1],
        "title": f"Shipment {s[1]} is past expected delivery date",
        "description": f"Target was {s[2]} • Associated with PO #{s[4]}",
        "date": s[2].isoformat() if s[2] else None,
        "status": "Delayed",
        "priority": "Urgent",
        "target": "shipments"
    })

print(f"\nGenerated {len(attention)} attention items for supplier {supplier_id}:")
for a in attention:
    print(" ", a)

# 4. Recent activity from OrderStatusHistory
cur.execute("""
    SELECT history_id, purchase_order_id, shipment_id, status, previous_status, action, notes, changed_by, created_at
    FROM "OrderStatusHistory"
    WHERE supplier_id = %s
    ORDER BY created_at DESC
    LIMIT 5
""", (supplier_id,))
history = cur.fetchall()
print(f"\nFound {len(history)} history entries for supplier {supplier_id}:")
for h in history:
    print(" ", h)

cur.close()
conn.close()
