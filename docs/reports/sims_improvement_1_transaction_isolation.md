# SIMS Improvement 1 — Employee Transaction Data Isolation Report

**Date:** October 11, 2026  
**Module:** Inventory Management / Stock Movement Audit Trail  
**Feature:** Stock Transactions API & Data Isolation  
**Task:** Improvement 1 — Employee Transaction Data Isolation  
**Status:** Completed & Verified  

---

## 1. Original Issue and Reproducibility

### Issue Description
Prior to this fix, the stock transactions listing endpoint `GET /api/inventory/transactions` allowed users with the `Employee` role (`@role_required("Owner", "Manager", "Employee")`) to retrieve the entire enterprise-wide ledger of stock movements across all users and employees whenever the `user_id` query parameter was omitted. Furthermore, if an Employee explicitly provided a query parameter pointing to another user's ID (e.g., `?user_id=6` or `?user_id=1`), the endpoint accepted it and filtered by that foreign user ID, exposing transactions logged by managers, owners, and other warehouse staff. Similarly, the single transaction detail endpoint `GET /api/inventory/transactions/<transaction_id>` permitted any Employee to view details of any arbitrary transaction ID regardless of who recorded it.

### Reproducibility Verification
- **Reproduced:** Verified in the pre-fix code in `backend/app/routes/team1/inventory.py` and `backend/app/services/team1/inventory_service.py:849-947`.
- **Pre-fix Service Signature:** `get_stock_transactions(product_id=None, transaction_type=None, date_from=None, date_to=None, user_id_filter=None, shipment_id_filter=None, role=None)` lacked an `auth_user_id` parameter. The SQL query added `AND st.user_id = %s` only if `user_id_filter` was passed, with no validation verifying that an employee could only query their own user ID.
- **Single Transaction Check:** `get_stock_transaction_by_id(transaction_id, role=user_role)` only checked `if role == 'Supplier'` and did not verify whether the transaction's `user_id` matched the authenticated employee.

---

## 2. Root Cause Analysis

1. **Missing Authenticated Identity in Service Calls:** The route handler in `backend/app/routes/team1/inventory.py` extracted `claims.get("role")`, but failed to retrieve `auth_user_id = get_jwt_identity()` and pass it into `get_stock_transactions()` or `get_stock_transaction_by_id()`.
2. **Missing Server-Side Role-Based Scoping:** `inventory_service.py` treated `user_id_filter` as an optional filter for all authorized roles alike, instead of enforcing that `Employee` accounts are strictly bound to `st.user_id = auth_user_id`.
3. **No Mismatch Validation on Client Input:** If an employee client sent `?user_id=<other_user_id>`, the server did not reject the request or validate it against the authenticated JWT identity.

---

## 3. Files Inspected and Changed

| File Path | Change Type | Description |
| :--- | :--- | :--- |
| `backend/app/routes/team1/inventory.py` | Modified | Extracted `auth_user_id = get_jwt_identity()` in `list_stock_transactions()` and `view_stock_transaction()` and forwarded it to service functions. |
| `backend/app/services/team1/inventory_service.py` | Modified | Updated `get_stock_transactions()` and `get_stock_transaction_by_id()` to enforce mandatory `auth_user_id` scoping for `Employee`, reject mismatched `user_id` filters with 403 Forbidden, and enforce single-transaction ownership checks. |
| `tests/team1/test_employee_transaction_isolation.py` | Created | Added comprehensive 10-case non-destructive test suite covering all role combinations, parameter manipulations, single-transaction views, and unauthenticated requests. |

---

## 4. Description of the Fix

### 4.1 Route Layer (`backend/app/routes/team1/inventory.py`)
In `list_stock_transactions()` and `view_stock_transaction()`, the authenticated JWT identity is obtained using Flask-JWT-Extended's established `get_jwt_identity()`:

```python
# List Stock Transactions History
@inventory_bp.route("/transactions", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def list_stock_transactions():
    claims = get_jwt()
    user_role = claims.get("role")
    auth_user_id = get_jwt_identity()

    product_id = request.args.get("product_id")
    tx_type = request.args.get("transaction_type") or request.args.get("type")
    date_from = request.args.get("date_from") or request.args.get("start_date")
    date_to = request.args.get("date_to") or request.args.get("end_date")
    user_id_filter = request.args.get("user_id")
    shipment_id_filter = request.args.get("shipment_id")

    transactions, error = get_stock_transactions(
        product_id=product_id,
        transaction_type=tx_type,
        date_from=date_from,
        date_to=date_to,
        user_id_filter=user_id_filter,
        shipment_id_filter=shipment_id_filter,
        role=user_role,
        auth_user_id=auth_user_id
    )

    if error:
        if "Access denied" in error:
            return jsonify({"error": error}), 403
        return jsonify({"error": error}), 500

    return jsonify({
        "transactions": transactions,
        "count": len(transactions)
    }), 200
```

