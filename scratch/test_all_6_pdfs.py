import io
import sys
import os
import pypdf

sys.path.insert(0, os.path.abspath('backend'))
from app.services.team3.report_service import generate_snapshot_pdf

report_types = [
    ("Inventory", [
        {"product_id": 1, "product_name": "Test Mouse", "sku": "MOU-01", "category_name": "Peripherals",
         "quantity_available": 15, "reorder_level": 5, "unit_price": 799.00, "inventory_value": 11985.00,
         "stock_status": "NORMAL", "status": "Active"}
    ]),
    ("Stock Transactions", [
        {"transaction_id": 101, "transaction_date": "2026-10-10 12:00:00", "transaction_type": "INBOUND",
         "product_name": "Test Mouse", "sku": "MOU-01", "quantity": 10, "performed_by": "demo_manager",
         "purchase_order_id": 5, "shipment_number": "SH-100", "notes": "Initial delivery"}
    ]),
    ("Purchase Orders", [
        {"purchase_order_id": 5, "supplier_name": "Tech Corp", "order_date": "2026-10-01", "status": "APPROVED",
         "total_amount": 15980.00, "items": [
             {"product_name": "Test Mouse", "sku": "MOU-01", "quantity": 20, "unit_price": 799.00, "total_price": 15980.00}
         ]}
    ]),
    ("Quotations", [
        {"quotation_id": 12, "quotation_number": "QT-2026-001", "supplier_name": "Tech Corp", "quotation_date": "2026-09-28",
         "status": "APPROVED", "total_amount": 15000.00, "items": [
             {"product_name": "Test Mouse", "sku": "MOU-01", "quantity": 20, "quoted_price": 750.00, "subtotal": 15000.00}
         ]}
    ]),
    ("Supplier Performance", [
        {"supplier_id": 2, "supplier_name": "Tech Corp", "status": "Active", "total_purchase_orders": 4,
         "accepted_purchase_orders": 4, "total_order_value": 63920.00, "po_acceptance_rate": 100.0,
         "total_quotations": 3, "responded_quotations": 3, "approved_quotations": 2, "total_quoted_value": 45000.00,
         "quotation_response_rate": 100.0, "quotation_approval_rate": 66.7, "total_shipments": 4,
         "delivered_shipments": 4, "on_time_delivery_rate": 100.0}
    ]),
    ("Audit Trail", [
        {"log_id": 1, "action_time": "2026-10-10 10:00:00", "user_id": 1, "actor_username": "demo_owner",
         "action": "INSERT", "table_name": "Products", "record_id": 1, "description": "Created product MOU-01",
         "outcome": "Success", "ip_address": "127.0.0.1"}
    ])
]

for rep_type, items in report_types:
    report = {
        "report_id": 999,
        "report_name": f"Test {rep_type} Snapshot",
        "report_type": rep_type,
        "generated_by": 1,
        "generated_by_username": "demo_owner",
        "generated_on": "2026-10-10 12:00:00",
        "has_snapshot": True,
        "snapshot": items
    }
    result, error, status_code = generate_snapshot_pdf(report)
    assert status_code == 200, f"Failed for {rep_type}: {error}"
    pdf_bytes, filename = result
    assert pdf_bytes.startswith(b'%PDF'), f"Invalid PDF bytes for {rep_type}"
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    text = "".join(p.extract_text() for p in reader.pages)
    assert "SIMS" in text
    assert "Page 1 of" in text
    # Check currency symbol in monetary report types
    if rep_type in ("Inventory", "Purchase Orders", "Quotations", "Supplier Performance"):
        assert ("\u20b9" in text or "INR" in text), f"Missing INR/Rupee in {rep_type} PDF text"
    print(f"SUCCESS: {rep_type} PDF generated ({len(pdf_bytes)} bytes, {len(reader.pages)} page(s))")

print("ALL 6 REPORT TYPES GENERATED PERFECT PRINT-QUALITY PDFS WITH CURRENCY STANDARDIZATION!")
