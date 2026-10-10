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

    def test_10_phase2_owner_and_manager_generate_and_retrieve_snapshot(self):
        """Phase 2: Owner and Manager can generate a report and retrieve its saved snapshot"""
        # 1. Owner generates report
        payload_owner = {
            "report_name": "Phase 2 Owner Snapshot Test",
            "report_type": "Inventory"
        }
        resp_gen_own = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json=payload_owner
        )
        self.assertEqual(resp_gen_own.status_code, 201)
        data_gen_own = resp_gen_own.get_json()
        report_id_own = data_gen_own["report"]["report_id"]
        self.assertTrue(data_gen_own["report"].get("has_snapshot"))

        # Owner retrieves report detail
        resp_get_own = self.client.get(
            f"/api/reports/{report_id_own}",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_get_own.status_code, 200)
        detail_own = resp_get_own.get_json()
        self.assertEqual(detail_own["report_id"], report_id_own)
        self.assertEqual(detail_own["report_name"], "Phase 2 Owner Snapshot Test")
        self.assertEqual(detail_own["report_type"], "Inventory")
        self.assertEqual(detail_own["generated_by"], self.owner_user_id)
        self.assertTrue(detail_own["has_snapshot"])
        self.assertIsNone(detail_own["message"])
        self.assertIsInstance(detail_own["snapshot"], list)
        self.assertGreater(len(detail_own["snapshot"]), 0)

        # 2. Manager generates report
        payload_mgr = {
            "report_name": "Phase 2 Manager Snapshot Test",
            "report_type": "Inventory"
        }
        resp_gen_mgr = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json=payload_mgr
        )
        self.assertEqual(resp_gen_mgr.status_code, 201)
        data_gen_mgr = resp_gen_mgr.get_json()
        report_id_mgr = data_gen_mgr["report"]["report_id"]
        self.assertTrue(data_gen_mgr["report"].get("has_snapshot"))

        # Manager retrieves report detail
        resp_get_mgr = self.client.get(
            f"/api/reports/{report_id_mgr}",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_get_mgr.status_code, 200)
        detail_mgr = resp_get_mgr.get_json()
        self.assertEqual(detail_mgr["report_id"], report_id_mgr)
        self.assertEqual(detail_mgr["generated_by"], self.manager_user_id)
        self.assertTrue(detail_mgr["has_snapshot"])
        self.assertIsInstance(detail_mgr["snapshot"], list)

    def test_11_phase2_detail_auth_and_rbac_restrictions(self):
        """Phase 2: GET /api/reports/<id> rejects anonymous, invalid token, employee, and supplier requests"""
        valid_id = 1

        # Anonymous request rejected with 401
        resp_anon = self.client.get(f"/api/reports/{valid_id}")
        self.assertEqual(resp_anon.status_code, 401)

        # Invalid token rejected with 401/422
        resp_bad = self.client.get(
            f"/api/reports/{valid_id}",
            headers={"Authorization": "Bearer fake_token_abc"}
        )
        self.assertIn(resp_bad.status_code, [401, 422])

        # Employee request rejected with 403
        resp_emp = self.client.get(
            f"/api/reports/{valid_id}",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_emp.status_code, 403)
        self.assertEqual(resp_emp.get_json().get("error"), "Access denied")

        # Supplier request rejected with 403
        resp_sup = self.client.get(
            f"/api/reports/{valid_id}",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp_sup.status_code, 403)
        self.assertEqual(resp_sup.get_json().get("error"), "Access denied")

    def test_12_phase2_invalid_and_nonexistent_report_ids(self):
        """Phase 2: Validation of report IDs (non-integer, <= 0 -> 400; non-existent -> 404)"""
        # Non-numeric IDs return 400
        for bad_id in ["abc", "null", "undefined", "12.34"]:
            resp = self.client.get(
                f"/api/reports/{bad_id}",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp.status_code, 400, f"Expected 400 for {bad_id}")
            self.assertEqual(resp.get_json().get("error"), "Invalid report ID")

        # Non-positive IDs return 400
        for non_pos in ["0", "-1", "-999"]:
            resp = self.client.get(
                f"/api/reports/{non_pos}",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp.status_code, 400, f"Expected 400 for {non_pos}")
            self.assertEqual(resp.get_json().get("error"), "Invalid report ID")

        # Non-existent ID returns 404
        resp_404 = self.client.get(
            "/api/reports/999999999",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_404.status_code, 404)
        self.assertEqual(resp_404.get_json().get("error"), "Report not found")

    def test_13_phase2_legacy_report_without_snapshot(self):
        """Phase 2: Legacy reports without snapshot remain accessible with explicit unavailable message"""
        # Report ID 1 is a legacy record with report_data IS NULL
        resp = self.client.get(
            "/api/reports/1",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["report_id"], 1)
        self.assertFalse(data["has_snapshot"])
        self.assertIsNone(data["snapshot"])
        self.assertEqual(data["message"], "Historical snapshot data is unavailable for this report")
        self.assertIsNotNone(data["report_name"])
        self.assertIsNotNone(data["generated_on"])

    def test_14_phase2_snapshot_immutability_against_live_inventory_changes(self):
        """Phase 2: Historical snapshot remains unchanged when live inventory changes; live inventory is NOT queried"""
        # Generate a report with known snapshot data
        resp_gen = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"report_name": "Immutability Test Report", "report_type": "Inventory"}
        )
        self.assertEqual(resp_gen.status_code, 201)
        report_id = resp_gen.get_json()["report"]["report_id"]
        original_snapshot = resp_gen.get_json()["data"]

        # When viewing the historical report, ensure fetch_inventory_report_data is NEVER called
        with patch("app.services.team3.report_service.fetch_inventory_report_data") as mock_fetch:
            resp_get = self.client.get(
                f"/api/reports/{report_id}",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp_get.status_code, 200)
            mock_fetch.assert_not_called()  # Confirms no silent re-generation

            data = resp_get.get_json()
            self.assertTrue(data["has_snapshot"])
            self.assertEqual(len(data["snapshot"]), len(original_snapshot))
            self.assertEqual(data["snapshot"][0]["product_id"], original_snapshot[0]["product_id"])

    def test_15_phase2_persistence_error_handling(self):
        """Phase 2: Database persistence errors during generation roll back and return 500 without false success"""
        mock_items = [
            {
                "product_id": 1,
                "product_name": "Item 1",
                "sku": "SKU1",
                "quantity_available": 10,
                "reorder_level": 5,
                "unit_price": 10.0,
                "inventory_value": 100.0,
                "status": "Active",
                "stock_status": "IN STOCK",
                "category_name": "Cat",
                "last_updated": None
            }
        ]

        with patch("app.services.team3.report_service.fetch_inventory_report_data", return_value=(mock_items, None, 200)):
            with patch("app.services.team3.report_service.get_db_connection") as mock_db:
                mock_conn = mock_db.return_value
                mock_cursor = mock_conn.cursor.return_value
                # Make execute raise an exception during INSERT
                mock_cursor.execute.side_effect = Exception("Simulated DB Disk Failure")

                resp = self.client.post(
                    "/api/reports/generate",
                    headers={"Authorization": f"Bearer {self.owner_token}"},
                    json={"report_name": "Fail Test", "report_type": "Inventory"}
                )
    def test_16_phase4_stock_transactions_generation_and_retrieval_owner_and_manager(self):
        """Phase 4: Owner and Manager can generate and retrieve Stock Transactions reports with verified snapshot schema"""
        for role_name, token, user_id in [
            ("Owner", self.owner_token, self.owner_user_id),
            ("Manager", self.manager_token, self.manager_user_id)
        ]:
            with self.subTest(role=role_name):
                resp_gen = self.client.post(
                    "/api/reports/generate",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "report_name": f"Phase 4 Stock Transactions Test ({role_name})",
                        "report_type": "Stock Transactions"
                    }
                )
                self.assertEqual(resp_gen.status_code, 201)
                gen_data = resp_gen.get_json()
                self.assertIn("report", gen_data)
                self.assertEqual(gen_data["report"]["report_type"], "Stock Transactions")
                self.assertEqual(gen_data["report"]["generated_by"], user_id)
                self.assertTrue(gen_data["report"]["has_snapshot"])
                self.assertIsInstance(gen_data["data"], list)

                report_id = gen_data["report"]["report_id"]

                # Retrieve detail
                resp_detail = self.client.get(
                    f"/api/reports/{report_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(resp_detail.status_code, 200)
                detail = resp_detail.get_json()
                self.assertEqual(detail["report_id"], report_id)
                self.assertEqual(detail["report_type"], "Stock Transactions")
                self.assertTrue(detail["has_snapshot"])
                self.assertIsInstance(detail["snapshot"], list)

                # Validate snapshot item schema if transactions exist
                if len(detail["snapshot"]) > 0:
                    first_tx = detail["snapshot"][0]
                    self.assertIn("transaction_id", first_tx)
                    self.assertIn("product_id", first_tx)
                    self.assertIn("product_name", first_tx)
                    self.assertIn("sku", first_tx)
                    self.assertIn("transaction_type", first_tx)
                    self.assertIn("quantity", first_tx)
                    self.assertIn("transaction_date", first_tx)
                    self.assertIn("performed_by", first_tx)
                    self.assertIn("notes", first_tx)

    def test_17_phase4_purchase_orders_generation_and_retrieval_owner_and_manager(self):
        """Phase 4: Owner and Manager can generate and retrieve Purchase Orders reports with verified nested PO schema"""
        for role_name, token, user_id in [
            ("Owner", self.owner_token, self.owner_user_id),
            ("Manager", self.manager_token, self.manager_user_id)
        ]:
            with self.subTest(role=role_name):
                resp_gen = self.client.post(
                    "/api/reports/generate",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "report_name": f"Phase 4 Purchase Orders Test ({role_name})",
                        "report_type": "Purchase Orders"
                    }
                )
                self.assertEqual(resp_gen.status_code, 201)
                gen_data = resp_gen.get_json()
                self.assertIn("report", gen_data)
                self.assertEqual(gen_data["report"]["report_type"], "Purchase Orders")
                self.assertEqual(gen_data["report"]["generated_by"], user_id)
                self.assertTrue(gen_data["report"]["has_snapshot"])
                self.assertIsInstance(gen_data["data"], list)

                report_id = gen_data["report"]["report_id"]

                # Retrieve detail
                resp_detail = self.client.get(
                    f"/api/reports/{report_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(resp_detail.status_code, 200)
                detail = resp_detail.get_json()
                self.assertEqual(detail["report_id"], report_id)
                self.assertEqual(detail["report_type"], "Purchase Orders")
                self.assertTrue(detail["has_snapshot"])
                self.assertIsInstance(detail["snapshot"], list)

                # Validate snapshot PO item schema if POs exist
                if len(detail["snapshot"]) > 0:
                    first_po = detail["snapshot"][0]
                    self.assertIn("purchase_order_id", first_po)
                    self.assertIn("reference_number", first_po)
                    self.assertIn("supplier_id", first_po)
                    self.assertIn("supplier_name", first_po)
                    self.assertIn("order_date", first_po)
                    self.assertIn("total_amount", first_po)
                    self.assertIn("status", first_po)
                    self.assertIn("items", first_po)
                    self.assertIsInstance(first_po["items"], list)
                    if len(first_po["items"]) > 0:
                        first_line = first_po["items"][0]
                        self.assertIn("purchase_order_item_id", first_line)
                        self.assertIn("product_id", first_line)
                        self.assertIn("product_name", first_line)
                        self.assertIn("sku", first_line)
                        self.assertIn("quantity", first_line)
                        self.assertIn("unit_price", first_line)
                        self.assertIn("subtotal", first_line)

    def test_18_phase4_unsupported_report_type_rejection(self):
        """Unsupported report types return HTTP 400 Bad Request"""
        invalid_types = ["Shipments", "Audit Trail", "RandomType", ""]
        for bad_type in invalid_types:
            with self.subTest(report_type=bad_type):
                resp = self.client.post(
                    "/api/reports/generate",
                    headers={"Authorization": f"Bearer {self.owner_token}"},
                    json={"report_name": "Invalid Type Test", "report_type": bad_type}
                )
                self.assertEqual(resp.status_code, 400)
                err_msg = resp.get_json().get("error", "")
                self.assertTrue("Invalid report type" in err_msg or "required" in err_msg)

    def test_19_phase4_rbac_and_spoofed_identity_for_new_report_types(self):
        """Phase 4: Anonymous, Employee, and Supplier rejected; spoofed generated_by is strictly ignored"""
        for rep_type in ["Stock Transactions", "Purchase Orders"]:
            # Anonymous rejected with 401
            resp_anon = self.client.post(
                "/api/reports/generate",
                json={"report_name": f"Anon {rep_type}", "report_type": rep_type}
            )
            self.assertEqual(resp_anon.status_code, 401)

            # Employee rejected with 403
            resp_emp = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {self.employee_token}"},
                json={"report_name": f"Emp {rep_type}", "report_type": rep_type}
            )
            self.assertEqual(resp_emp.status_code, 403)

            # Supplier rejected with 403
            resp_sup = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {self.supplier_token}"},
                json={"report_name": f"Sup {rep_type}", "report_type": rep_type}
            )
            self.assertEqual(resp_sup.status_code, 403)

            # Spoofed identity ignored for Owner
            resp_spoof = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {self.owner_token}"},
                json={
                    "report_name": f"Spoof Test {rep_type}",
                    "report_type": rep_type,
                    "generated_by": 999999  # Attempted spoof
                }
            )
            self.assertEqual(resp_spoof.status_code, 201)
            self.assertEqual(resp_spoof.get_json()["report"]["generated_by"], self.owner_user_id)

    def test_20_phase4_historical_detail_does_not_query_underlying_tables(self):
        """Phase 4: Historical detail retrieval does NOT query live transaction or PO tables"""
        # Create a Stock Transactions report
        resp_tx = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"report_name": "Historical Immutability TX", "report_type": "Stock Transactions"}
        )
        self.assertEqual(resp_tx.status_code, 201)
        tx_id = resp_tx.get_json()["report"]["report_id"]

        with patch("app.services.team3.report_service.fetch_stock_transactions_report_data") as mock_tx_fetch:
            resp_get_tx = self.client.get(
                f"/api/reports/{tx_id}",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp_get_tx.status_code, 200)
            mock_tx_fetch.assert_not_called()

        # Create a Purchase Orders report
        resp_po = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"report_name": "Historical Immutability PO", "report_type": "Purchase Orders"}
        )
        self.assertEqual(resp_po.status_code, 201)
        po_id = resp_po.get_json()["report"]["report_id"]

        with patch("app.services.team3.report_service.fetch_purchase_orders_report_data") as mock_po_fetch:
            resp_get_po = self.client.get(
                f"/api/reports/{po_id}",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp_get_po.status_code, 200)
            mock_po_fetch.assert_not_called()

    def test_21_phase4_persistence_failure_rollback(self):
        """Phase 4: Database persistence errors for new report types roll back and return 500"""
        mock_data = [{"item": 1}]
        fetchers = {
            "Stock Transactions": "app.services.team3.report_service.fetch_stock_transactions_report_data",
            "Purchase Orders": "app.services.team3.report_service.fetch_purchase_orders_report_data"
        }
        for rep_type, fetcher_target in fetchers.items():
            with patch(fetcher_target, return_value=(mock_data, None, 200)):
                with patch("app.services.team3.report_service.get_db_connection") as mock_db:
                    mock_conn = mock_db.return_value
                    mock_cursor = mock_conn.cursor.return_value
                    mock_cursor.execute.side_effect = Exception("Simulated DB Write Error")

                    resp = self.client.post(
                        "/api/reports/generate",
                        headers={"Authorization": f"Bearer {self.owner_token}"},
                        json={"report_name": f"Fail {rep_type}", "report_type": rep_type}
                    )
                    self.assertEqual(resp.status_code, 500)
                    self.assertEqual(resp.get_json().get("error"), "Failed to create report record")
                    mock_conn.rollback.assert_called_once()

    def test_22_phase5_quotations_report_generation_and_retrieval(self):
        """Phase 5: Owner and Manager can generate and retrieve Quotations reports with valid snapshots"""
        for token, user_id, role_label in [
            (self.owner_token, self.owner_user_id, "Owner"),
            (self.manager_token, self.manager_user_id, "Manager")
        ]:
            resp = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "report_name": f"Test Quotations Report {role_label}",
                    "report_type": "Quotations"
                }
            )
            self.assertEqual(resp.status_code, 201)
            body = resp.get_json()
            self.assertIn("report", body)
            report_meta = body["report"]
            self.assertEqual(report_meta["report_type"], "Quotations")
            self.assertEqual(report_meta["generated_by"], user_id)
            self.assertTrue(report_meta["has_snapshot"])
            report_id = report_meta["report_id"]

            # Verify historical detail retrieval
            resp_detail = self.client.get(
                f"/api/reports/{report_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(resp_detail.status_code, 200)
            detail = resp_detail.get_json()
            self.assertTrue(detail["has_snapshot"])
            self.assertIsInstance(detail["snapshot"], list)
            if len(detail["snapshot"]) > 0:
                first_q = detail["snapshot"][0]
                self.assertIn("quotation_id", first_q)
                self.assertIn("quotation_number", first_q)
                self.assertIn("supplier_id", first_q)
                self.assertIn("supplier_name", first_q)
                self.assertIn("status", first_q)
                self.assertIn("total_amount", first_q)
                self.assertIn("items", first_q)
                self.assertIsInstance(first_q["items"], list)
                if len(first_q["items"]) > 0:
                    first_line = first_q["items"][0]
                    self.assertIn("product_id", first_line)
                    self.assertIn("product_name", first_line)
                    self.assertIn("quoted_quantity", first_line)
                    self.assertIn("unit_price", first_line)
                    self.assertIn("subtotal", first_line)

    def test_23_phase5_supplier_performance_report_generation_and_retrieval(self):
        """Phase 5: Owner and Manager can generate and retrieve Supplier Performance reports with explainable metrics"""
        for token, user_id, role_label in [
            (self.owner_token, self.owner_user_id, "Owner"),
            (self.manager_token, self.manager_user_id, "Manager")
        ]:
            resp = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "report_name": f"Test Supplier Performance {role_label}",
                    "report_type": "Supplier Performance"
                }
            )
            self.assertEqual(resp.status_code, 201)
            body = resp.get_json()
            report_meta = body["report"]
            self.assertEqual(report_meta["report_type"], "Supplier Performance")
            self.assertEqual(report_meta["generated_by"], user_id)
            self.assertTrue(report_meta["has_snapshot"])
            report_id = report_meta["report_id"]

            # Verify historical detail retrieval
            resp_detail = self.client.get(
                f"/api/reports/{report_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(resp_detail.status_code, 200)
            detail = resp_detail.get_json()
            self.assertTrue(detail["has_snapshot"])
            self.assertIsInstance(detail["snapshot"], list)
            if len(detail["snapshot"]) > 0:
                first_sup = detail["snapshot"][0]
                self.assertIn("supplier_id", first_sup)
                self.assertIn("supplier_name", first_sup)
                self.assertIn("total_purchase_orders", first_sup)
                self.assertIn("total_order_value", first_sup)
                self.assertIn("total_quotations", first_sup)
                self.assertIn("quotation_response_rate", first_sup)
                self.assertIn("total_shipments", first_sup)
                self.assertIn("metric_definitions", first_sup)

    def test_24_phase5_unsupported_report_type_and_date_validation(self):
        """Phase 5: Rejects unsupported types and invalid date ranges with HTTP 400"""
        # Unsupported report type
        resp_bad_type = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"report_name": "Audit Test", "report_type": "Audit Trail"}
        )
        self.assertEqual(resp_bad_type.status_code, 400)
        self.assertIn("Invalid report type", resp_bad_type.get_json().get("error", ""))

        # Invalid date format
        resp_bad_date = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={
                "report_name": "Bad Date Test",
                "report_type": "Quotations",
                "start_date": "not-a-date"
            }
        )
        self.assertEqual(resp_bad_date.status_code, 400)
        self.assertIn("Invalid start_date format", resp_bad_date.get_json().get("error", ""))

        # Reversed date range
        resp_rev_date = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={
                "report_name": "Reversed Date Test",
                "report_type": "Quotations",
                "start_date": "2026-12-31",
                "end_date": "2026-01-01"
            }
        )
        self.assertEqual(resp_rev_date.status_code, 400)
        self.assertIn("Start date cannot be after end date", resp_rev_date.get_json().get("error", ""))

    def test_25_phase5_rbac_and_spoofed_identity_for_phase5_types(self):
        """Phase 5: Anonymous, Employee, and Supplier rejected; spoofed generated_by is strictly ignored"""
        for rep_type in ["Quotations", "Supplier Performance"]:
            # Anonymous rejected with 401
            resp_anon = self.client.post(
                "/api/reports/generate",
                json={"report_name": f"Anon {rep_type}", "report_type": rep_type}
            )
            self.assertEqual(resp_anon.status_code, 401)

            # Employee rejected with 403
            resp_emp = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {self.employee_token}"},
                json={"report_name": f"Emp {rep_type}", "report_type": rep_type}
            )
            self.assertEqual(resp_emp.status_code, 403)

            # Supplier rejected with 403
            resp_sup = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {self.supplier_token}"},
                json={"report_name": f"Sup {rep_type}", "report_type": rep_type}
            )
            self.assertEqual(resp_sup.status_code, 403)

            # Spoofed identity ignored for Owner
            resp_spoof = self.client.post(
                "/api/reports/generate",
                headers={"Authorization": f"Bearer {self.owner_token}"},
                json={
                    "report_name": f"Spoof Test {rep_type}",
                    "report_type": rep_type,
                    "generated_by": 999999
                }
            )
            self.assertEqual(resp_spoof.status_code, 201)
            self.assertEqual(resp_spoof.get_json()["report"]["generated_by"], self.owner_user_id)

    def test_26_phase5_historical_detail_does_not_query_underlying_tables(self):
        """Phase 5: Historical detail retrieval does NOT query live quotation or supplier tables"""
        # Create a Quotations report
        resp_q = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"report_name": "Historical Immutability Quotations", "report_type": "Quotations"}
        )
        self.assertEqual(resp_q.status_code, 201)
        q_id = resp_q.get_json()["report"]["report_id"]

        with patch("app.services.team3.report_service.fetch_quotations_report_data") as mock_q_fetch:
            resp_get_q = self.client.get(
                f"/api/reports/{q_id}",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp_get_q.status_code, 200)
            mock_q_fetch.assert_not_called()

        # Create a Supplier Performance report
        resp_sp = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"report_name": "Historical Immutability Supplier Perf", "report_type": "Supplier Performance"}
        )
        self.assertEqual(resp_sp.status_code, 201)
        sp_id = resp_sp.get_json()["report"]["report_id"]

        with patch("app.services.team3.report_service.fetch_supplier_performance_report_data") as mock_sp_fetch:
            resp_get_sp = self.client.get(
                f"/api/reports/{sp_id}",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp_get_sp.status_code, 200)
            mock_sp_fetch.assert_not_called()

    def test_27_phase5_persistence_failure_rollback(self):
        """Phase 5: Database persistence errors for Phase 5 report types roll back and return 500"""
        mock_data = [{"supplier_id": 1}]
        fetchers = {
            "Quotations": "app.services.team3.report_service.fetch_quotations_report_data",
            "Supplier Performance": "app.services.team3.report_service.fetch_supplier_performance_report_data"
        }
        for rep_type, fetcher_target in fetchers.items():
            with patch(fetcher_target, return_value=(mock_data, None, 200)):
                with patch("app.services.team3.report_service.get_db_connection") as mock_db:
                    mock_conn = mock_db.return_value
                    mock_cursor = mock_conn.cursor.return_value
                    mock_cursor.execute.side_effect = Exception("Simulated DB Write Error")

                    resp = self.client.post(
                        "/api/reports/generate",
                        headers={"Authorization": f"Bearer {self.owner_token}"},
                        json={"report_name": f"Fail {rep_type}", "report_type": rep_type}
                    )
                    self.assertEqual(resp.status_code, 500)
                    self.assertEqual(resp.get_json().get("error"), "Failed to create report record")
                    mock_conn.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()


