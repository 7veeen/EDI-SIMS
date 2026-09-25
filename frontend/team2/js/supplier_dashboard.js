/**
 * ====================================================================
 * SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2
 * SUPPLIER DASHBOARD JAVASCRIPT CONTROLLER (VANILLA JS)
 * Handles API communication, state management, and DOM rendering.
 * ====================================================================
 */

(function () {
  "use strict";

  // Determine API Base URL (support both hosted on Flask and opened via file://)
  const isDirectFile = window.location.protocol === "file:";
  const API_BASE = isDirectFile
    ? "http://localhost:5000/api/team2/supplier"
    : "/api/team2/supplier";

  // Global State (Defaulting to live DB Supplier 4: 'Supplier 1 Company')
  const state = {
    activeSupplierId: "4",
    isLoading: false,
    summaryCounts: {
      pending_requests: 0,
      pending_quotations: 0,
      pending_purchase_orders: 0,
      orders_to_ship: 0,
      shipped_orders: 0,
      delivered_orders: 0
    },
    supplierInfo: null,
    stockRequests: [],
    purchaseOrders: [],
    shipments: [],
    notifications: []
  };

  // Toast Notification Helper
  let toastTimer = null;
  function showToast(message) {
    const toast = document.getElementById("moduleToast");
    const toastText = document.getElementById("moduleToastText");
    if (!toast || !toastText) return;

    toastText.textContent = message;
    toast.classList.add("show");

    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove("show");
    }, 3500);
  }

  // Helper: Format Date
  function formatDate(isoString) {
    if (!isoString) return "N/A";
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
      });
    } catch {
      return isoString;
    }
  }

  // Helper: Format Currency
  function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD"
    }).format(Number(amount));
  }

  // Helper: Escape HTML to prevent XSS
  function escapeHTML(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Helper: Standard Fetch Wrapper with Auth Headers
  async function apiFetch(endpoint) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        "X-Supplier-Id": state.activeSupplierId,
        "X-User-Role": "supplier"
      }
    });

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      throw new Error(errJson.message || `HTTP Error ${response.status}`);
    }

    const result = await response.json();
    return result.data;
  }

  // Render Status Badge
  function renderStatusBadge(status) {
    const cleanStatus = (status || "pending").toLowerCase();
    const formatted = cleanStatus.replace(/_/g, " ");
    return `<span class="badge badge-${escapeHTML(cleanStatus)}">${escapeHTML(formatted)}</span>`;
  }

  // Update Summary Cards UI
  function updateSummaryCards(counts) {
    document.getElementById("countPendingRequests").textContent = counts.pending_requests ?? 0;
    document.getElementById("countPendingQuotes").textContent = counts.pending_quotations ?? 0;
    document.getElementById("countPendingPOs").textContent = counts.pending_purchase_orders ?? 0;
    document.getElementById("countOrdersToShip").textContent = counts.orders_to_ship ?? 0;
    document.getElementById("countShippedOrders").textContent = counts.shipped_orders ?? 0;
    document.getElementById("countDeliveredOrders").textContent = counts.delivered_orders ?? 0;
  }

  // Render Stock Requests Table
  function renderStockRequests(requests) {
    const tbody = document.getElementById("tbodyStockRequests");
    const countBadge = document.getElementById("badgeStockRequests");
    const loadingEl = document.getElementById("stateLoadingRequests");
    const emptyEl = document.getElementById("stateEmptyRequests");
    const errorEl = document.getElementById("stateErrorRequests");

    loadingEl.style.display = "none";
    errorEl.style.display = "none";

    countBadge.textContent = `${requests.length} records`;

    if (!requests || requests.length === 0) {
      tbody.innerHTML = "";
      emptyEl.style.display = "flex";
      return;
    }

    emptyEl.style.display = "none";
    tbody.innerHTML = requests
      .map(
        (req) => `
        <tr>
          <td class="font-medium">${escapeHTML(req.request_number || req.id)}</td>
          <td class="text-subtle">${escapeHTML(formatDate(req.request_date))}</td>
          <td>${escapeHTML(req.items_summary || "Inventory Batch")}</td>
          <td><strong>${escapeHTML(req.quantity ?? "-")}</strong></td>
          <td>${renderStatusBadge(req.status)}</td>
        </tr>
      `
      )
      .join("");
  }

  // Render Purchase Orders Table
  function renderPurchaseOrders(pos) {
    const tbody = document.getElementById("tbodyPurchaseOrders");
    const countBadge = document.getElementById("badgePurchaseOrders");
    const loadingEl = document.getElementById("stateLoadingPOs");
    const emptyEl = document.getElementById("stateEmptyPOs");
    const errorEl = document.getElementById("stateErrorPOs");

    loadingEl.style.display = "none";
    errorEl.style.display = "none";

    countBadge.textContent = `${pos.length} records`;

    if (!pos || pos.length === 0) {
      tbody.innerHTML = "";
      emptyEl.style.display = "flex";
      return;
    }

    emptyEl.style.display = "none";
    tbody.innerHTML = pos
      .map(
        (po) => `
        <tr>
          <td class="font-medium">${escapeHTML(po.po_number || po.id)}</td>
          <td class="text-subtle">${escapeHTML(formatDate(po.order_date))}</td>
          <td><strong>${escapeHTML(formatCurrency(po.total_amount))}</strong></td>
          <td>${renderStatusBadge(po.status)}</td>
        </tr>
      `
      )
      .join("");
  }

  // Render Shipments Table
  function renderShipments(shipments) {
    const tbody = document.getElementById("tbodyShipments");
    const countBadge = document.getElementById("badgeShipments");
    const loadingEl = document.getElementById("stateLoadingShipments");
    const emptyEl = document.getElementById("stateEmptyShipments");
    const errorEl = document.getElementById("stateErrorShipments");

    loadingEl.style.display = "none";
    errorEl.style.display = "none";

    countBadge.textContent = `${shipments.length}`;

    if (!shipments || shipments.length === 0) {
      tbody.innerHTML = "";
      emptyEl.style.display = "flex";
      return;
    }

    emptyEl.style.display = "none";
    tbody.innerHTML = shipments
      .map(
        (s) => `
        <tr>
          <td class="font-medium">
            <div>${escapeHTML(s.po_number || s.shipment_number || s.id)}</div>
            ${s.tracking_number ? `<small class="text-subtle">Trk: ${escapeHTML(s.tracking_number)}</small>` : ""}
          </td>
          <td>${renderStatusBadge(s.status)}</td>
          <td class="text-subtle">${escapeHTML(formatDate(s.expected_delivery))}</td>
        </tr>
      `
      )
      .join("");
  }

  // Render Notifications List
  function renderNotifications(notifs) {
    const container = document.getElementById("notificationsList");
    const countBadge = document.getElementById("badgeNotifications");
    const sidebarBadge = document.getElementById("sidebarNotifBadge");
    const loadingEl = document.getElementById("stateLoadingNotifications");
    const emptyEl = document.getElementById("stateEmptyNotifications");
    const errorEl = document.getElementById("stateErrorNotifications");

    loadingEl.style.display = "none";
    errorEl.style.display = "none";

    countBadge.textContent = `${notifs.length}`;
    if (sidebarBadge) {
      sidebarBadge.textContent = `${notifs.length}`;
    }

    if (!notifs || notifs.length === 0) {
      container.innerHTML = "";
      emptyEl.style.display = "flex";
      return;
    }

    emptyEl.style.display = "none";
    container.innerHTML = notifs
      .map(
        (n) => `
        <div class="notification-item">
          <div class="notif-indicator ${n.is_read ? "read" : ""}"></div>
          <div class="notif-content">
            <div class="notif-title">${escapeHTML(n.title)}</div>
            <div class="notif-message">${escapeHTML(n.message)}</div>
            <div class="notif-time">${escapeHTML(formatDate(n.created_at))}</div>
          </div>
        </div>
      `
      )
      .join("");
  }

  // Main Dashboard Loader
  async function loadDashboard() {
    state.isLoading = true;

    // Show loading states for all sections
    document.getElementById("stateLoadingRequests").style.display = "flex";
    document.getElementById("stateLoadingPOs").style.display = "flex";
    document.getElementById("stateLoadingShipments").style.display = "flex";
    document.getElementById("stateLoadingNotifications").style.display = "flex";

    document.getElementById("stateEmptyRequests").style.display = "none";
    document.getElementById("stateEmptyPOs").style.display = "none";
    document.getElementById("stateEmptyShipments").style.display = "none";
    document.getElementById("stateEmptyNotifications").style.display = "none";

    document.getElementById("stateErrorRequests").style.display = "none";
    document.getElementById("stateErrorPOs").style.display = "none";
    document.getElementById("stateErrorShipments").style.display = "none";
    document.getElementById("stateErrorNotifications").style.display = "none";

    try {
      const data = await apiFetch("/dashboard");

      // Update Supplier Profile in Header and Sidebar
      if (data.supplier) {
        state.supplierInfo = data.supplier;
        const compName = data.supplier.company_name || `Supplier ${data.supplier.id}`;
        const contact = data.supplier.contact_person || data.supplier.contact_name || "Authorized Representative";
        
        document.getElementById("supplierNameDisplay").textContent = compName;
        document.getElementById("supplierContactDisplay").textContent = contact;

        // Update Sidebar User Card
        const sbName = document.getElementById("sidebarUserName");
        const sbRole = document.getElementById("sidebarUserRole");
        const sbAvatar = document.getElementById("sidebarAvatar");

        if (sbName) sbName.textContent = compName;
        if (sbRole) sbRole.textContent = `${contact} • ${data.supplier.status || 'Active'}`;
        if (sbAvatar) {
          const initials = compName
            .split(" ")
            .map((w) => w[0])
            .slice(0, 2)
            .join("")
            .toUpperCase() || "S1";
          sbAvatar.textContent = initials;
        }
      }

      // Update Summary Cards
      if (data.summary_counts) {
        state.summaryCounts = data.summary_counts;
        updateSummaryCards(data.summary_counts);
      }

      // Update Recent Stock Requests
      state.stockRequests = data.recent_stock_requests || [];
      renderStockRequests(state.stockRequests);

      // Update Recent Purchase Orders
      state.purchaseOrders = data.recent_purchase_orders || [];
      renderPurchaseOrders(state.purchaseOrders);

      // Update Pending Shipments
      state.shipments = data.pending_shipments || [];
      renderShipments(state.shipments);

      // Update Notifications
      state.notifications = data.recent_notifications || [];
      renderNotifications(state.notifications);

      // Update Database Status Badge
      const dbStatus = data.database_status;
      const dbDot = document.getElementById("dbStatusDot");
      const dbText = document.getElementById("dbStatusText");
      const banner = document.getElementById("dbNoticeBanner");

      if (dbStatus && dbStatus.supabase_configured) {
        dbDot.className = "connection-dot";
        dbText.textContent = "Supabase Live";
        banner.style.display = "none";
      } else {
        dbDot.className = "connection-dot warning";
        dbText.textContent = "Supabase Disconnected";
        banner.style.display = "flex";
      }
    } catch (err) {
      console.error("Failed to load dashboard:", err);
      // Fallback: Individual section error states
      document.getElementById("stateLoadingRequests").style.display = "none";
      document.getElementById("stateErrorRequests").style.display = "flex";
      document.getElementById("errorMsgRequests").textContent = err.message;

      document.getElementById("stateLoadingPOs").style.display = "none";
      document.getElementById("stateErrorPOs").style.display = "flex";
      document.getElementById("errorMsgPOs").textContent = err.message;

      document.getElementById("stateLoadingShipments").style.display = "none";
      document.getElementById("stateErrorShipments").style.display = "flex";
      document.getElementById("errorMsgShipments").textContent = err.message;

      document.getElementById("stateLoadingNotifications").style.display = "none";
      document.getElementById("stateErrorNotifications").style.display = "flex";
      document.getElementById("errorMsgNotifications").textContent = err.message;

      const dbDot = document.getElementById("dbStatusDot");
      const dbText = document.getElementById("dbStatusText");
      dbDot.className = "connection-dot warning";
      dbText.textContent = "Server Offline";
    } finally {
      state.isLoading = false;
    }
  }

  // Individual Section Loaders (For Retry Buttons)
  async function loadStockRequests() {
    document.getElementById("stateLoadingRequests").style.display = "flex";
    document.getElementById("stateErrorRequests").style.display = "none";
    try {
      const data = await apiFetch("/recent-stock-requests");
      renderStockRequests(data || []);
    } catch (e) {
      document.getElementById("stateLoadingRequests").style.display = "none";
      document.getElementById("stateErrorRequests").style.display = "flex";
      document.getElementById("errorMsgRequests").textContent = e.message;
    }
  }

  async function loadPurchaseOrders() {
    document.getElementById("stateLoadingPOs").style.display = "flex";
    document.getElementById("stateErrorPOs").style.display = "none";
    try {
      const data = await apiFetch("/recent-purchase-orders");
      renderPurchaseOrders(data || []);
    } catch (e) {
      document.getElementById("stateLoadingPOs").style.display = "none";
      document.getElementById("stateErrorPOs").style.display = "flex";
      document.getElementById("errorMsgPOs").textContent = e.message;
    }
  }

  async function loadShipments() {
    document.getElementById("stateLoadingShipments").style.display = "flex";
    document.getElementById("stateErrorShipments").style.display = "none";
    try {
      const data = await apiFetch("/pending-shipments");
      renderShipments(data || []);
    } catch (e) {
      document.getElementById("stateLoadingShipments").style.display = "none";
      document.getElementById("stateErrorShipments").style.display = "flex";
      document.getElementById("errorMsgShipments").textContent = e.message;
    }
  }

  async function loadNotifications() {
    document.getElementById("stateLoadingNotifications").style.display = "flex";
    document.getElementById("stateErrorNotifications").style.display = "none";
    try {
      const data = await apiFetch("/notifications");
      renderNotifications(data || []);
    } catch (e) {
      document.getElementById("stateLoadingNotifications").style.display = "none";
      document.getElementById("stateErrorNotifications").style.display = "flex";
      document.getElementById("errorMsgNotifications").textContent = e.message;
    }
  }

  // Setup Sidebar Interactivity
  function setupSidebarInteractions() {
    const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
    navItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        const moduleName = item.getAttribute("data-module");
        if (moduleName === "dashboard") {
          e.preventDefault();
          navItems.forEach((n) => n.classList.remove("active"));
          item.classList.add("active");
          loadDashboard();
        } else if (moduleName === "Notifications") {
          // Smooth scroll to notifications card
          const notifCard = document.getElementById("headingNotifications");
          if (notifCard) {
            notifCard.scrollIntoView({ behavior: "smooth" });
          }
        } else {
          e.preventDefault();
          showToast(`The ${moduleName} module will be implemented separately as per project scope.`);
        }
      });
    });

    // Mobile / Tablet Sidebar Toggle
    const toggleBtn = document.getElementById("sidebarToggleBtn");
    const sidebar = document.getElementById("appSidebar");
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
      });
      // Close sidebar when clicking outside on mobile
      document.addEventListener("click", (e) => {
        if (
          sidebar.classList.contains("open") &&
          !sidebar.contains(e.target) &&
          !toggleBtn.contains(e.target)
        ) {
          sidebar.classList.remove("open");
        }
      });
    }
  }

  // Event Listeners
  document.addEventListener("DOMContentLoaded", () => {
    // Setup Sidebar
    setupSidebarInteractions();

    // Refresh button
    const refreshBtn = document.getElementById("refreshDashboardBtn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        loadDashboard();
      });
    }

    // Apply Supplier Switcher
    const applyBtn = document.getElementById("applySupplierBtn");
    const supplierInput = document.getElementById("supplierIdInput");
    if (applyBtn && supplierInput) {
      applyBtn.addEventListener("click", () => {
        const newId = supplierInput.value.trim();
        if (newId) {
          state.activeSupplierId = newId;
          loadDashboard();
        }
      });
      supplierInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          applyBtn.click();
        }
      });
    }

    // Initial Load
    loadDashboard();
  });

  // Expose global methods for retry buttons and external interactions
  window.DashboardApp = {
    loadDashboard,
    loadStockRequests,
    loadPurchaseOrders,
    loadShipments,
    loadNotifications,
    showToast
  };
})();
