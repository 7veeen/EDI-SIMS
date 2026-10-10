import sys
import os
import io
import json
import xml.sax.saxutils as saxutils
from datetime import datetime
from decimal import Decimal

# ReportLab imports
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.pdfgen import canvas
import pypdf

sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

def test_audit_trail_fetch():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            al.log_id,
            al.action,
            al.table_name,
            al.record_id,
            al.action_time,
            al.ip_address,
            al.user_id,
            COALESCE(u.username, CONCAT('User #', al.user_id::text)) AS actor_username
        FROM "AuditLogs" al
        LEFT JOIN "Users" u ON al.user_id = u.user_id
        ORDER BY al.action_time DESC, al.log_id DESC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    report_data = []
    for r in rows:
        action = r[1] or "UNKNOWN"
        tbl = r[2] or "System"
        rec_id = r[3]
        ip = r[5] or "127.0.0.1"
        uname = r[7] or "System"

        # Generate readable safe description
        if action.startswith('CREATE'):
            desc = f"Created new record in {tbl} (ID: {rec_id})"
        elif action.startswith('UPDATE'):
            desc = f"Updated record in {tbl} (ID: {rec_id})"
        elif action.startswith('DELETE'):
            desc = f"Deleted record from {tbl} (ID: {rec_id})"
        elif 'STATUS' in action:
            desc = f"Changed status in {tbl} (ID: {rec_id})"
        elif 'LOGIN' in action:
            desc = f"User logged in from {ip}"
        elif 'STOCK' in action:
            desc = f"Stock transaction recorded in {tbl} (ID: {rec_id})"
        else:
            desc = f"Performed {action.replace('_', ' ').title()} on {tbl} (ID: {rec_id})"

        report_data.append({
            "log_id": r[0],
            "timestamp": r[4].isoformat() if hasattr(r[4], 'isoformat') and r[4] else str(r[4]),
            "action": action,
            "entity_type": tbl,
            "record_id": rec_id,
            "ip_address": ip,
            "user_id": r[6],
            "username": uname,
            "description": desc,
            "status": "SUCCESS"
        })
    print(f"Audit Trail fetched {len(report_data)} events. Sample:")
    print(json.dumps(report_data[0], indent=2))
    return report_data

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
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        # Footer text
        footer_text = f"SIMS • Smart Inventory Management System  |  Historical Report Archive  |  Page {self._pageNumber} of {page_count}"
        self.drawString(36, 25, footer_text)
        self.drawRightString(self._pagesize[0] - 36, 25, "Confidential • Internal Use Only")
        # Line above footer
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 36, self._pagesize[0] - 36, 36)
        self.restoreState()

def test_pdf_build():
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b")
    )
    sub_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b")
    )

    story = [
        Paragraph("SIMS Historical Report: Audit Trail Snapshot", title_style),
        Paragraph("Generated on 2026-10-10 • Report ID #999 • Confidential", sub_style),
        Spacer(1, 15),
    ]

    table_data = [
        ["Log ID", "Timestamp", "User", "Action", "Entity", "Record ID", "IP Address", "Description"]
    ]
    for i in range(15):
        table_data.append([
            f"#{i+1}",
            "2026-10-10 14:00",
            "demo_owner",
            "USER_UPDATED",
            "Users",
            "23",
            "127.0.0.1",
            f"Updated user record #{i+1} in Users table."
        ])

    t = Table(table_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    doc.build(story, canvasmaker=NumberedCanvas)
    pdf_bytes = pdf_buffer.getvalue()
    print(f"PDF built successfully! Size: {len(pdf_bytes)} bytes.")
    
    # Parse with pypdf to verify validity
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    print(f"pypdf successfully read PDF! Pages count: {len(reader.pages)}")
    text_content = reader.pages[0].extract_text()
    assert "SIMS Historical Report" in text_content
    print("PDF text extraction verified!")

if __name__ == '__main__':
    test_audit_trail_fetch()
    test_pdf_build()
