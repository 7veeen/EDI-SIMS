import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team3.audit_service import (
    log_audit_event,
    get_all_audit_logs
)
from app.services.team2.stock_request_service import (
    create_stock_request,
    respond_to_stock_request
)
from app.services.team2.supplier_service import (
    create_supplier,
    update_supplier,
    delete_supplier
)
from app.services.team3.dashboard_service import get_owner_dashboard


class AuditLogsModernizationTestCase(unittest.TestCase):
    """
    Focused unit & integration verification suite for SIMS Improvement 6 — Audit Logs Modernization (Phase 2).
    Zero live writes against Supabase (all mutations and queries mocked).
    Covers all 14 required verification scenarios.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def _create_mock_conn(self):
        """Create a mock database connection and cursor with transaction control."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit = MagicMock()
        mock_conn.rollback = MagicMock()
        return mock_conn, mock_cursor

    # -------------------------------------------------------------------------
    # SCENARIO 1: Stock Request creation produces STOCK_REQUEST_CREATED
    # -------------------------------------------------------------------------
    @patch("app.services.team2.stock_request_service.get_db_connection")
    @patch("app.services.team3.audit_service.log_audit_event")
    def test_01_stock_request_creation_audit(self, mock_audit, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Mock supplier lookup, product lookup, max id, insert return
        mock_cursor.fetchone.side_effect = [
            (5, "Acme Supplies"),        # Supplier exists
            (10, "Steel Rod", "SKU-10"), # Product exists
            (101,),                      # Next request ID
            (102, datetime.now())        # Inserted stock_request_id
        ]
        mock_audit.return_value = (901, None)

        payload = {
            "supplier_id": 5,
            "items": [{"product_id": 10, "quantity": 25}],
            "priority": "High",
            "required_date": "2026-11-01",
            "notes": "Urgent construction materials"
        }

        res, err = create_stock_request(requested_by_user_id=2, data=payload)
        self.assertIsNone(err)
        self.assertIsNotNone(res)
        self.assertEqual(res["stock_request_id"], 102)

        # Verify audit call
        mock_audit.assert_called_once()
        k_args = mock_audit.call_args[1]
        self.assertEqual(k_args["action"], "STOCK_REQUEST_CREATED")
        self.assertEqual(k_args["table_name"], "StockRequests")
        self.assertEqual(k_args["record_id"], 102)
        self.assertEqual(k_args["user_id"], 2)
        self.assertEqual(k_args["cursor"], mock_cursor)
        mock_conn.commit.assert_called_once()

    # -------------------------------------------------------------------------
    # SCENARIO 2: Stock Request response produces STOCK_REQUEST_RESPONDED
    # -------------------------------------------------------------------------
    @patch("app.services.team2.stock_request_service.get_db_connection")
    @patch("app.services.team3.audit_service.log_audit_event")
    @patch("app.services.team3.notification_service.create_notification")
    def test_02_stock_request_response_audit(self, mock_notif, mock_audit, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Mock select for update, items, update returning
        mock_cursor.fetchone.side_effect = [
            (102, "SR-2026-0102", 5, "Pending", 2), # Request row
            ("SR-2026-0102", "Accepted", datetime.now()) # Update row
        ]
        mock_cursor.fetchall.return_value = [(10, 25)]
        mock_audit.return_value = (902, None)

        payload = {"action": "Accept", "notes": "Fulfillment scheduled"}
        res, err = respond_to_stock_request(stock_request_id=102, user_id=6, role="Manager", data=payload)

        self.assertIsNone(err)
        self.assertEqual(res["status"], "Accepted")

        # Verify audit call
        mock_audit.assert_called_once()
        k_args = mock_audit.call_args[1]
        self.assertEqual(k_args["action"], "STOCK_REQUEST_RESPONDED")
        self.assertEqual(k_args["table_name"], "StockRequests")
        self.assertEqual(k_args["record_id"], 102)
        self.assertEqual(k_args["user_id"], 6)
        self.assertEqual(k_args["cursor"], mock_cursor)
        mock_conn.commit.assert_called_once()

    # -------------------------------------------------------------------------
    # SCENARIO 3 & 4: Supplier CRUD produces expected audit events & cursor
    # -------------------------------------------------------------------------
    @patch("app.services.team2.supplier_service.get_db_connection")
    @patch("app.services.team3.audit_service.log_audit_event")
    def test_03_supplier_create_audit(self, mock_audit, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Name uniqueness check returns None, insert returns new row
        mock_cursor.fetchone.side_effect = [
            None,
            (42, "Apex Fasteners", "John Apex", "555-0199", "john@apex.com", "Active", None)
        ]
        mock_audit.return_value = (903, None)

        data = {"supplier_name": "Apex Fasteners", "contact_person": "John Apex", "phone": "555-0199", "email": "john@apex.com"}
        res, err = create_supplier(data)
        self.assertIsNone(err)
        self.assertEqual(res["supplier_id"], 42)

        mock_audit.assert_called_once()
        k_args = mock_audit.call_args[1]
        self.assertEqual(k_args["action"], "CREATE_SUPPLIER")
        self.assertEqual(k_args["table_name"], "Suppliers")
        self.assertEqual(k_args["record_id"], 42)
        self.assertEqual(k_args["cursor"], mock_cursor)
        mock_conn.commit.assert_called_once()

    @patch("app.services.team2.supplier_service.get_db_connection")
    @patch("app.services.team3.audit_service.log_audit_event")
    def test_04_supplier_update_audit(self, mock_audit, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Existence check returns row, update returning
        mock_cursor.fetchone.side_effect = [
            (42, "Apex Fasteners", "Active", None),
            (42, "Apex Fasteners Global", "John Apex", "555-0199", "john@apex.com", "Active", None)
        ]
        mock_audit.return_value = (904, None)

        data = {"contact_person": "John Apex Updated"}
        res, err = update_supplier(42, data)
        self.assertIsNone(err)
        self.assertEqual(res["supplier_id"], 42)

        mock_audit.assert_called_once()
        k_args = mock_audit.call_args[1]
        self.assertEqual(k_args["action"], "UPDATE_SUPPLIER")
        self.assertEqual(k_args["table_name"], "Suppliers")
        self.assertEqual(k_args["record_id"], 42)
        self.assertEqual(k_args["cursor"], mock_cursor)
        mock_conn.commit.assert_called_once()

    @patch("app.services.team2.supplier_service.get_db_connection")
    @patch("app.services.team3.audit_service.log_audit_event")
    def test_05_supplier_delete_audit_hard_and_soft(self, mock_audit, mock_get_conn):
        # Case A: Hard delete when zero references
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            (42, "Apex Fasteners", "Active"), # Exists
            (0,), # PO count = 0
            (0,), # Quotation count = 0
            (0,)  # Shipment count = 0
        ]
        mock_audit.return_value = (905, None)

        res, err = delete_supplier(42)
        self.assertIsNone(err)
        self.assertTrue(res.get("deleted"))
        mock_audit.assert_called_once()
        self.assertEqual(mock_audit.call_args[1]["action"], "DELETE_SUPPLIER")
        self.assertEqual(mock_audit.call_args[1]["record_id"], 42)
        self.assertEqual(mock_audit.call_args[1]["cursor"], mock_cursor)
        mock_conn.commit.assert_called_once()

        # Case B: Soft deactivate when references exist
        mock_audit.reset_mock()
        mock_cursor.fetchone.side_effect = [
            (42, "Apex Fasteners", "Active"), # Exists
            (2,), # PO count = 2
            (1,), # Quotation count = 1
            (0,)  # Shipment count = 0
        ]
        res_soft, err_soft = delete_supplier(42)
        self.assertIsNone(err_soft)
        self.assertTrue(res_soft.get("deactivated"))
        mock_audit.assert_called_once()
        self.assertEqual(mock_audit.call_args[1]["action"], "DELETE_SUPPLIER")
        self.assertEqual(mock_audit.call_args[1]["record_id"], 42)

    # -------------------------------------------------------------------------
    # SCENARIO 5, 6, 7: Search, Action, Entity, and Date Filtering
    # -------------------------------------------------------------------------
    @patch("app.services.team3.audit_service.get_db_connection")
    def test_06_search_and_filters_sql_parameterization(self, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.return_value = (15,) # Count = 15
        mock_cursor.fetchall.return_value = [
            (10, 1, "STOCK_IN", "StockTransactions", 100, datetime.now(), "127.0.0.1", "demo_owner", "Owner")
        ]

        # Execute search with keyword, action, table, start date, and end date
        res, err = get_all_audit_logs(
            search="owner",
            action="STOCK_IN",
            table_name="StockTransactions",
            start_date="2026-10-01",
            end_date="2026-10-12",
            page=1,
            limit=20
        )
        self.assertIsNone(err)
        self.assertEqual(res["total"], 15)
        self.assertEqual(res["total_pages"], 1)

        # Inspect executed queries to verify parameterized clauses
        self.assertEqual(mock_cursor.execute.call_count, 2)
        count_call_args = mock_cursor.execute.call_args_list[0]
        data_call_args = mock_cursor.execute.call_args_list[1]

        count_sql, count_params = count_call_args[0]
        data_sql, data_params = data_call_args[0]

        # Verify safe parameterization
        self.assertIn("al.action_time >= %s", count_sql)
        self.assertIn("al.action_time <= %s", count_sql)
        self.assertIn("UPPER(al.action) = %s", count_sql)
        self.assertIn("LOWER(al.table_name) = LOWER(%s)", count_sql)
        self.assertIn("u.username ILIKE %s", count_sql)
        self.assertIn("CAST(al.record_id AS TEXT) ILIKE %s", count_sql)

        # Verify inclusive end-date parameter
        self.assertEqual(count_params[0], "2026-10-01 00:00:00")
        self.assertEqual(count_params[1], "2026-10-12 23:59:59.999999")
        self.assertEqual(count_params[2], "STOCK_IN")
        self.assertEqual(count_params[3], "StockTransactions")

    # -------------------------------------------------------------------------
    # SCENARIO 8: Pagination calculations
    # -------------------------------------------------------------------------
    @patch("app.services.team3.audit_service.get_db_connection")
    def test_07_pagination_page_and_total_pages(self, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Test case A: total = 125, limit = 50 -> total_pages = 3
        mock_cursor.fetchone.return_value = (125,)
        mock_cursor.fetchall.return_value = []

        res_a, err_a = get_all_audit_logs(page=2, limit=50)
        self.assertIsNone(err_a)
        self.assertEqual(res_a["total"], 125)
        self.assertEqual(res_a["page"], 2)
        self.assertEqual(res_a["limit"], 50)
        self.assertEqual(res_a["total_pages"], 3)

        # Test case B: total = 0 -> total_pages = 0
        mock_cursor.fetchone.return_value = (0,)
        res_b, err_b = get_all_audit_logs(page=1, limit=50)
        self.assertIsNone(err_b)
        self.assertEqual(res_b["total"], 0)
        self.assertEqual(res_b["total_pages"], 0)

    # -------------------------------------------------------------------------
    # SCENARIO 9: Invalid page, limit, and date inputs handled safely
    # -------------------------------------------------------------------------
    def test_08_invalid_query_parameters_safety(self):
        # Invalid page
        res, err = get_all_audit_logs(page=0)
        self.assertIsNone(res)
        self.assertIn("Invalid page", err)

        res, err = get_all_audit_logs(page="invalid")
        self.assertIsNone(res)
        self.assertIn("Invalid page", err)

        # Invalid limit
        res, err = get_all_audit_logs(limit=0)
        self.assertIsNone(res)
        self.assertIn("Invalid limit", err)

        res, err = get_all_audit_logs(limit=105)
        self.assertIsNone(res)
        self.assertIn("Invalid limit", err)

        # Invalid dates
        res, err = get_all_audit_logs(start_date="2026/10/01")
        self.assertIsNone(res)
        self.assertIn("Invalid start_date format", err)

        res, err = get_all_audit_logs(end_date="not-a-date")
        self.assertIsNone(res)
        self.assertIn("Invalid end_date format", err)

        # Start date after end date
        res, err = get_all_audit_logs(start_date="2026-10-20", end_date="2026-10-10")
        self.assertIsNone(res)
        self.assertIn("Start date cannot be after end date", err)

    # -------------------------------------------------------------------------
    # SCENARIO 10: Actor role join returns role_name correctly
    # -------------------------------------------------------------------------
    @patch("app.services.team3.audit_service.get_db_connection")
    def test_09_actor_role_join_returned(self, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.return_value = (1,)
        mock_cursor.fetchall.return_value = [
            (99, 1, "LOGIN", "Users", 1, datetime(2026, 10, 12, 10, 0, 0), "192.168.1.1", "demo_owner", "Owner")
        ]

        res, err = get_all_audit_logs(page=1, limit=10)
        self.assertIsNone(err)
        self.assertEqual(len(res["logs"]), 1)
        item = res["logs"][0]
        self.assertEqual(item["username"], "demo_owner")
        self.assertEqual(item["role_name"], "Owner")

    # -------------------------------------------------------------------------
    # SCENARIO 11: Owner-only authorization remains enforced on API route
    # -------------------------------------------------------------------------
    def test_10_owner_only_authorization_on_route(self):
        # 1. Anonymous request (no token) -> 401
        resp_anon = self.client.get("/api/audit-logs/")
        self.assertEqual(resp_anon.status_code, 401)

        # 2. Invalid inputs from Owner produce 400
        from flask_jwt_extended import create_access_token
        owner_token = create_access_token(identity="1", additional_claims={"role": "Owner"})
        mgr_token = create_access_token(identity="2", additional_claims={"role": "Manager"})

        resp_mgr = self.client.get("/api/audit-logs/", headers={"Authorization": f"Bearer {mgr_token}"})
        self.assertEqual(resp_mgr.status_code, 403)

        resp_invalid_page = self.client.get("/api/audit-logs/?page=-5", headers={"Authorization": f"Bearer {owner_token}"})
        self.assertEqual(resp_invalid_page.status_code, 400)
        self.assertIn("error", resp_invalid_page.get_json())

    # -------------------------------------------------------------------------
    # SCENARIO 12: Owner Dashboard consumer compatibility
    # -------------------------------------------------------------------------
    @patch("app.services.team3.dashboard_service.get_db_connection")
    def test_11_owner_dashboard_recent_audits_compatibility(self, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Mock sequence of fetchall and fetchone for get_owner_dashboard
        mock_cursor.fetchall.side_effect = [
            [], # 1. Users breakdown
            [], # 5. PurchaseOrders breakdown
            [], # 7. Recent purchase orders
            [], # 11A. Pending quotations
            [], # 11B. Low stock products
            [], # 11C. Pending purchase orders
            [(1, "STOCK_IN", "demo_owner", datetime.now(), "StockTransactions", 101, "127.0.0.1")] # 12. Recent audit logs
        ]
        mock_cursor.fetchone.side_effect = [
            (5,), # 2. Total suppliers
            (10, 50, 1000.0, 2, 0), # 3. Inventory health
            (10, 5, 15), # 4. Stock movement throughput
            (1,), # 6. Pending quotations count
            (1, 1, 1, 3), # 8. Shipments
            None, # 9. Latest backup
            (1, "Database", "Healthy", 100, "OK", datetime.now()) # 10. System health
        ]

        stats = get_owner_dashboard()
        self.assertIn("recent_audits", stats)
        self.assertIsInstance(stats["recent_audits"], list)
        self.assertEqual(len(stats["recent_audits"]), 1)
        self.assertEqual(stats["recent_audits"][0]["username"], "demo_owner")

    # -------------------------------------------------------------------------
    # SCENARIO 13: XSS protections verified in frontend audit template
    # -------------------------------------------------------------------------
    def test_12_xss_protection_in_frontend_template(self):
        # Inspect audit-logs.js source code to verify Utils.escapeHtml wraps all rendered fields
        js_path = os.path.join(backend_dir, "..", "frontend", "js", "pages", "audit-logs.js")
        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        self.assertIn("Utils.escapeHtml(userDisplay)", js_content)
        self.assertIn("Utils.escapeHtml(l.action", js_content)
        self.assertIn("Utils.escapeHtml(l.table_name", js_content)
        self.assertIn("Utils.escapeHtml(recordIdDisplay)", js_content)
        self.assertIn("Utils.escapeHtml(l.ip_address", js_content)
        self.assertIn("Utils.escapeHtml(String(logItem.log_id", js_content)

    # -------------------------------------------------------------------------
    # SCENARIO 14: Audit insert failure preserves transaction atomicity (rollback)
    # -------------------------------------------------------------------------
    @patch("app.services.team2.stock_request_service.get_db_connection")
    @patch("app.services.team3.audit_service.log_audit_event")
    def test_13_audit_failure_triggers_transaction_rollback(self, mock_audit, mock_get_conn):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            (5, "Acme Supplies"),
            (10, "Steel Rod", "SKU-10"),
            (101,),
            (102, datetime.now())
        ]
        # Simulate audit logging failure raising an exception on the transaction cursor
        from psycopg2 import DatabaseError
        mock_audit.side_effect = DatabaseError("Simulated disk error during audit logging")

        payload = {
            "supplier_id": 5,
            "items": [{"product_id": 10, "quantity": 10}]
        }

        res, err = create_stock_request(requested_by_user_id=2, data=payload)
        self.assertIsNone(res)
        self.assertIsNotNone(err)
        # Transaction must have been rolled back
        mock_conn.rollback.assert_called_once()
        # Commit must NOT have been called
        mock_conn.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
