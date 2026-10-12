import unittest
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import date
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


class SupplierPaymentsPhase2TestCase(unittest.TestCase):
    """
    Focused verification suite for SIMS Supplier Payments MVP — Phase 2 Backend Services & API.
    Covers RBAC, supplier isolation, shipment eligibility, overpayment prevention,
    PO cumulative cap, atomic status transitions, and input validation without polluting live DB.
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
    # Group 1: Role-Based Endpoint Access Control
    # =========================================================================

    def test_01_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to all financial endpoints must return 401."""
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
                resp = self.client.get(url)
            elif method == "POST":
                resp = self.client.post(url, json={})
            elif method == "PATCH":
                resp = self.client.patch(url, json={})
            self.assertEqual(resp.status_code, 401, f"{method} {url} did not return 401")

    def test_02_employee_access_strictly_denied(self):
        """Employees must be strictly rejected (403) from all financial invoice and payment routes."""
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
            self.assertEqual(resp.status_code, 403, f"Employee was not denied on {method} {url}")

    def test_03_supplier_cannot_approve_reject_or_record_payments(self):
        """Suppliers must receive 403 when attempting approve, reject, or record payment."""
        headers = {"Authorization": f"Bearer {self.supplier_token}"}
        
        # Supplier cannot approve
        resp_app = self.client.patch("/api/invoices/1/approve", headers=headers)
        self.assertEqual(resp_app.status_code, 403)

        # Supplier cannot reject
        resp_rej = self.client.patch("/api/invoices/1/reject", json={"reason": "test"}, headers=headers)
        self.assertEqual(resp_rej.status_code, 403)

        # Supplier cannot record payment
        resp_pay = self.client.post("/api/payments", json={"invoice_id": 1, "amount_paid": 100}, headers=headers)
        self.assertEqual(resp_pay.status_code, 403)

    def test_04_owner_and_manager_cannot_submit_invoice_as_supplier(self):
        """Owner and Manager cannot submit invoices (POST /api/invoices is Supplier only)."""
        resp_owner = self.client.post(
            "/api/invoices",
            json={"invoice_number": "INV-1"},
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_owner.status_code, 403)

        resp_mgr = self.client.post(
            "/api/invoices",
            json={"invoice_number": "INV-1"},
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp_mgr.status_code, 403)

    # =========================================================================
    # Group 2: Service-Level Validation & Business Rules
    # =========================================================================

    def test_05_invoice_amount_mathematical_consistency(self):
        """Reject invoices where subtotal + tax != total, or negative/zero amounts."""
        # Case A: total != subtotal + tax
        res, err, code = submit_invoice(
            user_id=1, role="Supplier",
            data={
                "invoice_number": "INV-001",
                "purchase_order_id": 1,
                "due_date": "2026-11-01",
                "subtotal": 100.00,
                "tax_amount": 18.00,
                "total_amount": 150.00
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("must equal subtotal", err)

        # Case B: zero total
        res, err, code = submit_invoice(
            user_id=1, role="Supplier",
            data={
                "invoice_number": "INV-001",
                "purchase_order_id": 1,
                "due_date": "2026-11-01",
                "subtotal": 0.00,
                "tax_amount": 0.00,
                "total_amount": 0.00
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("greater than zero", err)

        # Case C: due_date < invoice_date
        res, err, code = submit_invoice(
            user_id=1, role="Supplier",
            data={
                "invoice_number": "INV-001",
                "purchase_order_id": 1,
                "invoice_date": "2026-11-05",
                "due_date": "2026-11-01",
                "subtotal": 100.00,
                "tax_amount": 0.00,
                "total_amount": 100.00
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("due_date must be on or after", err)

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_06_unreceived_shipment_rejection(self, mock_get_conn):
        """Reject invoice if shipment is not delivered or goods receipt not recorded."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # 1. Supplier ID = 5
        mock_cursor.fetchone.side_effect = [
            (5,),                                                # resolve_supplier_id_for_user
            (1, 5, "Accepted", Decimal("1000.00")),              # PO row
            (10, 1, 5, "In Transit", "Pending Receipt", None, 0) # Shipment not delivered!
        ]

        res, err, code = submit_invoice(
            user_id=12, role="Supplier",
            data={
                "invoice_number": "INV-002",
                "purchase_order_id": 1,
                "shipment_id": 10,
                "due_date": "2026-11-01",
                "subtotal": 100.00,
                "tax_amount": 0.00,
                "total_amount": 100.00
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("Shipment must be delivered", err)

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_07_duplicate_invoice_number_rejection(self, mock_get_conn):
        """Reject duplicate invoice number for the same supplier."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            (5,),                                                  # resolve_supplier_id_for_user
            (1, 5, "Accepted", Decimal("1000.00")),                # PO row
            (10, 1, 5, "Delivered", "Fully Received", "2026-10-10", 50), # Shipment
            (999,)                                                 # Duplicate invoice exists!
        ]

        res, err, code = submit_invoice(
            user_id=12, role="Supplier",
            data={
                "invoice_number": "INV-EXISTING",
                "purchase_order_id": 1,
                "shipment_id": 10,
                "due_date": "2026-11-01",
                "subtotal": 100.00,
                "tax_amount": 0.00,
                "total_amount": 100.00
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 409)
        self.assertIn("already exists", err)

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_08_purchase_order_cumulative_cap_enforcement(self, mock_get_conn):
        """Reject invoice if cumulative invoices exceed PO total."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            (5,),                                                  # resolve_supplier_id_for_user
            (1, 5, "Accepted", Decimal("1000.00")),                # PO total = 1000.00
            (10, 1, 5, "Delivered", "Fully Received", "2026-10-10", 50), # Shipment
            None,                                                  # No duplicate invoice
            (Decimal("800.00"),)                                   # Already invoiced 800.00!
        ]

        # Attempt to invoice 300.00 (800 + 300 = 1100 > 1000)
        res, err, code = submit_invoice(
            user_id=12, role="Supplier",
            data={
                "invoice_number": "INV-NEW",
                "purchase_order_id": 1,
                "shipment_id": 10,
                "due_date": "2026-11-01",
                "subtotal": 300.00,
                "tax_amount": 0.00,
                "total_amount": 300.00
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("exceed Purchase Order total", err)

    # =========================================================================
    # Group 3: Approval, Rejection, and Cancellation
    # =========================================================================

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_09_approval_only_permitted_from_submitted_status(self, mock_get_conn):
        """Cannot approve an invoice that is already Approved or Paid."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (1, "INV-001", "Approved", Decimal("500.00"))

        res, err, code = approve_invoice(invoice_id=1, user_id=1, role="Owner")
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("Cannot approve invoice with status 'Approved'", err)

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_10_rejection_requires_reason(self, mock_get_conn):
        """Rejection must fail if rejection_reason is empty."""
        res, err, code = reject_invoice(invoice_id=1, user_id=1, role="Owner", rejection_reason="")
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("rejection_reason is required", err)

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_11_cannot_cancel_invoice_with_recorded_payments(self, mock_get_conn):
        """Invoice cannot be cancelled if payments have already been recorded."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            (1, 5, "INV-001", "Approved", ""),        # Invoice row
            (2,)                                      # 2 payments exist!
        ]

        res, err, code = cancel_invoice(invoice_id=1, user_id=1, role="Owner", reason="test")
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("Cannot cancel invoice with recorded payments", err)

    # =========================================================================
    # Group 4: Payment Recording & Overpayment Prevention
    # =========================================================================

    @patch("app.services.team2.supplier_payment_service.get_db_connection")
    def test_12_payment_rejected_on_unapproved_invoice(self, mock_get_conn):
        """Payments can only be recorded on Approved or Partially Paid invoices."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = (1, 5, "INV-001", Decimal("500.00"), "Submitted")

        res, err, code = record_payment(
            user_id=1, role="Owner",
            data={
                "invoice_id": 1,
                "amount_paid": 100.00,
                "payment_method": "Bank Transfer / NEFT",
                "payment_reference": "UTR123"
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("Payments can only be recorded against 'Approved' or 'Partially Paid' invoices", err)

    @patch("app.services.team2.supplier_payment_service.get_db_connection")
    def test_13_overpayment_rejected(self, mock_get_conn):
        """Payment amount exceeding remaining balance is strictly rejected."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            (1, 5, "INV-001", Decimal("500.00"), "Approved"),  # Invoice total = 500
            (Decimal("400.00"),)                               # Existing paid = 400 (remaining = 100)
        ]

        # Attempt to pay 150.00 (> remaining 100.00)
        res, err, code = record_payment(
            user_id=1, role="Owner",
            data={
                "invoice_id": 1,
                "amount_paid": 150.00,
                "payment_method": "Bank Transfer / NEFT",
                "payment_reference": "UTR123"
            }
        )
        self.assertIsNone(res)
        self.assertEqual(code, 400)
        self.assertIn("exceeds remaining invoice balance", err)

    @patch("app.services.team2.supplier_payment_service.log_audit_event")
    @patch("app.services.team2.supplier_payment_service.get_db_connection")
    def test_14_partial_payment_and_final_payment_transitions(self, mock_get_conn, mock_audit):
        """Verify status transitions from Approved -> Partially Paid -> Paid."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Step A: Partial payment (paying 200 of 500)
        mock_cursor.fetchone.side_effect = [
            (1, 5, "INV-001", Decimal("500.00"), "Approved"),  # Invoice row
            (Decimal("0.00"),),                                # Existing paid = 0
            (101, "2026-10-12T10:00:00")                       # Payment inserted RETURNING
        ]

        res, err, code = record_payment(
            user_id=1, role="Owner",
            data={
                "invoice_id": 1,
                "amount_paid": 200.00,
                "payment_method": "Bank Transfer / NEFT",
                "payment_reference": "UTR001"
            }
        )
        self.assertIsNotNone(res)
        self.assertEqual(code, 201)
        self.assertEqual(res["invoice"]["status"], "Partially Paid")
        self.assertEqual(res["invoice"]["remaining_balance"], 300.00)

        # Step B: Final payment (paying remaining 300)
        mock_cursor.fetchone.side_effect = [
            (1, 5, "INV-001", Decimal("500.00"), "Partially Paid"),  # Invoice row
            (Decimal("200.00"),),                                    # Existing paid = 200
            (102, "2026-10-12T11:00:00")                             # Payment inserted RETURNING
        ]

        res2, err2, code2 = record_payment(
            user_id=1, role="Owner",
            data={
                "invoice_id": 1,
                "amount_paid": 300.00,
                "payment_method": "RTGS",
                "payment_reference": "UTR002"
            }
        )
        self.assertIsNotNone(res2)
        self.assertEqual(code2, 201)
        self.assertEqual(res2["invoice"]["status"], "Paid")
        self.assertEqual(res2["invoice"]["remaining_balance"], 0.00)

    # =========================================================================
    # Group 5: Supplier Isolation
    # =========================================================================

    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    def test_15_supplier_query_scoped_strictly_to_own_records(self, mock_get_conn):
        """Supplier queries must automatically filter by the authenticated supplier_id."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock resolve_supplier_id_for_user returning 7
        mock_cursor.fetchone.return_value = (7,)
        mock_cursor.fetchall.return_value = []

        res, err, code = get_invoices(user_id=15, role="Supplier")
        self.assertIsNotNone(res)
        self.assertEqual(code, 200)

        # Verify SQL executed contains supplier_id filtering
        executed_query = mock_cursor.execute.call_args[0][0]
        self.assertIn("si.supplier_id = %s", executed_query)
        executed_params = mock_cursor.execute.call_args[0][1]
        self.assertIn(7, executed_params)


if __name__ == "__main__":
    unittest.main()
