import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.extensions import get_db_connection


class Team3BackupsTestCase(unittest.TestCase):
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

    def test_01_public_access_denied_for_anonymous_requests(self):
        """Test unauthenticated GET and POST requests are rejected with 401 Unauthorized"""
        resp_get = self.client.get("/api/backups/")
        self.assertEqual(resp_get.status_code, 401)

        resp_post = self.client.post("/api/backups/", json={})
        self.assertEqual(resp_post.status_code, 401)

    def test_02_access_denied_for_unauthorized_roles(self):
        """Test Manager, Employee, and Supplier roles are rejected with 403 Forbidden"""
        for token, role_name in [
            (self.manager_token, "Manager"),
            (self.employee_token, "Employee"),
            (self.supplier_token, "Supplier")
        ]:
            resp_get = self.client.get(
                "/api/backups/",
                headers={"Authorization": f"Bearer {token}"}
            )
            self.assertEqual(resp_get.status_code, 403, f"{role_name} should receive 403 on GET")

            resp_post = self.client.post(
                "/api/backups/",
                headers={"Authorization": f"Bearer {token}"},
                json={}
            )
            self.assertEqual(resp_post.status_code, 403, f"{role_name} should receive 403 on POST")

    def test_03_owner_get_backup_history(self):
        """Test Owner role can retrieve backup history with enriched metadata"""
        resp = self.client.get(
            "/api/backups/",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        first = data[0]
        expected_keys = {
            "backup_id", "backup_name", "backup_type",
            "backup_date", "backup_size", "created_by",
            "status", "creator_username"
        }
        self.assertTrue(expected_keys.issubset(first.keys()))
        self.assertIn(first["status"], ["Success", "Failed"])

    def test_04_owner_create_backup_validation(self):
        """Test backup creation validation rejects invalid user ID"""
        resp = self.client.post(
            "/api/backups/",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"created_by": 999999}
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertEqual(data.get("error"), "Invalid user_id")

    def test_05_backup_artifact_schema_coverage(self):
        """Test latest backup artifact exists, is valid JSON, and covers all core tables"""
        backups_dir = os.path.abspath(os.path.join(backend_dir, "backups"))
        self.assertTrue(os.path.exists(backups_dir), "Backups directory must exist")

        json_files = sorted([f for f in os.listdir(backups_dir) if f.endswith(".json")])
        self.assertGreater(len(json_files), 0, "At least one backup artifact should exist")

        latest_file = os.path.join(backups_dir, json_files[-1])
        self.assertGreater(os.path.getsize(latest_file), 0)

        with open(latest_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        self.assertIsInstance(backup_data, dict)
        core_tables = [
            "Users", "Roles", "Categories", "Products", "Inventory",
            "PurchaseOrders", "PurchaseOrderItems", "Shipments",
            "StockRequests", "StockRequestItems", "StockTransactions",
            "Suppliers", "SupplierQuotations", "AuditLogs",
            "SystemStatus", "Reports", "Notifications"
        ]
        for tbl in core_tables:
            self.assertIn(tbl, backup_data, f"Table {tbl} must be present in backup")
            self.assertIsInstance(backup_data[tbl], list)

    def test_06_database_error_handling(self):
        """Test database failure during backup returns 500 without crashing"""
        with patch("app.routes.team3.backups.get_db_connection") as mock_conn:
            mock_conn.side_effect = Exception("Simulated DB connection failure")

            resp = self.client.get(
                "/api/backups/",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            # In get_backups, unhandled error in route produces 500
            self.assertIn(resp.status_code, [500])


if __name__ == "__main__":
    unittest.main()
