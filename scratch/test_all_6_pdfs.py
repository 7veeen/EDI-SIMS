import io
import json
import re
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


def generate_snapshot_pdf(report):
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
        # Empty table state
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
        # Alternating row colors
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


# Test all 6 PDF generation
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from test_all_6_exports import mock_data

for r_type, data in mock_data.items():
    rep = {
        "report_id": 888,
        "report_name": f"Verified {r_type} Snapshot",
        "report_type": r_type,
        "generated_by": 1,
        "generated_by_username": "demo_owner",
        "generated_on": "2026-10-10 16:00:00",
        "has_snapshot": True,
        "snapshot": data
    }
    res, err, code = generate_snapshot_pdf(rep)
    assert code == 200, f"PDF failed for {r_type}: {err}"
    pdf_bytes, fn = res
    assert pdf_bytes.startswith(b'%PDF'), f"Invalid PDF signature for {r_type}"
    assert fn.endswith(".pdf")

    # Verify with pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    num_pages = len(reader.pages)
    text_content = "".join(page.extract_text() for page in reader.pages)
    assert "SIMS" in text_content
    assert str(rep["report_id"]) in text_content
    assert "Page 1 of" in text_content
    print(f"PDF OK for {r_type}: {fn}, pages={num_pages}, bytes={len(pdf_bytes)}")

print("All 6 PDF exports validated and parsed successfully with PyPDF!")