### 4.2 Service Layer (`backend/app/services/team1/inventory_service.py`)
1. **List Scoping Enforcement:**
   - If `role == 'Employee'`:
     - Requires valid `auth_user_id`.
     - If client provides a `user_id` query parameter that does not match `auth_user_id`, immediately returns `None, "Access denied. Employees can only view their own transaction records."` (HTTP 403).
     - Forces `scoped_user_id = emp_uid`, appending `AND st.user_id = %s` to the SQL query.
   - If `role in ('Owner', 'Manager')`:
     - Retains existing behavior: if `user_id_filter` is supplied, filters by that user; otherwise returns all transactions.
   - If `role == 'Supplier'`:
     - Returns `None, "Access denied. Suppliers cannot view transaction history."` (HTTP 403).
2. **Single Transaction Detail Scoping:**
   - `get_stock_transaction_by_id(transaction_id, role=None, auth_user_id=None)` verifies `tx_user_id == emp_uid` for `Employee`. Mismatched transactions return `None, "Access denied. You do not have permission to view this transaction."` (HTTP 403).

---

## 5. Authorization Behavior by Role

| User Role | Query Parameter `user_id` Behavior | Returned Transactions Scope | Single Transaction Access (`GET /<id>`) |
| :--- | :--- | :--- | :--- |
| **Employee** | **Omitted:** Server auto-scopes to authenticated employee ID.<br>**Matching own ID:** Allowed, scoped to own ID.<br>**Mismatched ID:** HTTP 403 Forbidden ("Access denied. Employees can only view their own transaction records."). | Strictly records where `st.user_id = auth_user_id`. Counts match returned rows. | Allowed **only** if transaction was logged by authenticated employee (`st.user_id == auth_user_id`). Otherwise HTTP 403. |
| **Manager** | **Omitted:** Full enterprise transaction visibility.<br>**Supplied:** Scoped to requested `user_id`. | Organization-wide stock movement ledger. | Full access to any transaction. |
| **Owner** | **Omitted:** Full enterprise transaction visibility.<br>**Supplied:** Scoped to requested `user_id`. | Organization-wide stock movement ledger. | Full access to any transaction. |
| **Supplier** | Any parameters rejected. | HTTP 403 Forbidden ("Access denied. Suppliers cannot view transaction history."). | HTTP 403 Forbidden. |
| **Unauthenticated** | Any parameters rejected. | HTTP 401 Unauthorized / HTTP 422 Invalid Token. | HTTP 401 Unauthorized. |

---

## 6. Tests Executed and Results

A comprehensive, focused, non-destructive test suite was executed:

**Command:**
```powershell
pytest tests/team1/test_employee_transaction_isolation.py
```

### Test Results Summary

| # | Test Case Identifier | Purpose | Result |
| :-: | :--- | :--- | :-: |
| 1 | `test_01_employee_query_without_user_id_only_returns_own_records` | Verifies Employee calling endpoint with no `user_id` returns strictly own records | **PASSED** |
| 2 | `test_02_employee_query_with_own_user_id_succeeds` | Verifies Employee passing own `user_id=7` succeeds and returns own records | **PASSED** |
| 3 | `test_03_employee_query_with_other_user_id_is_forbidden` | Verifies Employee passing another user's ID (`?user_id=6` or `5`) receives 403 Forbidden | **PASSED** |
| 4 | `test_04_employee_query_with_additional_filters_cannot_bypass_scoping` | Verifies filtering by `transaction_type=STOCK_IN` maintains strict employee scoping | **PASSED** |
| 5 | `test_05_response_contract_and_counts_match_scope` | Verifies payload contract `{"transactions": [...], "count": N}` matches scoped count | **PASSED** |
| 6 | `test_06_owner_and_manager_retain_unrestricted_visibility` | Verifies Owner and Manager retain full visibility and can filter by employee ID | **PASSED** |
| 7 | `test_07_supplier_access_is_forbidden` | Verifies Supplier role receives HTTP 403 Forbidden | **PASSED** |
| 8 | `test_08_unauthenticated_requests_are_rejected` | Verifies missing token (401) and invalid token (422) rejection | **PASSED** |
| 9 | `test_09_single_transaction_detail_authorization` | Verifies single transaction access: own (200), other user (403), manager (200), supplier (403) | **PASSED** |
| 10 | `test_10_service_level_isolation_direct_call` | Service function unit test verifying `get_stock_transactions` and mismatched filter errors | **PASSED** |

**Execution Summary:** `10 passed in 35.83s` (100% pass rate).

### Regression Testing
Regression test suites for existing dashboard and status endpoints were also executed:
```powershell
pytest tests/team3/test_status.py tests/team3/test_dashboard.py
```
**Result:** `20 passed in 63.96s` (100% pass rate).

---

## 7. Tests Not Run and Remaining Risks

- **Full End-to-End Browser Flow:** Full browser automation was not executed during this focused fix to respect the strict non-destructive constraints.
- **Remaining Risks:** None identified for this endpoint. The API response contract (`{"transactions": [...], "count": N}`) and field names are completely preserved, ensuring zero disruption to existing frontend views (`stock-transactions.js` and `inventory.js`).

---

## 8. Confirmations

- **Database Schema Changes:** None required. All enforcement is handled at the application service and query building layer.
- **Live Business Data:** Zero production or live records were inserted, modified, or deleted during implementation and testing.
- **Architecture Integrity:** Existing JWT authentication, RBAC decorators, connection pooling, and error conventions were strictly preserved.
