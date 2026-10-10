import io
import json
import re
import csv
import xml.sax.saxutils
from datetime import datetime
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import pypdf

DANGEROUS_FORMULA_PREFIXES = ('=', '+', '-', '@')

def sanitize_csv_cell(value):
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
        self.line(36, 28, self._pagesize[0] - 36, 28)
        footer_text = "SIMS — Smart Inventory Management System  |  Confidential Historical Report"
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawString(36, 16, footer_text)
        self.drawRightString(self._pagesize[0] - 36, 16, page_text)
        self.restoreState()

def serialize_snapshot_to_csv(report):
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

# Mock test for all 6 report types
mock_data = {
    "Inventory": [{
        "product_id": 1, "product_name": "Test Laptop", "sku": "TECH-001",
        "category_name": "Electronics", "quantity_available": 15, "reorder_level": 5,
        "unit_price": 999.99, "inventory_value": 14999.85, "stock_status": "NORMAL", "status": "Active"
    }],
    "Stock Transactions": [{
        "transaction_id": 101, "transaction_date": "2026-10-10 12:00:00",
        "transaction_type": "INBOUND", "product_id": 1, "product_name": "Test Laptop",
        "sku": "TECH-001", "quantity": 10, "user_id": 2, "performed_by": "demo_manager",
        "purchase_order_id": 1, "shipment_id": 1, "shipment_number": "SH-001", "notes": "=malicious"
    }],
    "Purchase Orders": [{
        "purchase_order_id": 201, "supplier_id": 1, "supplier_name": "Global Supplies",
        "order_date": "2026-10-09", "expected_delivery_date": "2026-10-15",
        "status": "APPROVED", "total_amount": 1500.0, "supplier_response": "Accepted",
        "ordered_by": 2, "ordered_by_username": "demo_manager",
        "items": [{
            "product_id": 1, "product_name": "Test Laptop", "sku": "TECH-001",
            "quantity": 2, "unit_price": 750.0, "total_price": 1500.0
        }]
    }],
    "Quotations": [{
        "quotation_id": 301, "quotation_number": "QT-2026-0001", "supplier_id": 1,
        "supplier_name": "Global Supplies", "quotation_date": "2026-10-08",
        "valid_until": "2026-11-08", "status": "APPROVED", "total_amount": 1400.0,
        "approved_by_username": "demo_owner", "rejection_reason": "",
        "items": [{
            "product_id": 1, "product_name": "Test Laptop", "sku": "TECH-001",
            "quoted_price": 700.0, "quantity": 2, "subtotal": 1400.0
        }]
    }],
    "Supplier Performance": [{
        "supplier_id": 1, "supplier_name": "Global Supplies", "contact_person": "Jane Doe",
        "email": "jane@example.com", "phone": "123-456", "status": "Active",
        "total_purchase_orders": 5, "accepted_purchase_orders": 4, "rejected_purchase_orders": 1,
        "delivered_purchase_orders": 4, "total_order_value": 7500.0, "po_acceptance_rate": 80.0,
        "total_quotations": 6, "responded_quotations": 5, "approved_quotations": 4,
        "total_quoted_value": 8500.0, "quotation_response_rate": 83.3, "quotation_approval_rate": 80.0,
        "total_shipments": 4, "delivered_shipments": 4, "measurable_deliveries": 3,
        "on_time_deliveries": 3, "late_deliveries": 0, "on_time_delivery_rate": 100.0,
        "avg_delivery_delay_days": -1.5
    }],
    "Audit Trail": [{
        "log_id": 401, "action_time": "2026-10-10 14:20:00", "user_id": 2,
        "actor_username": "demo_manager", "action": "UPDATE", "table_name": "Products",
        "record_id": 1, "description": "UPDATE record #1 in Products", "outcome": "Success",
        "ip_address": "127.0.0.1"
    }]
}

for r_type, data in mock_data.items():
    rep = {
        "report_id": 999,
        "report_name": f"Test {r_type} Report",
        "report_type": r_type,
        "has_snapshot": True,
        "snapshot": data
    }
    res, err, code = serialize_snapshot_to_csv(rep)
    assert code == 200, f"Failed for {r_type}: {err}"
    csv_bytes, fn = res
    assert csv_bytes.startswith(b'\xef\xbb\xbf')
    assert fn.endswith(".csv")
    parsed = list(csv.reader(io.StringIO(csv_bytes.decode('utf-8-sig'))))
    assert len(parsed) >= 2, f"Not enough rows for {r_type}: {len(parsed)}"
    print(f"CSV OK for {r_type}: {fn}, rows={len(parsed)}")

print("All 6 CSV exports validated successfully!")
