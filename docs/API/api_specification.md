# Smart Inventory Management System (SIMS) - REST API Specification

This document provides the complete API contracts, request payloads, response bodies, and HTTP status codes for all modules across Team 1, Team 2, and Team 3.

---

## 🔒 Authentication & Headers

Protected endpoints require a JSON Web Token (JWT) in the HTTP Authorization header:
```http
Authorization: Bearer <your_jwt_access_token>
Content-Type: application/json
```

### Standard HTTP Status Codes
* `200 OK`: Request succeeded.
* `201 Created`: Resource successfully created.
* `400 Bad Request`: Validation failure or missing required fields.
* `401 Unauthorized`: Missing or invalid JWT token.
* `403 Forbidden`: Account is inactive or user role lacks sufficient permissions.
* `404 Not Found`: Target entity does not exist.
* `423 Locked`: Dependent system module is busy (e.g., inventory loading).
* `500 Internal Server Error`: Unhandled database or server exception.

---

## 👥 Team 1: Authentication, Users & Master Catalog

### 1. User Login
* **Method**: `POST`
* **Path**: `/api/auth/login`
* **Access**: Public
* **Request Body**:
```json
{
  "username": "manager1",
  "password": "Password123"
}
```
* **Success Response (`200 OK`)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "user": {
    "user_id": 1,
    "username": "manager1",
    "role": "Manager"
  }
}
```
* **Error Responses**:
  * `400 Bad Request`: `{"error": "Username and password are required"}`
  * `401 Unauthorized`: `{"error": "Invalid credentials"}`
  * `403 Forbidden`: `{"error": "User account is inactive"}`

---

### 2. Change Password
* **Method**: `PUT`
* **Path**: `/api/auth/change-password`
* **Access**: Authenticated (Any Role)
* **Request Body**:
```json
{
  "current_password": "OldPassword123",
  "new_password": "NewSecretPassword456"
}
```
* **Success Response (`200 OK`)**:
```json
{
  "message": "Password changed successfully"
}
```
* **Error Responses**:
  * `400 Bad Request`: `{"error": "New password must be at least 8 characters long"}`
  * `400 Bad Request`: `{"error": "Current password does not match"}`

---

### 3. List Users
* **Method**: `GET`
* **Path**: `/api/users/`
* **Access**: `Owner`, `Manager`
* **Success Response (`200 OK`)**:
```json
[
  {
    "user_id": 1,
    "username": "owner",
    "email": "owner@inventory.com",
    "role_id": 1,
    "role_name": "Owner",
    "status": "Active"
  }
]
```

---

### 4. Create User
* **Method**: `POST`
* **Path**: `/api/users/`
* **Access**: `Owner`
* **Request Body**:
```json
{
  "username": "new_employee",
  "email": "employee@inventory.com",
  "password": "InitialPassword123",
  "role_id": 3
}
```
* **Success Response (`201 Created`)**:
```json
{
  "message": "User created successfully",
  "user_id": 5
}
```

---

### 5. Update User Status
* **Method**: `PUT`
* **Path**: `/api/users/<user_id>/status`
* **Access**: `Owner`
* **Request Body**:
```json
{
  "status": "Inactive"
}
```
* **Success Response (`200 OK`)**:
```json
{
  "message": "User status updated to Inactive"
}
```

---

### 6. List Categories
* **Method**: `GET`
* **Path**: `/api/categories/`
* **Access**: Authenticated (All Roles)
* **Success Response (`200 OK`)**:
```json
[
  {
    "category_id": 1,
    "category_name": "Electronics",
    "description": "Electronic components and accessories"
  }
]
```

---

### 7. Create Category
* **Method**: `POST`
* **Path**: `/api/categories/`
* **Access**: `Owner`, `Manager`
* **Request Body**:
```json
{
  "category_name": "Office Supplies",
  "description": "Stationery and general supplies"
}
```
* **Success Response (`201 Created`)**:
```json
{
  "message": "Category created successfully",
  "category_id": 5
}
```

---

## 📦 Team 2: Suppliers, Purchase Orders & Transactions

### 8. List Suppliers
* **Method**: `GET`
* **Path**: `/api/suppliers/`
* **Access**: `Owner`, `Manager`
* **Success Response (`200 OK`)**:
```json
[
  {
    "supplier_id": 1,
    "supplier_name": "Apex Distribution",
    "contact_person": "Robert Vance",
    "phone": "+1-555-0199",
    "email": "contact@apex.com",
    "status": "Active"
  }
]
```

---

### 9. Create Purchase Order
* **Method**: `POST`
* **Path**: `/api/purchase-orders/`
* **Access**: `Manager`
* **Request Body**:
```json
{
  "supplier_id": 1,
  "expected_delivery": "2026-10-15",
  "items": [
    {
      "product_id": 2,
      "quantity": 50,
      "unit_price": 14.50
    }
  ]
}
```
* **Success Response (`201 Created`)**:
```json
{
  "message": "Purchase order created successfully",
  "purchase_order_id": 104,
  "total_amount": 725.00,
  "status": "Created"
}
```

---

### 10. Record Stock Transaction
* **Method**: `POST`
* **Path**: `/api/transactions/`
* **Access**: `Employee`, `Manager`
* **Request Body**:
```json
{
  "product_id": 2,
  "transaction_type": "STOCK_IN",
  "quantity": 50,
  "purchase_order_id": 104
}
```
* **Success Response (`201 Created`)**:
```json
{
  "message": "Stock transaction recorded successfully",
  "transaction_id": 201,
  "new_quantity_available": 115
}
```

---

## 📊 Team 3: Dashboards, Reports, Auditing & Backups

### 11. Employee Dashboard KPIs
* **Method**: `GET`
* **Path**: `/api/dashboard/employee`
* **Access**: `Employee`
* **Success Response (`200 OK`)**:
```json
{
  "total_products": 28,
  "total_stock": 1420,
  "stock_in": 350,
  "stock_out": 120,
  "low_stock_products": [
    {
      "product_id": 4,
      "product_name": "Wireless Mouse M30",
      "quantity_available": 6
    }
  ]
}
```

---

### 12. Supplier Dashboard KPIs
* **Method**: `GET`
* **Path**: `/api/dashboard/supplier`
* **Access**: `Supplier`
* **Success Response (`200 OK`)**:
```json
{
  "total_purchase_orders": 12,
  "received_orders": 3,
  "completed_orders": 8,
  "total_purchase_amount": 18450.00,
  "total_quotations": 15,
  "pending_quotations": 4,
  "approved_quotations": 9
}
```

---

### 13. Check Inventory Status for Reporting
* **Method**: `GET`
* **Path**: `/api/reports/status`
* **Access**: Authenticated
* **Success Response (`200 OK`)**:
```json
{
  "status": "READY",
  "progress": 100,
  "message": "Inventory synchronized and ready for reporting",
  "updated_at": "2026-09-20T10:00:00"
}
```

---

### 14. Generate Inventory Report
* **Method**: `POST`
* **Path**: `/api/reports/generate`
* **Access**: Authenticated
* **Request Body**:
```json
{
  "report_name": "Q3 Inventory Balance",
  "report_type": "Inventory",
  "generated_by": 1
}
```
* **Success Response (`201 Created`)**:
```json
{
  "message": "Report generated successfully",
  "report": {
    "report_id": 14,
    "report_name": "Q3 Inventory Balance",
    "report_type": "Inventory",
    "generated_by": 1,
    "generated_on": "2026-09-21T18:00:00"
  },
  "data": [
    {
      "product_id": 1,
      "product_name": "USB Cable Type-C",
      "sku": "SKU-USB-01",
      "quantity_available": 45,
      "reorder_level": 20,
      "status": "Active",
      "stock_status": "IN STOCK",
      "last_updated": "2026-09-18T14:30:00"
    }
  ]
}
```
* **Lock Response (`423 Locked`)**:
```json
{
  "error": "Report generation locked",
  "status": "LOADING",
  "progress": 45,
  "message": "Inventory refresh in progress"
}
```

---

### 15. List Notifications & Mark as Read
* **List Notifications**: `GET /api/notifications/`
* **Mark as Read**: `PATCH /api/notifications/<notification_id>/read`
* **Success Response (`200 OK`)**:
```json
{
  "notification_id": 3,
  "is_read": true
}
```

---

### 16. Query Audit Logs
* **Method**: `GET`
* **Path**: `/api/audit-logs/`
* **Access**: `Owner`
* **Success Response (`200 OK`)**:
```json
[
  {
    "log_id": 42,
    "user_id": 1,
    "action": "UPDATE",
    "table_name": "Users",
    "record_id": 3,
    "action_time": "2026-09-19T11:45:00",
    "ip_address": "192.168.1.10"
  }
]
```

---

### 17. Create Full Database Backup
* **Method**: `POST`
* **Path**: `/api/backups/`
* **Access**: `Owner`
* **Request Body**:
```json
{
  "created_by": 1
}
```
* **Success Response (`201 Created`)**:
```json
{
  "message": "Backup created successfully",
  "backup_id": 9,
  "backup_name": "inventory_backup_20260921_180000.json",
  "backup_type": "Full",
  "backup_size": "14.85 KB",
  "created_by": 1,
  "status": "Success",
  "file_path": "F:\\Smart Inventory Management System\\backend\\backups\\inventory_backup_20260921_180000.json"
}
```

---

## 📡 Team 3: System Status & Health Monitoring

### 18. Public Backend Liveness Ping
* **Method**: `GET`
* **Path**: `/api/status/` (or `/api/status`)
* **Access**: Public (No Authentication)
* **Description**: Returns minimal backend liveness status. Does not expose database internals, credentials, or configuration.
* **Success Response (`200 OK`)**:
```json
{
  "status": "UP"
}
```

---

### 19. Detailed System Health & Subsystem Telemetry
* **Method**: `GET`
* **Path**: `/api/status/health`
* **Access**: `Owner`, `Manager` (Protected via `@role_required("Owner", "Manager")`)
* **Description**: Gathers full telemetry including backend process uptime, PostgreSQL connectivity and query round-trip latency (ms), and module readiness states from the `SystemStatus` table.
* **Latency Benchmark & Performance Threshold Policy**:
  * **Warning Threshold**: `500.0 ms` (`LATENCY_WARNING_THRESHOLD_MS`).
  * **Database Connectivity Status** (`database.status`): Evaluated independently from performance (`CONNECTED` vs `DISCONNECTED`).
  * **Database Performance Status** (`database.performance`): Evaluated against the 500 ms threshold (`NORMAL` when `<= 500 ms`, `ELEVATED` when `> 500 ms`).
  * **Performance Warning Flag** (`database.performance_warning` / `performance_warning`): Boolean flag (`true` when latency exceeds 500 ms).
* **Overall Health Determination Policy**:
  * **`HEALTHY`**: Backend is `UP`, Database is `CONNECTED`, monitored `Inventory` module is `READY`, and Database response time is `NORMAL` (`<= 500 ms`).
  * **`DEGRADED`**: Evaluated if Database is `DISCONNECTED`, `Inventory` module is not `READY`, or Database query latency is `ELEVATED` (`> 500 ms`).
* **Success Response (`200 OK`) — Normal Latency** *(Sample illustrative response)*:
```json
{
  "overall_status": "HEALTHY",
  "backend": {
    "status": "UP"
  },
  "database": {
    "status": "CONNECTED",
    "latency_ms": 137.33,
    "performance": "NORMAL",
    "performance_warning": false,
    "latency_threshold_ms": 500.0
  },
  "performance_warning": false,
  "modules": [
    {
      "name": "Inventory",
      "status": "READY",
      "progress": 100,
      "message": "Inventory is ready",
      "updated_at": "2026-09-13T12:24:54.182475"
    }
  ],
  "uptime_seconds": 3600,
  "checked_at": "2026-09-26T12:00:00.000000+00:00"
}
```
* **Success Response (`200 OK`) — Elevated Latency Performance Advisory** *(Sample illustrative response)*:
```json
{
  "overall_status": "DEGRADED",
  "backend": {
    "status": "UP"
  },
  "database": {
    "status": "CONNECTED",
    "latency_ms": 650.0,
    "performance": "ELEVATED",
    "performance_warning": true,
    "latency_threshold_ms": 500.0
  },
  "performance_warning": true,
  "modules": [
    {
      "name": "Inventory",
      "status": "READY",
      "progress": 100,
      "message": "Inventory is ready",
      "updated_at": "2026-09-13T12:24:54.182475"
    }
  ],
  "uptime_seconds": 3600,
  "checked_at": "2026-09-26T12:00:00.000000+00:00"
}
```
* **Degraded / Service Unavailable Response (`503 Service Unavailable`)**:
  Returned when the PostgreSQL database check fails or connection cannot be established.
```json
{
  "overall_status": "DEGRADED",
  "backend": {
    "status": "UP"
  },
  "database": {
    "status": "DISCONNECTED",
    "latency_ms": null,
    "performance": "UNAVAILABLE",
    "performance_warning": false,
    "latency_threshold_ms": 500.0
  },
  "performance_warning": false,
  "modules": [],
  "uptime_seconds": 3600,
  "checked_at": "2026-09-26T12:00:00.000000+00:00"
}
```
* **Error Responses**:
  * `401 Unauthorized`: Missing or malformed JWT access token.
  * `403 Forbidden`: User account is inactive or role is not Owner/Manager (e.g. Employee or Supplier).


