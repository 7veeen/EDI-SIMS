// SIMS Central Data Store with Full Initial Dataset from Database Snapshots
const Store = {
  // 1. Current Session
  currentUser: {
    user_id: 1,
    username: "Mrugadni",
    email: "mrugadni@inventory.com",
    role: "Owner",
    avatar: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80"
  },

  // 2. Categories
  categories: [
    { category_id: 1, category_name: "Electronics", description: "Peripherals, accessories, keyboards and mice", item_count: 2 },
    { category_id: 2, category_name: "Stationery", description: "Office writing material and notebooks", item_count: 1 },
    { category_id: 3, category_name: "Furniture", description: "Ergonomic chairs and desks", item_count: 1 },
    { category_id: 4, category_name: "Cables & Adapters", description: "High speed data and power connectivity", item_count: 1 }
  ],

  // 3. Products
  products: [
    { product_id: 1, product_name: "Dell Wireless Mouse", category_id: 1, category_name: "Electronics", sku: "ELEC-MOU-001", selling_price: 799.00, reorder_level: 10, status: "Active", stock: 70 },
    { product_id: 2, product_name: "HP Keyboard Pro", category_id: 1, category_name: "Electronics", sku: "ELEC-KEY-001", selling_price: 999.00, reorder_level: 10, status: "Active", stock: 48 },
    { product_id: 3, product_name: "A4 Executive Notebook", category_id: 2, category_name: "Stationery", sku: "STAT-NOT-001", selling_price: 80.00, reorder_level: 20, status: "Active", stock: 40 },
    { product_id: 4, product_name: "Ergonomic Office Chair", category_id: 3, category_name: "Furniture", sku: "FURN-CHA-001", selling_price: 4500.00, reorder_level: 10, status: "Active", stock: 8 },
    { product_id: 5, product_name: "USB Type-C Fast Cable", category_id: 4, category_name: "Cables & Adapters", sku: "COMP-CAB-001", selling_price: 500.00, reorder_level: 10, status: "Active", stock: 12 }
  ],

  // 4. Inventory
  inventory: [
    { inventory_id: 1, product_id: 1, product_name: "Dell Wireless Mouse", sku: "ELEC-MOU-001", quantity_available: 70, reorder_level: 10, last_updated: "2026-09-20 14:25" },
    { inventory_id: 2, product_id: 2, product_name: "HP Keyboard Pro", sku: "ELEC-KEY-001", quantity_available: 48, reorder_level: 10, last_updated: "2026-09-20 15:10" },
    { inventory_id: 3, product_id: 3, product_name: "A4 Executive Notebook", sku: "STAT-NOT-001", quantity_available: 40, reorder_level: 20, last_updated: "2026-09-21 09:30" },
    { inventory_id: 4, product_id: 4, product_name: "Ergonomic Office Chair", sku: "FURN-CHA-001", quantity_available: 8, reorder_level: 10, last_updated: "2026-09-22 11:45" },
    { inventory_id: 5, product_id: 5, product_name: "USB Type-C Fast Cable", sku: "COMP-CAB-001", quantity_available: 12, reorder_level: 10, last_updated: "2026-09-22 12:15" }
  ],

  // 5. Suppliers
  suppliers: [
    { supplier_id: 1, supplier_name: "TechWorld Suppliers", contact_person: "Rahul Sharma", phone: "+91 98765 43210", email: "rahul@techworld.com", status: "Active", total_orders: 1 },
    { supplier_id: 2, supplier_name: "OfficeMart Pvt Ltd", contact_person: "Priya Patil", phone: "+91 98765 43211", email: "priya@officemart.com", status: "Active", total_orders: 1 },
    { supplier_id: 3, supplier_name: "Global Electronics", contact_person: "Amit Joshi", phone: "+91 98765 43212", email: "amit@globalelectronics.com", status: "Active", total_orders: 1 }
  ],

  // 6. Purchase Orders
  purchaseOrders: [
    { purchase_order_id: 1, po_number: "PO-2026-001", supplier_id: 1, supplier_name: "TechWorld Suppliers", ordered_by: "manager1", order_date: "2026-09-03", expected_delivery: "2026-09-10", total_amount: 32500.00, status: "Received" },
    { purchase_order_id: 2, po_number: "PO-2026-002", supplier_id: 2, supplier_name: "OfficeMart Pvt Ltd", ordered_by: "manager1", order_date: "2026-09-03", expected_delivery: "2026-09-13", total_amount: 25500.00, status: "Received" },
    { purchase_order_id: 3, po_number: "PO-2026-003", supplier_id: 3, supplier_name: "Global Electronics", ordered_by: "owner", order_date: "2026-09-03", expected_delivery: "2026-09-08", total_amount: 15000.00, status: "Completed" }
  ],

  // 7. Supplier Quotations
  quotations: [
    { quotation_id: 1, supplier_id: 1, supplier_name: "TechWorld Suppliers", product_id: 1, product_name: "Dell Wireless Mouse", quoted_price: 650.00, quantity: 50, valid_until: "2026-10-15", status: "Pending" },
    { quotation_id: 2, supplier_id: 2, supplier_name: "OfficeMart Pvt Ltd", product_id: 1, product_name: "Dell Wireless Mouse", quoted_price: 620.00, quantity: 50, valid_until: "2026-10-20", status: "Pending" },
    { quotation_id: 3, supplier_id: 3, supplier_name: "Global Electronics", product_id: 2, product_name: "HP Keyboard Pro", quoted_price: 850.00, quantity: 30, valid_until: "2026-10-25", status: "Approved" }
  ],

  // 8. Stock Transactions
  transactions: [
    { transaction_id: 1, product_name: "Dell Wireless Mouse", sku: "ELEC-MOU-001", user: "employee1", transaction_type: "STOCK_IN", quantity: 50, po_ref: "PO-2026-001", date: "2026-09-03 09:25" },
    { transaction_id: 2, product_name: "HP Keyboard Pro", sku: "ELEC-KEY-001", user: "employee1", transaction_type: "STOCK_IN", quantity: 30, po_ref: "PO-2026-002", date: "2026-09-03 10:15" },
    { transaction_id: 3, product_name: "Dell Wireless Mouse", sku: "ELEC-MOU-001", user: "employee1", transaction_type: "STOCK_OUT", quantity: 5, po_ref: "Manual Dispatch", date: "2026-09-12 14:00" },
    { transaction_id: 4, product_name: "A4 Executive Notebook", sku: "STAT-NOT-001", user: "employee1", transaction_type: "STOCK_OUT", quantity: 10, po_ref: "Internal Request", date: "2026-09-18 16:30" }
  ],

  // 9. Reports
  reports: [
    { report_id: 1, report_name: "September Inventory Snapshot", report_type: "Inventory", generated_by: "owner", generated_on: "2026-09-19 11:30" },
    { report_id: 2, report_name: "Weekly Stock Balance", report_type: "Inventory", generated_by: "manager1", generated_on: "2026-09-14 18:50" },
    { report_id: 3, report_name: "Low-Stock Reorder Assessment", report_type: "Inventory", generated_by: "employee1", generated_on: "2026-09-12 10:15" }
  ],

  // 10. Notifications
  notifications: [
    { notification_id: 1, title: "Low Stock Alert", message: "Product 'Ergonomic Office Chair' is down to 8 units (Threshold: 10).", type: "WARNING", is_read: false, time: "10 mins ago" },
    { notification_id: 2, title: "Purchase Order Completed", message: "PO-2026-003 from Global Electronics has been completed.", type: "SUCCESS", is_read: false, time: "1 hour ago" },
    { notification_id: 3, title: "New Quotation Submitted", message: "TechWorld Suppliers posted a quote for Dell Wireless Mouse.", type: "INFO", is_read: true, time: "3 hours ago" },
    { notification_id: 4, title: "Database Backup Finished", message: "Automated snapshot backup completed successfully (14.68 KB).", type: "SUCCESS", is_read: true, time: "1 day ago" }
  ],

  // 11. Audit Logs
  auditLogs: [
    { log_id: 104, user: "owner", action: "UPDATE", table: "Users", record_id: "3", time: "2026-09-22 10:15", ip: "192.168.1.15" },
    { log_id: 103, user: "manager1", action: "INSERT", table: "Reports", record_id: "3", time: "2026-09-21 16:40", ip: "192.168.1.22" },
    { log_id: 102, user: "employee1", action: "INSERT", table: "StockTransactions", record_id: "4", time: "2026-09-18 16:30", ip: "192.168.1.45" },
    { log_id: 101, user: "owner", action: "INSERT", table: "Categories", record_id: "4", time: "2026-09-12 11:20", ip: "192.168.1.15" }
  ],

  // 12. Backups
  backups: [
    { backup_id: 1, backup_name: "inventory_backup_20260919_115747.json", backup_type: "Full", backup_size: "14.68 KB", created_by: "owner", status: "Success", date: "2026-09-19 11:57" },
    { backup_id: 2, backup_name: "inventory_backup_20260919_113128.json", backup_type: "Full", backup_size: "14.41 KB", created_by: "owner", status: "Success", date: "2026-09-19 11:31" },
    { backup_id: 3, backup_name: "inventory_backup_20260918_120810.json", backup_type: "Full", backup_size: "13.60 KB", created_by: "manager1", status: "Success", date: "2026-09-18 12:08" }
  ],

  // 13. System Status
  systemStatus: [
    { module_name: "Inventory", status: "READY", progress: 100, message: "Inventory cache synchronized and ready for reports.", updated_at: "2026-09-22 12:00" },
    { module_name: "Authentication", status: "READY", progress: 100, message: "JWT authentication service operational.", updated_at: "2026-09-22 12:00" },
    { module_name: "Procurement Engine", status: "READY", progress: 100, message: "Purchase order and quotation pipeline active.", updated_at: "2026-09-22 12:00" },
    { module_name: "Automated Backups", status: "READY", progress: 100, message: "Local snapshot engine standing by.", updated_at: "2026-09-22 12:00" }
  ],

  // 14. Users & Roles
  users: [
    { user_id: 1, username: "owner", email: "owner@inventory.com", role: "Owner", status: "Active" },
    { user_id: 2, username: "manager1", email: "manager@inventory.com", role: "Manager", status: "Active" },
    { user_id: 3, username: "employee1", email: "employee@inventory.com", role: "Employee", status: "Active" },
    { user_id: 4, username: "supplier1", email: "supplier@inventory.com", role: "Supplier", status: "Active" }
  ],

  // 15. Settings
  settings: {
    apiUrl: "http://127.0.0.1:5000",
    lowStockThreshold: 10,
    currencySymbol: "USD",
    autoRefreshInterval: 30,
    theme: "light"
  }
};

