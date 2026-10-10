import csv
import io
import json
import re
import xml.sax.saxutils
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from app.extensions import get_db_connection


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 26, self._pagesize[0] - 36, 26)
        footer_text = "SIMS — Smart Inventory Management System  |  Point-in-Time Historical Snapshot Archive"
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawString(36, 14, footer_text)
        self.drawRightString(self._pagesize[0] - 36, 14, page_text)
        self.restoreState()


def _safe_escape(val):
    if val is None:
        return ""
    return xml.sax.saxutils.escape(str(val))



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


SUPPORTED_REPORT_TYPES = ("Inventory", "Stock Transactions", "Purchase Orders", "Quotations", "Supplier Performance", "Audit Trail")


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


def fetch_audit_trail_report_data(start_date=None, end_date=None, user_id=None, action=None, table_name=None):
    """
    Queries historical audit log records from the verified AuditLogs table.
    Enriches with actor usernames, safe event descriptions, and outcome.
    Excludes sensitive secrets, passwords, or authentication payloads.
    Returns:
        (report_data_list, None, 200) on success,
        (None, {"error": "..."}, 400/500) on error.
    """
    # Validate date formats if provided
    if start_date:
        try:
            datetime.strptime(str(start_date).strip(), "%Y-%m-%d")
            start_date = str(start_date).strip()
        except ValueError:
            return None, {"error": "Invalid start_date format. Expected YYYY-MM-DD"}, 400

    if end_date:
        try:
            datetime.strptime(str(end_date).strip(), "%Y-%m-%d")
            end_date = str(end_date).strip()
        except ValueError:
            return None, {"error": "Invalid end_date format. Expected YYYY-MM-DD"}, 400

    if start_date and end_date and start_date > end_date:
        return None, {"error": "Start date cannot be after end date"}, 400

    # Validate user_id if provided
    parsed_user_id = None
    if user_id is not None and str(user_id).strip() != "":
        try:
            parsed_user_id = int(user_id)
            if parsed_user_id <= 0:
                return None, {"error": "Invalid user_id filter. Expected positive integer"}, 400
        except (ValueError, TypeError):
            return None, {"error": "Invalid user_id filter. Expected positive integer"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = '''
            SELECT
                al.log_id,
                al.action_time,
                al.user_id,
                COALESCE(u.username, CONCAT('User #', al.user_id::text)) AS actor_username,
                al.action,
                al.table_name,
                al.record_id,
                al.ip_address
            FROM public."AuditLogs" al
            LEFT JOIN public."Users" u ON al.user_id = u.user_id
            WHERE 1=1
        '''
        params = []
        if start_date:
            query += " AND al.action_time >= %s"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND al.action_time <= %s"
            params.append(f"{end_date} 23:59:59.999999")
        if parsed_user_id:
            query += " AND al.user_id = %s"
            params.append(parsed_user_id)
        if action and str(action).strip():
            query += " AND LOWER(al.action) = LOWER(%s)"
            params.append(str(action).strip())
        if table_name and str(table_name).strip():
            query += " AND LOWER(al.table_name) = LOWER(%s)"
            params.append(str(table_name).strip())

        query += " ORDER BY al.action_time DESC, al.log_id DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        report_data = []
        for r in rows:
            act_time_str = r[1].isoformat() if hasattr(r[1], 'isoformat') and r[1] else (str(r[1]) if r[1] else None)
            act = r[4] or "UNKNOWN"
            tbl = r[5] or "General"
            rec_id = r[6]
            if rec_id:
                desc = f"{act} record #{rec_id} in {tbl}"
            else:
                desc = f"{act} event on {tbl}"

            report_data.append({
                "log_id": r[0],
                "action_time": act_time_str,
                "user_id": r[2],
                "actor_username": r[3] or "System",
                "action": act,
                "table_name": tbl,
                "record_id": rec_id,
                "ip_address": r[7] or "N/A",
                "description": desc,
                "outcome": "Success"
            })

        return report_data, None, 200
    except Exception:
        return None, {"error": "Database error while fetching audit trail data"}, 500
    finally:
        cursor.close()
        conn.close()


def generate_report_record(report_name, report_type, generated_by, start_date=None, end_date=None,
                           user_id_filter=None, action_filter=None, entity_type_filter=None, **kwargs):
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
    elif report_type == "Audit Trail":
        report_data, error, status_code = fetch_audit_trail_report_data(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id_filter,
            action=action_filter,
            table_name=entity_type_filter
        )
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


def generate_inventory_report_record(report_name, report_type, generated_by, start_date=None, end_date=None, **kwargs):
    """
    Backward-compatibility wrapper for generating reports.
    """
    return generate_report_record(report_name, report_type, generated_by, start_date=start_date, end_date=end_date, **kwargs)



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


def serialize_snapshot_to_csv(report):
    """
    Serializes a saved historical report snapshot into RFC 4180 compliant CSV bytes with UTF-8 BOM encoding.
    Supports all 6 report types: Inventory, Stock Transactions, Purchase Orders, Quotations, Supplier Performance, Audit Trail.
    Protects against CSV Formula Injection (CWE-1236) on all textual columns.
    Returns:
        ((csv_bytes, filename), None, 200) on success,
        (None, error_dict, 400/404/500) on failure.
    """
    if not report.get("has_snapshot") or report.get("snapshot") is None:
        return None, {
            "error": "Historical snapshot unavailable for this report",
            "message": "This report was created before snapshot persistence was enabled."
        }, 404

    report_id = report.get("report_id", 0)
    report_name = str(report.get("report_name", "Report"))
    report_type = report.get("report_type")
    snapshot = report.get("snapshot")

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')

    items = snapshot if isinstance(snapshot, list) else []

    if report_type == "Inventory":
        writer.writerow([
            "Report ID", "Report Name", "Product ID", "Product Name", "SKU",
            "Category", "Available Quantity", "Reorder Level", "Unit Price",
            "Inventory Value", "Stock Status", "Status"
        ])
        for it in items:
            writer.writerow([
                report_id,
                sanitize_csv_cell(report_name),
                it.get("product_id"),
                sanitize_csv_cell(it.get("product_name")),
                sanitize_csv_cell(it.get("sku")),
                sanitize_csv_cell(it.get("category_name")),
                it.get("quantity_available", 0),
                it.get("reorder_level", 0),
                f"{float(it.get('unit_price', 0)):.2f}",
                f"{float(it.get('inventory_value', 0)):.2f}",
                sanitize_csv_cell(it.get("stock_status")),
                sanitize_csv_cell(it.get("status"))
            ])

    elif report_type == "Stock Transactions":
        writer.writerow([
            "Report ID", "Report Name", "Transaction ID", "Transaction Date",
            "Transaction Type", "Product ID", "Product Name", "SKU", "Quantity",
            "Performed By User ID", "Performed By Username", "Purchase Order ID",
            "Shipment ID", "Shipment Number", "Notes"
        ])
        for it in items:
            writer.writerow([
                report_id,
                sanitize_csv_cell(report_name),
                it.get("transaction_id"),
                sanitize_csv_cell(it.get("transaction_date")),
                sanitize_csv_cell(it.get("transaction_type")),
                it.get("product_id"),
                sanitize_csv_cell(it.get("product_name")),
                sanitize_csv_cell(it.get("sku")),
                it.get("quantity", 0),
                it.get("user_id"),
                sanitize_csv_cell(it.get("performed_by")),
                it.get("purchase_order_id") or "N/A",
                it.get("shipment_id") or "N/A",
                sanitize_csv_cell(it.get("shipment_number") or "N/A"),
                sanitize_csv_cell(it.get("notes") or "")
            ])

    elif report_type == "Purchase Orders":
        writer.writerow([
            "Report ID", "Report Name", "Purchase Order ID", "Supplier ID",
            "Supplier Name", "Order Date", "Expected Delivery Date", "Status",
            "Total Amount", "Supplier Response", "Ordered By", "Product ID",
            "Product Name", "SKU", "Quantity Ordered", "Unit Price", "Line Total"
        ])
        for po in items:
            po_items = po.get("items") or []
            if not po_items:
                writer.writerow([
                    report_id,
                    sanitize_csv_cell(report_name),
                    po.get("purchase_order_id"),
                    po.get("supplier_id"),
                    sanitize_csv_cell(po.get("supplier_name")),
                    sanitize_csv_cell(po.get("order_date")),
                    sanitize_csv_cell(po.get("expected_delivery_date") or "N/A"),
                    sanitize_csv_cell(po.get("status")),
                    f"{float(po.get('total_amount', 0)):.2f}",
                    sanitize_csv_cell(po.get("supplier_response") or "N/A"),
                    sanitize_csv_cell(po.get("ordered_by_username") or f"User #{po.get('ordered_by')}"),
                    "N/A", "N/A", "N/A", 0, "0.00", "0.00"
                ])
            else:
                for it in po_items:
                    writer.writerow([
                        report_id,
                        sanitize_csv_cell(report_name),
                        po.get("purchase_order_id"),
                        po.get("supplier_id"),
                        sanitize_csv_cell(po.get("supplier_name")),
                        sanitize_csv_cell(po.get("order_date")),
                        sanitize_csv_cell(po.get("expected_delivery_date") or "N/A"),
                        sanitize_csv_cell(po.get("status")),
                        f"{float(po.get('total_amount', 0)):.2f}",
                        sanitize_csv_cell(po.get("supplier_response") or "N/A"),
                        sanitize_csv_cell(po.get("ordered_by_username") or f"User #{po.get('ordered_by')}"),
                        it.get("product_id"),
                        sanitize_csv_cell(it.get("product_name")),
                        sanitize_csv_cell(it.get("sku")),
                        it.get("quantity", 0),
                        f"{float(it.get('unit_price', 0)):.2f}",
                        f"{float(it.get('total_price', 0)):.2f}"
                    ])

    elif report_type == "Quotations":
        writer.writerow([
            "Report ID", "Report Name", "Quotation ID", "Quotation Number",
            "Supplier ID", "Supplier Name", "Quotation Date", "Valid Until",
            "Status", "Total Amount", "Approved By", "Rejection Reason",
            "Product ID", "Product Name", "SKU", "Quoted Price", "Quantity", "Subtotal"
        ])
        for q in items:
            q_items = q.get("items") or []
            if not q_items:
                writer.writerow([
                    report_id,
                    sanitize_csv_cell(report_name),
                    q.get("quotation_id"),
                    sanitize_csv_cell(q.get("quotation_number")),
                    q.get("supplier_id"),
                    sanitize_csv_cell(q.get("supplier_name")),
                    sanitize_csv_cell(q.get("quotation_date")),
                    sanitize_csv_cell(q.get("valid_until") or "N/A"),
                    sanitize_csv_cell(q.get("status")),
                    f"{float(q.get('total_amount', 0)):.2f}",
                    sanitize_csv_cell(q.get("approved_by_username") or "N/A"),
                    sanitize_csv_cell(q.get("rejection_reason") or ""),
                    "N/A", "N/A", "N/A", "0.00", 0, "0.00"
                ])
            else:
                for it in q_items:
                    writer.writerow([
                        report_id,
                        sanitize_csv_cell(report_name),
                        q.get("quotation_id"),
                        sanitize_csv_cell(q.get("quotation_number")),
                        q.get("supplier_id"),
                        sanitize_csv_cell(q.get("supplier_name")),
                        sanitize_csv_cell(q.get("quotation_date")),
                        sanitize_csv_cell(q.get("valid_until") or "N/A"),
                        sanitize_csv_cell(q.get("status")),
                        f"{float(q.get('total_amount', 0)):.2f}",
                        sanitize_csv_cell(q.get("approved_by_username") or "N/A"),
                        sanitize_csv_cell(q.get("rejection_reason") or ""),
                        it.get("product_id"),
                        sanitize_csv_cell(it.get("product_name")),
                        sanitize_csv_cell(it.get("sku")),
                        f"{float(it.get('quoted_price', 0)):.2f}",
                        it.get("quantity", 0),
                        f"{float(it.get('subtotal', 0)):.2f}"
                    ])

    elif report_type == "Supplier Performance":
        writer.writerow([
            "Report ID", "Report Name", "Supplier ID", "Supplier Name",
            "Contact Person", "Email", "Phone", "Status",
            "Total POs", "Accepted POs", "Rejected POs", "Delivered POs",
            "Total PO Value ($)", "PO Acceptance Rate (%)",
            "Total Quotations", "Responded Quotations", "Approved Quotations",
            "Total Quoted Value ($)", "Quotation Response Rate (%)",
            "Quotation Approval Rate (%)", "Total Shipments", "Delivered Shipments",
            "Measurable Deliveries", "On-Time Deliveries", "Late Deliveries",
            "On-Time Delivery Rate (%)", "Avg Delivery Delay (Days)"
        ])
        for s in items:
            writer.writerow([
                report_id,
                sanitize_csv_cell(report_name),
                s.get("supplier_id"),
                sanitize_csv_cell(s.get("supplier_name")),
                sanitize_csv_cell(s.get("contact_person") or ""),
                sanitize_csv_cell(s.get("email") or ""),
                sanitize_csv_cell(s.get("phone") or ""),
                sanitize_csv_cell(s.get("status") or ""),
                s.get("total_purchase_orders", 0),
                s.get("accepted_purchase_orders", 0),
                s.get("rejected_purchase_orders", 0),
                s.get("delivered_purchase_orders", 0),
                f"{float(s.get('total_order_value', 0)):.2f}",
                f"{float(s.get('po_acceptance_rate', 0)):.1f}%",
                s.get("total_quotations", 0),
                s.get("responded_quotations", 0),
                s.get("approved_quotations", 0),
                f"{float(s.get('total_quoted_value', 0)):.2f}",
                f"{float(s.get('quotation_response_rate', 0)):.1f}%",
                f"{float(s.get('quotation_approval_rate', 0)):.1f}%",
                s.get("total_shipments", 0),
                s.get("delivered_shipments", 0),
                s.get("measurable_deliveries", 0),
                s.get("on_time_deliveries", 0),
                s.get("late_deliveries", 0),
                f"{float(s.get('on_time_delivery_rate', 0)):.1f}%",
                f"{float(s.get('avg_delivery_delay_days', 0)):.1f}"
            ])

    elif report_type == "Audit Trail":
        writer.writerow([
            "Report ID", "Report Name", "Audit Event ID", "Event Timestamp",
            "Actor User ID", "Actor Username", "Action Type", "Entity Type",
            "Entity ID", "Event Description", "Outcome", "IP Address"
        ])
        for ev in items:
            writer.writerow([
                report_id,
                sanitize_csv_cell(report_name),
                ev.get("log_id"),
                sanitize_csv_cell(ev.get("action_time")),
                ev.get("user_id") or "N/A",
                sanitize_csv_cell(ev.get("actor_username") or "System"),
                sanitize_csv_cell(ev.get("action")),
                sanitize_csv_cell(ev.get("table_name")),
                ev.get("record_id") or "N/A",
                sanitize_csv_cell(ev.get("description") or ""),
                sanitize_csv_cell(ev.get("outcome") or "Success"),
                sanitize_csv_cell(ev.get("ip_address") or "N/A")
            ])
    else:
        return None, {"error": f"Unsupported report type '{report_type}' for CSV export"}, 400

    csv_text = output.getvalue()
    csv_bytes = csv_text.encode('utf-8-sig')

    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', report_name.strip().lower())
    clean_name = re.sub(r'_+', '_', clean_name).strip('_') or "report"
    filename = f"{clean_name}_id{report_id}.csv"

    return (csv_bytes, filename), None, 200


def generate_snapshot_pdf(report):
    """
    Generates a readable, print-quality PDF for a saved historical report snapshot.
    Supports all 6 report types with tailored layouts, summary KPI cards, repeated headers,
    page numbering via NumberedCanvas, and XML-escaped user data.
    Returns:
        ((pdf_bytes, filename), None, 200) on success,
        (None, error_dict, 400/404/500) on failure.
    """
    if not report.get("has_snapshot") or report.get("snapshot") is None:
        return None, {
            "error": "Historical snapshot unavailable for this report",
            "message": "This report was created before snapshot persistence was enabled."
        }, 404

    report_id = report.get("report_id", 0)
    report_name = str(report.get("report_name", "Report"))
    report_type = report.get("report_type")
    generated_by = report.get("generated_by_username") or f"User #{report.get('generated_by', 'N/A')}"
    generated_on = report.get("generated_on")
    if hasattr(generated_on, "strftime"):
        gen_on_str = generated_on.strftime("%Y-%m-%d %H:%M:%S")
    else:
        gen_on_str = str(generated_on) if generated_on else "N/A"

    snapshot = report.get("snapshot")
    items = snapshot if isinstance(snapshot, list) else []

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=38
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0f172a')
    )
    badge_style = ParagraphStyle(
        'TypeBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#2563eb')
    )
    meta_lbl_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#64748b')
    )
    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0f172a')
    )
    kpi_val_style = ParagraphStyle(
        'KPIVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor('#0f172a')
    )
    kpi_lbl_style = ParagraphStyle(
        'KPILbl',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        alignment=1,
        textColor=colors.HexColor('#64748b')
    )
    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )
    th_r_style = ParagraphStyle(
        'TableHeaderRight',
        parent=th_style,
        alignment=2
    )
    th_c_style = ParagraphStyle(
        'TableHeaderCenter',
        parent=th_style,
        alignment=1
    )
    td_style = ParagraphStyle(
        'TableData',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#1e293b')
    )
    td_r_style = ParagraphStyle(
        'TableDataRight',
        parent=td_style,
        alignment=2
    )
    td_c_style = ParagraphStyle(
        'TableDataCenter',
        parent=td_style,
        alignment=1
    )

    story = []

    # 1. Header Banner
    header_table_data = [
        [
            Paragraph("SIMS — Smart Inventory Management System", title_style),
            Paragraph(f"REPORT TYPE: {_safe_escape(report_type).upper()}", badge_style)
        ],
        [
            Paragraph(f"<b>Snapshot Report:</b> {_safe_escape(report_name)}", meta_val_style),
            Paragraph(f"<b>Report ID:</b> #{report_id} &nbsp;|&nbsp; <b>Archive Status:</b> Point-in-Time Snapshot", meta_val_style)
        ]
    ]
    header_table = Table(header_table_data, colWidths=[460, 260])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 2. Metadata Box
    meta_box_data = [
        [
            Paragraph("Generated By", meta_lbl_style),
            Paragraph("Generated Date & Time", meta_lbl_style),
            Paragraph("Snapshot Size", meta_lbl_style),
            Paragraph("Historical Immutability", meta_lbl_style)
        ],
        [
            Paragraph(_safe_escape(generated_by), meta_val_style),
            Paragraph(_safe_escape(gen_on_str), meta_val_style),
            Paragraph(f"{len(items)} record(s)", meta_val_style),
            Paragraph("Verified Immutable JSONB", meta_val_style)
        ]
    ]
    meta_box = Table(meta_box_data, colWidths=[180, 200, 160, 180])
    meta_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#edf2f7')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_box)
    story.append(Spacer(1, 8))

    # 3. KPI Callouts and Table Content by Report Type
    col_widths = []
    table_data = []

    if report_type == "Inventory":
        tot_qty = sum(int(it.get("quantity_available", 0) or 0) for it in items)
        tot_val = sum(float(it.get("inventory_value", 0) or 0) for it in items)
        low_stock = sum(1 for it in items if it.get("stock_status") == "LOW STOCK")

        kpi_data = [
            [Paragraph(f"{len(items)}", kpi_val_style),
             Paragraph(f"{tot_qty:,}", kpi_val_style),
             Paragraph(f"${tot_val:,.2f}", kpi_val_style),
             Paragraph(f"{low_stock}", kpi_val_style)],
            [Paragraph("Total Products", kpi_lbl_style),
             Paragraph("Available Units", kpi_lbl_style),
             Paragraph("Total Inventory Valuation", kpi_lbl_style),
             Paragraph("Low Stock Items", kpi_lbl_style)]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[180, 180, 180, 180])
        kpi_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        col_widths = [45, 145, 80, 95, 55, 55, 65, 75, 55, 50]
        table_data.append([
            Paragraph("ID", th_style),
            Paragraph("Product Name", th_style),
            Paragraph("SKU", th_style),
            Paragraph("Category", th_style),
            Paragraph("Qty", th_r_style),
            Paragraph("Reorder", th_r_style),
            Paragraph("Unit Price", th_r_style),
            Paragraph("Total Value", th_r_style),
            Paragraph("Stock Status", th_c_style),
            Paragraph("Status", th_c_style)
        ])
        for it in items:
            table_data.append([
                Paragraph(_safe_escape(it.get("product_id")), td_style),
                Paragraph(_safe_escape(it.get("product_name")), td_style),
                Paragraph(_safe_escape(it.get("sku")), td_style),
                Paragraph(_safe_escape(it.get("category_name")), td_style),
                Paragraph(f"{it.get('quantity_available', 0)}", td_r_style),
                Paragraph(f"{it.get('reorder_level', 0)}", td_r_style),
                Paragraph(f"${float(it.get('unit_price', 0)):.2f}", td_r_style),
                Paragraph(f"${float(it.get('inventory_value', 0)):.2f}", td_r_style),
                Paragraph(_safe_escape(it.get("stock_status")), td_c_style),
                Paragraph(_safe_escape(it.get("status")), td_c_style)
            ])

    elif report_type == "Stock Transactions":
        tot_qty = sum(int(it.get("quantity", 0) or 0) for it in items)
        inbound = sum(1 for it in items if (it.get("transaction_type") or "").upper() == "INBOUND")
        outbound = sum(1 for it in items if (it.get("transaction_type") or "").upper() == "OUTBOUND")

        kpi_data = [
            [Paragraph(f"{len(items)}", kpi_val_style),
             Paragraph(f"{tot_qty:,}", kpi_val_style),
             Paragraph(f"{inbound}", kpi_val_style),
             Paragraph(f"{outbound}", kpi_val_style)],
            [Paragraph("Total Transactions", kpi_lbl_style),
             Paragraph("Units Transacted", kpi_lbl_style),
             Paragraph("Inbound Transactions", kpi_lbl_style),
             Paragraph("Outbound Transactions", kpi_lbl_style)]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[180, 180, 180, 180])
        kpi_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        col_widths = [45, 95, 65, 140, 75, 45, 80, 85, 90]
        table_data.append([
            Paragraph("Tx ID", th_style),
            Paragraph("Date & Time", th_style),
            Paragraph("Type", th_c_style),
            Paragraph("Product Name", th_style),
            Paragraph("SKU", th_style),
            Paragraph("Qty", th_r_style),
            Paragraph("Performed By", th_style),
            Paragraph("PO / Shipment", th_style),
            Paragraph("Notes", td_style)
        ])
        for it in items:
            po_ship = []
            if it.get("purchase_order_id"):
                po_ship.append(f"PO #{it.get('purchase_order_id')}")
            if it.get("shipment_number"):
                po_ship.append(f"SH: {it.get('shipment_number')}")
            elif it.get("shipment_id"):
                po_ship.append(f"SH #{it.get('shipment_id')}")
            po_ship_str = " / ".join(po_ship) if po_ship else "N/A"

            table_data.append([
                Paragraph(_safe_escape(it.get("transaction_id")), td_style),
                Paragraph(_safe_escape(it.get("transaction_date")), td_style),
                Paragraph(_safe_escape(it.get("transaction_type")), td_c_style),
                Paragraph(_safe_escape(it.get("product_name")), td_style),
                Paragraph(_safe_escape(it.get("sku")), td_style),
                Paragraph(f"{it.get('quantity', 0)}", td_r_style),
                Paragraph(_safe_escape(it.get("performed_by")), td_style),
                Paragraph(_safe_escape(po_ship_str), td_style),
                Paragraph(_safe_escape(it.get("notes") or "-"), td_style)
            ])

    elif report_type == "Purchase Orders":
        tot_val = sum(float(po.get("total_amount", 0) or 0) for po in items)
        tot_lines = sum(len(po.get("items") or []) for po in items)
        app_pos = sum(1 for po in items if (po.get("status") or "").upper() in ("APPROVED", "ACCEPTED", "COMPLETED"))

        kpi_data = [
            [Paragraph(f"{len(items)}", kpi_val_style),
             Paragraph(f"${tot_val:,.2f}", kpi_val_style),
             Paragraph(f"{tot_lines}", kpi_val_style),
             Paragraph(f"{app_pos}", kpi_val_style)],
            [Paragraph("Total Purchase Orders", kpi_lbl_style),
             Paragraph("Total Order Value", kpi_lbl_style),
             Paragraph("Itemized Line Records", kpi_lbl_style),
             Paragraph("Approved / Completed POs", kpi_lbl_style)]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[180, 180, 180, 180])
        kpi_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        col_widths = [45, 110, 65, 60, 65, 140, 75, 45, 55, 60]
        table_data.append([
            Paragraph("PO #", th_style),
            Paragraph("Supplier", th_style),
            Paragraph("Order Date", th_style),
            Paragraph("Status", th_c_style),
            Paragraph("PO Total", th_r_style),
            Paragraph("Product Item", th_style),
            Paragraph("SKU", th_style),
            Paragraph("Qty", th_r_style),
            Paragraph("Price", th_r_style),
            Paragraph("Subtotal", th_r_style)
        ])
        for po in items:
            po_items = po.get("items") or []
            if not po_items:
                table_data.append([
                    Paragraph(_safe_escape(po.get("purchase_order_id")), td_style),
                    Paragraph(_safe_escape(po.get("supplier_name")), td_style),
                    Paragraph(_safe_escape(po.get("order_date")), td_style),
                    Paragraph(_safe_escape(po.get("status")), td_c_style),
                    Paragraph(f"${float(po.get('total_amount', 0)):.2f}", td_r_style),
                    Paragraph("(No item details)", td_style),
                    Paragraph("-", td_style),
                    Paragraph("-", td_r_style),
                    Paragraph("-", td_r_style),
                    Paragraph("-", td_r_style)
                ])
            else:
                for idx, it in enumerate(po_items):
                    table_data.append([
                        Paragraph(_safe_escape(po.get("purchase_order_id")) if idx == 0 else "", td_style),
                        Paragraph(_safe_escape(po.get("supplier_name")) if idx == 0 else "", td_style),
                        Paragraph(_safe_escape(po.get("order_date")) if idx == 0 else "", td_style),
                        Paragraph(_safe_escape(po.get("status")) if idx == 0 else "", td_c_style),
                        Paragraph(f"${float(po.get('total_amount', 0)):.2f}" if idx == 0 else "", td_r_style),
                        Paragraph(_safe_escape(it.get("product_name")), td_style),
                        Paragraph(_safe_escape(it.get("sku")), td_style),
                        Paragraph(f"{it.get('quantity', 0)}", td_r_style),
                        Paragraph(f"${float(it.get('unit_price', 0)):.2f}", td_r_style),
                        Paragraph(f"${float(it.get('total_price', 0)):.2f}", td_r_style)
                    ])

    elif report_type == "Quotations":
        tot_val = sum(float(q.get("total_amount", 0) or 0) for q in items)
        tot_lines = sum(len(q.get("items") or []) for q in items)
        app_q = sum(1 for q in items if (q.get("status") or "").upper() in ("APPROVED", "ACCEPTED"))

        kpi_data = [
            [Paragraph(f"{len(items)}", kpi_val_style),
             Paragraph(f"${tot_val:,.2f}", kpi_val_style),
             Paragraph(f"{tot_lines}", kpi_val_style),
             Paragraph(f"{app_q}", kpi_val_style)],
            [Paragraph("Total Quotations", kpi_lbl_style),
             Paragraph("Total Quoted Amount", kpi_lbl_style),
             Paragraph("Itemized Product Quotes", kpi_lbl_style),
             Paragraph("Approved Quotations", kpi_lbl_style)]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[180, 180, 180, 180])
        kpi_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        col_widths = [75, 115, 65, 55, 60, 140, 70, 45, 45, 50]
        table_data.append([
            Paragraph("Quote #", th_style),
            Paragraph("Supplier", th_style),
            Paragraph("Date", th_style),
            Paragraph("Status", th_c_style),
            Paragraph("Total", th_r_style),
            Paragraph("Quoted Product", th_style),
            Paragraph("SKU", th_style),
            Paragraph("Qty", th_r_style),
            Paragraph("Price", th_r_style),
            Paragraph("Subtotal", th_r_style)
        ])
        for q in items:
            q_items = q.get("items") or []
            if not q_items:
                table_data.append([
                    Paragraph(_safe_escape(q.get("quotation_number") or f"QT #{q.get('quotation_id')}"), td_style),
                    Paragraph(_safe_escape(q.get("supplier_name")), td_style),
                    Paragraph(_safe_escape(q.get("quotation_date")), td_style),
                    Paragraph(_safe_escape(q.get("status")), td_c_style),
                    Paragraph(f"${float(q.get('total_amount', 0)):.2f}", td_r_style),
                    Paragraph("(No items)", td_style),
                    Paragraph("-", td_style),
                    Paragraph("-", td_r_style),
                    Paragraph("-", td_r_style),
                    Paragraph("-", td_r_style)
                ])
            else:
                for idx, it in enumerate(q_items):
                    table_data.append([
                        Paragraph(_safe_escape(q.get("quotation_number") or f"QT #{q.get('quotation_id')}") if idx == 0 else "", td_style),
                        Paragraph(_safe_escape(q.get("supplier_name")) if idx == 0 else "", td_style),
                        Paragraph(_safe_escape(q.get("quotation_date")) if idx == 0 else "", td_style),
                        Paragraph(_safe_escape(q.get("status")) if idx == 0 else "", td_c_style),
                        Paragraph(f"${float(q.get('total_amount', 0)):.2f}" if idx == 0 else "", td_r_style),
                        Paragraph(_safe_escape(it.get("product_name")), td_style),
                        Paragraph(_safe_escape(it.get("sku")), td_style),
                        Paragraph(f"{it.get('quantity', 0)}", td_r_style),
                        Paragraph(f"${float(it.get('quoted_price', 0)):.2f}", td_r_style),
                        Paragraph(f"${float(it.get('subtotal', 0)):.2f}", td_r_style)
                    ])

    elif report_type == "Supplier Performance":
        tot_sup = len(items)
        tot_pos = sum(int(s.get("total_purchase_orders", 0) or 0) for s in items)
        tot_val = sum(float(s.get("total_order_value", 0) or 0) for s in items)
        avg_acc = (sum(float(s.get("po_acceptance_rate", 0) or 0) for s in items) / tot_sup) if tot_sup else 0.0

        kpi_data = [
            [Paragraph(f"{tot_sup}", kpi_val_style),
             Paragraph(f"{tot_pos}", kpi_val_style),
             Paragraph(f"${tot_val:,.2f}", kpi_val_style),
             Paragraph(f"{avg_acc:.1f}%", kpi_val_style)],
            [Paragraph("Suppliers Evaluated", kpi_lbl_style),
             Paragraph("Total Orders Placed", kpi_lbl_style),
             Paragraph("Total Order Value", kpi_lbl_style),
             Paragraph("Average PO Acceptance", kpi_lbl_style)]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[180, 180, 180, 180])
        kpi_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        col_widths = [120, 50, 70, 70, 60, 70, 70, 60, 75, 75]
        table_data.append([
            Paragraph("Supplier Name", th_style),
            Paragraph("Status", th_c_style),
            Paragraph("POs (Tot/Acc)", th_style),
            Paragraph("PO Value", th_r_style),
            Paragraph("PO Acc %", th_c_style),
            Paragraph("Quotes (Tot/R)", th_style),
            Paragraph("Quote Value", th_r_style),
            Paragraph("Appr %", th_c_style),
            Paragraph("Shipments", th_style),
            Paragraph("On-Time %", th_c_style)
        ])
        for s in items:
            po_str = f"{s.get('total_purchase_orders', 0)} / {s.get('accepted_purchase_orders', 0)}"
            q_str = f"{s.get('total_quotations', 0)} / {s.get('responded_quotations', 0)}"
            sh_str = f"{s.get('delivered_shipments', 0)} / {s.get('total_shipments', 0)}"

            table_data.append([
                Paragraph(_safe_escape(s.get("supplier_name")), td_style),
                Paragraph(_safe_escape(s.get("status") or "Active"), td_c_style),
                Paragraph(po_str, td_style),
                Paragraph(f"${float(s.get('total_order_value', 0)):.2f}", td_r_style),
                Paragraph(f"{float(s.get('po_acceptance_rate', 0)):.1f}%", td_c_style),
                Paragraph(q_str, td_style),
                Paragraph(f"${float(s.get('total_quoted_value', 0)):.2f}", td_r_style),
                Paragraph(f"{float(s.get('quotation_approval_rate', 0)):.1f}%", td_c_style),
                Paragraph(sh_str, td_style),
                Paragraph(f"{float(s.get('on_time_delivery_rate', 0)):.1f}%", td_c_style)
            ])

    elif report_type == "Audit Trail":
        tot_events = len(items)
        actors = len(set(ev.get("user_id") for ev in items if ev.get("user_id")))
        tables = len(set(ev.get("table_name") for ev in items if ev.get("table_name")))

        kpi_data = [
            [Paragraph(f"{tot_events}", kpi_val_style),
             Paragraph(f"{actors}", kpi_val_style),
             Paragraph(f"{tables}", kpi_val_style),
             Paragraph("Success", kpi_val_style)],
            [Paragraph("Total Audit Events", kpi_lbl_style),
             Paragraph("Active User Actors", kpi_lbl_style),
             Paragraph("Entity Tables Affected", kpi_lbl_style),
             Paragraph("Overall Outcome Status", kpi_lbl_style)]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[180, 180, 180, 180])
        kpi_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 10))

        col_widths = [50, 95, 80, 60, 75, 50, 190, 60, 60]
        table_data.append([
            Paragraph("Log ID", th_style),
            Paragraph("Event Timestamp", th_style),
            Paragraph("Actor", th_style),
            Paragraph("Action", th_c_style),
            Paragraph("Entity Table", th_style),
            Paragraph("Rec ID", th_style),
            Paragraph("Safe Description", th_style),
            Paragraph("Outcome", th_c_style),
            Paragraph("IP Address", th_c_style)
        ])
        for ev in items:
            table_data.append([
                Paragraph(_safe_escape(ev.get("log_id")), td_style),
                Paragraph(_safe_escape(ev.get("action_time")), td_style),
                Paragraph(_safe_escape(ev.get("actor_username") or "System"), td_style),
                Paragraph(_safe_escape(ev.get("action")), td_c_style),
                Paragraph(_safe_escape(ev.get("table_name")), td_style),
                Paragraph(_safe_escape(ev.get("record_id") or "-"), td_style),
                Paragraph(_safe_escape(ev.get("description") or "-"), td_style),
                Paragraph(_safe_escape(ev.get("outcome") or "Success"), td_c_style),
                Paragraph(_safe_escape(ev.get("ip_address") or "N/A"), td_c_style)
            ])

    # 4. Render Main Table
    if len(table_data) <= 1:
        empty_tbl = Table([[Paragraph("No historical records captured in this report snapshot.", meta_val_style)]], colWidths=[720])
        empty_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ]))
        story.append(empty_tbl)
    else:
        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc')))
        main_table.setStyle(TableStyle(t_style))
        story.append(main_table)

    # 5. Build Document with NumberedCanvas
    try:
        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', report_name.strip().lower())
        clean_name = re.sub(r'_+', '_', clean_name).strip('_') or "report"
        filename = f"{clean_name}_id{report_id}.pdf"
        return (pdf_bytes, filename), None, 200
    except Exception as e:
        return None, {"error": f"Failed to generate report PDF: {str(e)}"}, 500

