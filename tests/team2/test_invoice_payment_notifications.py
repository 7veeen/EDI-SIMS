import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import date

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team2.supplier_invoice_service import (
    submit_invoice,
    approve_invoice,
    reject_invoice,
    cancel_invoice
)
from app.services.team2.supplier_payment_service import record_payment


class InvoicePaymentNotificationsTestCase(unittest.TestCase):
    """
    Focused verification suite for SIMS Improvement 5 — Invoice & Payment Notifications (Phase 2).
    Validates:
    1. Invoice submission recipients and actor exclusion.
    2. Invoice approval notification to the correct Supplier.
    3. Invoice rejection notification and rejection reason.
    4. Supplier-initiated cancellation recipients.
    5. Management-initiated cancellation recipients (Supplier + other Managers).
    6. One consolidated notification for a recorded payment (Partially Paid & Fully Paid).
    7. Correct reference types ('Invoice', 'Payment') and IDs.
    8. Inactive/missing recipient tolerance.
    9. Non-blocking resilience: notification exceptions do not roll back or fail financial operations.
    10. Preservation of RBAC, audit logging, and financial constraints.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def _create_mock_conn(self):
        """Create a mock database connection and cursor with transaction control."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.autocommit = False
        return mock_conn, mock_cursor

    # =========================================================================
    # Test 1: Invoice submission recipients and actor exclusion
    # =========================================================================
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team2.supplier_invoice_service.resolve_supplier_id_for_user")
    @patch("app.services.team3.notification_service.get_active_managers_and_owners")
    @patch("app.services.team3.notification_service.create_notification")
    def test_01_invoice_submission_recipients_and_actor_exclusion(
        self, mock_create_notif, mock_get_mgrs, mock_resolve_sup, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        supplier_user_id = 55
        supplier_id = 9
        mock_resolve_sup.return_value = supplier_id

        # PO lock query: po_id=1, supplier_id=9, status='Issued', total=50000.00
        # Shipment query: (shipment_id, po_id, supplier_id, status, receiving_status, delivered_at, units)
        # Duplicate check: None
        # Cumulative invoice check: existing=0.00
        # Insert RETURNING: invoice_id=101, created_at, updated_at
        mock_cursor.fetchone.side_effect = [
            (1, supplier_id, "Issued", Decimal("50000.00")),   # PO row
            (10, 1, supplier_id, "Delivered", "Fully Received", "2026-10-12T09:00:00", 50),  # shipment row
            None,                                              # duplicate invoice_number check
            (Decimal("0.00"),),                               # cumulative existing
            (101, "2026-10-12T10:00:00", "2026-10-12T10:00:00")  # RETURNING
        ]

        # Active managers: IDs 1 (Owner) and 2 (Manager)
        mock_get_mgrs.return_value = [1, 2]

        data = {
            "invoice_number": "INV-TEST-001",
            "purchase_order_id": 1,
            "shipment_id": 10,
            "invoice_date": "2026-10-12",
            "due_date": "2026-11-12",
            "subtotal": "40000.00",
            "tax_amount": "7200.00",
            "total_amount": "47200.00"
        }

        result, err, status = submit_invoice(supplier_user_id, "Supplier", data)

        self.assertIsNone(err)
        self.assertEqual(status, 201)
        self.assertEqual(result["invoice_id"], 101)
        self.assertTrue(mock_conn.commit.called)

        # Verify recipient resolution called with actor exclusion
        mock_get_mgrs.assert_called_once_with(exclude_user_id=supplier_user_id)

        # Verify create_notification called for each manager
        self.assertEqual(mock_create_notif.call_count, 2)
        notif_calls = mock_create_notif.call_args_list

        for call in notif_calls:
            kwargs = call[1]
            self.assertIn(kwargs["user_id"], [1, 2])
            self.assertNotEqual(kwargs["user_id"], supplier_user_id)
            self.assertEqual(kwargs["title"], "New Invoice Submitted")
            self.assertEqual(kwargs["reference_type"], "Invoice")
            self.assertEqual(kwargs["reference_id"], 101)
            self.assertEqual(kwargs["notification_type"], "Invoice")

    # =========================================================================
    # Test 2: Invoice approval notification to correct Supplier
    # =========================================================================
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team3.notification_service.get_supplier_user_id")
    @patch("app.services.team3.notification_service.create_notification")
    def test_02_invoice_approval_notification_to_supplier(
        self, mock_create_notif, mock_get_sup_user, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Select invoice for update: (invoice_id, invoice_number, status, total_amount, supplier_id)
        # Update RETURNING updated_at
        mock_cursor.fetchone.side_effect = [
            (101, "INV-TEST-001", "Submitted", Decimal("47200.00"), 9),
            ("2026-10-12T10:05:00",)
        ]

        mock_get_sup_user.return_value = 55  # Supplier's user_id

        result, err, status = approve_invoice(101, user_id=1, role="Owner")

        self.assertIsNone(err)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "Approved")
        self.assertTrue(mock_conn.commit.called)

        # Verify supplier resolution
        mock_get_sup_user.assert_called_once_with(9)

        # Verify notification sent to Supplier user
        mock_create_notif.assert_called_once()
        kwargs = mock_create_notif.call_args[1]
        self.assertEqual(kwargs["user_id"], 55)
        self.assertEqual(kwargs["title"], "Invoice Approved")
        self.assertEqual(kwargs["reference_type"], "Invoice")
        self.assertEqual(kwargs["reference_id"], 101)
        self.assertIn("INV-TEST-001", kwargs["message"])

    # =========================================================================
    # Test 3: Invoice rejection notification and rejection reason
    # =========================================================================
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team3.notification_service.get_supplier_user_id")
    @patch("app.services.team3.notification_service.create_notification")
    def test_03_invoice_rejection_notification_and_reason(
        self, mock_create_notif, mock_get_sup_user, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Select invoice for update: (invoice_id, invoice_number, status, supplier_id)
        # Update RETURNING updated_at
        mock_cursor.fetchone.side_effect = [
            (101, "INV-TEST-001", "Submitted", 9),
            ("2026-10-12T10:05:00",)
        ]

        mock_get_sup_user.return_value = 55

        result, err, status = reject_invoice(
            invoice_id=101,
            user_id=2,
            role="Manager",
            rejection_reason="Incorrect tax calculation for interstate supply"
        )

        self.assertIsNone(err)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "Rejected")
        self.assertTrue(mock_conn.commit.called)

        # Verify notification contains clean rejection reason
        mock_create_notif.assert_called_once()
        kwargs = mock_create_notif.call_args[1]
        self.assertEqual(kwargs["user_id"], 55)
        self.assertEqual(kwargs["title"], "Invoice Rejected")
        self.assertEqual(kwargs["priority"], "High")
        self.assertEqual(kwargs["reference_type"], "Invoice")
        self.assertEqual(kwargs["reference_id"], 101)
        self.assertIn("Incorrect tax calculation for interstate supply", kwargs["message"])

    # =========================================================================
    # Test 4: Supplier-initiated cancellation recipients
    # =========================================================================
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team2.supplier_invoice_service.resolve_supplier_id_for_user")
    @patch("app.services.team3.notification_service.get_active_managers_and_owners")
    @patch("app.services.team3.notification_service.create_notification")
    def test_04_supplier_initiated_cancellation_recipients(
        self, mock_create_notif, mock_get_mgrs, mock_resolve_sup, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        mock_resolve_sup.return_value = 9
        # Select for update: (invoice_id, supplier_id, invoice_number, status, notes)
        # Payment count: 0
        # Update RETURNING updated_at
        mock_cursor.fetchone.side_effect = [
            (101, 9, "INV-TEST-001", "Submitted", None),
            (0,),
            ("2026-10-12T10:10:00",)
        ]

        mock_get_mgrs.return_value = [1, 2]

        result, err, status = cancel_invoice(
            invoice_id=101,
            user_id=55,
            role="Supplier",
            reason="Submitted incorrect quantity"
        )

        self.assertIsNone(err)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "Cancelled")

        # Verify active managers notified, excluding acting supplier
        mock_get_mgrs.assert_called_once_with(exclude_user_id=55)
        self.assertEqual(mock_create_notif.call_count, 2)
        for call in mock_create_notif.call_args_list:
            kwargs = call[1]
            self.assertIn(kwargs["user_id"], [1, 2])
            self.assertEqual(kwargs["title"], "Invoice Cancelled")
            self.assertIn("Supplier cancelled invoice", kwargs["message"])
            self.assertEqual(kwargs["reference_type"], "Invoice")
            self.assertEqual(kwargs["reference_id"], 101)

    # =========================================================================
    # Test 5: Management-initiated cancellation recipients (Supplier + Other Managers)
    # =========================================================================
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team3.notification_service.get_supplier_user_id")
    @patch("app.services.team3.notification_service.get_active_managers_and_owners")
    @patch("app.services.team3.notification_service.create_notification")
    def test_05_management_initiated_cancellation_recipients(
        self, mock_create_notif, mock_get_mgrs, mock_get_sup_user, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Select for update: (invoice_id, supplier_id, invoice_number, status, notes)
        # Payment count: 0
        # Update RETURNING updated_at
        mock_cursor.fetchone.side_effect = [
            (101, 9, "INV-TEST-001", "Approved", None),
            (0,),
            ("2026-10-12T10:10:00",)
        ]

        mock_get_sup_user.return_value = 55  # Supplier user
        mock_get_mgrs.return_value = [2]     # Other manager (acting user is 1)

        result, err, status = cancel_invoice(
            invoice_id=101,
            user_id=1,
            role="Owner",
            reason="PO terms renegotiated"
        )

        self.assertIsNone(err)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "Cancelled")

        # Verify supplier user notified AND other manager notified (2 calls total)
        mock_get_sup_user.assert_called_once_with(9)
        mock_get_mgrs.assert_called_once_with(exclude_user_id=1)
        self.assertEqual(mock_create_notif.call_count, 2)

        notified_users = [c[1]["user_id"] for c in mock_create_notif.call_args_list]
        self.assertIn(55, notified_users)
        self.assertIn(2, notified_users)
        self.assertNotIn(1, notified_users)  # Acting owner excluded

    # =========================================================================
    # Test 6: One consolidated notification for a recorded payment (Partially Paid)
    # =========================================================================
    @patch("app.services.team2.supplier_payment_service.get_db_connection")
    @patch("app.services.team2.supplier_payment_service.log_audit_event")
    @patch("app.services.team3.notification_service.get_supplier_user_id")
    @patch("app.services.team3.notification_service.create_notification")
    def test_06_record_payment_consolidated_notification_partial(
        self, mock_create_notif, mock_get_sup_user, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Invoice row: (invoice_id, supplier_id, invoice_number, total_amount, status)
        # Existing paid: 0.00
        # Payment insert RETURNING: payment_id, created_at
        mock_cursor.fetchone.side_effect = [
            (101, 9, "INV-TEST-001", Decimal("50000.00"), "Approved"),
            (Decimal("0.00"),),
            (201, "2026-10-12T10:15:00")
        ]

        mock_get_sup_user.return_value = 55

        pay_data = {
            "invoice_id": 101,
            "amount_paid": "20000.00",
            "payment_method": "Bank Transfer / NEFT",
            "payment_reference": "NEFT-HDFC-998877",
            "notes": "First milestone disbursement"
        }

        result, err, status = record_payment(user_id=1, role="Owner", data=pay_data)

        self.assertIsNone(err)
        self.assertEqual(status, 201)
        self.assertEqual(result["payment"]["payment_id"], 201)
        self.assertEqual(result["invoice"]["status"], "Partially Paid")
        self.assertEqual(result["invoice"]["remaining_balance"], 30000.00)

        # EXACTLY ONE consolidated notification must be dispatched
        self.assertEqual(mock_create_notif.call_count, 1)
        kwargs = mock_create_notif.call_args[1]
        self.assertEqual(kwargs["user_id"], 55)
        self.assertEqual(kwargs["title"], "Payment Received")
        self.assertEqual(kwargs["reference_type"], "Payment")
        self.assertEqual(kwargs["reference_id"], 201)
        self.assertEqual(kwargs["notification_type"], "Payment")

        # Message must contain amount, invoice number, remaining balance, and status
        msg = kwargs["message"]
        self.assertIn("20000.00", msg)
        self.assertIn("INV-TEST-001", msg)
        self.assertIn("NEFT-HDFC-998877", msg)
        self.assertIn("30000.00", msg)
        self.assertIn("Partially Paid", msg)

    # =========================================================================
    # Test 7: One consolidated notification for a recorded payment (Fully Paid)
    # =========================================================================
    @patch("app.services.team2.supplier_payment_service.get_db_connection")
    @patch("app.services.team2.supplier_payment_service.log_audit_event")
    @patch("app.services.team3.notification_service.get_supplier_user_id")
    @patch("app.services.team3.notification_service.create_notification")
    def test_07_record_payment_consolidated_notification_full(
        self, mock_create_notif, mock_get_sup_user, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        # Invoice row: total 50000, existing paid 20000, remaining 30000
        mock_cursor.fetchone.side_effect = [
            (101, 9, "INV-TEST-001", Decimal("50000.00"), "Partially Paid"),
            (Decimal("20000.00"),),
            (202, "2026-10-12T10:20:00")
        ]

        mock_get_sup_user.return_value = 55

        pay_data = {
            "invoice_id": 101,
            "amount_paid": "30000.00",
            "payment_method": "RTGS",
            "payment_reference": "RTGS-ICICI-112233"
        }

        result, err, status = record_payment(user_id=2, role="Manager", data=pay_data)

        self.assertIsNone(err)
        self.assertEqual(status, 201)
        self.assertEqual(result["invoice"]["status"], "Paid")
        self.assertEqual(result["invoice"]["remaining_balance"], 0.00)

        # EXACTLY ONE consolidated notification must be dispatched
        self.assertEqual(mock_create_notif.call_count, 1)
        kwargs = mock_create_notif.call_args[1]
        self.assertEqual(kwargs["user_id"], 55)
        self.assertEqual(kwargs["title"], "Payment Received — Invoice Settled")
        self.assertEqual(kwargs["reference_type"], "Payment")
        self.assertEqual(kwargs["reference_id"], 202)

        msg = kwargs["message"]
        self.assertIn("30000.00", msg)
        self.assertIn("INV-TEST-001", msg)
        self.assertIn("RTGS-ICICI-112233", msg)
        self.assertIn("0.00", msg)
        self.assertIn("Fully Paid", msg)

    # =========================================================================
    # Test 8: Inactive or missing recipient handled gracefully
    # =========================================================================
    @patch("app.services.team2.supplier_invoice_service.get_db_connection")
    @patch("app.services.team2.supplier_invoice_service.log_audit_event")
    @patch("app.services.team3.notification_service.get_supplier_user_id")
    @patch("app.services.team3.notification_service.create_notification")
    def test_08_missing_or_inactive_recipient_handled_gracefully(
        self, mock_create_notif, mock_get_sup_user, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            (101, "INV-TEST-001", "Submitted", Decimal("47200.00"), 9),
            ("2026-10-12T10:05:00",)
        ]

        # Inactive/missing supplier user returns None
        mock_get_sup_user.return_value = None

        result, err, status = approve_invoice(101, user_id=1, role="Owner")

        # Business operation must succeed without crash
        self.assertIsNone(err)
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "Approved")
        self.assertTrue(mock_conn.commit.called)

        # No notification call should be attempted when recipient is None
        mock_create_notif.assert_not_called()

    # =========================================================================
    # Test 9: Non-blocking resilience: notification exceptions do not fail financial commit
    # =========================================================================
    @patch("app.services.team2.supplier_payment_service.get_db_connection")
    @patch("app.services.team2.supplier_payment_service.log_audit_event")
    @patch("app.services.team3.notification_service.get_supplier_user_id")
    @patch("app.services.team3.notification_service.create_notification")
    def test_09_notification_exception_does_not_fail_committed_operation(
        self, mock_create_notif, mock_get_sup_user, mock_audit, mock_get_conn
    ):
        mock_conn, mock_cursor = self._create_mock_conn()
        mock_get_conn.return_value = mock_conn

        mock_cursor.fetchone.side_effect = [
            (101, 9, "INV-TEST-001", Decimal("50000.00"), "Approved"),
            (Decimal("0.00"),),
            (201, "2026-10-12T10:15:00")
        ]

        mock_get_sup_user.return_value = 55
        # Simulate network or database error during notification insert
        mock_create_notif.side_effect = RuntimeError("Supabase connection timeout during notification insert")

        pay_data = {
            "invoice_id": 101,
            "amount_paid": "10000.00",
            "payment_method": "UPI",
            "payment_reference": "UPI-TRANS-9900"
        }

        # Payment recording MUST succeed despite notification failure
        result, err, status = record_payment(user_id=1, role="Owner", data=pay_data)

        self.assertIsNone(err)
        self.assertEqual(status, 201)
        self.assertEqual(result["payment"]["payment_id"], 201)
        self.assertTrue(mock_conn.commit.called)
        self.assertFalse(mock_conn.rollback.called)

    # =========================================================================
    # Test 10: Preservation of RBAC, audit logging, and financial constraints
    # =========================================================================
    def test_10_preservation_of_rbac_and_validation(self):
        # 1. Employee cannot record payment
        result, err, status = record_payment(user_id=3, role="Employee", data={"invoice_id": 101})
        self.assertEqual(status, 403)
        self.assertIn("Access denied", err)

        # 2. Employee cannot approve invoice
        result, err, status = approve_invoice(invoice_id=101, user_id=3, role="Employee")
        self.assertEqual(status, 403)
        self.assertIn("Access denied", err)

        # 3. Employee cannot reject invoice
        result, err, status = reject_invoice(invoice_id=101, user_id=3, role="Employee", rejection_reason="test")
        self.assertEqual(status, 403)
        self.assertIn("Access denied", err)

        # 4. Employee cannot cancel invoice
        result, err, status = cancel_invoice(invoice_id=101, user_id=3, role="Employee")
        self.assertEqual(status, 403)
        self.assertIn("Access denied", err)


if __name__ == "__main__":
    unittest.main()
