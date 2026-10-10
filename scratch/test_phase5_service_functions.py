import sys
sys.path.insert(0, 'backend')
import json
from decimal import Decimal
from datetime import date, datetime
from app.extensions import get_db_connection

def test_quotations_fetch(start_date=None, end_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
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
            WHERE 1=1
        """
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
                    "quotation_date": r[11].isoformat() if hasattr(r[11], 'isoformat') and r[11] else (str(r[11]) if r[11] else None),
                    "valid_until": r[14].isoformat() if hasattr(r[14], 'isoformat') and r[14] else (str(r[14]) if r[14] else None),
                    "status": r[15] or "Pending",
                    "notes": r[17] or "",
                    "submitted_at": r[18].isoformat() if hasattr(r[18], 'isoformat') and r[18] else (str(r[18]) if r[18] else None),
                    "approved_at": r[19].isoformat() if hasattr(r[19], 'isoformat') and r[19] else (str(r[19]) if r[19] else None),
                    "approved_by": r[20],
                    "approved_by_username": r[21] or "",
                    "rejection_reason": r[22] or "",
                    "ordered_by": r[23],
                    "ordered_by_username": r[24] or "",
                    "po_order_date": r[25].isoformat() if hasattr(r[25], 'isoformat') and r[25] else (str(r[25]) if r[25] else None),
                    "po_total": float(r[26]) if r[26] is not None else 0.0,
                    "po_status": r[27] or "",
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
    except Exception as e:
        return None, {"error": f"Database error: {str(e)}"}, 500
    finally:
        cursor.close()
        conn.close()


def test_supplier_performance_fetch(start_date=None, end_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Fetch all suppliers
        cursor.execute('''
            SELECT supplier_id, supplier_name, contact_person, email, phone, status
            FROM "Suppliers"
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
            FROM "PurchaseOrders"
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

        # Group PO metrics by supplier_id
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

            st_lower = st.lower()
            if st_lower in ("accepted", "completed"):
                sup_po["accepted_pos"] += cnt
            elif st_lower == "delivered":
                sup_po["delivered_pos"] += cnt
                sup_po["accepted_pos"] += cnt  # Delivered orders were previously accepted
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
            FROM "SupplierQuotations"
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
            # Responded: supplier submitted an offer or decision was reached
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
            FROM "Shipments"
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
        report_data = []
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

            # Calculate rates safely with clear denominators
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
    except Exception as e:
        return None, {"error": f"Database error: {str(e)}"}, 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    q_data, q_err, q_status = test_quotations_fetch()
    print("QUOTATIONS RESULT: Status =", q_status, "Count =", len(q_data) if q_data else 0)
    if q_data:
        print("Sample Quotation:", json.dumps(q_data[0], indent=2))

    sp_data, sp_err, sp_status = test_supplier_performance_fetch()
    print("\nSUPPLIER PERFORMANCE RESULT: Status =", sp_status, "Count =", len(sp_data) if sp_data else 0)
    if sp_data:
        print("Sample Supplier Performance:", json.dumps(sp_data[0], indent=2))
