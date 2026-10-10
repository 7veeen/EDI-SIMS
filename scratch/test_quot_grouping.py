import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.execute("""
    SELECT 
        q.quotation_id,
        q.quotation_number,
        q.purchase_order_id,
        q.supplier_id,
        s.supplier_name,
        s.contact_person,
        s.email AS supplier_email,
        s.phone AS supplier_phone,
        q.product_id,
        p.product_name,
        p.sku AS product_sku,
        q.quotation_date,
        q.quoted_price,
        q.quantity,
        q.valid_until,
        q.status,
        COALESCE(q.total_amount, (q.quoted_price * q.quantity)) AS line_total,
        q.notes,
        q.submitted_at,
        q.approved_at,
        q.approved_by,
        u.username AS approved_by_username,
        q.rejection_reason,
        po.ordered_by,
        pou.username AS ordered_by_username,
        po.order_date AS po_order_date,
        po.total_amount AS po_total,
        po.status AS po_status,
        poi.quantity AS original_po_quantity
    FROM "SupplierQuotations" q
    JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
    JOIN "Products" p ON q.product_id = p.product_id
    LEFT JOIN "PurchaseOrders" po ON q.purchase_order_id = po.purchase_order_id
    LEFT JOIN "PurchaseOrderItems" poi ON (po.purchase_order_id = poi.purchase_order_id AND q.product_id = poi.product_id)
    LEFT JOIN "Users" u ON q.approved_by = u.user_id
    LEFT JOIN "Users" pou ON po.ordered_by = pou.user_id
    ORDER BY q.quotation_date DESC, q.quotation_id DESC;
""")
rows = cur.fetchall()
print("Total rows fetched:", len(rows))

# Let us check grouping logic
grouped = {}
for r in rows:
    qid = r[0]
    q_num = r[1]
    # Key: if q_num is present, use q_num, else f'ID_{qid}'
    group_key = q_num if (q_num and q_num.strip()) else f"ID_{qid}"
    if group_key not in grouped:
        grouped[group_key] = {
            "quotation_id": qid,
            "quotation_number": q_num or f"QT-2026-{qid:04d}",
            "purchase_order_id": r[2],
            "supplier_id": r[3],
            "supplier_name": r[4],
            "contact_person": r[5] or "",
            "supplier_email": r[6] or "",
            "supplier_phone": r[7] or "",
            "quotation_date": str(r[11]) if r[11] else None,
            "valid_until": str(r[14]) if r[14] else None,
            "status": r[15] or "Pending",
            "notes": r[17] or "",
            "submitted_at": str(r[18]) if r[18] else None,
            "approved_at": str(r[19]) if r[19] else None,
            "approved_by": r[20],
            "approved_by_username": r[21] or "",
            "rejection_reason": r[22] or "",
            "ordered_by": r[23],
            "ordered_by_username": r[24] or "",
            "po_order_date": str(r[25]) if r[25] else None,
            "po_total": float(r[26]) if r[26] is not None else 0.0,
            "po_status": r[27] or "",
            "total_amount": 0.0,
            "items": []
        }
    
    qty = int(r[13]) if r[13] is not None else 0
    price = float(r[12]) if r[12] is not None else 0.0
    subtot = float(r[16]) if r[16] is not None and float(r[16]) > 0 else round(price * qty, 2)
    req_qty = int(r[28]) if r[28] is not None else None

    grouped[group_key]["total_amount"] = round(grouped[group_key]["total_amount"] + subtot, 2)
    grouped[group_key]["items"].append({
        "quotation_id": qid,
        "product_id": r[8],
        "product_name": r[9],
        "sku": r[10] or "",
        "requested_quantity": req_qty,
        "quoted_quantity": qty,
        "unit_price": price,
        "subtotal": subtot,
        "status": r[15],
        "notes": r[17] or ""
    })

print("Total unique grouped quotations:", len(grouped))
for k, v in list(grouped.items())[:5]:
    print(f"Quotation: {v['quotation_number']} (PO #{v['purchase_order_id']}, Supplier: {v['supplier_name']}), Items: {len(v['items'])}, Total: {v['total_amount']}, Status: {v['status']}")

cur.close()
conn.close()
