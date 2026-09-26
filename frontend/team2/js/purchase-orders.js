/**
 * ====================================================================
 * SMART INVENTORY MANAGEMENT SYSTEM - TEAM 2
 * SUPPLIER PURCHASE ORDERS CONTROLLER (VANILLA JS)
 * Handles PO listing, details modal, items view, accept/reject workflows.
 * Dynamically resolves data for the logged-in/active supplier only.
 * ====================================================================
 */

(function () {
  "use strict";

  // Determine API Base URL (support both hosted on Flask and opened via file://)
  const isDirectFile = window.location.protocol === "file:";
  const API_BASE = isDirectFile
    ? "http://localhost:5000/api/team2/supplier"
    : "/api/team2/supplier";

  // Helper: Retrieve authenticated/logged-in supplier ID dynamically
  function getLoggedInSupplierId() {
    // Priority 1: URL query param (?supplier_id=5)
    const urlParams = new URLSearchParams(window.location.search);
    const urlId = urlParams.get("supplier_id");
    if (urlId && urlId.trim()) {
      localStorage.setItem("sims_active_supplier_id", urlId.trim());
      localStorage.setItem("supplier_id", urlId.trim());
      return urlId.trim();
    }

    // Priority 2: Stored active supplier in localStorage
    const storedId = localStorage.getItem("sims_active_supplier_id") || localStorage.getItem("supplier_id");
    if (storedId && storedId.trim()) {
      return storedId.trim();
    }

    // Priority 3: User object in storage (if set by authentication module)
    try {
      const userStr = localStorage.getItem("user") || sessionStorage.getItem("user") || localStorage.getItem("current_user");
      if (userStr) {
        const u = JSON.parse(userStr);
        if (u.supplier_id) return String(u.supplier_id);
        if (u.user_id) return String(u.user_id);
      }
    } catch (_) {}

    // Priority 4: Default fallback
    return "4";
  }

  // State
  const state = {
    activeSupplierId: getLoggedInSupplierId(),
    orders: [],
    currentOrder: null,
    statusFilter: "all",
    searchQuery: "",
    isLoading: false,
    supplierProfile: null
  };

  // Toast Notification
  let toastTimer = null;
  function showToast(message, type = "primary") {
    const toast = document.getElementById("poToast");
    const toastText = document.getElementById("poToastText");
    if (!toast || !toastText) return;

    toastText.textContent = message;
    toast.className = `toast-notice ${type} show`;

    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.remove("show");
    }, 4000);
  }

  // Format Currency (INR / USD format)
  function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return "₹0.00";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2
    }).format(Number(amount));
  }

  // Format Date
  function formatDate(isoString) {
    if (!isoString) return "N/A";
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      return d.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
      });
    } catch {
      return isoString;
    }
  }

  // Escape HTML to prevent XSS
  function escapeHTML(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Standard API Fetch Wrapper with Supplier Auth Headers
  async function apiFetch(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const token = localStorage.getItem("token") || localStorage.getItem("jwt") || sessionStorage.getItem("token");
    const headers = {
      "Content-Type": "application/json",
      "X-Supplier-Id": state.activeSupplierId,
      "X-User-Role": "supplier",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };

    const response = await fetch(url, {
      ...options,
      headers
    });

    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(result.message || `HTTP Error ${response.status}`);
    }
    return result.data;
  }

  // Render Status Badge
  function renderBadge(status) {
    const clean = (status || "Pending").toLowerCase().replace(/_/g, " ");
    let badgeClass = "badge-pending";
    if (clean === "accepted" || clean === "confirmed" || clean === "completed") {
      badgeClass = "badge-accepted";
    } else if (clean === "rejected" || clean === "cancelled") {
      badgeClass = "badge-rejected";
    } else if (clean === "in progress" || clean === "open") {
      badgeClass = "badge-in_progress";
    }
    return `<span class="badge ${badgeClass}">${escapeHTML(status || "Pending")}</span>`;
  }

  // Load and display supplier profile & populate switcher
  async function loadSupplierProfile() {
    try {
      // 1. Fetch available suppliers list for dropdown
      const supList = await apiFetch("/purchase-orders/suppliers");
      const select = document.getElementById("supplierSelect");
      if (select && Array.isArray(supList) && supList.length > 0) {
        select.innerHTML = "";
        supList.forEach((s) => {
          const opt = document.createElement("option");
          opt.value = String(s.supplier_id);
          opt.textContent = `${s.company_name} (ID: ${s.supplier_id})`;
          if (String(s.supplier_id) === String(state.activeSupplierId)) {
            opt.selected = true;
          }
          select.appendChild(opt);
        });
      }

      // 2. Fetch current profile
      const profile = await apiFetch("/purchase-orders/current-supplier");
      if (profile) {
        state.supplierProfile = profile;
        const nameEl = document.getElementById("supplierNameDisplay");
        const contactEl = document.getElementById("supplierContactDisplay");
        const sideName = document.getElementById("sidebarUserName");
        const sideRole = document.getElementById("sidebarUserRole");
        const sideAvatar = document.getElementById("sidebarAvatar");

        const compName = profile.company_name || `Supplier ${state.activeSupplierId}`;
        const contact = profile.contact_name || profile.contact_person || "Authorized Supplier";
        const email = profile.email || profile.status || "Active";

        if (nameEl) nameEl.textContent = compName;
        if (contactEl) contactEl.textContent = `${contact} • ${email}`;
        if (sideName) sideName.textContent = compName;
        if (sideRole) sideRole.textContent = `${contact} • ${profile.status || "Active"}`;
        if (sideAvatar) {
          const initials = compName
            .split(" ")
            .map((w) => w[0])
            .slice(0, 2)
            .join("")
            .toUpperCase() || "SP";
          sideAvatar.textContent = initials;
        }
      }
    } catch (err) {
      console.warn("Could not load supplier profile:", err);
    }
  }

  // Switch Supplier Account Function
  function switchSupplier(newId) {
    if (!newId || newId === state.activeSupplierId) return;
    state.activeSupplierId = String(newId);
    localStorage.setItem("sims_active_supplier_id", String(newId));
    localStorage.setItem("supplier_id", String(newId));

    // Sync URL parameter so link sharing or bookmarking is 100% accurate
    const url = new URL(window.location);
    url.searchParams.set("supplier_id", newId);
    window.history.replaceState({}, "", url);

    showToast(`Switched active supplier account to ID ${newId}`);
    loadSupplierProfile();
    loadOrders();
  }

  // Load Purchase Orders strictly for the active supplier
  async function loadOrders() {
    state.isLoading = true;
    const loadingEl = document.getElementById("poLoadingState");
    const emptyEl = document.getElementById("poEmptyState");
    const errorEl = document.getElementById("poErrorState");
    const tbody = document.getElementById("poTableBody");
    const countBadge = document.getElementById("badgePOCount");

    loadingEl.style.display = "flex";
    emptyEl.style.display = "none";
    errorEl.style.display = "none";
    tbody.innerHTML = "";

    try {
      let endpoint = `/purchase-orders?status=${encodeURIComponent(state.statusFilter)}&supplier_id=${encodeURIComponent(state.activeSupplierId)}`;
      if (state.searchQuery) {
        endpoint += `&search=${encodeURIComponent(state.searchQuery)}`;
      }

      const orders = await apiFetch(endpoint);
      state.orders = orders || [];
      renderOrders(state.orders);
    } catch (err) {
      console.error("Error loading purchase orders:", err);
      loadingEl.style.display = "none";
      errorEl.style.display = "flex";
      document.getElementById("poErrorMsg").textContent = err.message || "Failed to load purchase orders.";
    } finally {
      state.isLoading = false;
    }
  }

  // Render Orders Table
  function renderOrders(orders) {
    const loadingEl = document.getElementById("poLoadingState");
    const emptyEl = document.getElementById("poEmptyState");
    const tbody = document.getElementById("poTableBody");
    const countBadge = document.getElementById("badgePOCount");

    loadingEl.style.display = "none";
    countBadge.textContent = `${orders.length} records`;

    if (!orders || orders.length === 0) {
      emptyEl.style.display = "flex";
      tbody.innerHTML = "";
      return;
    }

    emptyEl.style.display = "none";
    tbody.innerHTML = orders
      .map(
        (po) => `
        <tr>
          <td class="font-medium">${escapeHTML(po.po_number || `PO-${po.id}`)}</td>
          <td class="text-subtle">${escapeHTML(formatDate(po.order_date))}</td>
          <td><span style="font-size: 12px; color: var(--text-muted);">${escapeHTML(po.categories || "General Inventory")}</span></td>
          <td><strong>${escapeHTML(po.item_count)} items</strong></td>
          <td><strong style="color: var(--text-main);">${escapeHTML(formatCurrency(po.total_amount))}</strong></td>
          <td>${renderBadge(po.status)}</td>
          <td>${renderBadge(po.supplier_response || "Pending")}</td>
          <td style="text-align: right;">
            <button class="btn btn-outline btn-view-po" onclick="POApp.openDetails(${po.id})">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
              View
            </button>
          </td>
        </tr>
      `
      )
      .join("");
  }

  // Open PO Details Modal
  async function openDetails(poId) {
    const modal = document.getElementById("poDetailsModal");
    const itemsTbody = document.getElementById("modalItemsTableBody");
    const acceptBtn = document.getElementById("modalAcceptBtn");
    const rejectBtn = document.getElementById("modalRejectBtn");
    const responseNote = document.getElementById("modalResponseStatusNote");
    const rejectionAlert = document.getElementById("modalRejectionAlert");

    itemsTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px;">Loading items...</td></tr>`;
    modal.classList.add("show");

    try {
      const po = await apiFetch(`/purchase-orders/${poId}`);
      state.currentOrder = po;

      document.getElementById("modalPoNumber").textContent = po.po_number || `PO-${po.id}`;
      document.getElementById("modalPoStatusBadge").innerHTML = renderBadge(po.status);
      document.getElementById("modalOrderDate").textContent = formatDate(po.order_date);
      document.getElementById("modalExpectedDelivery").textContent = formatDate(po.expected_delivery);
      document.getElementById("modalManagerName").textContent = po.manager_name || "Manager";
      document.getElementById("modalSupplierName").textContent = po.supplier_name || `Supplier ${po.supplier_id}`;
      document.getElementById("modalStatusText").textContent = po.status;
      document.getElementById("modalResponseText").innerHTML = renderBadge(po.supplier_response || "Pending");
      document.getElementById("modalTotalAmount").textContent = formatCurrency(po.total_amount);
      document.getElementById("modalItemCount").textContent = po.items ? po.items.length : 0;

      // Handle Rejection alert if applicable
      const isRejected = (po.supplier_response || "").toLowerCase() === "rejected";
      if (isRejected && po.rejection_reason) {
        rejectionAlert.style.display = "block";
        document.getElementById("modalRejectionReasonText").textContent = po.rejection_reason;
      } else {
        rejectionAlert.style.display = "none";
      }

      // Handle Action Controls based on response status
      const responseStatus = (po.supplier_response || "Pending").trim().toLowerCase();
      if (responseStatus === "pending") {
        acceptBtn.style.display = "inline-flex";
        rejectBtn.style.display = "inline-flex";
        responseNote.textContent = "Action Required: Please Accept or Reject this Purchase Order.";
      } else if (responseStatus === "accepted") {
        acceptBtn.style.display = "none";
        rejectBtn.style.display = "none";
        const dateStr = po.supplier_response_date ? formatDate(po.supplier_response_date) : "";
        responseNote.innerHTML = `<span style="color: var(--success); font-weight: 600;">✓ Accepted by your organization ${dateStr ? `on ${dateStr}` : ""}</span>`;
      } else {
        acceptBtn.style.display = "none";
        rejectBtn.style.display = "none";
        const dateStr = po.supplier_response_date ? formatDate(po.supplier_response_date) : "";
        responseNote.innerHTML = `<span style="color: var(--danger); font-weight: 600;">✕ Declined by your organization ${dateStr ? `on ${dateStr}` : ""}</span>`;
      }

      // Render Line Items Table (strictly read-only)
      if (!po.items || po.items.length === 0) {
        itemsTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px; color: var(--text-dim);">No line items specified.</td></tr>`;
      } else {
        itemsTbody.innerHTML = po.items
          .map(
            (item) => `
            <tr>
              <td class="font-medium">${escapeHTML(item.product_name)}</td>
              <td><code style="background: var(--bg-subtle); padding: 2px 6px; border-radius: 4px; font-size: 11px;">${escapeHTML(item.sku)}</code></td>
              <td>${escapeHTML(item.category)}</td>
              <td><strong style="color: var(--primary);">${escapeHTML(item.quantity)}</strong></td>
              <td>${escapeHTML(formatCurrency(item.unit_price))}</td>
              <td><strong>${escapeHTML(formatCurrency(item.subtotal))}</strong></td>
            </tr>
          `
          )
          .join("");
      }
    } catch (err) {
      console.error("Error opening PO details:", err);
      showToast(err.message || "Failed to load purchase order details", "danger");
      closeDetails();
    }
  }

  // Close PO Details Modal
  function closeDetails() {
    const modal = document.getElementById("poDetailsModal");
    if (modal) modal.classList.remove("show");
  }

  // Accept Flow
  function openAcceptConfirm() {
    if (!state.currentOrder) return;
    document.getElementById("acceptPoNumberDisplay").textContent = state.currentOrder.po_number || `PO-${state.currentOrder.id}`;
    document.getElementById("acceptPoAmountDisplay").textContent = formatCurrency(state.currentOrder.total_amount);
    document.getElementById("acceptConfirmModal").classList.add("show");
  }

  function closeAcceptConfirm() {
    document.getElementById("acceptConfirmModal").classList.remove("show");
  }

  async function executeAccept() {
    if (!state.currentOrder) return;
    const poId = state.currentOrder.id;
    closeAcceptConfirm();

    try {
      const updated = await apiFetch(`/purchase-orders/${poId}/accept`, {
        method: "POST"
      });
      showToast(`Purchase Order ${updated.po_number || `PO-${poId}`} accepted successfully!`, "success");
      openDetails(poId);
      loadOrders();
    } catch (err) {
      console.error("Error accepting PO:", err);
      showToast(err.message || "Failed to accept purchase order", "danger");
    }
  }

  // Reject Flow
  function openRejectConfirm() {
    if (!state.currentOrder) return;
    document.getElementById("rejectPoNumberDisplay").textContent = state.currentOrder.po_number || `PO-${state.currentOrder.id}`;
    document.getElementById("rejectionReasonInput").value = "";
    document.getElementById("rejectConfirmModal").classList.add("show");
  }

  function closeRejectConfirm() {
    document.getElementById("rejectConfirmModal").classList.remove("show");
  }

  async function executeReject() {
    if (!state.currentOrder) return;
    const poId = state.currentOrder.id;
    const reason = document.getElementById("rejectionReasonInput").value.trim();
    closeRejectConfirm();

    try {
      const updated = await apiFetch(`/purchase-orders/${poId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason })
      });
      showToast(`Purchase Order ${updated.po_number || `PO-${poId}`} has been rejected.`, "danger");
      openDetails(poId);
      loadOrders();
    } catch (err) {
      console.error("Error rejecting PO:", err);
      showToast(err.message || "Failed to reject purchase order", "danger");
    }
  }

  // Setup Event Listeners
  document.addEventListener("DOMContentLoaded", () => {
    // Initialize active supplier
    state.activeSupplierId = getLoggedInSupplierId();

    // Initial Load of profile & orders
    loadSupplierProfile();
    loadOrders();

    // Supplier Select Dropdown Event Listener
    const supplierSelect = document.getElementById("supplierSelect");
    if (supplierSelect) {
      supplierSelect.addEventListener("change", (e) => {
        switchSupplier(e.target.value);
      });
    }

    // Refresh Button
    const refreshBtn = document.getElementById("refreshPOBtn");
    if (refreshBtn) refreshBtn.addEventListener("click", () => {
      loadSupplierProfile();
      loadOrders();
    });

    // Filter Change
    const statusSelect = document.getElementById("statusFilter");
    if (statusSelect) {
      statusSelect.addEventListener("change", (e) => {
        state.statusFilter = e.target.value;
        loadOrders();
      });
    }

    // Search Input with Debounce
    const searchInput = document.getElementById("searchInput");
    let searchTimeout = null;
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        state.searchQuery = e.target.value;
        if (searchTimeout) clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
          loadOrders();
        }, 300);
      });
    }

    // Clear Filters
    const clearBtn = document.getElementById("clearFiltersBtn");
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        state.statusFilter = "all";
        state.searchQuery = "";
        if (statusSelect) statusSelect.value = "all";
        if (searchInput) searchInput.value = "";
        loadOrders();
      });
    }

    // Modal Close Buttons
    const closeModalBtn = document.getElementById("closeModalBtn");
    const modalCloseActionBtn = document.getElementById("modalCloseActionBtn");
    if (closeModalBtn) closeModalBtn.addEventListener("click", closeDetails);
    if (modalCloseActionBtn) modalCloseActionBtn.addEventListener("click", closeDetails);

    // Accept / Reject Buttons in Modal
    const modalAcceptBtn = document.getElementById("modalAcceptBtn");
    const modalRejectBtn = document.getElementById("modalRejectBtn");
    if (modalAcceptBtn) modalAcceptBtn.addEventListener("click", openAcceptConfirm);
    if (modalRejectBtn) modalRejectBtn.addEventListener("click", openRejectConfirm);

    // Submodal Actions
    const cancelAcceptBtn = document.getElementById("cancelAcceptBtn");
    const closeAcceptConfirmBtn = document.getElementById("closeAcceptConfirmBtn");
    const confirmAcceptBtn = document.getElementById("confirmAcceptBtn");
    if (cancelAcceptBtn) cancelAcceptBtn.addEventListener("click", closeAcceptConfirm);
    if (closeAcceptConfirmBtn) closeAcceptConfirmBtn.addEventListener("click", closeAcceptConfirm);
    if (confirmAcceptBtn) confirmAcceptBtn.addEventListener("click", executeAccept);

    const cancelRejectBtn = document.getElementById("cancelRejectBtn");
    const closeRejectConfirmBtn = document.getElementById("closeRejectConfirmBtn");
    const confirmRejectBtn = document.getElementById("confirmRejectBtn");
    if (cancelRejectBtn) cancelRejectBtn.addEventListener("click", closeRejectConfirm);
    if (closeRejectConfirmBtn) closeRejectConfirmBtn.addEventListener("click", closeRejectConfirm);
    if (confirmRejectBtn) confirmRejectBtn.addEventListener("click", executeReject);

    // Sidebar Navigation for Out-of-Scope Modules
    const navItems = document.querySelectorAll(".sidebar-nav .nav-item");
    navItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        const href = item.getAttribute("href");
        if (href && href !== "#" && !href.startsWith("#")) {
          // Allow normal navigation for real page links (e.g. / or index.html)
          return;
        }

        const moduleName = item.getAttribute("data-module");
        if (moduleName) {
          e.preventDefault();
          showToast(`The ${moduleName} module will be implemented separately as per project scope.`);
        }
      });
    });

    // Mobile Sidebar Toggle
    const toggleBtn = document.getElementById("sidebarToggleBtn");
    const sidebar = document.getElementById("appSidebar");
    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
      });
      document.addEventListener("click", (e) => {
        if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
          sidebar.classList.remove("open");
        }
      });
    }
  });

  // Expose global methods
  window.POApp = {
    loadOrders,
    openDetails,
    closeDetails,
    switchSupplier,
    state
  };
})();
