import unittest
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team3.dashboard_service import (
    get_owner_dashboard,
    get_manager_dashboard,
    get_employee_dashboard,
    get_supplier_dashboard,
)


class DashboardConsolidationTestCase(unittest.TestCase):
    """
    Test suite for SIMS Phase 2 Step 2: Dashboard Query Consolidation.
    Validates consolidated query responses, data types, null handling,
    empty collection safety, and role isolation.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login tokens
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

    def test_owner_dashboard_structure_and_types(self):
        """Owner dashboard returns correct consolidated scalar metrics and list collections."""
        with self.app.app_context():
            data = get_owner_dashboard()
            self.assertIsInstance(data, dict)

            # Backward-compatible scalar keys
            self.assertIsInstance(data["total_users"], int)
            self.assertIsInstance(data["total_suppliers"], int)
            self.assertIsInstance(data["total_products"], int)
            self.assertIsInstance(data["total_inventory_value"], (int, float))
            self.assertIsInstance(data["recent_audits"], list)

            # Extended executive metrics
            self.assertIsInstance(data["active_pos_count"], int)
            self.assertIsInstance(data["active_pos_value"], (int, float))
            self.assertIsInstance(data["total_pos_count"], int)
            self.assertIsInstance(data["pending_quotations_count"], int)
            self.assertIsInstance(data["low_stock_count"], int)
            self.assertIsInstance(data["out_of_stock_count"], int)
            self.assertIsInstance(data["active_users_count"], int)
            self.assertIsInstance(data["inactive_users_count"], int)
            self.assertIsInstance(data["users_by_role"], dict)
            self.assertIsInstance(data["po_status_breakdown"], dict)
            self.assertIsInstance(data["recent_orders"], list)
            self.assertIsInstance(data["shipment_stats"], dict)
            self.assertIsInstance(data["inventory_health"], dict)
            self.assertIsInstance(data["attention_items"], list)

            # Audit items contract
            for audit in data["recent_audits"]:
                self.assertIn("log_id", audit)
                self.assertIn("action", audit)
                self.assertIn("username", audit)
                self.assertIn("timestamp", audit)
                self.assertIn("details", audit)

            # Attention items contract
            for item in data["attention_items"]:
                self.assertIn("type", item)
                self.assertIn("id", item)
                self.assertIn("title", item)
                self.assertIn("subtitle", item)
                self.assertIn("status", item)
                self.assertIn("badge", item)
                self.assertIn("action_label", item)
                self.assertIn("action_route", item)

    def test_manager_dashboard_structure_and_types(self):
        """Manager dashboard returns correct consolidated metrics, attention items, and lists."""
        with self.app.app_context():
            data = get_manager_dashboard()
            self.assertIsInstance(data, dict)

            self.assertIsInstance(data["active_pos"], int)
            self.assertIsInstance(data["pending_po_value"], (int, float))
            self.assertIsInstance(data["low_stock_count"], int)
            self.assertIsInstance(data["pending_quotations"], int)
            self.assertIsInstance(data["pending_deliveries"], int)
            self.assertIsInstance(data["shipment_stats"], dict)
            self.assertIsInstance(data["attention_items"], list)
            self.assertIsInstance(data["recent_orders"], list)
            self.assertIsInstance(data["critical_low_stock"], list)
            self.assertIsInstance(data["stock_requests_overview"], dict)
            self.assertIsInstance(data["recent_stock_requests"], list)
            self.assertIsInstance(data["recent_stock_movement"], int)
            self.assertIsInstance(data["recent_transactions"], list)
            self.assertIsInstance(data["recent_activity"], list)

            # Verify shipment stats structure
            ship_stats = data["shipment_stats"]
            for key in ["ready_for_shipment", "dispatched", "in_transit", "delayed", "delivered", "total"]:
                self.assertIn(key, ship_stats)
                self.assertIsInstance(ship_stats[key], int)

            # Verify stock requests overview structure
            sr_overview = data["stock_requests_overview"]
            for key in ["pending", "quoted", "rejected", "total"]:
                self.assertIn(key, sr_overview)
                self.assertIsInstance(sr_overview[key], int)

    def test_employee_dashboard_unauthenticated_safety(self):
        """Employee dashboard safely returns catalog stats when user_id is None."""
        with self.app.app_context():
            data = get_employee_dashboard(None)
            self.assertIsInstance(data, dict)
            self.assertIsInstance(data["total_products"], int)
            self.assertIsInstance(data["total_stock"], int)
            self.assertIsInstance(data["stock_in"], int)
            self.assertIsInstance(data["stock_out"], int)
            self.assertIsInstance(data["low_stock_products"], list)
            self.assertEqual(data["tasks"], [])
            self.assertEqual(data["assigned_shipments"], [])
            self.assertEqual(data["assigned_shipments_count"], 0)

    def test_employee_dashboard_authenticated_isolation(self):
        """Employee dashboard properly scopes tasks, shipments, and transactions to authenticated employee."""
        resp = self.client.get(
            "/api/dashboard/employee",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)

        self.assertEqual(data["employee_name"], "demo_employee")
        self.assertIsInstance(data["employee_id"], int)
        self.assertIsInstance(data["assigned_shipments"], list)
        self.assertIsInstance(data["attention_items"], list)
        self.assertIsInstance(data["recent_transactions"], list)
        self.assertIsInstance(data["tasks"], list)

        # Verify all shipments belong to this employee
        for shp in data["assigned_shipments"]:
            self.assertIn("shipment_id", shp)
            self.assertIn("shipment_number", shp)
            self.assertIn("can_stock_in", shp)
            self.assertIsInstance(shp["can_stock_in"], bool)

        # Verify attention items structure
        for att in data["attention_items"]:
            self.assertEqual(att["type"], "shipment_receiving")
            self.assertIn("shipment_id", att)
            self.assertIn("title", att)
            self.assertIn("priority", att)

    def test_supplier_dashboard_authenticated_isolation(self):
        """Supplier dashboard properly isolates metrics and lists to authenticated supplier profile."""
        resp = self.client.get(
            "/api/dashboard/supplier",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)

        self.assertIn("supplier_id", data)
        self.assertIn("supplier_name", data)
        self.assertIsInstance(data["open_requests"], int)
        self.assertIsInstance(data["total_requests"], int)
        self.assertIsInstance(data["pending_quotations"], int)
        self.assertIsInstance(data["approved_quotations"], int)
        self.assertIsInstance(data["total_quotations"], int)
        self.assertIsInstance(data["active_pos"], int)
        self.assertIsInstance(data["total_purchase_orders"], int)
        self.assertIsInstance(data["total_order_value"], (int, float))
        self.assertIsInstance(data["shipment_stats"], dict)
        self.assertIsInstance(data["attention_items"], list)
        self.assertIsInstance(data["recent_stock_requests"], list)
        self.assertIsInstance(data["recent_orders"], list)
        self.assertIsInstance(data["recent_activity"], list)

    def test_supplier_dashboard_nonexistent_profile_returns_error(self):
        """Supplier dashboard returns error when non-supplier user_id is requested."""
        with self.app.app_context():
            data, error = get_supplier_dashboard(999999)
            self.assertIsNone(data)
            self.assertEqual(error, "Supplier profile not found for authenticated user.")

    def test_null_and_empty_list_safety(self):
        """Consolidated dashboards handle empty or null values gracefully without throwing."""
        with self.app.app_context():
            # Employee with dummy non-existent ID
            data = get_employee_dashboard(999999)
            self.assertIsInstance(data, dict)
            self.assertEqual(data["assigned_shipments"], [])
            self.assertEqual(data["tasks"], [])
            self.assertEqual(data["recent_transactions"], [])
            self.assertEqual(data["completed_stock_ins_count"], 0)


if __name__ == "__main__":
    unittest.main()
