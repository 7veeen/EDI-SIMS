# SIMS Improvement 2 — Stock Request Route Authorization Report

**Date:** October 11, 2026  
**Module:** Stock Requests / Procurement & Supplier Portal  
**Feature:** Route-Level RBAC Authorization & Supplier Isolation  
**Task:** Improvement 2 — Stock Request Route Authorization  
**Status:** Completed & Verified  

---

## 1. Summary and Completion Status

Improvement 2 (Stock Request Route Authorization) from the approved SIMS implementation roadmap has been successfully implemented, verified, and thoroughly tested.

- **Completion Status:** Fully Completed and Verified.
- **Goal Achieved:** Replaced bare `@jwt_required()` decorators on the Stock Request listing (`GET /api/stock-requests/`) and single request detail (`GET /api/stock-requests/<int:stock_request_id>`) endpoints with explicit route-level RBAC enforcement (`@role_required("Owner", "Manager", "Supplier")`).
- **Defect Closed:** Prevented unauthorized roles—specifically `Employee` and unauthenticated callers—from invoking Stock Request endpoints and consuming backend business/database resources before authorization validation.
- **Defense in Depth Preserved:** Maintained all existing service-level role verification (`if role not in ("Owner", "Manager", "Supplier")`) and strict supplier-scoping checks (`resolve_supplier_id_for_user()`) in `backend/app/services/team2/stock_request_service.py`.
- **Zero Schema or Data Impact:** No database schema alterations, migration scripts, or production record mutations were performed.

---

## 2. Original Audit Finding and Verification

### 2.1 The Audit Finding
The previous SIMS codebase security audit flagged that:
> The Stock Request listing endpoint `GET /api/stock-requests/` reportedly used `@jwt_required()` without an explicit route-level `@role_required` decorator, relying entirely on downstream service checks to reject unauthorized users like Employees.

### 2.2 Verification Against Current Code
Inspection of `backend/app/routes/team2/stock_requests.py` confirmed that this finding was **accurate and still existed prior to this improvement**:

1. **Listing Endpoint (`GET /api/stock-requests/`):**
   ```python
   # BEFORE (Lines 14-15)
   @stock_requests_bp.route("/", methods=["GET"])
   @jwt_required()
   def list_stock_requests():
   ```
   Lacked `@role_required("Owner", "Manager", "Supplier")`. Any authenticated user with an `Employee` JWT token would successfully bypass route decorators, execute `list_stock_requests()`, acquire database connections, and only be rejected downstream inside the service function.

2. **Single Detail Endpoint (`GET /api/stock-requests/<int:stock_request_id>`):**
   ```python
   # BEFORE (Lines 43-44)
   @stock_requests_bp.route("/<int:stock_request_id>", methods=["GET"])
   @jwt_required()
   def get_single_stock_request(stock_request_id):
   ```
   Lacked `@role_required("Owner", "Manager", "Supplier")`. Similarly allowed unauthorized roles to bypass route boundary security.

3. **Creation and Response Endpoints (`POST /` and `PATCH/POST /<id>/respond`):**
   - `create_new_stock_request` had `@role_required("Owner", "Manager")` (correct).
   - `respond_stock_request` had `@role_required("Supplier", "Owner", "Manager")` (correct).

Hence, both read endpoints (`GET /` and `GET /<id>`) were missing route-level RBAC decorators.

---

## 3. Stock Request Routes Inspected

All endpoints declared in `backend/app/routes/team2/stock_requests.py` were inspected:

| Endpoint Path | HTTP Methods | Function Name | Pre-Fix Decorators | Post-Fix Decorators |
| :--- | :--- | :--- | :--- | :--- |
| `/api/stock-requests/` | GET | `list_stock_requests` | `@jwt_required()` | `@role_required("Owner", "Manager", "Supplier")` |
| `/api/stock-requests/<int:stock_request_id>` | GET | `get_single_stock_request` | `@jwt_required()` | `@role_required("Owner", "Manager", "Supplier")` |
| `/api/stock-requests/` | POST | `create_new_stock_request` | `@role_required("Owner", "Manager")` | `@role_required("Owner", "Manager")` (Preserved) |
| `/api/stock-requests/<int:stock_request_id>/respond` | PATCH, POST | `respond_stock_request` | `@role_required("Supplier", "Owner", "Manager")` | `@role_required("Supplier", "Owner", "Manager")` (Preserved) |

---

## 4. Authorization Matrix by Role and Operation

Based on the application architecture, business requirements (`frontend/js/app.js` navigation permissions: `roles: ['Owner', 'Manager', 'Supplier']`), and existing service logic, the authoritative authorization matrix is:

