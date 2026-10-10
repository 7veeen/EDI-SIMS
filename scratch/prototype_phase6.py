import sys
import io
import json
import csv
import re
import xml.sax.saxutils as saxutils
from datetime import datetime
from decimal import Decimal

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.pdfgen import canvas
import pypdf

sys.path.insert(0, 'backend')
from app.extensions import get_db_connection
from app.services.team3.report_service import (
    fetch_inventory_report_data,
    fetch_stock_transactions_report_data,
    fetch_purchase_orders_report_data,
    fetch_quotations_report_data,
    fetch_supplier_performance_report_data
)

def sanitize_filename(name):
    clean = re.sub(r'[^a-zA-Z0-9_\- ]', '', str(name or 'report'))
    clean = clean.strip().replace(' ', '_').lower()
    return clean or 'report'

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
        try:
            float(stripped)
            return value
        except ValueError:
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
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        # Footer
        footer_text = f"SIMS • Smart Inventory Management System  |  Historical Report Archive  |  Page {self._pageNumber} of {page_count}"
        self.drawString(36, 22, footer_text)
        self.drawRightString(self._pagesize[0] - 36, 22, "Confidential • Internal Use Only")
        # Line above footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 32, self._pagesize[0] - 36, 32)
        self.restoreState()

def test_all():
    print("=== Testing prototype phase 6 ===")
    
    # 1. Test CSV Sanitization
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("   +cmd") == "'+cmd"
    assert sanitize_csv_cell("@SUM(A1)") == "'@SUM(A1)"
    assert sanitize_csv_cell("-calc") == "'-calc"
    assert sanitize_csv_cell("-15") == "-15"
    assert sanitize_csv_cell("-12.50") == "-12.50"
    assert sanitize_csv_cell("+100") == "+100"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"
    print(" [PASS] CSV Sanitization rules verified!")

    # 2. Fetch mock or live data for each of the 6 report types
    inv_data, _, _ = fetch_inventory_report_data()
    st_data, _, _ = fetch_stock_transactions_report_data()
    po_data, _, _ = fetch_purchase_orders_report_data()
    q_data, _, _ = fetch_quotations_report_data()
    sp_data, _, _ = fetch_supplier_performance_report_data()
    
    print(f" Data counts: Inv={len(inv_data)}, ST={len(st_data)}, PO={len(po_data)}, Q={len(q_data)}, SP={len(sp_data)}")

if __name__ == '__main__':
    test_all()
