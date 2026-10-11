import unittest
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team1.inventory_service import (
    get_stock_transactions,
    get_stock_transaction_by_id
)


class EmployeeTransactionDataIsolationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login and obtain tokens for each role using existing test accounts
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

    # =========================================================================
    # Test 1: Employee requests transactions without user_id parameter
    # =========================================================================
    def test_01_employee_query_without_user_id_only_returns_own_records(self):
        """
        Verify that when an Employee calls GET /api/inventory/transactions
        without specifying user_id, all returned rows belong strictly to that employee.
        """
        resp = self.client.get(
            "/api/inventory/transactions",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("transactions", data)
        self.assertIn("count", data)
        self.assertEqual(data["count"], len(data["transactions"]))

        # Verify every returned record is strictly owned by demo_employee (user_id 7 or username demo_employee)
        for tx in data["transactions"]:
            self.assertEqual(
                tx.get("username"),
                "demo_employee",
                f"Isolation breach: Employee saw transaction {tx.get('transaction_id')} logged by {tx.get('username')}"
            )
            self.assertEqual(tx.get("user_id"), 7)

    # =========================================================================
    # Test 2: Employee requests transactions supplying their own user_id
    # =========================================================================
    def test_02_employee_query_with_own_user_id_succeeds(self):
        """
        Verify that an Employee explicitly passing their own user_id (7)
        succeeds and returns only their own transactions.
        """
        resp = self.client.get(
            "/api/inventory/transactions?user_id=7",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("transactions", data)
        for tx in data["transactions"]:
            self.assertEqual(tx.get("user_id"), 7)
            self.assertEqual(tx.get("username"), "demo_employee")

    # =========================================================================
    # Test 3: Employee attempts to retrieve another user's records via user_id
    # =========================================================================
    def test_03_employee_query_with_other_user_id_is_forbidden(self):
        """
        Verify that an Employee passing another user's user_id (e.g. user_id 6 - Manager, or user_id 5 - Owner)
        is rejected with 403 Forbidden, and zero foreign records are returned.
        """
        # Attempt to access Manager's transactions (user_id 6)
        resp_mgr = self.client.get(
            "/api/inventory/transactions?user_id=6",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_mgr.status_code, 403)
        err_data = resp_mgr.get_json()
        self.assertIn("error", err_data)
        self.assertIn("Access denied", err_data["error"])

        # Attempt to access Owner's transactions (user_id 1 or 5)
        resp_own = self.client.get(
            "/api/inventory/transactions?user_id=5",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_own.status_code, 403)
        err_own = resp_own.get_json()
        self.assertIn("Access denied", err_own["error"])

    # =========================================================================
    # Test 4: Employee filtering by product, type, or date remains strictly scoped
    # =========================================================================
    def test_04_employee_query_with_additional_filters_cannot_bypass_scoping(self):
        """
        Verify that combining query filters (product_id, transaction_type, date_from)
        never allows an Employee to see other users' transactions.
        """
        resp = self.client.get(
            "/api/inventory/transactions?transaction_type=STOCK_IN",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        for tx in data["transactions"]:
            self.assertEqual(tx.get("user_id"), 7)
            self.assertEqual(tx.get("username"), "demo_employee")
            self.assertEqual(tx.get("transaction_type"), "STOCK_IN")

    # =========================================================================
    # Test 5: Response contract compatibility (transactions list + count match)
    # =========================================================================
    def test_05_response_contract_and_counts_match_scope(self):
        """
        Verify returned payload structure adheres to the existing contract:
        {"transactions": [...], "count": N}
        where count exactly matches the scoped array length.
        """
        resp = self.client.get(
            "/api/inventory/transactions",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data["transactions"], list)
        self.assertIsInstance(data["count"], int)
        self.assertEqual(data["count"], len(data["transactions"]))

    # =========================================================================
    # Test 6: Owner and Manager maintain full visibility across all users
    # =========================================================================
    def test_06_owner_and_manager_retain_unrestricted_visibility(self):
        """
        Verify that Owner and Manager roles can view all transactions and can
        optionally filter by any user_id.
        """
        # Manager can view all transactions (contains both user 6 and user 7)
        resp_mgr = self.client.get(
            "/api/inventory/transactions",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr.status_code, 200)
        mgr_data = resp_mgr.get_json()
        mgr_uids = {tx.get("user_id") for tx in mgr_data["transactions"]}
        # In the demo data, both user 6 and user 7 have transactions
        self.assertGreater(len(mgr_data["transactions"]), 0)

        # Manager can explicitly filter by employee's user_id (7)
        resp_mgr_filtered = self.client.get(
            "/api/inventory/transactions?user_id=7",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr_filtered.status_code, 200)
        filtered_data = resp_mgr_filtered.get_json()
        for tx in filtered_data["transactions"]:
            self.assertEqual(tx.get("user_id"), 7)

        # Owner has full access
        resp_owner = self.client.get(
            "/api/inventory/transactions",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_owner.status_code, 200)
        owner_data = resp_owner.get_json()
        self.assertGreater(len(owner_data["transactions"]), 0)

    # =========================================================================
    # Test 7: Supplier access is strictly forbidden
    # =========================================================================
    def test_07_supplier_access_is_forbidden(self):
        """
        Verify that Supplier role cannot access stock transactions (HTTP 403).
        """
        resp = self.client.get(
            "/api/inventory/transactions",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn("error", data)

    # =========================================================================
    # Test 8: Unauthenticated and invalid token requests are rejected
    # =========================================================================
    def test_08_unauthenticated_requests_are_rejected(self):
        """
        Verify that missing or malformed tokens are rejected by the authentication layer.
        """
        # No token
        resp_no_auth = self.client.get("/api/inventory/transactions")
        self.assertIn(resp_no_auth.status_code, [401, 403])

        # Invalid token
        resp_bad_token = self.client.get(
            "/api/inventory/transactions",
            headers={"Authorization": "Bearer invalid_garbage_token"}
        )
        self.assertIn(resp_bad_token.status_code, [401, 422])

    # =========================================================================
    # Test 9: Single transaction detail endpoint isolation
    # =========================================================================
    def test_09_single_transaction_detail_authorization(self):
        """
        Verify that GET /api/inventory/transactions/<id> enforces:
        - Employee viewing own transaction -> 200 OK
        - Employee viewing another user's transaction -> 403 Forbidden
        - Manager viewing any transaction -> 200 OK
        - Supplier viewing any transaction -> 403 Forbidden
        """
        # First, find one transaction owned by employee (7) and one by manager (6)
        resp_mgr = self.client.get(
            "/api/inventory/transactions",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr.status_code, 200)
        all_tx = resp_mgr.get_json()["transactions"]

        emp_tx_id = None
        mgr_tx_id = None
        for tx in all_tx:
            if tx.get("user_id") == 7 and emp_tx_id is None:
                emp_tx_id = tx.get("transaction_id")
            elif tx.get("user_id") == 6 and mgr_tx_id is None:
                mgr_tx_id = tx.get("transaction_id")
            if emp_tx_id and mgr_tx_id:
                break

        self.assertIsNotNone(emp_tx_id, "Could not find a demo employee transaction for testing")
        self.assertIsNotNone(mgr_tx_id, "Could not find a demo manager transaction for testing")

        # Employee views own transaction -> 200 OK
        resp_emp_own = self.client.get(
            f"/api/inventory/transactions/{emp_tx_id}",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_emp_own.status_code, 200)
        self.assertEqual(resp_emp_own.get_json()["transaction"]["transaction_id"], emp_tx_id)

        # Employee views manager's transaction -> 403 Forbidden
        resp_emp_other = self.client.get(
            f"/api/inventory/transactions/{mgr_tx_id}",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp_emp_other.status_code, 403)
        self.assertIn("Access denied", resp_emp_other.get_json()["error"])

        # Manager views employee's transaction -> 200 OK
        resp_mgr_emp = self.client.get(
            f"/api/inventory/transactions/{emp_tx_id}",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr_emp.status_code, 200)

        # Supplier views any transaction -> 403 Forbidden
        resp_sup = self.client.get(
            f"/api/inventory/transactions/{emp_tx_id}",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp_sup.status_code, 403)

    # =========================================================================
    # Test 10: Service function level regression test
    # =========================================================================
    def test_10_service_level_isolation_direct_call(self):
        """
        Direct service function test verifying that calling get_stock_transactions()
        with role='Employee' and auth_user_id=7 strictly scopes rows to user_id=7,
        and passing mismatched user_id_filter=6 returns an Access denied error.
        """
        # Call as Employee with auth_user_id=7 and no user_id_filter
        txs, err = get_stock_transactions(role="Employee", auth_user_id=7)
        self.assertIsNone(err)
        self.assertIsInstance(txs, list)
        for t in txs:
            self.assertEqual(t["user_id"], 7)

        # Call as Employee with auth_user_id=7 and mismatched user_id_filter=6
        txs_mismatch, err_mismatch = get_stock_transactions(
            role="Employee",
            auth_user_id=7,
            user_id_filter=6
        )
        self.assertIsNone(txs_mismatch)
        self.assertIn("Access denied", err_mismatch)

        # Call without auth_user_id for Employee returns error
        txs_no_id, err_no_id = get_stock_transactions(role="Employee", auth_user_id=None)
        self.assertIsNone(txs_no_id)
        self.assertIn("Access denied", err_no_id)


if __name__ == "__main__":
    unittest.main()