| Operation | HTTP Endpoint | Owner | Manager | Supplier | Employee | Unauthenticated |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **List Stock Requests** | `GET /api/stock-requests/` | **ALLOW** (All org requests) | **ALLOW** (All org requests) | **ALLOW** (Strictly scoped to own company) | **DENY (403)** | **DENY (401)** |
| **View Request Details** | `GET /api/stock-requests/<id>` | **ALLOW** (Any request) | **ALLOW** (Any request) | **ALLOW** (Assigned company request only) | **DENY (403)** | **DENY (401)** |
| **Create Stock Request** | `POST /api/stock-requests/` | **ALLOW** | **ALLOW** | **DENY (403)** | **DENY (403)** | **DENY (401)** |
| **Respond to Request** | `PATCH /api/stock-requests/<id>/respond` | **ALLOW** (Admin override) | **ALLOW** (Admin override) | **ALLOW** (Assigned company request only) | **DENY (403)** | **DENY (401)** |

### Supplier Isolation Guarantees:
- **Zero Cross-Supplier Visibility:** When `role == "Supplier"`, the server resolves `auth_supplier_id` directly from `public."Suppliers"` using the JWT identity.
- **Tamper-Proof Query Parameters:** If a supplier sends `?supplier_id=<other_id>`, the backend ignores or overwrites it with `filter_supplier_id = auth_supplier_id`.
- **Detail Isolation:** Accessing `GET /api/stock-requests/<id>` where the stock request's `supplier_id != auth_supplier_id` returns HTTP 403 Forbidden (`"Access denied. You can only view stock requests assigned to your company."`).
- **Response Isolation:** Attempting to respond to another supplier's request returns HTTP 403 Forbidden.

---

## 5. Files Changed and Reason for Each Change

| File Path | Nature of Change | Rationale |
| :--- | :--- | :--- |
| `backend/app/routes/team2/stock_requests.py` | Modified | Applied `@role_required("Owner", "Manager", "Supplier")` to `list_stock_requests` and `get_single_stock_request`. Added bare route path aliases (`@stock_requests_bp.route("", ...)`), cleaned unused `jwt_required` import. |
| `tests/team2/test_stock_request_authorization.py` | Created | Authored a comprehensive 24-test non-destructive automated test suite covering authentication, RBAC, supplier isolation, query parameter manipulation, service-level defense-in-depth, and payload contracts. |

---

## 6. Route-Level Authorization Changes

In `backend/app/routes/team2/stock_requests.py`:
- `list_stock_requests`:
  ```python
  @stock_requests_bp.route("/", methods=["GET"])
  @stock_requests_bp.route("", methods=["GET"])
  @role_required("Owner", "Manager", "Supplier")
  def list_stock_requests():
  ```
- `get_single_stock_request`:
  ```python
  @stock_requests_bp.route("/<int:stock_request_id>", methods=["GET"])
  @role_required("Owner", "Manager", "Supplier")
  def get_single_stock_request(stock_request_id):
  ```
- `create_new_stock_request`:
  ```python
  @stock_requests_bp.route("/", methods=["POST"])
  @stock_requests_bp.route("", methods=["POST"])
  @role_required("Owner", "Manager")
  def create_new_stock_request():
  ```

Because `@role_required` in `backend/app/middleware/team1_auth.py` wraps `@jwt_required()` and verifies the active user status in `public."Users"`, unauthorized requests are halted immediately at the HTTP boundary before database connection initialization or service invocation.

---

## 7. Service-Level Checks Preserved

All downstream defense-in-depth authorization checks in `backend/app/services/team2/stock_request_service.py` remain intact and functional:

1. **`get_stock_requests()`**:
   ```python
   if role not in ("Owner", "Manager", "Supplier"):
       return None, "Access denied. Only Owners, Managers, and Suppliers can view stock requests."
   ```
2. **`get_stock_request_by_id()`**:
   ```python
   if role not in ("Owner", "Manager", "Supplier"):
       return None, "Access denied. Only Owners, Managers, and Suppliers can view stock requests."
   ...
   if role == "Supplier":
       auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
       if not auth_supplier_id or auth_supplier_id != req_supplier_id:
           return None, "Access denied. You can only view stock requests assigned to your company."
   ```
3. **`respond_to_stock_request()`**:
   ```python
   if role not in ("Supplier", "Owner", "Manager"):
       return None, "Access denied. Only the assigned Supplier or Managers can respond to stock requests."
   ...
   if role == "Supplier":
       auth_supplier_id = resolve_supplier_id_for_user(cursor, user_id)
       if not auth_supplier_id or auth_supplier_id != req_supplier_id:
           return None, "Access denied. You can only respond to stock requests assigned to your company."
   ```

---

## 8. Tests Executed and Actual Results

The dedicated test suite `tests/team2/test_stock_request_authorization.py` was executed using pytest against the active application instance.

