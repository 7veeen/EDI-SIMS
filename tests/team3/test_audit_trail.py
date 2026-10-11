import unittest
import json
import os
import sys
from decimal import Decimal
from unittest.mock import patch, MagicMock

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.extensions import get_db_connection
from app.services.team3.audit_service import (
    log_audit_event,
    get_authenticated_actor_id,
    get_client_ip,
    get_all_audit_logs
)
from app.services.team3.report_service import (
    fetch_audit_trail_report_data
)


class Phase8AuditTrailTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login and obtain tokens for each role
        cls.owner_token, cls.owner_user_id = cls._get_token_and_id("demo_owner", "password123")
        cls.manager_token, cls.manager_user_id = cls._get_token_and_id("demo_manager", "password123")
        cls.employee_token, cls.employee_user_id = cls._get_token_and_id("demo_employee", "password123")
        cls.supplier_token, cls.supplier_user_id = cls._get_token_and_id("demo_supplier", "password123")
        cls.demo_supplier_id = 5  # Demo Supplier Company

    @classmethod
    def _get_token_and_id(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        user = data.get("user") or {}
        return data.get("access_token"), user.get("user_id")

    # =========================================================================
    # STEP K1: SHARED AUDIT UTILITY TESTS
    # =========================================================================

    def test_01_shared_audit_utility_direct_insertion(self):
        """Test log_audit_event inserts a valid record with actor and timestamp."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            log_id, err = log_audit_event(
                action="TEST_ACTION_DIRECT",
                table_name="TestTable",
                record_id=99991,
                user_id=self.owner_user_id,
                cursor=cursor,
                ip_address="192.168.1.100"
            )
            self.assertIsNone(err)
            self.assertIsNotNone(log_id)
            conn.commit()

            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id, ip_address FROM public."AuditLogs" WHERE log_id = %s',
                (log_id,)
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], log_id)
            self.assertEqual(row[1], self.owner_user_id)
            self.assertEqual(row[2], "TEST_ACTION_DIRECT")
            self.assertEqual(row[3], "TestTable")
            self.assertEqual(row[4], 99991)
            self.assertEqual(row[5], "192.168.1.100")
        finally:
            cursor.close()
            conn.close()

    def test_02_actor_spoofing_prevention(self):
        """Test that client-supplied actor ID in payload is rejected in favor of verified JWT identity."""
        resp = self.client.post(
            "/api/inventory/stock-out",
            headers={"Authorization": f"Bearer {self.employee_token}"},
            json={
                "product_id": 1,
                "quantity": 1,
                "reason": "Spoof test",
                "user_id": 9999,  # Attempt to spoof actor
                "actor_id": 9999
            }
        )
        self.assertEqual(resp.status_code, 200)
        tx_id = resp.get_json()["transaction"]["transaction_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT user_id FROM public."AuditLogs" WHERE action = \'STOCK_OUT\' AND record_id = %s',
                (tx_id,)
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            # Must be the authenticated employee's user_id, NOT 9999
            self.assertEqual(row[0], self.employee_user_id)
            self.assertNotEqual(row[0], 9999)
        finally:
            cursor.close()
            conn.close()

    def test_03_sql_injection_safety_in_audit_utility(self):
        """Test SQL injection patterns in action, table_name, or ip_address are safely parameterized."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            injection_action = "ACTION'; DROP TABLE dummy; --"
            injection_table = 'Table" OR "1"="1'
            log_id, err = log_audit_event(
                action=injection_action,
                table_name=injection_table,
                record_id=123,
                user_id=self.manager_user_id,
                cursor=cursor,
                ip_address="127.0.0.1; SELECT 1;"
            )
            self.assertIsNone(err)
            self.assertIsNotNone(log_id)
            conn.commit()

            cursor.execute(
                'SELECT action, table_name, ip_address FROM public."AuditLogs" WHERE log_id = %s',
                (log_id,)
            )
            row = cursor.fetchone()
            self.assertEqual(row[0], injection_action.upper())
            self.assertEqual(row[1], injection_table)
            self.assertEqual(row[2], "127.0.0.1; SELECT 1;")
        finally:
            cursor.close()
            conn.close()

    def test_04_audit_failure_handling_and_logging(self):
        """Test that if audit log insertion fails on transaction cursor, exception propagates to protect transaction atomicity."""
        mock_cursor = MagicMock()
        from psycopg2 import DatabaseError
        mock_cursor.execute.side_effect = DatabaseError("Simulated DB Disk Failure")

        with self.assertRaises(DatabaseError):
            log_audit_event(
                action="FAIL_TEST",
                table_name="TestTable",
                record_id=1,
                user_id=self.owner_user_id,
                cursor=mock_cursor
            )

    def test_05_sensitive_data_exclusion(self):
        """Verify password hashes, tokens and secrets are never inserted into AuditLogs schema."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT column_name FROM information_schema.columns WHERE table_name = \'AuditLogs\' AND table_schema = \'public\''
            )
            columns = [c[0] for c in cursor.fetchall()]
            self.assertNotIn("password", columns)
            self.assertNotIn("password_hash", columns)
            self.assertNotIn("token", columns)
            self.assertNotIn("payload", columns)
        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # STEP K2: BUSINESS WORKFLOW & AUDIT INSTRUMENTATION TESTS
    # =========================================================================

    def test_06_stock_out_success_and_audit(self):
        """Test successful stock-out creates a STOCK_OUT audit record."""
        resp = self.client.post(
            "/api/inventory/stock-out",
            headers={"Authorization": f"Bearer {self.employee_token}"},
            json={
                "product_id": 1,
                "quantity": 1,
                "reason": "Damage",
                "notes": "Verified in Phase 8 test"
            }
        )
        self.assertEqual(resp.status_code, 200)
        tx_id = resp.get_json()["transaction"]["transaction_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'STOCK_OUT\' AND record_id = %s',
                (tx_id,)
            )
            audit = cursor.fetchone()
            self.assertIsNotNone(audit, "STOCK_OUT audit record must exist")
            self.assertEqual(audit[1], self.employee_user_id)
            self.assertEqual(audit[2], "STOCK_OUT")
            self.assertEqual(audit[3], "StockTransactions")
        finally:
            cursor.close()
            conn.close()

    def test_07_stock_out_failure_no_audit(self):
        """Test stock-out failure (insufficient stock) creates NO audit record."""
        resp = self.client.post(
            "/api/inventory/stock-out",
            headers={"Authorization": f"Bearer {self.employee_token}"},
            json={
                "product_id": 1,
                "quantity": 99999999,
                "reason": "Damage"
            }
        )
        self.assertEqual(resp.status_code, 400)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT count(*) FROM public."AuditLogs" WHERE action = \'STOCK_OUT\' AND record_id = 99999999'
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
        finally:
            cursor.close()
            conn.close()

    def test_08_stock_in_success_and_audit(self):
        """Test successful stock-in (goods receipt) creates a STOCK_IN audit record."""
        # 1. Create a PO with product 1
        resp_po = self.client.post(
            "/api/purchase-orders/",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={
                "supplier_id": self.demo_supplier_id,
                "expected_delivery": "2026-12-15",
                "items": [{"product_id": 1, "quantity": 5, "unit_price": 50.0}]
            }
        )
        self.assertEqual(resp_po.status_code, 201)
        po_id = resp_po.get_json()["purchase_order"]["purchase_order_id"]

        # 2. Supplier accepts PO
        self.client.patch(
            f"/api/purchase-orders/{po_id}/respond",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"response": "Accepted"}
        )

        # 3. Create shipment in In Transit state
        resp_ship = self.client.post(
            "/api/shipments/",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={
                "purchase_order_id": po_id,
                "carrier": "DHL Express",
                "tracking_number": "TRK-STOCKIN-001",
                "status": "In Transit"
            }
        )
        self.assertEqual(resp_ship.status_code, 201)
        shipment_id = resp_ship.get_json()["shipment"]["shipment_id"]

        # 4. Mark shipment as Delivered
        resp_del = self.client.patch(
            f"/api/shipments/{shipment_id}/status",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"status": "Delivered"}
        )
        self.assertEqual(resp_del.status_code, 200)

        # 5. Perform Stock-In
        resp_in = self.client.post(
            "/api/inventory/stock-in",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={
                "shipment_id": shipment_id,
                "product_id": 1,
                "quantity": 2,
                "notes": "Phase 8 goods receipt verified"
            }
        )
        self.assertEqual(resp_in.status_code, 200)
        tx_id = resp_in.get_json()["transaction"]["transaction_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'STOCK_IN\' AND record_id = %s',
                (tx_id,)
            )
            audit = cursor.fetchone()
            self.assertIsNotNone(audit, "STOCK_IN audit record must exist")
            self.assertEqual(audit[1], self.manager_user_id)
            self.assertEqual(audit[2], "STOCK_IN")
            self.assertEqual(audit[3], "StockTransactions")
        finally:
            cursor.close()
            conn.close()

    def test_09_adjust_inventory_success_and_audit(self):
        """Test adjust_inventory creates an INVENTORY_ADJUSTED audit record."""
        resp = self.client.put(
            "/api/inventory/1",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={
                "adjustment": 1,
                "type": "ADD",
                "notes": "Phase 8 inventory adjustment"
            }
        )
        self.assertEqual(resp.status_code, 200)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, user_id, action, table_name FROM public."AuditLogs" WHERE action = \'INVENTORY_ADJUSTED\' AND user_id = %s ORDER BY log_id DESC LIMIT 1',
                (self.manager_user_id,)
            )
            audit = cursor.fetchone()
            self.assertIsNotNone(audit, "INVENTORY_ADJUSTED audit record must exist")
            self.assertEqual(audit[1], self.manager_user_id)
            self.assertEqual(audit[2], "INVENTORY_ADJUSTED")
            self.assertEqual(audit[3], "Inventory")
        finally:
            cursor.close()
            conn.close()

    def test_10_purchase_order_creation_and_audit(self):
        """Test purchase order creation creates a PO_CREATED audit record."""
        po_payload = {
            "supplier_id": self.demo_supplier_id,
            "expected_delivery": "2026-12-01",
            "items": [
                {"product_id": 1, "quantity": 5, "unit_price": 50.0}
            ]
        }
        resp = self.client.post(
            "/api/purchase-orders/",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json=po_payload
        )
        self.assertEqual(resp.status_code, 201)
        po_id = resp.get_json()["purchase_order"]["purchase_order_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'PO_CREATED\' AND record_id = %s',
                (po_id,)
            )
            audit = cursor.fetchone()
            self.assertIsNotNone(audit, "PO_CREATED audit record must exist")
            self.assertEqual(audit[1], self.manager_user_id)
            self.assertEqual(audit[2], "PO_CREATED")
            self.assertEqual(audit[3], "PurchaseOrders")
        finally:
            cursor.close()
            conn.close()

    def test_11_purchase_order_status_change_and_audit(self):
        """Test supplier responding to PO (accept) creates PO_ACCEPTED audit record."""
        # 1. Create a PO for demo_supplier
        resp_po = self.client.post(
            "/api/purchase-orders/",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={
                "supplier_id": self.demo_supplier_id,
                "expected_delivery": "2026-12-01",
                "items": [{"product_id": 1, "quantity": 2, "unit_price": 80.0}]
            }
        )
        self.assertEqual(resp_po.status_code, 201)
        po_id = resp_po.get_json()["purchase_order"]["purchase_order_id"]

        # 2. Supplier responds with Accept
        resp_resp = self.client.patch(
            f"/api/purchase-orders/{po_id}/respond",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"response": "Accepted"}
        )
        self.assertEqual(resp_resp.status_code, 200)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'PO_ACCEPTED\' AND record_id = %s',
                (po_id,)
            )
            audit = cursor.fetchone()
            self.assertIsNotNone(audit, "PO_ACCEPTED audit record must exist")
            self.assertEqual(audit[1], self.supplier_user_id)
            self.assertEqual(audit[2], "PO_ACCEPTED")
            self.assertEqual(audit[3], "PurchaseOrders")
        finally:
            cursor.close()
            conn.close()

    def test_12_purchase_order_failed_transition_no_audit(self):
        """Test failed PO response transition does NOT create a false audit record."""
        resp = self.client.patch(
            "/api/purchase-orders/999999/respond",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"response": "Accepted"}
        )
        self.assertEqual(resp.status_code, 404)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT count(*) FROM public."AuditLogs" WHERE action = \'PO_ACCEPTED\' AND record_id = 999999'
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
        finally:
            cursor.close()
            conn.close()

    def test_13_quotation_workflow_and_audit(self):
        """Test quotation creation and rejection create corresponding audit records."""
        # 1. Create and accept a PO to enable quotation
        resp_po = self.client.post(
            "/api/purchase-orders/",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={
                "supplier_id": self.demo_supplier_id,
                "expected_delivery": "2026-12-05",
                "items": [{"product_id": 1, "quantity": 4, "unit_price": 60.0}]
            }
        )
        self.assertEqual(resp_po.status_code, 201)
        po_id = resp_po.get_json()["purchase_order"]["purchase_order_id"]

        self.client.patch(
            f"/api/purchase-orders/{po_id}/respond",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"response": "Accepted"}
        )

        # 2. Supplier creates quotation
        resp_q = self.client.post(
            "/api/quotations/",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={
                "purchase_order_id": po_id,
                "product_id": 1,
                "quoted_price": 55.0,
                "quantity": 4,
                "notes": "Quotation submitted in Phase 8"
            }
        )
        self.assertEqual(resp_q.status_code, 201)
        quot_id = resp_q.get_json()["quotation"]["quotation_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'QUOTATION_CREATED\' AND record_id = %s',
                (quot_id,)
            )
            audit_created = cursor.fetchone()
            self.assertIsNotNone(audit_created)
            self.assertEqual(audit_created[1], self.supplier_user_id)

            # 3. Manager rejects quotation
            resp_rej = self.client.post(
                f"/api/quotations/{quot_id}/reject",
                headers={"Authorization": f"Bearer {self.manager_token}"},
                json={"rejection_reason": "Price exceeds budget"}
            )
            self.assertEqual(resp_rej.status_code, 200)

            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'QUOTATION_REJECTED\' AND record_id = %s',
                (quot_id,)
            )
            audit_rej = cursor.fetchone()
            self.assertIsNotNone(audit_rej)
            self.assertEqual(audit_rej[1], self.manager_user_id)
        finally:
            cursor.close()
            conn.close()

    def test_14_shipment_workflow_and_audit(self):
        """Test shipment creation, employee assignment, and status update create audit records."""
        # 1. Create and accept a PO
        resp_po = self.client.post(
            "/api/purchase-orders/",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={
                "supplier_id": self.demo_supplier_id,
                "expected_delivery": "2026-12-10",
                "items": [{"product_id": 1, "quantity": 10, "unit_price": 40.0}]
            }
        )
        self.assertEqual(resp_po.status_code, 201)
        po_id = resp_po.get_json()["purchase_order"]["purchase_order_id"]

        self.client.patch(
            f"/api/purchase-orders/{po_id}/respond",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"response": "Accepted"}
        )

        # 2. Supplier creates shipment
        resp_ship = self.client.post(
            "/api/shipments/",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={
                "purchase_order_id": po_id,
                "carrier": "Blue Dart Express",
                "tracking_number": "TRK-PHASE8-9001",
                "package_count": 2
            }
        )
        self.assertEqual(resp_ship.status_code, 201)
        shipment_id = resp_ship.get_json()["shipment"]["shipment_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'SHIPMENT_CREATED\' AND record_id = %s',
                (shipment_id,)
            )
            audit_ship = cursor.fetchone()
            self.assertIsNotNone(audit_ship)
            self.assertEqual(audit_ship[1], self.supplier_user_id)

            # 3. Manager assigns employee (URL: /api/shipments/<id>/assign)
            resp_assign = self.client.post(
                f"/api/shipments/{shipment_id}/assign",
                headers={"Authorization": f"Bearer {self.manager_token}"},
                json={"employee_id": self.employee_user_id}
            )
            self.assertEqual(resp_assign.status_code, 200)

            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'EMPLOYEE_ASSIGNED\' AND record_id = %s',
                (shipment_id,)
            )
            audit_assign = cursor.fetchone()
            self.assertIsNotNone(audit_assign)
            self.assertEqual(audit_assign[1], self.manager_user_id)

            # 4. Supplier updates shipment status to In Transit
            resp_stat = self.client.patch(
                f"/api/shipments/{shipment_id}/status",
                headers={"Authorization": f"Bearer {self.supplier_token}"},
                json={"status": "In Transit"}
            )
            self.assertEqual(resp_stat.status_code, 200)

            cursor.execute(
                'SELECT log_id, user_id, action, table_name, record_id FROM public."AuditLogs" WHERE action = \'SHIPMENT_STATUS_CHANGED\' AND record_id = %s',
                (shipment_id,)
            )
            audit_stat = cursor.fetchone()
            self.assertIsNotNone(audit_stat)
            self.assertEqual(audit_stat[1], self.supplier_user_id)
        finally:
            cursor.close()
            conn.close()

    def test_15_product_and_category_lifecycle_audit(self):
        """Test category and product creation, update, and deactivation create audit records."""
        import time
        unique_suffix = int(time.time())
        # 1. Category Creation
        resp_cat = self.client.post(
            "/api/categories/",
            headers={"Authorization": f"Bearer {self.manager_token}"},
            json={"category_name": f"P8AudCat_{unique_suffix}", "description": "Category for Phase 8"}
        )
        self.assertEqual(resp_cat.status_code, 201)
        cat_id = resp_cat.get_json()["category"]["category_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id, action FROM public."AuditLogs" WHERE action = \'CREATE_CATEGORY\' AND record_id = %s',
                (cat_id,)
            )
            self.assertIsNotNone(cursor.fetchone())

            # 2. Category Update
            resp_upd_cat = self.client.put(
                f"/api/categories/{cat_id}",
                headers={"Authorization": f"Bearer {self.manager_token}"},
                json={"category_name": f"P8AudCatUpd_{unique_suffix}"}
            )
            self.assertEqual(resp_upd_cat.status_code, 200)
            cursor.execute(
                'SELECT log_id, action FROM public."AuditLogs" WHERE action = \'UPDATE_CATEGORY\' AND record_id = %s',
                (cat_id,)
            )
            self.assertIsNotNone(cursor.fetchone())

            # 3. Product Creation
            import time
            unique_sku = f"SKU-P8-{int(time.time())}"
            resp_prod = self.client.post(
                "/api/products/",
                headers={"Authorization": f"Bearer {self.manager_token}"},
                json={
                    "product_name": "Phase8AudProd",
                    "sku": unique_sku,
                    "category_id": cat_id,
                    "selling_price": 250.0,
                    "reorder_level": 5
                }
            )
            self.assertEqual(resp_prod.status_code, 201)
            prod_id = resp_prod.get_json()["product"]["product_id"]

            cursor.execute(
                'SELECT log_id, action FROM public."AuditLogs" WHERE action = \'CREATE_PRODUCT\' AND record_id = %s',
                (prod_id,)
            )
            self.assertIsNotNone(cursor.fetchone())

            # 4. Product Update
            resp_upd_prod = self.client.put(
                f"/api/products/{prod_id}",
                headers={"Authorization": f"Bearer {self.manager_token}"},
                json={"product_name": "Phase8AudProdUpd", "selling_price": 275.0}
            )
            self.assertEqual(resp_upd_prod.status_code, 200)
            cursor.execute(
                'SELECT log_id, action FROM public."AuditLogs" WHERE action = \'UPDATE_PRODUCT\' AND record_id = %s',
                (prod_id,)
            )
            self.assertIsNotNone(cursor.fetchone())

            # 5. Product Deactivation
            resp_del_prod = self.client.delete(
                f"/api/products/{prod_id}",
                headers={"Authorization": f"Bearer {self.manager_token}"}
            )
            self.assertEqual(resp_del_prod.status_code, 200)
            cursor.execute(
                'SELECT log_id, action FROM public."AuditLogs" WHERE action IN (\'DEACTIVATE_PRODUCT\', \'DELETE_PRODUCT\') AND record_id = %s',
                (prod_id,)
            )
            self.assertIsNotNone(cursor.fetchone())
        finally:
            cursor.close()
            conn.close()

    def test_16_auth_login_audit_success_and_failure(self):
        """Test successful login creates LOGIN audit record, failed login does NOT."""
        # 1. Failed login
        resp_fail = self.client.post("/api/auth/login", json={
            "username": "demo_manager",
            "password": "WrongPassword!999"
        })
        self.assertEqual(resp_fail.status_code, 401)

        # 2. Successful login
        resp_ok = self.client.post("/api/auth/login", json={
            "username": "demo_manager",
            "password": "password123"
        })
        self.assertEqual(resp_ok.status_code, 200)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT log_id FROM public."AuditLogs" WHERE action = \'LOGIN\' AND user_id = %s ORDER BY log_id DESC LIMIT 1',
                (self.manager_user_id,)
            )
            row = cursor.fetchone()
            self.assertIsNotNone(row)
        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # STEP K3: AUTHORIZATION & SPOOFING TESTS
    # =========================================================================

    def test_17_unauthenticated_request_rejected_no_audit(self):
        """Test unauthenticated calls are rejected with 401 and produce no business audit logs."""
        resp = self.client.post("/api/categories/", json={"category_name": "UnauthCat"})
        self.assertEqual(resp.status_code, 401)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT count(*) FROM public."Categories" WHERE category_name = \'UnauthCat\'')
            self.assertEqual(cursor.fetchone()[0], 0)
        finally:
            cursor.close()
            conn.close()

    def test_18_rbac_unauthorized_action_rejected_no_audit(self):
        """Test unauthorized roles (Employee attempting to approve quotation) are rejected with 403."""
        resp = self.client.post(
            "/api/quotations/1/approve",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertIn(resp.status_code, [403, 404])

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT count(*) FROM public."AuditLogs" WHERE action = \'QUOTATION_APPROVED\' AND user_id = %s AND record_id = 1',
                (self.employee_user_id,)
            )
            self.assertEqual(cursor.fetchone()[0], 0)
        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # STEP K4: REPORTS MODULE INTEGRATION TESTS
    # =========================================================================

    def test_19_audit_trail_report_data_fetches_new_events(self):
        """Test fetch_audit_trail_report_data returns newly instrumented audit actions and supports action filtering."""
        rows, err, status = fetch_audit_trail_report_data()
        self.assertEqual(status, 200)
        self.assertIsNone(err)
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)

        # Check action names present
        actions_present = {r.get("action") for r in rows}
        self.assertIn("STOCK_OUT", actions_present)
        self.assertIn("PO_CREATED", actions_present)

        # Verify action-level filtering works
        filtered_rows, f_err, f_status = fetch_audit_trail_report_data(action="STOCK_OUT")
        self.assertEqual(f_status, 200)
        self.assertGreater(len(filtered_rows), 0)
        for r in filtered_rows:
            self.assertEqual(r.get("action"), "STOCK_OUT")

    def test_20_audit_trail_csv_and_pdf_export(self):
        """Test CSV and PDF export for Audit Trail report include audit records cleanly."""
        # 1. Generate an Audit Trail report snapshot
        resp_gen = self.client.post(
            "/api/reports/generate",
            headers={"Authorization": f"Bearer {self.owner_token}"},
            json={"report_name": "Phase 8 Audit Trail Verification", "report_type": "Audit Trail"}
        )
        self.assertEqual(resp_gen.status_code, 201)
        rep_id = resp_gen.get_json()["report"]["report_id"]

        # 2. Export CSV
        resp_csv = self.client.get(
            f"/api/reports/{rep_id}/export/csv",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_csv.status_code, 200)
        self.assertIn("text/csv", resp_csv.content_type)
        csv_bytes = resp_csv.data
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))
        csv_text = csv_bytes.decode("utf-8-sig")
        self.assertIn("Report ID", csv_text)

        # 3. Export PDF
        resp_pdf = self.client.get(
            f"/api/reports/{rep_id}/export/pdf",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf.content_type, "application/pdf")
        self.assertTrue(resp_pdf.data.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
