import csv
import io
import json
from datetime import datetime
from decimal import Decimal

from app.extensions import get_db_connection


def check_inventory_status():
    """
    Checks the status of the Inventory module in the SystemStatus table.
    Returns:
        (status_info_dict, None, 200) on success,
        (None, {"error": "..."}, 404/500) on error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT status, progress, message, updated_at
            FROM "SystemStatus"
            WHERE module_name = 'Inventory'
        ''')
        row = cursor.fetchone()
        if row is None:
            return None, {"error": "Inventory status not found"}, 404

        status_info = {
            "status": row[0],
            "progress": row[1],
            "message": row[2],
            "updated_at": row[3]
        }
        return status_info, None, 200
    except Exception:
        return None, {"error": "Database error while checking inventory status"}, 500
    finally:
        cursor.close()
        conn.close()


def get_reports_metadata():
    """
    Retrieves the list of generated reports metadata from the Reports table.
    Returns:
        (reports_list, None, 200) on success,
        (None, {"error": "..."}, 500) on error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT
                r.report_id,
                r.report_name,
                r.report_type,
                r.generated_by,
                r.generated_on,
                u.username,
                (r.report_data IS NOT NULL) AS has_snapshot
            FROM "Reports" r
            LEFT JOIN "Users" u ON r.generated_by = u.user_id
            ORDER BY r.report_id DESC
        ''')
        rows = cursor.fetchall()
        reports = []
        for row in rows:
            reports.append({
                "report_id": row[0],
                "report_name": row[1],
                "report_type": row[2],
                "generated_by": row[3],
                "generated_on": row[4],
                "generated_by_username": row[5] or f"User #{row[3]}",
                "has_snapshot": bool(row[6])
            })
        return reports, None, 200
    except Exception:
        return None, {"error": "Database error while fetching reports list"}, 500
    finally:
        cursor.close()
        conn.close()


def fetch_inventory_report_data():
    """
    Queries current live inventory items with product details, category, available stock,
    reorder level, unit price, and calculated inventory value.
    Validates that the Inventory module is in 'READY' status first.
    Returns:
        (report_data_list, None, 200) on success,
        (None, error_dict, 423/404/500) on lock or error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check whether inventory module is ready
        cursor.execute('''
            SELECT status, progress, message
            FROM "SystemStatus"
            WHERE module_name = 'Inventory'
        ''')
        status_row = cursor.fetchone()
        if status_row is None:
            return None, {"error": "Inventory status not found"}, 404

        inventory_status, progress, message = status_row[0], status_row[1], status_row[2]

        if inventory_status != "READY":
            return None, {
                "error": "Report generation locked",
                "status": inventory_status,
                "progress": progress,
                "message": message
            }, 423

        cursor.execute('''
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                COALESCE(c.category_name, 'Uncategorized') AS category_name,
                COALESCE(i.quantity_available, 0) AS quantity_available,
                COALESCE(p.reorder_level, 0) AS reorder_level,
                COALESCE(p.selling_price, 0.00) AS selling_price,
                (COALESCE(i.quantity_available, 0) * COALESCE(p.selling_price, 0.00)) AS inventory_value,
                COALESCE(p.status, 'Unknown') AS status,
                i.last_updated
            FROM public."Products" p
            LEFT JOIN public."Categories" c
                ON p.category_id = c.category_id
            LEFT JOIN public."Inventory" i
                ON p.product_id = i.product_id
            ORDER BY p.product_id ASC
        ''')

        rows = cursor.fetchall()
        report_data = []

        for row in rows:
            qty = int(row[4])
            reorder = int(row[5])
            unit_price = Decimal(str(row[6]))
            inv_value = Decimal(str(row[7]))
            stock_status = "LOW STOCK" if qty <= reorder else "IN STOCK"

            report_data.append({
                "product_id": row[0],
                "product_name": row[1],
                "sku": row[2],
                "category_name": row[3],
                "quantity_available": qty,
                "reorder_level": reorder,
                "unit_price": float(unit_price),
                "inventory_value": float(inv_value),
                "status": row[8],
                "stock_status": stock_status,
                "last_updated": row[9]
            })

        return report_data, None, 200

    except Exception:
        return None, {"error": "Database error while fetching inventory data"}, 500
    finally:
        cursor.close()
        conn.close()


SUPPORTED_REPORT_TYPES = ("Inventory", "Stock Transactions", "Purchase Orders", "Quotations", "Supplier Performance")


def fetch_stock_transactions_report_data():
    """
    Queries current stock transactions with product details, performed-by user,
    associated purchase orders, and shipment references.
    Returns:
        (report_data_list, None, 200) on success,
        (None, {"error": "..."}, 500) on database error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
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
            ORDER BY st.transaction_date DESC, st.transaction_id DESC
        ''')
        rows = cursor.fetchall()
        report_data = []
        for r in rows:
            tx_date_str = r[6].isoformat() if hasattr(r[6], 'isoformat') and r[6] else (str(r[6]) if r[6] else None)
            report_data.append({
                "transaction_id": r[0],
                "product_id": r[1],
                "product_name": r[2],
                "sku": r[3],
                "transaction_type": r[4],
                "quantity": int(r[5]),
                "transaction_date": tx_date_str,
                "user_id": r[7],
                "performed_by": r[8],
                "purchase_order_id": r[9],
                "shipment_id": r[10],
                "shipment_number": r[11],
                "notes": r[12]
            })
        return report_data, None, 200
    except Exception:
        return None, {"error": "Database error while fetching stock transactions data"}, 500
    finally:
        cursor.close()
        conn.close()