### Execution Output:
```
platform win32 -- Python 3.14.4, pytest-8.4.0, pluggy-1.6.0
collected 24 items

tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_01_unauthenticated_list_requests_rejected PASSED [  4%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_02_unauthenticated_single_request_rejected PASSED [  8%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_03_unauthenticated_create_request_rejected PASSED [ 12%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_04_unauthenticated_respond_request_rejected PASSED [ 16%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_05_invalid_token_rejected PASSED [ 20%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_06_employee_cannot_list_stock_requests_route_rbac PASSED [ 25%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_07_employee_cannot_access_single_stock_request_route_rbac PASSED [ 29%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_08_employee_cannot_create_stock_request PASSED [ 33%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_09_employee_cannot_respond_to_stock_request PASSED [ 37%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_10_owner_can_list_stock_requests PASSED [ 41%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_11_manager_can_list_stock_requests PASSED [ 45%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_12_owner_can_view_single_stock_request PASSED [ 50%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_13_manager_can_view_single_stock_request PASSED [ 54%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_14_bare_url_alias_works_for_authorized_users PASSED [ 58%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_15_supplier_can_list_own_stock_requests PASSED [ 62%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_16_supplier_cannot_bypass_isolation_via_query_param PASSED [ 66%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_17_supplier_can_view_own_stock_request_detail PASSED [ 70%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_18_supplier_cannot_view_another_suppliers_stock_request PASSED [ 75%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_19_supplier_cannot_create_stock_request PASSED [ 79%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_20_supplier_cannot_respond_to_foreign_stock_request PASSED [ 83%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_21_service_level_employee_rejection_list PASSED [ 87%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_22_service_level_employee_rejection_detail PASSED [ 91%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_23_service_level_supplier_isolation_detail PASSED [ 95%]
tests/team2/test_stock_request_authorization.py::StockRequestRouteAuthorizationTestCase::test_24_service_level_supplier_isolation_respond PASSED [100%]

============================= 24 passed in 43.57s =============================
```

**Result:** 24 passed, 0 failed.

---

## 9. Regression Results

To verify that completed Improvement 1 and existing system monitoring remain 100% functional, the regression suite covering `tests/team1/test_employee_transaction_isolation.py` and `tests/team3/test_status.py` was executed.

### Regression Output:
```
collected 20 items

tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_01_employee_query_without_user_id_only_returns_own_records PASSED [  5%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_02_employee_query_with_own_user_id_succeeds PASSED [ 10%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_03_employee_query_with_other_user_id_is_forbidden PASSED [ 15%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_04_employee_query_with_additional_filters_cannot_bypass_scoping PASSED [ 20%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_05_response_contract_and_counts_match_scope PASSED [ 25%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_06_owner_and_manager_retain_unrestricted_visibility PASSED [ 30%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_07_supplier_access_is_forbidden PASSED [ 35%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_08_unauthenticated_requests_are_rejected PASSED [ 40%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_09_single_transaction_detail_authorization PASSED [ 45%]
tests/team1/test_employee_transaction_isolation.py::EmployeeTransactionDataIsolationTestCase::test_10_service_level_isolation_direct_call PASSED [ 50%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_01_public_liveness_endpoint PASSED [ 55%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_02_detailed_health_owner_access PASSED [ 60%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_03_detailed_health_manager_access PASSED [ 65%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_04_detailed_health_access_denied_for_unauthorized_roles PASSED [ 70%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_05_detailed_health_access_denied_for_anonymous_requests PASSED [ 75%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_06_normal_latency_health_policy PASSED [ 80%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_07_elevated_latency_performance_warning PASSED [ 85%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_08_database_failure_returns_503_degraded PASSED [ 90%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_09_inventory_not_ready_reports_degraded PASSED [ 95%]
tests/team3/test_status.py::Team3SystemStatusAndHealthTestCase::test_10_existing_reports_status_endpoint_compatibility PASSED [100%]

======================== 20 passed in 61.62s (0:01:01) ========================
```

**Result:** 20 passed, 0 failed. No regressions detected.

---

## 10. Tests Not Run and Remaining Risks

- **End-to-End Browser Automation:** Full UI end-to-end browser clicking on the Stock Request page was intentionally not run during this step, adhering to constraint 9 ("Do not deploy or perform comprehensive end-to-end testing").
- **Live Stock Request Mutating Operations:** Tests did not execute state-altering `INSERT` or status-mutating `UPDATE` statements against production Supabase database tables to adhere to safety constraints.
- **Remaining Risks:** Low. The changes consist of applying standard, shared RBAC decorators (`@role_required`) in complete alignment with the rest of the application.

---

## 11. Confirmation of Database & Schema Safety

- **No Schema Changes:** Zero schema modifications, DDL statements, migrations, or column edits were performed.
- **No Production Data Altered:** No live Supabase records were created, modified, or deleted during implementation or testing.

---

## 12. Confirmation Regarding Unrelated Improvements

- **No Unrelated Improvements Implemented:** The following tasks remain deliberately untouched as required by the roadmap:
  - Improvement 3: Supplier Payments Placeholder Removal / Fix
  - Improvement 4: Notification Deep-Linking & Click-Through Handling
  - Improvement 5: Audit Logs Modernization & UI Component Alignment
  - Improvement 6: Header Navigation Controls & Theme Toggle
- **Improvement 1 Preserved:** Employee Transaction Data Isolation code and test assets remain untouched and passing.

---

## 13. Stopping Condition

In strict accordance with the instructions, execution is stopped following the completion of Improvement 2. No work on Improvement 3 will proceed until the user reviews this report and grants explicit approval.
