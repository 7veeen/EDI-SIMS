import unittest
import json
import csv
import io
import re
from decimal import Decimal

# Import create_app from backend
import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.extensions import get_db_connection


class Team3ReportsAndExportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login and obtain tokens for each role
        cls.owner_token = cls._get_token("demo_owner", "password123")
        cls.manager_token = cls._get_token("demo_manager", "password123")
        cls.employee_token = cls._get_token("demo_employee", "password123")
        cls.supplier_token = cls._get_token("demo_supplier", "password123")

    @classmethod
    def _get_token(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        return data.get("access_token")

    def test_01_existing_report_list_and_status(self):
        """Test GET /api/reports/ and GET /api/reports/status"""
        # GET /api/reports/
        resp = self.client.get("/api/reports/")
        self.assertEqual(resp.status_code, 200)
        reports = resp.get_json()
        self.assertIsInstance(reports, list)

        # GET /api/reports/status
        resp = self.client.get("/api/reports/status")
        self.assertEqual(resp.status_code, 200)
        status_data = resp.get_json()
        self.assertIn("status", status_data)
        self.assertIn("progress", status_data)
        self.assertEqual(status_data["status"], "READY")

    def test_02_existing_report_generation(self):
        """Test POST /api/reports/generate maintains existing functionality"""
        payload = {
            "report_name": "Automated Test Inventory Report",
            "report_type": "Inventory",
            "generated_by": 1
        }
        resp = self.client.post("/api/reports/generate", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Report generated successfully")
        self.assertIn("report", data)
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
        """Test that unauthorized requests (no token, wrong role) are properly rejected"""
        # Case A: No token provided
        resp_no_token = self.client.get("/api/reports/export")
        self.assertEqual(resp_no_token.status_code, 401)

        # Case B: Invalid/garbage token
        resp_bad_token = self.client.get(
            "/api/reports/export",
            headers={"Authorization": "Bearer invalid_jwt_token_here"}
        )
        self.assertIn(resp_bad_token.status_code, [401, 422])

        # Case C: Employee role (not permitted to export reports)
        resp_emp = self.client.get(
            "/api/reports/export",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_emp.status_code, 403)
        self.assertEqual(resp_emp.get_json().get("error"), "Access denied")

        # Case D: Supplier role (not permitted to export reports)
        resp_sup = self.client.get(
            "/api/reports/export",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp_sup.status_code, 403)
        self.assertEqual(resp_sup.get_json().get("error"), "Access denied")

    def test_06_inventory_not_ready_status_returns_423(self):
        """Test that 423 Locked is returned if Inventory status is not READY"""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Temporarily simulate inventory sync / loading
            cursor.execute('''
                UPDATE "SystemStatus"
                SET status = 'SYNCING', message = 'Synchronizing inventory database'
                WHERE module_name = 'Inventory'
            ''')
            conn.commit()

            # Test POST /api/reports/generate returns 423
            resp_gen = self.client.post("/api/reports/generate", json={
                "report_name": "Locked Test",
                "report_type": "Inventory",
                "generated_by": 1
            })
            self.assertEqual(resp_gen.status_code, 423)
            data_gen = resp_gen.get_json()
            self.assertEqual(data_gen.get("error"), "Report generation locked")
            self.assertEqual(data_gen.get("status"), "SYNCING")

            # Test GET /api/reports/export returns 423
            resp_exp = self.client.get(
                "/api/reports/export",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp_exp.status_code, 423)
            data_exp = resp_exp.get_json()
            self.assertEqual(data_exp.get("error"), "Report generation locked")
            self.assertEqual(data_exp.get("status"), "SYNCING")

        finally:
            # Always restore status to READY
            cursor.execute('''
                UPDATE "SystemStatus"
                SET status = 'READY', progress = 100, message = 'Inventory is ready'
                WHERE module_name = 'Inventory'
            ''')
            conn.commit()
            cursor.close()
            conn.close()

        # Verify restoration succeeded
        resp_after = self.client.get(
            "/api/reports/export",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_after.status_code, 200)

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


if __name__ == "__main__":
    unittest.main()
