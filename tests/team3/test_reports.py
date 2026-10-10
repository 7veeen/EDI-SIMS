import unittest
import json
import csv
import io
import re
from decimal import Decimal
from unittest.mock import patch

# Import create_app from backend
import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.extensions import get_db_connection
from app.services.team3.report_service import sanitize_csv_cell, generate_inventory_csv_export


class Team3ReportsAndExportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login and obtain tokens for each role
        cls.owner_token, cls.owner_user_id = cls._get_token_and_id("demo_owner", "password123")
        cls.manager_token, cls.manager_user_id = cls._get_token_and_id("demo_manager", "password123")
        cls.employee_token, cls.employee_user_id = cls._get_token_and_id("demo_employee", "password123")
        cls.supplier_token, cls.supplier_user_id = cls._get_token_and_id("demo_supplier", "password123")

    @classmethod
    def _get_token_and_id(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        user = data.get("user") or {}
        return data.get("access_token"), user.get("user_id")

    def test_01_existing_report_list_and_status(self):
        """Test GET /api/reports/ and GET /api/reports/status require Owner or Manager auth"""
        # Anonymous requests are rejected with 401
        resp_anon_list = self.client.get("/api/reports/")
        self.assertEqual(resp_anon_list.status_code, 401)

        resp_anon_status = self.client.get("/api/reports/status")
        self.assertEqual(resp_anon_status.status_code, 401)

        # Manager authorized
        resp_mgr_list = self.client.get(
            "/api/reports/",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr_list.status_code, 200)
        reports = resp_mgr_list.get_json()
        self.assertIsInstance(reports, list)

        resp_mgr_status = self.client.get(
            "/api/reports/status",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr_status.status_code, 200)
        status_data = resp_mgr_status.get_json()
        self.assertIn("status", status_data)
        self.assertIn("progress", status_data)
        self.assertEqual(status_data["status"], "READY")

        # Owner authorized
        resp_own_list = self.client.get(
            "/api/reports/",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_own_list.status_code, 200)

        resp_own_status = self.client.get(
            "/api/reports/status",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_own_status.status_code, 200)

    def test_02_existing_report_generation(self):
        """Test POST /api/reports/generate derives identity from verified JWT"""
        # Anonymous request rejected with 401
        payload = {
            "report_name": "Automated Test Inventory Report",
            "report_type": "Inventory"
        }
        resp_anon = self.client.post("/api/reports/generate", json=payload)
        self.assertEqual(resp_anon.status_code, 401)

        # Manager request authorized; generated_by is derived from Manager JWT identity
        resp_mgr = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json=payload
        )
        self.assertEqual(resp_mgr.status_code, 201)
        data = resp_mgr.get_json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Report generated successfully")
        self.assertIn("report", data)
        self.assertEqual(data["report"]["generated_by"], self.manager_user_id)
        self.assertIn("data", data)
        self.assertIsInstance(data["data"], list)
        self.assertGreater(len(data["data"]), 0)

        # Verify item structure preserves existing keys
        first_item = data["data"][0]
        for key in ["product_id", "product_name", "sku", "quantity_available", "reorder_level", "status", "stock_status"]:
            self.assertIn(key, first_item)
        # Verify enhanced keys
        for key in ["category_name", "unit_price", "inventory_value"]:
            self.assertIn(key, first_item)

    def test_03_csv_export_owner_and_manager_success(self):
        """Test GET /api/reports/export returns valid CSV for Owner and Manager"""
        for token_role, token in [("Owner", self.owner_token), ("Manager", self.manager_token)]:
            with self.subTest(role=token_role):
                resp = self.client.get(
                    "/api/reports/export",
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(resp.status_code, 200)
                self.assertIn("text/csv", resp.content_type)

                # Verify Content-Disposition header
                disposition = resp.headers.get("Content-Disposition", "")
                self.assertIn("attachment", disposition)
                self.assertIn("filename=", disposition)

                # Extract filename
                match = re.search(r'filename="?([^";]+)"?', disposition)
                self.assertIsNotNone(match)
                filename = match.group(1)
                self.assertTrue(filename.startswith("current_inventory_report_"))
                self.assertTrue(filename.endswith(".csv"))

                # Check UTF-8 BOM encoding for Excel compatibility
                raw_bytes = resp.data
                self.assertTrue(raw_bytes.startswith(b'\xef\xbb\xbf'), "CSV must start with UTF-8 BOM for Excel")

                # Parse CSV content
                csv_text = raw_bytes.decode('utf-8-sig')
                reader = csv.reader(io.StringIO(csv_text))
                rows = list(reader)

                self.assertGreater(len(rows), 1, "CSV must contain header and at least 1 data row")

                # Verify Column Headers
                expected_headers = [
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
                ]
                self.assertEqual(rows[0], expected_headers)

                # Verify data rows
                for row in rows[1:]:
                    self.assertEqual(len(row), len(expected_headers))
                    product_id, name, sku, category, qty, reorder, price, inv_val, stock_stat, status, last_upd = row

                    qty_int = int(qty)
                    reorder_int = int(reorder)
                    price_dec = Decimal(price)
                    inv_val_dec = Decimal(inv_val)

                    # Verify inventory calculation: value = qty * price
                    self.assertEqual(inv_val_dec, (qty_int * price_dec))

                    # Verify stock status
                    expected_stock_stat = "LOW STOCK" if qty_int <= reorder_int else "IN STOCK"
                    self.assertEqual(stock_stat, expected_stock_stat)

    def test_04_csv_export_endpoint_alias(self):
        """Test GET /api/reports/export/csv alias also works"""
        resp = self.client.get(
            "/api/reports/export/csv",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.content_type)

    def test_05_unauthorized_requests_rejected(self):
        """Test that unauthorized requests across all report endpoints are properly rejected"""
        endpoints = [
            ("GET", "/api/reports/"),
            ("GET", "/api/reports/status"),
            ("POST", "/api/reports/generate"),
            ("GET", "/api/reports/export"),
            ("GET", "/api/reports/export/csv"),
        ]

        for method, ep in endpoints:
            with self.subTest(endpoint=ep, check="no_token"):
                resp = self.client.open(ep, method=method, json={})
                self.assertEqual(resp.status_code, 401, f"{ep} allowed without token")

            with self.subTest(endpoint=ep, check="bad_token"):
                resp = self.client.open(
                    ep,
                    method=method,
                    headers={"Authorization": "Bearer invalid_garbage_token"},
                    json={}
                )
                self.assertIn(resp.status_code, [401, 422], f"{ep} allowed with bad token")

            with self.subTest(endpoint=ep, check="employee_forbidden"):
                resp = self.client.open(
                    ep,
                    method=method,
                    headers={"Authorization": f"Bearer {self.employee_token}"},
                    json={"report_name": "Test", "report_type": "Inventory"}
                )
                self.assertEqual(resp.status_code, 403, f"{ep} allowed Employee")
                self.assertEqual(resp.get_json().get("error"), "Access denied")

            with self.subTest(endpoint=ep, check="supplier_forbidden"):
                resp = self.client.open(
                    ep,
                    method=method,
                    headers={"Authorization": f"Bearer {self.supplier_token}"},
                    json={"report_name": "Test", "report_type": "Inventory"}
                )
                self.assertEqual(resp.status_code, 403, f"{ep} allowed Supplier")
                self.assertEqual(resp.get_json().get("error"), "Access denied")

    def test_06_inventory_not_ready_status_returns_423(self):
        """Test that 423 Locked is returned if Inventory status is not READY (isolated test without DB mutation)"""
        mock_locked_response = (
            None,
            {
                "error": "Report generation locked",
                "status": "SYNCING",
                "progress": 45,
                "message": "Synchronizing inventory database"
            },
            423
        )

        with patch("app.routes.team3.reports.generate_inventory_report_record", return_value=mock_locked_response):
            resp_gen = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {self.owner_token}"},
                json={"report_name": "Locked Test", "report_type": "Inventory"}
            )
            self.assertEqual(resp_gen.status_code, 423)
            data_gen = resp_gen.get_json()
            self.assertEqual(data_gen.get("error"), "Report generation locked")
            self.assertEqual(data_gen.get("status"), "SYNCING")

        with patch("app.routes.team3.reports.generate_inventory_csv_export", return_value=(None, {"error": "Report generation locked", "status": "SYNCING"}, 423)):
            resp_exp = self.client.get(
                "/api/reports/export",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp_exp.status_code, 423)
            data_exp = resp_exp.get_json()
            self.assertEqual(data_exp.get("error"), "Report generation locked")

    def test_07_existing_dashboard_endpoints(self):
        """Test existing dashboard endpoints continue functioning without regression"""
        # Owner dashboard
        resp_owner = self.client.get(
            "/api/dashboard/owner",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_owner.status_code, 200)

        # Manager dashboard
        resp_mgr = self.client.get(
            "/api/dashboard/manager",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr.status_code, 200)

        # Employee dashboard
        resp_emp = self.client.get(
            "/api/dashboard/employee",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_emp.status_code, 200)

        # Supplier dashboard
        resp_sup = self.client.get(
            "/api/dashboard/supplier",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp_sup.status_code, 200)

    def test_08_identity_spoofing_prevention(self):
        """Test that client-supplied generated_by is completely ignored and verified JWT identity is used"""
        # Case A: Manager submits forged Owner ID in body
        resp_mgr_spoof = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={
                "report_name": "Manager Identity Test",
                "report_type": "Inventory",
                "generated_by": self.owner_user_id  # Client forging Owner ID
            }
        )
        self.assertEqual(resp_mgr_spoof.status_code, 201)
        data_mgr = resp_mgr_spoof.get_json()
        # Must be Manager ID, NOT Owner ID
        self.assertEqual(data_mgr["report"]["generated_by"], self.manager_user_id)
        self.assertNotEqual(data_mgr["report"]["generated_by"], self.owner_user_id)

        # Case B: Owner submits forged Employee ID in body
        resp_own_spoof = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={
                "report_name": "Owner Identity Test",
                "report_type": "Inventory",
                "generated_by": self.employee_user_id  # Client forging Employee ID
            }
        )
        self.assertEqual(resp_own_spoof.status_code, 201)
        data_own = resp_own_spoof.get_json()
        # Must be Owner ID, NOT Employee ID
        self.assertEqual(data_own["report"]["generated_by"], self.owner_user_id)
        self.assertNotEqual(data_own["report"]["generated_by"], self.employee_user_id)

        # Case C: Validation error if report_name or report_type missing
        resp_no_name = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={"report_type": "Inventory"}
        )
        self.assertEqual(resp_no_name.status_code, 400)
        self.assertIn("error", resp_no_name.get_json())

        resp_no_type = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={"report_name": "No Type Report"}
        )
        self.assertEqual(resp_no_type.status_code, 400)
        self.assertIn("error", resp_no_type.get_json())

    def test_09_csv_formula_injection_sanitization(self):
        """Comprehensive verification of CSV formula injection protection (CWE-1236)"""
        # 1. Normal product names and categories
        self.assertEqual(sanitize_csv_cell("Dell Wireless Mouse"), "Dell Wireless Mouse")
        self.assertEqual(sanitize_csv_cell("Office Supplies"), "Office Supplies")

        # 2. Text beginning with '='
        self.assertEqual(sanitize_csv_cell("=1+1"), "'=1+1")
        self.assertEqual(sanitize_csv_cell("=cmd|' /C calc'!A0"), "'=cmd|' /C calc'!A0")

        # 3. Text beginning with '+'
        self.assertEqual(sanitize_csv_cell("+12345"), "'+12345")
        self.assertEqual(sanitize_csv_cell("+SUM(A1:B1)"), "'+SUM(A1:B1)")

        # 4. Text beginning with '-'
        self.assertEqual(sanitize_csv_cell("-Discount SKU"), "'-Discount SKU")
        self.assertEqual(sanitize_csv_cell("-10% Promo"), "'-10% Promo")

        # 5. Text beginning with '@'
        self.assertEqual(sanitize_csv_cell("@special_sku"), "'@special_sku")
        self.assertEqual(sanitize_csv_cell("@SUM(1,2)"), "'@SUM(1,2)")

        # 6. Dangerous prefixes preceded by whitespace
        self.assertEqual(sanitize_csv_cell("   =2+2"), "'   =2+2")
        self.assertEqual(sanitize_csv_cell("  +command"), "'  +command")
        self.assertEqual(sanitize_csv_cell("   -danger"), "'   -danger")

        # 7. Leading tabs and relevant control characters
        self.assertEqual(sanitize_csv_cell("\t=cmd"), "'\t=cmd")
        self.assertEqual(sanitize_csv_cell("\t@SUM"), "'\t@SUM")

        # 8. Embedded and leading carriage returns / newlines
        self.assertEqual(sanitize_csv_cell("\r\n+test"), "'\r\n+test")
        self.assertEqual(sanitize_csv_cell("\n=calc"), "'\n=calc")

        # 9. Multiline text not starting with formula prefix
        multiline = "Line 1\r\nLine 2"
        self.assertEqual(sanitize_csv_cell(multiline), multiline)

        # 10. Commas and double quotes
        quotes_val = 'Widget, "Deluxe" Model'
        self.assertEqual(sanitize_csv_cell(quotes_val), quotes_val)

        # 11. Unicode and non-English text
        unicode_val = "Café Münch Büch € 🚀"
        self.assertEqual(sanitize_csv_cell(unicode_val), unicode_val)

        # 12. Empty strings and null values
        self.assertEqual(sanitize_csv_cell(""), "")
        self.assertEqual(sanitize_csv_cell(None), "")

        # 13. Numeric values: ensure non-strings are returned untouched
        self.assertEqual(sanitize_csv_cell(123), 123)
        self.assertEqual(sanitize_csv_cell(-50), -50)
        self.assertEqual(sanitize_csv_cell(99.99), 99.99)

        # 14. Full CSV export pipeline with malicious values
        mock_malicious_data = [
            {
                "product_id": 999,
                "product_name": "=cmd|' /C calc'!A0",
                "sku": "   @SUM(1,2)",
                "category_name": "+Electronics",
                "quantity_available": 10,
                "reorder_level": 5,
                "unit_price": Decimal("100.00"),
                "inventory_value": Decimal("1000.00"),
                "stock_status": "IN STOCK",
                "status": "-Active",
                "last_updated": None
            }
        ]

        with patch("app.services.team3.report_service.fetch_inventory_report_data", return_value=(mock_malicious_data, None, 200)):
            result, err, code = generate_inventory_csv_export()
            self.assertEqual(code, 200)
            self.assertIsNone(err)
            csv_bytes, filename = result

            # Verify UTF-8 BOM
            self.assertTrue(csv_bytes.startswith(b'\xef\xbb\xbf'))

            # Parse decoded CSV
            csv_str = csv_bytes.decode('utf-8-sig')
            reader = list(csv.reader(io.StringIO(csv_str)))
            self.assertEqual(len(reader), 2)  # Header + 1 row

            row = reader[1]
            # Verify neutralized cells
            self.assertEqual(row[1], "'=cmd|' /C calc'!A0")
            self.assertEqual(row[2], "'   @SUM(1,2)")
            self.assertEqual(row[3], "'+Electronics")
            self.assertEqual(row[4], "10")  # Quantity remains unquoted number
            self.assertEqual(row[5], "5")   # Reorder level remains unquoted number
            self.assertEqual(row[6], "100.00")
            self.assertEqual(row[7], "1000.00")
            self.assertEqual(row[8], "IN STOCK")
            self.assertEqual(row[9], "'-Active")


if __name__ == "__main__":
    unittest.main()

