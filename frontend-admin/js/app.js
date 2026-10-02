// SIMS Admin Application Controller & Router
const App = {
  currentRoute: "dashboard",

  init() {
    // Listen for hash change
    window.addEventListener("hashchange", () => this.handleRouting());

    // Keyboard shortcut for search (Cmd+F / Ctrl+K)
    window.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "f" || e.key === "k")) {
        e.preventDefault();
        const searchBox = document.getElementById("global-search");
        if (searchBox) searchBox.focus();
      }
      if (e.key === "Escape") {
        this.closeAllModals();
      }
    });

    // Initial route handling
    this.handleRouting();
    this.updateNotificationBadge();
  },

  navigate(route) {
    window.location.hash = `#${route}`;
  },

  handleRouting() {
    const hash = window.location.hash.replace("#", "") || "dashboard";
    this.currentRoute = hash;

    // Update active class in sidebar
    document.querySelectorAll(".nav-item").forEach(el => {
      if (el.getAttribute("data-route") === hash) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    });

    // Render corresponding view
    const viewContainer = document.getElementById("view-container");
    if (!viewContainer) return;

    switch (hash) {
      case "dashboard":
        viewContainer.innerHTML = DashboardView.render();
        break;
      case "inventory":
        viewContainer.innerHTML = InventoryView.renderInventory();
        break;
      case "products":
        viewContainer.innerHTML = InventoryView.renderProducts();
        break;
      case "categories":
        viewContainer.innerHTML = InventoryView.renderCategories();
        break;
      case "suppliers":
        viewContainer.innerHTML = ProcurementView.renderSuppliers();
        break;
      case "purchase-orders":
        viewContainer.innerHTML = ProcurementView.renderPurchaseOrders();
        break;
      case "quotations":
        viewContainer.innerHTML = ProcurementView.renderQuotations();
        break;
      case "stock-transactions":
        viewContainer.innerHTML = OperationsView.renderStockTransactions();
        break;
      case "reports":
        viewContainer.innerHTML = InsightsView.renderReports();
        break;
      case "notifications":
        viewContainer.innerHTML = InsightsView.renderNotifications();
        break;
      case "audit-logs":
        viewContainer.innerHTML = SystemView.renderAuditLogs();
        break;
      case "backups":
        viewContainer.innerHTML = SystemView.renderBackups();
        break;
      case "system-status":
        viewContainer.innerHTML = SystemView.renderSystemStatus();
        break;
      case "users-roles":
        viewContainer.innerHTML = SystemView.renderUsers();
        break;
      case "settings":
        viewContainer.innerHTML = SystemView.renderSettings();
        break;
      default:
        viewContainer.innerHTML = DashboardView.render();
        break;
    }

    // Scroll to top of content
    const mainContent = document.querySelector(".main-content");
    if (mainContent) mainContent.scrollTop = 0;
  },

  // Table real-time text filter
  filterTable(input, tableId) {
    const filter = input.value.toLowerCase();
    const table = document.getElementById(tableId);
    if (!table) return;

    const rows = table.getElementsByTagName("tbody")[0].getElementsByTagName("tr");
    for (let i = 0; i < rows.length; i++) {
      const text = rows[i].textContent.toLowerCase();
      rows[i].style.display = text.includes(filter) ? "" : "none";
    }
  },

  // Global search from topbar
  handleGlobalSearch(input) {
    const query = input.value.trim().toLowerCase();
    if (!query) return;

    // Search across products first
    const matchedProduct = Store.products.find(p => p.product_name.toLowerCase().includes(query) || p.sku.toLowerCase().includes(query));
    if (matchedProduct) {
      this.navigate("products");
      setTimeout(() => {
        const tableSearch = document.querySelector(".table-search-input");
        if (tableSearch) {
          tableSearch.value = query;
          this.filterTable(tableSearch, "table-products");
        }
      }, 100);
      return;
    }

    // Otherwise suppliers
    const matchedSupplier = Store.suppliers.find(s => s.supplier_name.toLowerCase().includes(query));
    if (matchedSupplier) {
      this.navigate("suppliers");
      setTimeout(() => {
        const tableSearch = document.querySelector(".table-search-input");
        if (tableSearch) {
          tableSearch.value = query;
          this.filterTable(tableSearch, "table-suppliers");
        }
      }, 100);
    }
  },

  // Modal Management
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("active");
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove("active");
  },

  closeAllModals() {
    document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
  },

  // Notification Handling
  updateNotificationBadge() {
    const unreadCount = Store.notifications.filter(n => !n.is_read).length;
    const badge = document.getElementById("notif-badge");
    const sidebarBadge = document.getElementById("sidebar-notif-badge");
    if (badge) badge.style.display = unreadCount > 0 ? "block" : "none";
    if (sidebarBadge) sidebarBadge.textContent = unreadCount;
  },

  markAllNotificationsRead() {
    Store.notifications.forEach(n => n.is_read = true);
    this.updateNotificationBadge();
    this.handleRouting();
    this.toast("All notifications marked as read.");
  },

  toggleNotificationRead(id) {
    const notif = Store.notifications.find(n => n.notification_id === id);
    if (notif) {
      notif.is_read = !notif.is_read;
      this.updateNotificationBadge();
      this.handleRouting();
    }
  },

  // Actions & Form Handlers
  saveNewProduct(e) {
    e.preventDefault();
    const name = document.getElementById("new-prod-name").value;
    const sku = document.getElementById("new-prod-sku").value;
    const categoryId = Number(document.getElementById("new-prod-cat").value);
    const price = Number(document.getElementById("new-prod-price").value);
    const reorder = Number(document.getElementById("new-prod-reorder").value);
    const stock = Number(document.getElementById("new-prod-stock").value);

    const category = Store.categories.find(c => c.category_id === categoryId) || Store.categories[0];
    const newId = Store.products.length + 1;

    Store.products.unshift({
      product_id: newId,
      product_name: name,
      category_id: categoryId,
      category_name: category.category_name,
      sku: sku,
      selling_price: price,
      reorder_level: reorder,
      status: "Active",
      stock: stock
    });

    Store.inventory.unshift({
      inventory_id: Store.inventory.length + 1,
      product_id: newId,
      product_name: name,
      sku: sku,
      quantity_available: stock,
      reorder_level: reorder,
      last_updated: "Just now"
    });

    this.closeModal("modal-add-product");
    this.handleRouting();
    this.toast(`Product "${name}" added to catalog.`);
  },

  saveNewCategory(e) {
    e.preventDefault();
    const name = document.getElementById("new-cat-name").value;
    const desc = document.getElementById("new-cat-desc").value;

    Store.categories.push({
      category_id: Store.categories.length + 1,
      category_name: name,
      description: desc,
      item_count: 0
    });

    this.closeModal("modal-add-category");
    this.handleRouting();
    this.toast(`Category "${name}" created.`);
  },

  saveNewSupplier(e) {
    e.preventDefault();
    const name = document.getElementById("new-sup-name").value;
    const contact = document.getElementById("new-sup-contact").value;
    const phone = document.getElementById("new-sup-phone").value;
    const email = document.getElementById("new-sup-email").value;

    Store.suppliers.push({
      supplier_id: Store.suppliers.length + 1,
      supplier_name: name,
      contact_person: contact,
      phone: phone,
      email: email,
      status: "Active",
      total_orders: 0
    });

    this.closeModal("modal-add-supplier");
    this.handleRouting();
    this.toast(`Supplier "${name}" registered.`);
  },

  saveNewPO(e) {
    e.preventDefault();
    const supplierId = Number(document.getElementById("po-supplier").value);
    const amount = Number(document.getElementById("po-amount").value);
    const delivery = document.getElementById("po-delivery").value;
    const supplier = Store.suppliers.find(s => s.supplier_id === supplierId);

    Store.purchaseOrders.unshift({
      purchase_order_id: Store.purchaseOrders.length + 1,
      po_number: `PO-2026-00${Store.purchaseOrders.length + 1}`,
      supplier_id: supplierId,
      supplier_name: supplier ? supplier.supplier_name : "Supplier",
      ordered_by: "owner",
      order_date: new Date().toISOString().split("T")[0],
      expected_delivery: delivery,
      total_amount: amount,
      status: "Created"
    });

    this.closeModal("modal-create-po");
    this.handleRouting();
    this.toast("Purchase Order successfully created.");
  },

  saveTransaction(e) {
    e.preventDefault();
    const productId = Number(document.getElementById("trx-prod").value);
    const type = document.getElementById("trx-type").value;
    const qty = Number(document.getElementById("trx-qty").value);
    const ref = document.getElementById("trx-ref").value;

    const product = Store.products.find(p => p.product_id === productId);
    const inv = Store.inventory.find(i => i.product_id === productId);

    if (inv) {
      if (type === "STOCK_IN") inv.quantity_available += qty;
      if (type === "STOCK_OUT") inv.quantity_available = Math.max(0, inv.quantity_available - qty);
      inv.last_updated = "Just now";
    }

    Store.transactions.unshift({
      transaction_id: Store.transactions.length + 1,
      product_name: product ? product.product_name : "Item",
      sku: product ? product.sku : "SKU-001",
      user: "owner",
      transaction_type: type,
      quantity: qty,
      po_ref: ref || "Manual Adjustment",
      date: "Just now"
    });

    this.closeModal("modal-record-transaction");
    this.handleRouting();
    this.toast(`Stock ${type === 'STOCK_IN' ? 'Receipt' : 'Dispatch'} logged.`);
  },

  triggerReportGeneration(e) {
    e.preventDefault();
    const name = document.getElementById("report-name").value;
    const type = document.getElementById("report-type").value;

    Store.reports.unshift({
      report_id: Store.reports.length + 1,
      report_name: name,
      report_type: type,
      generated_by: "owner",
      generated_on: new Date().toISOString().replace("T", " ").substring(0, 16)
    });

    this.closeModal("modal-generate-report");
    this.handleRouting();
    this.toast(`Report "${name}" generated successfully!`);
  },

  triggerNewBackup() {
    const timestamp = new Date().toISOString().replace(/[-:T]/g, "").substring(0, 14);
    const name = `inventory_backup_${timestamp}.json`;

    Store.backups.unshift({
      backup_id: Store.backups.length + 1,
      backup_name: name,
      backup_type: "Full",
      backup_size: "15.12 KB",
      created_by: "owner",
      status: "Success",
      date: new Date().toISOString().replace("T", " ").substring(0, 16)
    });

    this.handleRouting();
    this.toast("Full database JSON backup completed!");
  },

  downloadBackup(backupName) {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(Store, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", backupName);
    dlAnchorElem.click();
    this.toast(`Downloading ${backupName}...`);
  },

  toggleUserStatus(userId) {
    const user = Store.users.find(u => u.user_id === userId);
    if (user) {
      user.status = user.status === "Active" ? "Inactive" : "Active";
      this.handleRouting();
      this.toast(`User ${user.username} status set to ${user.status}.`);
    }
  },

  saveSettings() {
    const url = document.getElementById("setting-api-url").value;
    const threshold = Number(document.getElementById("setting-threshold").value);
    Store.settings.apiUrl = url;
    Store.settings.lowStockThreshold = threshold;
    this.toast("Settings saved successfully.");
  },

  toast(msg) {
    const toastEl = document.createElement("div");
    toastEl.style.position = "fixed";
    toastEl.style.bottom = "24px";
    toastEl.style.right = "24px";
    toastEl.style.backgroundColor = "#0f172a";
    toastEl.style.color = "#ffffff";
    toastEl.style.padding = "12px 20px";
    toastEl.style.borderRadius = "8px";
    toastEl.style.fontSize = "13px";
    toastEl.style.fontWeight = "600";
    toastEl.style.boxShadow = "0 10px 25px rgba(0,0,0,0.2)";
    toastEl.style.zIndex = "9999";
    toastEl.style.display = "flex";
    toastEl.style.alignItems = "center";
    toastEl.style.gap = "8px";
    toastEl.innerHTML = `<span style="color: #10b981;">●</span> ${msg}`;
    document.body.appendChild(toastEl);
    setTimeout(() => {
      toastEl.style.opacity = "0";
      toastEl.style.transition = "opacity 0.3s ease";
      setTimeout(() => toastEl.remove(), 300);
    }, 2500);
  }
};

// Start application when DOM loads
document.addEventListener("DOMContentLoaded", () => App.init());

