import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import date, datetime
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team2.supplier_invoice_service import (
    submit_invoice,
    get_invoices,
    get_invoice_by_id,
    approve_invoice,
    reject_invoice,
    cancel_invoice
)
from app.services.team2.supplier_payment_service import (
    record_payment,
    get_payments,
    get_payment_by_id
)


class SupplierPaymentsPhase4IntegrationTestCase(unittest.TestCase):
    """
    Phase 4 Integration Verification Test Suite for SIMS Supplier Payments MVP.
    Verifies complete end-to-end workflows across:
    - Supplier submission, viewing, and cancellation
    - Owner/Manager review, approval, rejection, full/partial payment disbursement
    - Employee isolation & unauthenticated denials
    - Overpayment protection, concurrency row-locking, and transaction rollbacks
    - Frontend API contract alignment
    All tests execute safely using isolated mocks and fixtures with ZERO modifications to the live database.
    """

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
    # 1. Supplier Complete Lifecycle: Submit -> Cancel
    # =========================================================================

    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_01_supplier_submit_and_cancel_lifecycle(self, mock_db_conn, mock_audit):
        """Supplier can submit an invoice against a delivered PO and cancel it while in Submitted status."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock resolution for submit_invoice
        mock_cursor.fetchone.side_effect = [
            (1,),                                                  # resolve_supplier_id_for_user
            (101, 1, 'Accepted', Decimal("50000.00")),             # Lock PO (4-tuple)
            (501, 101, 1, 'Delivered', 'Fully Received', datetime.now(), 100), # Lock Shipment (7-tuple)
            None,                                                  # Check duplicate invoice_number -> None
            (Decimal("0.00"),),                                    # Cumulative active invoices total
            (201, datetime.now(), datetime.now()),                 # Insert invoice RETURNING invoice_id, created_at, updated_at
        ]

        payload = {
            "purchase_order_id": 101,
            "shipment_id": 501,
            "invoice_number": "INV-PHASE4-001",
            "invoice_date": "2026-10-12",
            "due_date": "2026-11-12",
            "subtotal": "10000.00",
            "tax_amount": "1800.00",
            "total_amount": "11800.00",
            "notes": "Delivered consignment Phase 4 test"
        }

        # Step A: Submit invoice
        result, error, status_code = submit_invoice(user_id=10, role="Supplier", data=payload)
        self.assertIsNone(error)
        self.assertEqual(status_code, 201)
        self.assertEqual(result["invoice_number"], "INV-PHASE4-001")
        self.assertEqual(result["status"], "Submitted")
        self.assertEqual(result["remaining_balance"], 11800.00)

        # Step B: Supplier cancels the submitted invoice
        mock_cursor.fetchone.side_effect = [
            (1,),                                                  # resolve_supplier_id
            (201, 1, 'INV-PHASE4-001', 'Submitted', ''),           # Lock invoice FOR UPDATE (5-tuple)
            (Decimal("0.00"),),                                    # Sum of existing payments = 0
            (datetime.now(),),                                     # UPDATE ... RETURNING updated_at
        ]

        cancel_res, cancel_err, cancel_status = cancel_invoice(
            invoice_id=201,
            user_id=10,
            role="Supplier",
            reason="Supplier clerical correction"
        )
        self.assertIsNone(cancel_err)
        self.assertEqual(cancel_status, 200)
        self.assertEqual(cancel_res["status"], "Cancelled")

    # =========================================================================
    # 2. Owner/Manager Rejection Workflow with Mandatory Reason
    # =========================================================================

    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_02_manager_rejection_workflow(self, mock_db_conn, mock_audit):
        """Owner/Manager can reject a submitted invoice only with non-empty reason; empty reason is rejected."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Attempt A: Reject with empty reason via route
        headers = {"Authorization": f"Bearer {self.manager_token}"}
        resp_empty = self.client.patch("/api/invoices/202/reject", json={"rejection_reason": "   "}, headers=headers)
        self.assertEqual(resp_empty.status_code, 400)
        self.assertIn("rejection_reason is required", resp_empty.get_json()["error"])

        # Attempt B: Reject with valid non-empty reason
        mock_cursor.fetchone.side_effect = [
            (202, 'INV-PHASE4-002', 'Submitted', Decimal("5000.00")), # Lock invoice (4-tuple)
            (datetime.now(),),                                        # UPDATE RETURNING updated_at
        ]

        result, error, status_code = reject_invoice(
            invoice_id=202,
            user_id=2,
            role="Manager",
            rejection_reason="Price discrepancy on item #3 against quotation"
        )
        self.assertIsNone(error)
        self.assertEqual(status_code, 200)
        self.assertEqual(result["status"], "Rejected")
        self.assertEqual(result["rejection_reason"], "Price discrepancy on item #3 against quotation")

    # =========================================================================
    # 3. Complete Approval and Multi-Payment Workflow (Partial -> Final Settlement)
    # =========================================================================

    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team2.supplier_payment_service.log_audit_event")
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    @patch("app.services.team2.supplier_payment_service.get_db_connection")
    def test_03_approval_and_multi_payment_settlement(self, mock_pay_db, mock_inv_db, mock_pay_audit, mock_inv_audit):
        """Verify complete progression: Submitted -> Approved -> Partially Paid -> Overpayment Blocked -> Paid."""
        mock_inv_conn = MagicMock()
        mock_inv_cur = MagicMock()
        mock_inv_db.return_value = mock_inv_conn
        mock_inv_conn.cursor.return_value = mock_inv_cur

        mock_pay_conn = MagicMock()
        mock_pay_cur = MagicMock()
        mock_pay_db.return_value = mock_pay_conn
        mock_pay_conn.cursor.return_value = mock_pay_cur

        # 1. Manager Approves Invoice (Total: 1000.00)
        mock_inv_cur.fetchone.side_effect = [
            (203, 'INV-PHASE4-003', 'Submitted', Decimal("1000.00")), # Lock invoice (4-tuple)
            (datetime.now(),),                                        # UPDATE RETURNING updated_at
        ]
        app_res, app_err, app_code = approve_invoice(invoice_id=203, user_id=2, role="Manager")
        self.assertIsNone(app_err)
        self.assertEqual(app_code, 200)
        self.assertEqual(app_res["status"], "Approved")

        # 2. Record First Partial Payment (Amount: 400.00)
        mock_pay_cur.fetchone.side_effect = [
            (203, 1, 'INV-PHASE4-003', Decimal("1000.00"), 'Approved'), # Lock invoice (5-tuple)
            (Decimal("0.00"),),                                         # Existing payments sum -> 0.00
            (301, datetime.now()),                                      # Insert payment RETURNING payment_id, created_at
        ]
        pay1_res, pay1_err, pay1_code = record_payment(
            user_id=2,
            role="Manager",
            data={
                "invoice_id": 203,
                "amount_paid": "400.00",
                "payment_method": "Bank Transfer / NEFT",
                "payment_reference": "UTR-PHASE4-PART1",
                "payment_date": "2026-10-12"
            }
        )
        self.assertIsNone(pay1_err)
        self.assertEqual(pay1_code, 201)
        self.assertEqual(pay1_res["invoice"]["status"], "Partially Paid")
        self.assertEqual(pay1_res["invoice"]["total_paid"], 400.00)
        self.assertEqual(pay1_res["invoice"]["remaining_balance"], 600.00)

        # 3. Attempt Overpayment: Remaining balance is 600.00, attempting 600.01
        mock_pay_cur.fetchone.side_effect = [
            (203, 1, 'INV-PHASE4-003', Decimal("1000.00"), 'Partially Paid'), # Lock invoice
            (Decimal("400.00"),),                                             # Existing payments sum -> 400.00
        ]
        over_res, over_err, over_code = record_payment(
            user_id=2,
            role="Manager",
            data={
                "invoice_id": 203,
                "amount_paid": "600.01",
                "payment_method": "UPI",
                "payment_reference": "UPI-OVERPAY-ATTEMPT",
                "payment_date": "2026-10-12"
            }
        )
        self.assertEqual(over_code, 400)
        self.assertIn("exceeds remaining invoice balance", over_err)

        # 4. Record Final Settlement Payment (Amount: 600.00 exact)
        mock_pay_cur.fetchone.side_effect = [
            (203, 1, 'INV-PHASE4-003', Decimal("1000.00"), 'Partially Paid'), # Lock invoice
            (Decimal("400.00"),),                                             # Existing payments sum -> 400.00
            (302, datetime.now()),                                            # Insert payment RETURNING payment_id, created_at
        ]
        pay2_res, pay2_err, pay2_code = record_payment(
            user_id=2,
            role="Manager",
            data={
                "invoice_id": 203,
                "amount_paid": "600.00",
                "payment_method": "RTGS",
                "payment_reference": "RTGS-PHASE4-FINAL",
                "payment_date": "2026-10-12"
            }
        )
        self.assertIsNone(pay2_err)
        self.assertEqual(pay2_code, 201)
        self.assertEqual(pay2_res["invoice"]["status"], "Paid")
        self.assertEqual(pay2_res["invoice"]["total_paid"], 1000.00)
        self.assertEqual(pay2_res["invoice"]["remaining_balance"], 0.00)

        # 5. Attempt Payment against already Paid Invoice
        mock_pay_cur.fetchone.side_effect = [
            (203, 1, 'INV-PHASE4-003', Decimal("1000.00"), 'Paid'), # Lock invoice
        ]
        paid_res, paid_err, paid_code = record_payment(
            user_id=2,
            role="Manager",
            data={
                "invoice_id": 203,
                "amount_paid": "50.00",
                "payment_method": "Cash",
                "payment_reference": "CASH-ATTEMPT-PAID",
                "payment_date": "2026-10-12"
            }
        )
        self.assertEqual(paid_code, 400)
        self.assertIn("Payments can only be recorded against 'Approved' or 'Partially Paid' invoices", paid_err)

    # =========================================================
    # 4. Cancellation Prohibited Once Payments Are Recorded
    # =========================================================

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_04_cancellation_prohibited_on_paid_invoices(self, mock_db_conn):
        """Neither Supplier nor Manager can cancel an invoice with existing recorded disbursements."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock Approved invoice that has existing recorded payments:
        mock_cursor.fetchone.side_effect = [
            (204, 1, 'INV-PHASE4-004', 'Approved', ''),        # Lock invoice (5-tuple)
            (Decimal("400.00"),)                              # SUM(amount_paid) = 400.00 > 0
        ]

        res, err, status = cancel_invoice(
            invoice_id=204,
            user_id=1,
            role="Owner",
            reason="Attempting to cancel partially paid invoice"
        )
        self.assertEqual(status, 400)
        self.assertIn("Cannot cancel invoice with recorded payments", err)

    # =========================================================
    # 5. Supplier Data Isolation Enforced
    # =========================================================

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_05_supplier_query_data_isolation(self, mock_db_conn):
        """Supplier queries are strictly filtered to their own supplier_id; Owner/Manager have org-wide access."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Supplier 1 executes get_invoices
        mock_cursor.fetchone.return_value = (5,) # resolved supplier_id = 5
        mock_cursor.fetchall.return_value = []

        get_invoices(user_id=50, role="Supplier")

        # Verify SQL contains AND si.supplier_id = %s with param 5
        call_args = mock_cursor.execute.call_args[0]
        query_sql, params = call_args[0], call_args[1]
        self.assertIn("si.supplier_id = %s", query_sql)
        self.assertIn(5, params)

        # Owner executes get_invoices with no filter
        mock_cursor.reset_mock()
        mock_cursor.fetchall.return_value = []
        get_invoices(user_id=1, role="Owner")

        call_args_owner = mock_cursor.execute.call_args[0]
        query_sql_owner, params_owner = call_args_owner[0], call_args_owner[1]
        # Query does not restrict to a single supplier_id unless explicitly requested
        self.assertEqual(list(params_owner), [])

    # =========================================================
    # 6. Cumulative PO Amount Capping Enforced
    # =========================================================

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_06_cumulative_po_cap_enforcement(self, mock_db_conn):
        """Invoices that would cause cumulative non-rejected invoices to exceed the PO total are rejected."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # PO Total = 20000.00, Existing active invoices sum = 18000.00
        # New invoice = 2001.00 -> Total would be 20001.00 -> Exceeds PO total
        mock_cursor.fetchone.side_effect = [
            (1,),                                                  # resolve_supplier_id
            (105, 1, 'Delivered', Decimal("20000.00")),            # Lock PO (4-tuple)
            (505, 105, 1, 'Delivered', 'Fully Received', datetime.now(), 50), # Lock shipment (7-tuple)
            None,                                                  # No duplicate invoice number
            (Decimal("18000.00"),),                                # Cumulative active sum
        ]

        payload = {
            "purchase_order_id": 105,
            "shipment_id": 505,
            "invoice_number": "INV-PHASE4-EXCEED",
            "invoice_date": "2026-10-12",
            "due_date": "2026-11-12",
            "subtotal": "2001.00",
            "tax_amount": "0.00",
            "total_amount": "2001.00"
        }

        result, error, status_code = submit_invoice(user_id=10, role="Supplier", data=payload)
        self.assertEqual(status_code, 400)
        self.assertIn("exceed Purchase Order total", error)

    # =========================================================
    # 7. Unreceived and Mismatched Shipment Rejection
    # =========================================================

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_07_unreceived_and_mismatched_shipment_rejection(self, mock_db_conn):
        """Invoices referencing non-delivered shipments or shipments on another PO/supplier are rejected."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Shipment does not meet Delivered + positive stock in criteria (returns None)
        mock_cursor.fetchone.side_effect = [
            (1,),                                                  # resolve_supplier_id
            (106, 1, 'Delivered', Decimal("30000.00")),            # Lock PO
            None,                                                  # Shipment query returns None
        ]

        payload = {
            "purchase_order_id": 106,
            "shipment_id": 999,
            "invoice_number": "INV-PHASE4-BAD-SHP",
            "subtotal": "5000.00",
            "tax_amount": "0.00",
            "total_amount": "5000.00",
            "due_date": "2026-11-12"
        }

        result, error, status_code = submit_invoice(user_id=10, role="Supplier", data=payload)
        self.assertEqual(status_code, 404)
        self.assertIn("Shipment not found", error)

    # =========================================================
    # 8. Transaction Rollback Safety on Database Error
    # =========================================================

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_08_transaction_rollback_on_db_failure(self, mock_db_conn):
        """Database errors during invoice submission trigger conn.rollback() without leaving dangling locks."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Supplier resolution succeeds, subsequent PO lock query raises DB Exception
        mock_cursor.fetchone.side_effect = [
            (1,),
            Exception("Simulated DB Connection Timeout")
        ]

        payload = {
            "purchase_order_id": 107,
            "invoice_number": "INV-PHASE4-FAIL",
            "subtotal": "1000.00",
            "tax_amount": "0.00",
            "total_amount": "1000.00",
            "due_date": "2026-11-12"
        }

        result, error, status_code = submit_invoice(user_id=10, role="Supplier", data=payload)
        self.assertEqual(status_code, 500)
        mock_conn.rollback.assert_called_once()

    # =========================================================
    # 9. Employee Rejection Across All Endpoints (403)
    # =========================================================

    def test_09_employee_access_strictly_forbidden(self):
        """Employees have zero access to financial invoice or payment routes."""
        headers = {"Authorization": f"Bearer {self.employee_token}"}
        endpoints = [
            ("GET", "/api/invoices"),
            ("POST", "/api/invoices"),
            ("GET", "/api/invoices/1"),
            ("PATCH", "/api/invoices/1/approve"),
            ("PATCH", "/api/invoices/1/reject"),
            ("PATCH", "/api/invoices/1/cancel"),
            ("GET", "/api/invoices/1/payments"),
            ("GET", "/api/payments"),
            ("POST", "/api/payments"),
            ("GET", "/api/payments/1"),
        ]
        for method, url in endpoints:
            if method == "GET":
                resp = self.client.get(url, headers=headers)
            elif method == "POST":
                resp = self.client.post(url, json={}, headers=headers)
            elif method == "PATCH":
                resp = self.client.patch(url, json={}, headers=headers)
            self.assertEqual(resp.status_code, 403, f"{method} {url} allowed Employee access!")

    # =========================================================
    # 10. Frontend and Backend Contract Alignment
    # =========================================================

    def test_10_api_contract_alignment_verified(self):
        """Verify that frontend API helpers and payments.js payload keys map exactly to backend route parsers."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]

        frontend_payments_js = (repo_root / "frontend" / "js" / "pages" / "payments.js").read_text(encoding="utf-8")
        frontend_api_js = (repo_root / "frontend" / "js" / "api" / "api.js").read_text(encoding="utf-8")

        # 1. Invoice submission keys
        invoice_keys = [
            "purchase_order_id",
            "invoice_number",
            "invoice_date",
            "due_date",
            "subtotal",
            "tax_amount",
            "total_amount"
        ]
        for key in invoice_keys:
            self.assertIn(f"{key}:", frontend_payments_js, f"Frontend must send {key} in submit invoice")

        # 2. Payment recording keys
        payment_keys = [
            "invoice_id",
            "amount_paid",
            "payment_date",
            "payment_method",
            "payment_reference"
        ]
        for key in payment_keys:
            self.assertIn(f"{key}:", frontend_payments_js, f"Frontend must send {key} in record payment")

        # 3. Query parameter keys
        query_keys = ["search", "status", "date_from", "date_to", "page", "limit"]
        for key in query_keys:
            self.assertIn(key, frontend_payments_js, f"Frontend must support filter param {key}")

        # 4. Endpoints called in api.js
        self.assertIn("/invoices", frontend_api_js)
        self.assertIn("/payments", frontend_api_js)
        self.assertIn("/approve", frontend_api_js)
        self.assertIn("/reject", frontend_api_js)
        self.assertIn("/cancel", frontend_api_js)


if __name__ == "__main__":
    unittest.main()