def fetch_purchase_orders_report_data():
    """
    Queries current purchase orders with supplier details, creator, and ordered line items.
    Returns:
        (report_data_list, None, 200) on success,
        (None, {"error": "..."}, 500) on database error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Fetch purchase order headers
        cursor.execute('''
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
            ORDER BY po.order_date DESC, po.purchase_order_id DESC
        ''')
        po_rows = cursor.fetchall()

        # Fetch all purchase order line items in a single query
        cursor.execute('''
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
            ORDER BY poi.purchase_order_id ASC, poi.purchase_order_item_id ASC
        ''')
        poi_rows = cursor.fetchall()

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

        report_data = []
        for po in po_rows:
            p_id = po[0]
            items = items_by_po.get(p_id, [])
            amt = float(po[10]) if po[10] is not None else 0.0
            resp_date_str = po[13].isoformat() if hasattr(po[13], 'isoformat') and po[13] else (str(po[13]) if po[13] else None)

            report_data.append({
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
                "total_amount": amt,
                "status": po[11],
                "supplier_response": po[12],
                "supplier_response_date": resp_date_str,
                "rejection_reason": po[14],
                "item_count": len(items),
                "items": items
            })

        return report_data, None, 200
    except Exception:
        return None, {"error": "Database error while fetching purchase orders data"}, 500
    finally:
        cursor.close()
        conn.close()


def fetch_quotations_report_data(start_date=None, end_date=None):
    """
    Queries current supplier quotations with supplier, product, PO creator, and line items.
    Groups items sharing quotation_number to prevent duplication while preserving line details.
    Returns:
        (report_data_list, None, 200) on success,
        (None, {"error": "..."}, 500) on database error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = '''
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
            FROM public."SupplierQuotations" q
            JOIN public."Suppliers" s ON q.supplier_id = s.supplier_id
            JOIN public."Products" p ON q.product_id = p.product_id
            LEFT JOIN public."PurchaseOrders" po ON q.purchase_order_id = po.purchase_order_id
            LEFT JOIN public."PurchaseOrderItems" poi ON (po.purchase_order_id = poi.purchase_order_id AND q.product_id = poi.product_id)
            LEFT JOIN public."Users" u ON q.approved_by = u.user_id
            LEFT JOIN public."Users" pou ON po.ordered_by = pou.user_id
            WHERE 1=1
        '''
        params = []
        if start_date:
            query += " AND q.quotation_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND q.quotation_date <= %s"
            params.append(end_date)

        query += " ORDER BY q.quotation_date DESC, q.quotation_id DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        grouped = {}
        for r in rows:
            qid = r[0]
            q_num = r[1]
            # Key: if quotation_number is present and not empty, group by it; else each qid is its own record
            group_key = q_num if (q_num and str(q_num).strip()) else f"ID_{qid}"
            if group_key not in grouped:
                q_date_str = r[11].isoformat() if hasattr(r[11], 'isoformat') and r[11] else (str(r[11]) if r[11] else None)
                v_until_str = r[14].isoformat() if hasattr(r[14], 'isoformat') and r[14] else (str(r[14]) if r[14] else None)
                sub_at_str = r[18].isoformat() if hasattr(r[18], 'isoformat') and r[18] else (str(r[18]) if r[18] else None)
                app_at_str = r[19].isoformat() if hasattr(r[19], 'isoformat') and r[19] else (str(r[19]) if r[19] else None)
                po_date_str = r[25].isoformat() if hasattr(r[25], 'isoformat') and r[25] else (str(r[25]) if r[25] else None)

                grouped[group_key] = {
                    "quotation_id": qid,
                    "quotation_number": q_num or f"QT-2026-{qid:04d}",
                    "purchase_order_id": r[2],
                    "supplier_id": r[3],
                    "supplier_name": r[4] or "Unknown Supplier",
                    "contact_person": r[5] or "",
                    "supplier_email": r[6] or "",
                    "supplier_phone": r[7] or "",
                    "quotation_date": q_date_str,
                    "valid_until": v_until_str,
                    "status": r[15] or "Pending",
                    "notes": r[17] or "",
                    "submitted_at": sub_at_str,
                    "approved_at": app_at_str,
                    "approved_by": r[20],
                    "approved_by_username": r[21] or "",
                    "rejection_reason": r[22] or "",
                    "ordered_by": r[23],
                    "ordered_by_username": r[24] or "",
                    "po_order_date": po_date_str,
                    "po_total": float(r[26]) if r[26] is not None else 0.0,
                    "po_status": r[27] or "",
                    "reporting_period": {
                        "start_date": start_date,
                        "end_date": end_date,
                        "scope": "period" if (start_date or end_date) else "all-time"
                    },
                    "total_amount": 0.0,
                    "item_count": 0,
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
                "status": r[15] or "Pending",
                "notes": r[17] or ""
            })
            grouped[group_key]["item_count"] = len(grouped[group_key]["items"])

        report_data = list(grouped.values())
        return report_data, None, 200
    except Exception:
        return None, {"error": "Database error while fetching quotations data"}, 500
    finally:
        cursor.close()
        conn.close()


