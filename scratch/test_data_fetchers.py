"""
test_data_fetchers.py
Test candidate SQL queries for Stock Transactions and Purchase Orders report snapshots.
"""
import os
import sys
import json
from decimal import Decimal

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extensions import get_db_connection

def test_fetch_stock_transactions():
    print("--- 1. Testing Stock Transactions Report Data Fetch ---")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    st.transaction_id,
                    st.product_id,
                    COALESCE(p.product_name, 'Unknown Product') AS product_name,
                    COALESCE(p.sku, 'N/A') AS sku,
                    st.transaction_type,
                    st.quantity,
                    st.transaction_date,
                    st.user_id,
                    COALESCE(u.username, CONCAT('User #', st.user_id::text)) AS performed_by,
                    st.purchase_order_id,
                    st.shipment_id,
                    sh.shipment_number,
                    st.notes
                FROM public."StockTransactions" st
                LEFT JOIN public."Products" p ON st.product_id = p.product_id
                LEFT JOIN public."Users" u ON st.user_id = u.user_id
                LEFT JOIN public."Shipments" sh ON st.shipment_id = sh.shipment_id
                ORDER BY st.transaction_date DESC, st.transaction_id DESC;
            """)
            rows = cur.fetchall()
            print(f"Total transactions fetched: {len(rows)}")
            
            data = []
            stock_in_qty = 0
            stock_out_qty = 0

            for r in rows:
                tx_type = str(r[4]).upper()
                qty = int(r[5])
                if tx_type in ('STOCK_IN', 'IN'):
                    stock_in_qty += qty
                elif tx_type in ('STOCK_OUT', 'OUT'):
                    stock_out_qty += qty

                tx_item = {
                    "transaction_id": r[0],
                    "product_id": r[1],
                    "product_name": r[2],
                    "sku": r[3],
                    "transaction_type": r[4],
                    "quantity": qty,
                    "transaction_date": r[6].isoformat() if hasattr(r[6], 'isoformat') else str(r[6]),
                    "user_id": r[7],
                    "performed_by": r[8],
                    "purchase_order_id": r[9],
                    "shipment_id": r[10],
                    "shipment_number": r[11],
                    "notes": r[12]
                }
                data.append(tx_item)

            print(f"Sample transaction #1: {json.dumps(data[0], indent=2)}")
            print(f"Summary: Total Transactions={len(data)}, Stock In={stock_in_qty}, Stock Out={stock_out_qty}")

def test_fetch_purchase_orders():
    print("\n--- 2. Testing Purchase Orders Report Data Fetch ---")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Fetch all PO headers
            cur.execute("""
                SELECT 
                    po.purchase_order_id,
                    po.supplier_id,
                    s.supplier_name,
                    s.contact_person,
                    s.email AS supplier_email,
                    s.phone AS supplier_phone,
                    po.ordered_by,
                    u.username AS ordered_by_username,
                    po.order_date,
                    po.expected_delivery,
                    po.total_amount,
                    po.status,
                    po.supplier_response,
                    po.supplier_response_date,
                    po.rejection_reason
                FROM public."PurchaseOrders" po
                LEFT JOIN public."Suppliers" s ON po.supplier_id = s.supplier_id
                LEFT JOIN public."Users" u ON po.ordered_by = u.user_id
                ORDER BY po.order_date DESC, po.purchase_order_id DESC;
            """)
            po_rows = cur.fetchall()
            print(f"Total POs fetched: {len(po_rows)}")

            # Fetch all PO items
            cur.execute("""
                SELECT 
                    poi.purchase_order_item_id,
                    poi.purchase_order_id,
                    poi.product_id,
                    COALESCE(p.product_name, 'Unknown Product') AS product_name,
                    COALESCE(p.sku, 'N/A') AS sku,
                    poi.quantity,
                    poi.unit_price,
                    poi.subtotal
                FROM public."PurchaseOrderItems" poi
                LEFT JOIN public."Products" p ON poi.product_id = p.product_id
                ORDER BY poi.purchase_order_id ASC, poi.purchase_order_item_id ASC;
            """)
            poi_rows = cur.fetchall()
            print(f"Total PO items fetched: {len(poi_rows)}")

            # Group items by purchase_order_id
            items_by_po = {}
            for item in poi_rows:
                p_id = item[1]
                if p_id not in items_by_po:
                    items_by_po[p_id] = []
                items_by_po[p_id].append({
                    "purchase_order_item_id": item[0],
                    "product_id": item[2],
                    "product_name": item[3],
                    "sku": item[4],
                    "quantity": int(item[5]),
                    "unit_price": float(item[6]) if item[6] is not None else 0.0,
                    "subtotal": float(item[7]) if item[7] is not None else 0.0
                })

            po_list = []
            status_counts = {}
            total_val = Decimal("0.00")

            for po in po_rows:
                p_id = po[0]
                items = items_by_po.get(p_id, [])
                amt = Decimal(str(po[10])) if po[10] is not None else Decimal("0.00")
                total_val += amt

                st = po[11] or 'Unknown'
                status_counts[st] = status_counts.get(st, 0) + 1

                po_entry = {
                    "purchase_order_id": p_id,
                    "reference_number": f"PO-{p_id}",
                    "supplier_id": po[1],
                    "supplier_name": po[2] or f"Supplier #{po[1]}",
                    "contact_person": po[3],
                    "supplier_email": po[4],
                    "supplier_phone": po[5],
                    "ordered_by": po[6],
                    "ordered_by_username": po[7] or f"User #{po[6]}",
                    "order_date": str(po[8]) if po[8] else None,
                    "expected_delivery": str(po[9]) if po[9] else None,
                    "total_amount": float(amt),
                    "status": po[11],
                    "supplier_response": po[12],
                    "supplier_response_date": po[13].isoformat() if hasattr(po[13], 'isoformat') and po[13] else (str(po[13]) if po[13] else None),
                    "rejection_reason": po[14],
                    "item_count": len(items),
                    "items": items
                }
                po_list.append(po_entry)

            print(f"Sample PO #1: {json.dumps(po_list[0], indent=2)}")
            print(f"Summary: Total POs={len(po_list)}, Total Value={float(total_val)}, Status Counts={status_counts}")

if __name__ == "__main__":
    test_fetch_stock_transactions()
    test_fetch_purchase_orders()
