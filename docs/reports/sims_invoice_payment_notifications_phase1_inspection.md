# SIMS Improvement 5 — Invoice & Payment Notifications
## Phase 1: Read-Only Inspection and Implementation Planning Report

**Document ID:** `SIMS-NOTIF-INVOICE-PAYMENT-PHASE1-INSPECTION`  
**Execution Date:** 2026-10-12  
**Lifecycle Stage:** Phase 1 (Read-Only Inspection & Architecture Planning) — **COMPLETED**  
**Target Module:** Accounts Payable (AP) Supplier Invoices, Payment Disbursements, & Notification Deep-Linking  
**System:** Smart Inventory Management System (SIMS)  
**Status:** **INSPECTION COMPLETE — STRICTLY READ-ONLY (ZERO DATABASE MUTATIONS)**

---

## 1. Executive Summary

A comprehensive architectural and static code inspection of the Smart Inventory Management System (SIMS) was conducted across the backend services, routing layer, notification subsystem, database schema, and frontend Single Page Application (SPA). The objective was to evaluate how invoice and payment lifecycle events interact with the notification system, verify recipient resolution logic, and assess compatibility with the newly implemented Notification Deep-Linking dispatcher.

### Key Inspection Findings:
1. **Total Notification Deficit in Accounts Payable (AP):** None of the 8 invoice and payment lifecycle events currently generate any notifications. While audit logging via `log_audit_event` is consistently present inside transactional blocks, no calls to `create_notification` exist anywhere in [`backend/app/services/team2/supplier_invoice_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/supplier_invoice_service.py), [`backend/app/services/team2/supplier_payment_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/supplier_payment_service.py), or their respective route modules.
2. **Recipient Infrastructure is Ready:** Core helper utilities in [`backend/app/services/team3/notification_service.py`](file:///d:/7even/repica/2/backend/app/services/team3/notification_service.py) already exist and operate cleanly:
   - `get_active_managers_and_owners(exclude_user_id=None)` identifies active internal administrators without notifying the acting user.
   - `get_supplier_user_id(supplier_id)` securely maps a supplier organization profile to its corresponding active `user_id`.
   - `resolve_supplier_id_for_user(cursor, user_id)` maps user JWT tokens to supplier entities.
3. **Frontend Deep-Linking Compatibility:**
   - The reference normalizer in [`frontend/js/app.js`](file:///d:/7even/repica/2/frontend/js/app.js#L459-L475) already normalizes `'INVOICE'` and `'PAYMENT'`.
   - The action dispatcher (`App.navigateToReference`) already supports `'INVOICE'`, correctly launching `App.pages['payments'].viewInvoiceDetails(invoiceId)` with role enforcement for Owners, Managers, and Suppliers.
   - However, `'PAYMENT'` is currently **missing** from `configMap` in [`frontend/js/app.js`](file:///d:/7even/repica/2/frontend/js/app.js#L520-L565), even though [`frontend/js/pages/payments.js`](file:///d:/7even/repica/2/frontend/js/pages/payments.js#L1863) already implements `App.pages['payments'].viewPaymentVoucher(paymentId)`.
4. **Transaction Boundary Compliance:** In accordance with SIMS architectural conventions established in `shipment_service.py` and `quotation_service.py`, notifications must be dispatched strictly **after** `conn.commit()` within isolated `try/except` blocks to prevent financial transaction rollback in the event of notification service degradation.
5. **No Code or Database Modifications:** This inspection was purely analytical. No migrations were executed, no records were created or updated, and no source files were modified.

---

## 2. Files and Functions Inspected

### 2.1 Backend Services & Handlers
- [`backend/app/services/team2/supplier_invoice_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/supplier_invoice_service.py):
  - `submit_invoice(user_id, role, data)` (lines 38–341)
  - `get_invoices(...)` (lines 344–488)
  - `get_invoice_by_id(invoice_id, user_id, role)` (lines 564–709)
  - `approve_invoice(invoice_id, user_id, role)` (lines 712–793)
  - `reject_invoice(invoice_id, user_id, role, rejection_reason)` (lines 795–881)
  - `cancel_invoice(invoice_id, user_id, role, reason)` (lines 883–994)
  - `resolve_supplier_id_for_user(cursor, user_id)` (lines 20–35)
- [`backend/app/services/team2/supplier_payment_service.py`](file:///d:/7even/repica/2/backend/app/services/team2/supplier_payment_service.py):
  - `record_payment(user_id, role, data)` (lines 38–250)
  - `get_payments(...)` (lines 252–400)
  - `get_payment_by_id(payment_id, user_id, role)` (lines 402–493)
- [`backend/app/routes/team2/invoices.py`](file:///d:/7even/repica/2/backend/app/routes/team2/invoices.py): Inspected all Flask endpoints (`POST /`, `GET /`, `GET /<id>`, `PUT /<id>/approve`, `PUT /<id>/reject`, `PUT /<id>/cancel`).
- [`backend/app/routes/team2/payments.py`](file:///d:/7even/repica/2/backend/app/routes/team2/payments.py): Inspected all Flask endpoints (`POST /`, `GET /`, `GET /<id>`).
- [`backend/app/services/team3/notification_service.py`](file:///d:/7even/repica/2/backend/app/services/team3/notification_service.py):
  - `create_notification(...)` (lines 332–485)
  - `get_active_managers_and_owners(exclude_user_id)` (lines 487–520)
  - `get_supplier_user_id(supplier_id)` (lines 522–548)
  - `get_user_notifications(...)` (lines 5–90)
  - `mark_notification_as_read(...)` (lines 154–206)
- [`backend/app/services/team3/audit_service.py`](file:///d:/7even/repica/2/backend/app/services/team3/audit_service.py): Inspected `log_audit_event(...)`.

### 2.2 Frontend Deep-Linking & UI Controllers
- [`frontend/js/app.js`](file:///d:/7even/repica/2/frontend/js/app.js):
  - `App.routes` configuration (lines 6–25)
  - `App.normalizeReferenceType(type)` (lines 459–475)
  - `App.navigateToReference(referenceType, referenceId, notificationId)` (lines 477–634)
- [`frontend/js/pages/payments.js`](file:///d:/7even/repica/2/frontend/js/pages/payments.js):
  - `viewInvoiceDetails(invoiceId)` (lines 1222–1429)
  - `viewPaymentVoucher(paymentId)` (lines 1863–1955)
  - `openRecordPaymentModal(preselectedInvoiceId)` (lines 1690–1857)
  - `openSubmitInvoiceModal()` (lines 940–1218)
  - Tab state handlers (`renderInvoicesTab`, `renderPaymentsTab`)
- [`frontend/js/pages/notifications.js`](file:///d:/7even/repica/2/frontend/js/pages/notifications.js): Click handling and table synchronization.

### 2.3 Database Schemas & Migrations
- [`database/migrations/001_create_supplier_payments_and_invoices.sql`](file:///d:/7even/repica/2/database/migrations/001_create_supplier_payments_and_invoices.sql): Schema definition for `SupplierInvoices` and `SupplierPayments`.
- [`database/migrations/002_secure_supplier_payments_and_invoices_rls.sql`](file:///d:/7even/repica/2/database/migrations/002_secure_supplier_payments_and_invoices_rls.sql): Supabase Row Level Security policies.

### 2.4 Existing Test Suites
- [`tests/team2/test_supplier_payments_phase2.py`](file:///d:/7even/repica/2/tests/team2/test_supplier_payments_phase2.py): Backend AP test suite.
- [`tests/team2/test_supplier_payments_phase3_frontend.py`](file:///d:/7even/repica/2/tests/team2/test_supplier_payments_phase3_frontend.py): Frontend contract test suite.
- [`tests/team2/test_supplier_payments_phase4_integration.py`](file:///d:/7even/repica/2/tests/team2/test_supplier_payments_phase4_integration.py): Integration test suite.
- [`tests/team2/test_notification_deep_linking.js`](file:///d:/7even/repica/2/tests/team2/test_notification_deep_linking.js): Node DOM sandbox deep-linking suite.
- [`tests/team2/test_notification_deep_linking.py`](file:///d:/7even/repica/2/tests/team2/test_notification_deep_linking.py): Pytest runner for deep-linking.

---

## 3. Existing Notification Creation Flow for Invoice & Payment Events

The following table traces the 8 required lifecycle events against the live codebase:

| # | Event Description | Execution Function | Audit Event Generated | Notification Created Today? | Reference Stored | Current Recipients |
|---|---|---|---|:---:|---|---|
| **1** | Supplier submits an invoice | `submit_invoice()` (`supplier_invoice_service.py:38`) | `INVOICE_SUBMITTED` (`SupplierInvoices`, record `invoice_id`) | **NONE (Missing)** | N/A | None |
| **2** | Owner/Manager approves invoice | `approve_invoice()` (`supplier_invoice_service.py:712`) | `INVOICE_APPROVED` (`SupplierInvoices`, record `invoice_id`) | **NONE (Missing)** | N/A | None |
| **3** | Owner/Manager rejects invoice | `reject_invoice()` (`supplier_invoice_service.py:795`) | `INVOICE_REJECTED` (`SupplierInvoices`, record `invoice_id`) | **NONE (Missing)** | N/A | None |
| **4** | Supplier cancels submitted invoice | `cancel_invoice()` (`supplier_invoice_service.py:883`) | `INVOICE_CANCELLED` (`SupplierInvoices`, record `invoice_id`) | **NONE (Missing)** | N/A | None |
| **5** | Owner/Manager cancels eligible invoice | `cancel_invoice()` (`supplier_invoice_service.py:883`) | `INVOICE_CANCELLED` (`SupplierInvoices`, record `invoice_id`) | **NONE (Missing)** | N/A | None |
| **6** | Owner/Manager records a payment | `record_payment()` (`supplier_payment_service.py:38`) | `PAYMENT_RECORDED` (`SupplierPayments`, record `payment_id`) | **NONE (Missing)** | N/A | None |
| **7** | Invoice becomes partially paid | `record_payment()` (`supplier_payment_service.py:189`) | `PAYMENT_RECORDED` (Invoice update un-audited) | **NONE (Missing)** | N/A | None |
| **8** | Invoice becomes fully paid | `record_payment()` (`supplier_payment_service.py:187`) | `PAYMENT_RECORDED` (Invoice update un-audited) | **NONE (Missing)** | N/A | None |

### Codebase Observations:
- **Zero Trigger Hooks:** No signals, hooks, or helper calls exist in `supplier_invoice_service.py` or `supplier_payment_service.py` to trigger alerts.
- **Audit Logging Precedent:** Every event (except the status derivation in events 7 & 8) writes to `public."AuditLogs"` using the shared cursor within the uncommitted transaction block (`log_audit_event(..., cursor=cursor)`).
- **Silent Failures Avoided:** Because notifications are not yet wired up, no partial failure or transaction abort occurs due to notification errors.

---

## 4. Event-to-Recipient Matrix: Existing vs Proposed Behavior

| Event | Existing Behavior | Proposed Behavior | Recipient Resolution Method | Actor Exclusion Verified? |
|---|---|---|---|:---:|
| **1. Invoice Submitted** | No alert | Notify active Owners & Managers | `get_active_managers_and_owners(exclude_user_id=user_id)` | Yes (Supplier actor excluded) |
| **2. Invoice Approved** | No alert | Notify the Supplier linked to the invoice | `get_supplier_user_id(invoice.supplier_id)` | Yes (Approving Manager not notified) |
| **3. Invoice Rejected** | No alert | Notify the Supplier linked to the invoice (with rejection reason) | `get_supplier_user_id(invoice.supplier_id)` | Yes (Rejecting Manager not notified) |
| **4. Invoice Cancelled (by Supplier)** | No alert | Notify active Owners & Managers | `get_active_managers_and_owners(exclude_user_id=user_id)` | Yes (Supplier actor excluded) |
| **5. Invoice Cancelled (by Management)** | No alert | Notify the Supplier linked to the invoice | `get_supplier_user_id(invoice.supplier_id)` | Yes (Cancelling Manager excluded) |
| **6. Payment Recorded** | No alert | Notify the Supplier receiving the disbursement | `get_supplier_user_id(payment.supplier_id)` | Yes (Disbursing Manager not notified) |
| **7. Invoice Partially Paid** | No alert | **Consolidated into Event 6** | `get_supplier_user_id(payment.supplier_id)` | Yes |
| **8. Invoice Fully Paid** | No alert | **Consolidated into Event 6** | `get_supplier_user_id(payment.supplier_id)` | Yes |

### Recipient Decision Analysis:
1. **Supplier Mapping Mechanism:**
   - In PostgreSQL, `public."Suppliers"` contains `user_id BIGINT REFERENCES public."Users"(user_id)`.
   - `get_supplier_user_id(supplier_id)` performs:
     ```sql
     SELECT u.user_id FROM "Suppliers" s
     JOIN "Users" u ON s.user_id = u.user_id
     WHERE s.supplier_id = %s AND u.status = 'Active';
     ```
   - If the supplier user is inactive or deleted, `get_supplier_user_id` returns `None`, safely preventing dangling notification insertions.
2. **Owner/Manager Identification:**
   - `get_active_managers_and_owners(exclude_user_id)` queries `Users` joined with `Roles` where `r.role_name IN ('Owner', 'Manager')` and `u.status = 'Active'`.
   - Passing `exclude_user_id` guarantees that when an Owner performs an action, they do not receive redundant notifications.
3. **Data Isolation & Non-Procurement Employees:**
   - Employees (`role = 'Employee'`) are strictly excluded from all invoice and payment notifications. They do not have access to the accounts payable module.
   - Unrelated suppliers never receive notifications because `supplier_id` is always derived directly from the locked invoice or payment row.

---

## 5. Reference Types, Reference IDs, and Deep-Link Compatibility

### 5.1 Current Normalizer & Dispatcher Status in `frontend/js/app.js`

```javascript
// App.normalizeReferenceType(type)
if (clean === 'INVOICE' || clean === 'SUPPLIERINVOICE') return 'INVOICE';
if (clean === 'PAYMENT' || clean === 'SUPPLIERPAYMENT') return 'PAYMENT';
```

1. **`INVOICE` Reference:**
   - Normalized Key: `'INVOICE'`
   - Config in `navigateToReference`:
     ```javascript
     'INVOICE': {
         path: 'payments',
         actionType: 'modal',
         modalFn: 'viewInvoiceDetails',
         entityName: 'Invoice'
     }
     ```
   - Target Function: `App.pages['payments'].viewInvoiceDetails(invoiceId)` ([`payments.js:1222`](file:///d:/7even/repica/2/frontend/js/pages/payments.js#L1222)).
   - Functionality: Fully functional! Opens the comprehensive modal showing PO linkage, shipment tracking, subtotal, taxes, balance remaining, and embedded payment disbursement history.
   - RBAC Guard: Verified. Permitted for `Owner`, `Manager`, and `Supplier`. Blocked for `Employee`.
2. **`PAYMENT` Reference:**
   - Normalized Key: `'PAYMENT'`
   - Config in `navigateToReference`: **MISSING from `configMap`!**
   - If a notification contains `reference_type="Payment"`, the normalizer produces `'PAYMENT'`, but `configMap['PAYMENT']` is `undefined`, triggering:
     `Utils.showToast("Direct link unavailable for reference type: Payment", "warning")`.
   - Target Function in `payments.js`:
     `App.pages['payments'].viewPaymentVoucher(paymentId)` ([`payments.js:1863`](file:///d:/7even/repica/2/frontend/js/pages/payments.js#L1863)).
     This function already exists and accepts `paymentId`. It renders a complete corporate disbursement voucher modal with UTR/cheque reference, payment method, supplier name, and settled invoice summary.

### 5.2 Deep-Link Mapping Recommendations

| Event | Recommended `reference_type` | Recommended `reference_id` | Frontend Action Invoked | Target Modal View |
|---|---|---|---|---|
| Invoice Submitted | `Invoice` | `invoice_id` | `viewInvoiceDetails(invoiceId)` | Invoice Details Modal |
| Invoice Approved | `Invoice` | `invoice_id` | `viewInvoiceDetails(invoiceId)` | Invoice Details Modal |
| Invoice Rejected | `Invoice` | `invoice_id` | `viewInvoiceDetails(invoiceId)` | Invoice Details Modal (with Rejection Banner) |
| Invoice Cancelled | `Invoice` | `invoice_id` | `viewInvoiceDetails(invoiceId)` | Invoice Details Modal (with Cancelled Banner) |
| Payment Recorded | `Payment` (or `Invoice`) | `payment_id` (or `invoice_id`) | `viewPaymentVoucher(paymentId)` or `viewInvoiceDetails(invoiceId)` | Payment Voucher Modal / Invoice Details Modal |

> [!IMPORTANT]
> **Architectural Recommendation for Payment Deep-Linking:**
> In [`payments.js`](file:///d:/7even/repica/2/frontend/js/pages/payments.js#L1374), `viewInvoiceDetails(invoiceId)` already includes the full list of payments with one-click buttons to open each payment voucher. Conversely, `viewPaymentVoucher(paymentId)` focuses directly on the disbursement voucher.
> To support both seamlessly:
> 1. Set `reference_type = 'Payment'` and `reference_id = payment_id` for payment disbursements.
> 2. Add `'PAYMENT'` to `configMap` in [`frontend/js/app.js`](file:///d:/7even/repica/2/frontend/js/app.js#L564):
>    ```javascript
>    'PAYMENT': {
>        path: 'payments',
>        actionType: 'modal',
>        modalFn: 'viewPaymentVoucher',
>        entityName: 'Payment Voucher'
>    }
>    ```

---

## 6. Transaction Boundaries and Duplicate-Notification Risks

### 6.1 Transaction Boundary Architecture
In SIMS, financial consistency is paramount:
1. All table updates, row locks (`SELECT ... FOR UPDATE`), monetary balance calculations, and audit log writes happen within the database transaction (`conn.autocommit = False`).
2. The transaction MUST commit (`conn.commit()`) before notifications are dispatched.
3. Notification dispatch must be wrapped in an isolated `try/except Exception as notif_err:` block:
   ```python
   conn.commit()

   # Non-blocking notification dispatch
   try:
       from app.services.team3.notification_service import create_notification
       create_notification(
           user_id=target_user_id,
           title=title,
           message=message,
           notification_type="Invoice",
           priority="Normal",
           reference_type="Invoice",
           reference_id=invoice_id
       )
   except Exception as notif_err:
       print(f"[NOTIFICATION WARNING] Failed to send notification: {notif_err}", flush=True)
   ```
4. **Failure Guarantee:** If Supabase notifications table is temporarily locked or network connectivity fails during alert creation, the financial transaction is ALREADY committed and safe.

### 6.2 Duplicate Notification Risks & Prevention
1. **Built-in Unread Deduplication:**
   [`backend/app/services/team3/notification_service.py:398-429`](file:///d:/7even/repica/2/backend/app/services/team3/notification_service.py#L398-L429) checks:
   ```sql
   SELECT notification_id FROM "Notifications"
   WHERE user_id = %s AND is_read = FALSE
     AND reference_type = %s AND reference_id = %s AND notification_type = %s
   LIMIT 1;
   ```
   If an identical unread notification already exists, insertion is skipped.
2. **Disbursement Multi-Notification Trap (Events 6, 7, 8):**
   When an Owner/Manager records a payment against an invoice:
   - The payment is inserted into `SupplierPayments`.
   - The invoice balance is reduced, changing status to `'Partially Paid'` or `'Paid'`.
   - **Risk:** If the service fires one notification for "Payment Recorded" and another notification for "Invoice Partially Paid" / "Invoice Fully Paid", the supplier inbox receives **two alerts for one single user action**.
   - **Resolution:** Consolidate the alert into a single, high-fidelity message:
     - For partial settlement: Title: `"Payment Received"`, Message: `"Payment of ₹{amount_paid} recorded for invoice {invoice_number} (Ref: {payment_reference}). Remaining balance: ₹{remaining_balance}."`
     - For full settlement: Title: `"Payment Received — Invoice Settled"`, Message: `"Final payment of ₹{amount_paid} recorded for invoice {invoice_number} (Ref: {payment_reference}). Invoice is now fully paid."`

---

## 7. Authorization and Data-Isolation Observations

1. **Role-Based Route Access:**
   In `App.routes`, path `'payments'` allows `['Owner', 'Manager', 'Supplier']`. If an unauthorized role (e.g. `Employee`) clicks an invoice or payment deep link, `App.navigateToReference` halts immediately and displays:
   `"Invoice module is not accessible for role Employee"`. The browser hash remains unaltered.
2. **Backend Supplier Isolation (Anti-IDOR):**
   - In `get_invoice_by_id(invoice_id, user_id, role)`:
     If `role == 'Supplier'`, the authenticated supplier ID is resolved via `resolve_supplier_id_for_user(cursor, user_id)`. If the target invoice's `supplier_id` differs, a `403 Access denied. Invoice belongs to another supplier` error is returned.
   - In `get_payment_by_id(payment_id, user_id, role)`:
     The same check is enforced (`403 Access denied. Payment belongs to another supplier`).
3. **Sensitive Data Privacy in Notification Text:**
   - Notification messages must not expose bank account numbers, internal financial review notes, or management margin calculations.
   - Safe fields to include: Invoice Number, PO Number, Amount Paid, Remaining Balance, Payment Method, and Public Payment Reference (UTR/Cheque).

---

## 8. Existing Tests and Identified Test Gaps

### 8.1 Existing Tests Reviewed
- `tests/team2/test_supplier_payments_phase2.py`: Covers backend RBAC, input validation, overpayment prevention, and shipment eligibility. Does NOT test notification creation.
- `tests/team2/test_supplier_payments_phase3_frontend.py`: Validates HTML/JS static structure for payments. Does NOT test notification creation.
- `tests/team2/test_supplier_payments_phase4_integration.py`: End-to-end integration tests for invoice lifecycle. Does NOT assert notification creation.
- `tests/team2/test_notification_deep_linking.js`: Tests normalizer and dispatcher for existing reference types including `'INVOICE'`, but does not test `'PAYMENT'` voucher modal dispatch.

### 8.2 Identified Test Gaps (To be addressed in Phase 2)
1. **Unit Tests for Notification Dispatch:**
   - Test that `submit_invoice()` dispatches alerts to all active Owners and Managers.
   - Test that `approve_invoice()` dispatches an alert to the invoice's supplier user.
   - Test that `reject_invoice()` dispatches an alert with rejection reason to the supplier user.
   - Test that `cancel_invoice()` dispatches an alert to Owners/Managers when cancelled by Supplier, and to the Supplier when cancelled by Owner.
   - Test that `record_payment()` dispatches a single consolidated alert to the supplier user.
2. **Non-Blocking Resilience Test:**
   - Test that when `create_notification` throws an exception, the invoice or payment operation commits successfully without raising a 500 error.
3. **Frontend Deep-Linking Unit Test:**
   - Extend `test_notification_deep_linking.js` to assert that reference type `'PAYMENT'` navigates to `#payments` and executes `App.pages['payments'].viewPaymentVoucher(paymentId)`.

---

## 9. Recommended Minimal Changes for Phase 2

### 9.1 Backend (`backend/app/services/team2/`)
1. **In `supplier_invoice_service.py`:**
   - In `submit_invoice`: After `conn.commit()`, query `get_active_managers_and_owners(exclude_user_id=user_id)` and invoke `create_notification` for each recipient.
   - In `approve_invoice`: After `conn.commit()`, query `get_supplier_user_id(supplier_id)` and invoke `create_notification`.
   - In `reject_invoice`: After `conn.commit()`, query `get_supplier_user_id(supplier_id)` and invoke `create_notification`.
   - In `cancel_invoice`: After `conn.commit()`, if actor is Supplier, notify Owners/Managers; if actor is Owner/Manager, notify the Supplier.
2. **In `supplier_payment_service.py`:**
   - In `record_payment`: After `conn.commit()`, query `get_supplier_user_id(supplier_id)` and invoke `create_notification` with consolidated payment details and updated invoice status.

### 9.2 Frontend (`frontend/js/app.js`)
1. In `App.navigateToReference`:
   - Add `'PAYMENT'` to `configMap`:
     ```javascript
     'PAYMENT': {
         path: 'payments',
         actionType: 'modal',
         modalFn: 'viewPaymentVoucher',
         entityName: 'Payment Voucher'
     }
     ```

### 9.3 Test Additions (`tests/team2/`)
1. Create `tests/team2/test_invoice_payment_notifications.py` with mocked database connections to verify notification triggering without modifying live database records.
2. Add `'PAYMENT'` test case to `tests/team2/test_notification_deep_linking.js`.

---

## 10. Risks, Unresolved Business-Rule Decisions, and Limitations

### Decision 1: Consolidated vs Dual Payment Notifications
- **Option A (Recommended):** Emit a single consolidated notification upon payment recording indicating both the payment received and the updated invoice balance/status (`Partially Paid` or `Paid`).
- **Option B:** Emit two separate notifications: one for payment recording and one for invoice status update.
- *Recommendation:* Option A avoids alert fatigue and prevents unread notification clutter.

### Decision 2: Deep-Link Destination for Payment Alerts
- **Option A (Recommended):** Payment alerts use `reference_type="Payment"` and `reference_id=payment_id`, opening `viewPaymentVoucher(paymentId)`. The voucher already shows the settled invoice number.
- **Option B:** Payment alerts use `reference_type="Invoice"` and `reference_id=invoice_id`, opening `viewInvoiceDetails(invoiceId)`. The modal shows the invoice details and lists all payments.
- *Recommendation:* Support Option A by adding `'PAYMENT'` to `app.js` `configMap`. Both functions already exist in `payments.js`.

### Decision 3: Internal Notification on Management Invoice Cancellation
- When an Owner or Manager cancels an invoice, should **other** Owners and Managers also receive a notification in addition to the affected Supplier?
- *Recommendation:* Notify both the affected Supplier and other active Owners/Managers (excluding the actor).

---

## 11. Explicit Confirmation of Read-Only Execution

- **Zero Database Writes:** No SQL `INSERT`, `UPDATE`, or `DELETE` statements were executed against Supabase PostgreSQL.
- **Zero Schema Migrations:** No migration files were run or modified.
- **Zero Mock Records:** No test invoices, payments, or notifications were inserted into live tables.
- **Zero Application Edits:** No application code in `backend/` or `frontend/` was modified during this phase.
- Only this markdown inspection report file was authored.

---

**END OF REPORT — AWAITING USER APPROVAL PRIOR TO COMMENCING PHASE 2**