def fetch_supplier_performance_report_data(start_date=None, end_date=None):
    """
    Computes transparent, explainable operational performance metrics for all suppliers
    using verified data across Suppliers, PurchaseOrders, SupplierQuotations, and Shipments.
    Returns:
        (report_data_list, None, 200) on success,
        (None, {"error": "..."}, 500) on database error.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Fetch all suppliers
        cursor.execute('''
            SELECT supplier_id, supplier_name, contact_person, email, phone, status
            FROM public."Suppliers"
            ORDER BY supplier_id ASC;
        ''')
        supplier_rows = cursor.fetchall()

        # 2. Fetch PO metrics per supplier without joins to prevent duplicate counting
        po_query = '''
            SELECT 
                supplier_id,
                status,
                supplier_response,
                COUNT(*) AS po_count,
                COALESCE(SUM(total_amount), 0) AS po_value
            FROM public."PurchaseOrders"
            WHERE 1=1
        '''
        po_params = []
        if start_date:
            po_query += " AND order_date >= %s"
            po_params.append(start_date)
        if end_date:
            po_query += " AND order_date <= %s"
            po_params.append(end_date)
        po_query += " GROUP BY supplier_id, status, supplier_response"

        cursor.execute(po_query, tuple(po_params))
        po_summary_rows = cursor.fetchall()

        po_data_by_sup = {}
        for r in po_summary_rows:
            sup_id = r[0]
            st = r[1]
            sup_resp = r[2]
            cnt = int(r[3])
            val = float(r[4])

            if sup_id not in po_data_by_sup:
                po_data_by_sup[sup_id] = {
                    "total_pos": 0,
                    "accepted_pos": 0,
                    "rejected_pos": 0,
                    "pending_pos": 0,
                    "delivered_pos": 0,
                    "total_po_value": 0.0,
                    "status_counts": {}
                }
            sup_po = po_data_by_sup[sup_id]
            sup_po["total_pos"] += cnt
            sup_po["total_po_value"] = round(sup_po["total_po_value"] + val, 2)
            sup_po["status_counts"][st] = sup_po["status_counts"].get(st, 0) + cnt

            st_lower = (st or "").lower()
            if st_lower in ("accepted", "completed"):
                sup_po["accepted_pos"] += cnt
            elif st_lower == "delivered":
                sup_po["delivered_pos"] += cnt
                sup_po["accepted_pos"] += cnt
            elif st_lower == "rejected":
                sup_po["rejected_pos"] += cnt
            elif st_lower in ("pending", "created"):
                sup_po["pending_pos"] += cnt

        # 3. Fetch Quotation metrics per supplier
        quot_query = '''
            SELECT 
                supplier_id,
                status,
                COUNT(*) AS quot_count,
                COALESCE(SUM(COALESCE(total_amount, (quoted_price * quantity))), 0) AS quot_value
            FROM public."SupplierQuotations"
            WHERE 1=1
        '''
        quot_params = []
        if start_date:
            quot_query += " AND quotation_date >= %s"
            quot_params.append(start_date)
        if end_date:
            quot_query += " AND quotation_date <= %s"
            quot_params.append(end_date)
        quot_query += " GROUP BY supplier_id, status"

        cursor.execute(quot_query, tuple(quot_params))
        quot_summary_rows = cursor.fetchall()

        quot_data_by_sup = {}
        for r in quot_summary_rows:
            sup_id = r[0]
            st = r[1] or "Pending"
            cnt = int(r[2])
            val = float(r[3])

            if sup_id not in quot_data_by_sup:
                quot_data_by_sup[sup_id] = {
                    "total_quotations": 0,
                    "responded_quotations": 0,
                    "approved_quotations": 0,
                    "rejected_quotations": 0,
                    "pending_quotations": 0,
                    "total_quoted_value": 0.0,
                    "status_counts": {}
                }
            sup_q = quot_data_by_sup[sup_id]
            sup_q["total_quotations"] += cnt
            sup_q["total_quoted_value"] = round(sup_q["total_quoted_value"] + val, 2)
            sup_q["status_counts"][st] = sup_q["status_counts"].get(st, 0) + cnt

            st_lower = st.lower()
            if st_lower in ("submitted", "under review", "approved", "accepted", "rejected"):
                sup_q["responded_quotations"] += cnt
            if st_lower in ("approved", "accepted"):
                sup_q["approved_quotations"] += cnt
            elif st_lower in ("rejected", "expired"):
                sup_q["rejected_quotations"] += cnt
            elif st_lower in ("pending", "draft"):
                sup_q["pending_quotations"] += cnt

        # 4. Fetch Shipment & Delivery Performance metrics
        ship_query = '''
            SELECT 
                supplier_id,
                status,
                expected_delivery,
                delivered_at
            FROM public."Shipments"
            WHERE 1=1
        '''
        ship_params = []
        if start_date:
            ship_query += " AND created_at >= %s"
            ship_params.append(start_date)
        if end_date:
            ship_query += " AND created_at <= %s"
            ship_params.append(end_date)

        cursor.execute(ship_query, tuple(ship_params))
        ship_rows = cursor.fetchall()

        ship_data_by_sup = {}
        for r in ship_rows:
            sup_id = r[0]
            st = r[1] or "Unknown"
            exp_date = r[2]
            deliv_at = r[3]

            if sup_id not in ship_data_by_sup:
                ship_data_by_sup[sup_id] = {
                    "total_shipments": 0,
                    "delivered_shipments": 0,
                    "pending_shipments": 0,
                    "measurable_deliveries": 0,
                    "on_time_deliveries": 0,
                    "late_deliveries": 0,
                    "delay_days_sum": 0,
                    "status_counts": {}
                }
            sup_s = ship_data_by_sup[sup_id]
            sup_s["total_shipments"] += 1
            sup_s["status_counts"][st] = sup_s["status_counts"].get(st, 0) + 1

            if st.lower() == "delivered":
                sup_s["delivered_shipments"] += 1
                if exp_date and deliv_at:
                    sup_s["measurable_deliveries"] += 1
                    actual_date = deliv_at.date() if hasattr(deliv_at, 'date') else deliv_at
                    delay = (actual_date - exp_date).days
                    sup_s["delay_days_sum"] += delay
                    if delay <= 0:
                        sup_s["on_time_deliveries"] += 1
                    else:
                        sup_s["late_deliveries"] += 1
            else:
                sup_s["pending_shipments"] += 1

        # 5. Assemble comprehensive supplier performance metrics
        metric_definitions = {
            "po_acceptance_rate": "Accepted and Delivered POs divided by Total POs. Represents share of orders accepted/fulfilled.",
            "quotation_response_rate": "Responded quotations (Submitted, Under Review, Approved, Accepted, Rejected) divided by Total Quotations.",
            "quotation_approval_rate": "Approved and Accepted quotations divided by Responded Quotations.",
            "on_time_delivery_rate": "Deliveries on or before expected delivery date divided by Measurable Deliveries (deliveries with both planned and actual delivery dates recorded).",
            "avg_delivery_delay_days": "Average days difference between actual delivery date and planned expected delivery date. Values <= 0 indicate on-schedule or early fulfillment."
        }

        period_info = {
            "start_date": start_date,
            "end_date": end_date,
            "scope": "period" if (start_date or end_date) else "all-time"
        }

        report_data = []
        for s in supplier_rows:
            sup_id = s[0]
            sup_name = s[1]
            contact = s[2] or ""
            email = s[3] or ""
            phone = s[4] or ""
            sup_status = s[5] or "Active"

            po_info = po_data_by_sup.get(sup_id, {
                "total_pos": 0,
                "accepted_pos": 0,
                "rejected_pos": 0,
                "pending_pos": 0,
                "delivered_pos": 0,
                "total_po_value": 0.0,
                "status_counts": {}
            })

            q_info = quot_data_by_sup.get(sup_id, {
                "total_quotations": 0,
                "responded_quotations": 0,
                "approved_quotations": 0,
                "rejected_quotations": 0,
                "pending_quotations": 0,
                "total_quoted_value": 0.0,
                "status_counts": {}
            })

            s_info = ship_data_by_sup.get(sup_id, {
                "total_shipments": 0,
                "delivered_shipments": 0,
                "pending_shipments": 0,
                "measurable_deliveries": 0,
                "on_time_deliveries": 0,
                "late_deliveries": 0,
                "delay_days_sum": 0,
                "status_counts": {}
            })

            tot_pos = po_info["total_pos"]
            acc_pos = po_info["accepted_pos"]
            po_acc_rate = round((acc_pos / tot_pos) * 100, 1) if tot_pos > 0 else None

            tot_q = q_info["total_quotations"]
            resp_q = q_info["responded_quotations"]
            app_q = q_info["approved_quotations"]
            rej_q = q_info["rejected_quotations"]

            q_resp_rate = round((resp_q / tot_q) * 100, 1) if tot_q > 0 else None
            q_app_rate = round((app_q / resp_q) * 100, 1) if resp_q > 0 else None
            q_rej_rate = round((rej_q / resp_q) * 100, 1) if resp_q > 0 else None

            meas_deliv = s_info["measurable_deliveries"]
            on_time_deliv = s_info["on_time_deliveries"]
            late_deliv = s_info["late_deliveries"]
            delay_sum = s_info["delay_days_sum"]

            on_time_rate = round((on_time_deliv / meas_deliv) * 100, 1) if meas_deliv > 0 else None
            avg_delay = round(delay_sum / meas_deliv, 1) if meas_deliv > 0 else None

            report_data.append({
                "supplier_id": sup_id,
                "supplier_name": sup_name,
                "contact_person": contact,
                "email": email,
                "phone": phone,
                "status": sup_status,
                "reporting_period": period_info,
                # Purchase Order Metrics
                "total_purchase_orders": tot_pos,
                "accepted_purchase_orders": acc_pos,
                "rejected_purchase_orders": po_info["rejected_pos"],
                "pending_purchase_orders": po_info["pending_pos"],
                "delivered_purchase_orders": po_info["delivered_pos"],
                "total_order_value": po_info["total_po_value"],
                "po_acceptance_rate": po_acc_rate,
                "po_status_breakdown": po_info["status_counts"],
                # Quotation Metrics
                "total_quotations": tot_q,
                "responded_quotations": resp_q,
                "approved_quotations": app_q,
                "rejected_quotations": rej_q,
                "pending_quotations": q_info["pending_quotations"],
                "total_quoted_value": q_info["total_quoted_value"],
                "quotation_response_rate": q_resp_rate,
                "quotation_approval_rate": q_app_rate,
                "quotation_rejection_rate": q_rej_rate,
                "quotation_status_breakdown": q_info["status_counts"],
                # Delivery Performance Metrics
                "total_shipments": s_info["total_shipments"],
                "delivered_shipments": s_info["delivered_shipments"],
                "pending_shipments": s_info["pending_shipments"],
                "measurable_deliveries": meas_deliv,
                "on_time_deliveries": on_time_deliv,
                "late_deliveries": late_deliv,
                "on_time_delivery_rate": on_time_rate,
                "avg_delivery_delay_days": avg_delay,
                "delivery_metrics_note": (
                    f"{meas_deliv} of {s_info['delivered_shipments']} delivered shipments have recorded planned delivery dates."
                    if s_info["delivered_shipments"] > 0 else "No completed deliveries found."
                ),
                "metric_definitions": metric_definitions
            })

        return report_data, None, 200
    except Exception:
        return None, {"error": "Database error while fetching supplier performance data"}, 500
    finally:
        cursor.close()
        conn.close()


def generate_report_record(report_name, report_type, generated_by, start_date=None, end_date=None):
    """
    Creates a new entry in the Reports metadata table for any supported report type.
    Persists the point-in-time data snapshot in report_data JSONB.
    Returns:
        (result_dict, None, 201) on success,
        (None, error_dict, 400/423/500) on failure.
    """
    if report_type not in SUPPORTED_REPORT_TYPES:
        return None, {
            "error": f"Invalid report type '{report_type}'. Supported types: {', '.join(SUPPORTED_REPORT_TYPES)}"
        }, 400

    if report_type == "Inventory":
        report_data, error, status_code = fetch_inventory_report_data()
    elif report_type == "Stock Transactions":
        report_data, error, status_code = fetch_stock_transactions_report_data()
    elif report_type == "Purchase Orders":
        report_data, error, status_code = fetch_purchase_orders_report_data()
    elif report_type == "Quotations":
        report_data, error, status_code = fetch_quotations_report_data(start_date=start_date, end_date=end_date)
    elif report_type == "Supplier Performance":
        report_data, error, status_code = fetch_supplier_performance_report_data(start_date=start_date, end_date=end_date)
    else:
        return None, {"error": "Unsupported report type"}, 400

    if error:
        return None, error, status_code

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        snapshot_json = json.dumps(report_data, default=str)
        cursor.execute('''
            INSERT INTO "Reports"
            (
                report_name,
                report_type,
                generated_by,
                report_data
            )
            VALUES (%s, %s, %s, %s::jsonb)
            RETURNING report_id, report_name, report_type, generated_by, generated_on, report_data
        ''', (
            report_name,
            report_type,
            generated_by,
            snapshot_json
        ))
        row = cursor.fetchone()
        conn.commit()

        result = {
            "message": "Report generated successfully",
            "report": {
                "report_id": row[0],
                "report_name": row[1],
                "report_type": row[2],
                "generated_by": row[3],
                "generated_on": row[4],
                "has_snapshot": True
            },
            "data": report_data
        }
        return result, None, 201

    except Exception:
        conn.rollback()
        return None, {"error": "Failed to create report record"}, 500
    finally:
        cursor.close()
        conn.close()


def generate_inventory_report_record(report_name, report_type, generated_by, start_date=None, end_date=None):
    """
    Backward-compatibility wrapper for generating reports.
    """
    return generate_report_record(report_name, report_type, generated_by, start_date=start_date, end_date=end_date)


def get_report_by_id(report_id):
    """
    Retrieves a single report by ID along with its snapshot (if available).
    Returns:
        (report_dict, None, 200) on success,
        (None, error_dict, 404/500) on failure.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT
                r.report_id,
                r.report_name,
                r.report_type,
                r.generated_by,
                r.generated_on,
                r.report_data,
                u.username
            FROM "Reports" r
            LEFT JOIN "Users" u ON r.generated_by = u.user_id
            WHERE r.report_id = %s
        ''', (report_id,))
        row = cursor.fetchone()
        if not row:
            return None, {"error": "Report not found"}, 404

        raw_snapshot = row[5]
        # In psycopg2, JSONB columns are automatically parsed into python dicts/lists.
        # If it happens to be a string in certain driver setups, parse it safely.
        if isinstance(raw_snapshot, str):
            try:
                snapshot_data = json.loads(raw_snapshot)
            except Exception:
                snapshot_data = None
        else:
            snapshot_data = raw_snapshot

        has_snapshot = snapshot_data is not None

        report = {
            "report_id": row[0],
            "report_name": row[1],
            "report_type": row[2],
            "generated_by": row[3],
            "generated_on": row[4],
            "generated_by_username": row[6] or f"User #{row[3]}",
            "has_snapshot": has_snapshot,
            "snapshot": snapshot_data,
            "message": None if has_snapshot else "Historical snapshot data is unavailable for this report"
        }
        return report, None, 200
    except Exception:
        return None, {"error": "Database error while fetching report details"}, 500
    finally:
        cursor.close()
        conn.close()



DANGEROUS_FORMULA_PREFIXES = ('=', '+', '-', '@')


def sanitize_csv_cell(value):
    """
    Sanitizes untrusted text values to prevent CSV / Formula Injection (CWE-1236).
    If a text value (after stripping any leading whitespace or control characters such as
    spaces, tabs, carriage returns, newlines) begins with '=', '+', '-', or '@',
    it is prepended with a single quote (') so spreadsheet applications (Excel, Calc, Sheets)
    treat it as literal text rather than executing it as an expression or macro.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        return value
    if not value:
        return value

    stripped = value.lstrip(' \t\r\n\v\f')
    if stripped and stripped.startswith(DANGEROUS_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def generate_inventory_csv_export(report_type="Inventory"):
    """
    Generates a live inventory report formatted as RFC 4180 compliant CSV with UTF-8 BOM encoding.
    Returns:
        ((csv_bytes, filename), None, 200) on success,
        (None, error_dict, 423/404/500) on failure.
    """
    report_data, error, status_code = fetch_inventory_report_data()
    if error:
        return None, error, status_code

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')

    # Column headers
    writer.writerow([
        "Product ID",
        "Product Name",
        "SKU",
        "Category",
        "Available Quantity",
        "Reorder Level",
        "Unit Price",
        "Inventory Value",
        "Stock Status",
        "Status",
        "Last Updated"
    ])

    for item in report_data:
        last_updated_str = "N/A"
        if item.get("last_updated"):
            try:
                last_updated_str = item["last_updated"].strftime("%Y-%m-%d %H:%M:%S")
            except AttributeError:
                last_updated_str = str(item["last_updated"])

        writer.writerow([
            item["product_id"],
            sanitize_csv_cell(item["product_name"]),
            sanitize_csv_cell(item["sku"]),
            sanitize_csv_cell(item["category_name"]),
            item["quantity_available"],
            item["reorder_level"],
            f"{item['unit_price']:.2f}",
            f"{item['inventory_value']:.2f}",
            item["stock_status"],
            sanitize_csv_cell(item["status"]),
            last_updated_str
        ])

    csv_text = output.getvalue()
    csv_bytes = csv_text.encode('utf-8-sig')

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"current_inventory_report_{timestamp_str}.csv"

    return (csv_bytes, filename), None, 200
