// ==========================================================================
// SIMS — Executive Owner Dashboard Controller
// Adheres strictly to:
// 1. Real API Data > Fake Visual Data
// 2. Shared API & Auth Client
// 3. Graceful offline/error state handling
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  // Global State for Attention Items
  const attentionItems = [];

  // 1. Initialize Owner Session & Greeting
  function initOwnerSession() {
    const user = typeof Auth !== "undefined" ? Auth.getUser() : null;

    // Time of day greeting
    const hour = new Date().getHours();
    let timeOfDay = "Good morning";
    if (hour >= 12 && hour < 17) {
      timeOfDay = "Good afternoon";
    } else if (hour >= 17) {
      timeOfDay = "Good evening";
    }

    const greetingEl = document.getElementById("owner-greeting");
    const roleIndicatorEl = document.getElementById("owner-role-indicator");

    if (user && user.username) {
      if (greetingEl) greetingEl.textContent = `${timeOfDay}, ${user.username}`;
      if (roleIndicatorEl) roleIndicatorEl.textContent = `${user.role ? user.role.toUpperCase() : "OWNER"} AUTHORITY`;
    } else {
      if (greetingEl) greetingEl.textContent = `${timeOfDay}, Owner`;
      if (roleIndicatorEl) roleIndicatorEl.textContent = "OWNER AUTHORITY";
    }

    // Live clock in header
    updateLiveClock();
    setInterval(updateLiveClock, 1000);
  }

  function updateLiveClock() {
    const clockEl = document.getElementById("hero-timestamp");
    if (clockEl) {
      const now = new Date();
      clockEl.textContent = `System Time: ${now.toLocaleTimeString()} | ${now.toLocaleDateString()}`;
    }
  }

  // 2. Fetch Strategic Metrics from Real Backend APIs
  async function loadDashboardData() {
    attentionItems.length = 0; // reset
    let backendOnline = false;

    // A. Main Inventory & Stock Metrics (/api/dashboard/employee)
    try {
      const dashData = await API.request("/api/dashboard/employee");
      backendOnline = true;
      renderCoreMetrics(dashData);
    } catch (err) {
      console.warn("[Owner Dashboard] /api/dashboard/employee unavailable:", err.message);
      renderCoreMetricsOffline();
    }

    // B. Inventory Engine Status (/api/reports/status)
    try {
      const statusData = await API.request("/api/reports/status");
      backendOnline = true;
      renderInventoryStatus(statusData);
    } catch (err) {
      console.warn("[Owner Dashboard] /api/reports/status unavailable:", err.message);
      renderInventoryStatusOffline();
    }

    // C. Notification Subsystem (/api/notifications/)
    try {
      const notifs = await API.request("/api/notifications/");
      backendOnline = true;
      renderNotifications(notifs);
    } catch (err) {
      console.warn("[Owner Dashboard] /api/notifications/ unavailable:", err.message);
      renderNotificationsOffline();
    }

    // D. Audit Trail Stream (/api/audit-logs/)
    try {
      const logs = await API.request("/api/audit-logs/");
      backendOnline = true;
      renderAuditLogs(logs);
    } catch (err) {
      console.warn("[Owner Dashboard] /api/audit-logs/ unavailable:", err.message);
      renderAuditLogsOffline();
    }

    // E. Catalog Categories (/api/categories/)
    try {
      const catData = await API.request("/api/categories/");
      backendOnline = true;
      const catCountEl = document.getElementById("proc-total-categories");
      if (catCountEl && catData && catData.categories) {
        catCountEl.textContent = catData.categories.length;
      }
    } catch (err) {
      console.warn("[Owner Dashboard] /api/categories/ unavailable:", err.message);
      const catCountEl = document.getElementById("proc-total-categories");
      if (catCountEl) catCountEl.textContent = "--";
    }

    // F. Suppliers & Procurement (/api/users/?role=Supplier or /api/dashboard/supplier)
    try {
      const usersData = await API.request("/api/users/?role=Supplier");
      backendOnline = true;
      const suppCountEl = document.getElementById("proc-total-suppliers");
      if (suppCountEl && usersData && usersData.users) {
        suppCountEl.textContent = usersData.users.length;
      }
    } catch (err) {
      // If 403 or unavailable, keep clean without fake data
      const suppCountEl = document.getElementById("proc-total-suppliers");
      if (suppCountEl) suppCountEl.textContent = "--";
    }

    // G. Supplier POs / Quotations if session allows (/api/dashboard/supplier)
    try {
      const suppData = await API.request("/api/dashboard/supplier");
      backendOnline = true;
      const poEl = document.getElementById("proc-total-po");
      const quoteEl = document.getElementById("proc-total-quotes");
      const poSub = document.getElementById("proc-po-sub");
      const quoteSub = document.getElementById("proc-quotes-sub");

      if (poEl && suppData.total_purchase_orders !== undefined) {
        poEl.textContent = suppData.total_purchase_orders;
        if (poSub) poSub.textContent = `${suppData.completed_orders || 0} completed`;
      }
      if (quoteEl && suppData.total_quotations !== undefined) {
        quoteEl.textContent = suppData.total_quotations;
        if (quoteSub) quoteSub.textContent = `${suppData.pending_quotations || 0} pending review`;
      }

      if (suppData.pending_quotations > 0) {
        attentionItems.push({
          severity: "warning",
          badge: "QUOTATION",
          title: `${suppData.pending_quotations} Vendor Quotations Pending Review`,
          desc: "Procurement suppliers have submitted proposals requiring authorization.",
          actionLabel: "Review Quotes",
          actionUrl: "quotations.html"
        });
      }
    } catch (err) {
      // Protected by Supplier role in backend, render clean note
      const poEl = document.getElementById("proc-total-po");
      const quoteEl = document.getElementById("proc-total-quotes");
      if (poEl) poEl.textContent = "--";
      if (quoteEl) quoteEl.textContent = "--";
    }

    // Update Topbar Status & Connection Banner
    updateConnectionStatus(backendOnline);

    // Render aggregated attention items
    renderAttentionPanel();
  }

  // 3. Render Core Metrics (from real /api/dashboard/employee response)
  function renderCoreMetrics(data) {
    const totalProdEl = document.getElementById("kpi-total-products");
    const totalStockEl = document.getElementById("kpi-total-stock");
    const stockInEl = document.getElementById("kpi-stock-in");
    const lowStockEl = document.getElementById("kpi-low-stock");

    const totalProducts = data.total_products !== undefined ? Number(data.total_products) : 0;
    const totalStock = data.total_stock !== undefined ? Number(data.total_stock) : 0;
    const stockIn = data.stock_in !== undefined ? Number(data.stock_in) : 0;
    const stockOut = data.stock_out !== undefined ? Number(data.stock_out) : 0;
    const lowStockList = Array.isArray(data.low_stock_products) ? data.low_stock_products : [];

    if (totalProdEl) totalProdEl.textContent = totalProducts.toLocaleString();
    if (totalStockEl) totalStockEl.textContent = totalStock.toLocaleString();
    if (stockInEl) stockInEl.textContent = stockIn.toLocaleString();
    if (lowStockEl) lowStockEl.textContent = lowStockList.length;

    // Centerpiece: Inventory Health Distribution
    const zeroStockItems = lowStockList.filter(item => Number(item.quantity_available) === 0);
    const lowStockItems = lowStockList.filter(item => Number(item.quantity_available) > 0);
    const adequateStockCount = Math.max(0, totalProducts - lowStockList.length);

    const countAdequateEl = document.getElementById("health-count-adequate");
    const countLowEl = document.getElementById("health-count-low");
    const countZeroEl = document.getElementById("health-count-zero");
    const stripCatalogEl = document.getElementById("strip-catalog-count");

    if (countAdequateEl) countAdequateEl.textContent = `${adequateStockCount} SKUs`;
    if (countLowEl) countLowEl.textContent = `${lowStockItems.length} SKUs`;
    if (countZeroEl) countZeroEl.textContent = `${zeroStockItems.length} SKUs`;
    if (stripCatalogEl) stripCatalogEl.textContent = `${totalProducts} SKUs`;

    // Calculate Segment Percentages
    const barHealthy = document.getElementById("bar-healthy");
    const barLow = document.getElementById("bar-low");
    const barOut = document.getElementById("bar-out");
    const healthBadge = document.getElementById("health-summary-badge");

    if (totalProducts > 0) {
      const pctHealthy = ((adequateStockCount / totalProducts) * 100).toFixed(1);
      const pctLow = ((lowStockItems.length / totalProducts) * 100).toFixed(1);
      const pctOut = ((zeroStockItems.length / totalProducts) * 100).toFixed(1);

      if (barHealthy) barHealthy.style.width = `${pctHealthy}%`;
      if (barLow) barLow.style.width = `${pctLow}%`;
      if (barOut) barOut.style.width = `${pctOut}%`;

      if (healthBadge) {
        if (zeroStockItems.length > 0) {
          healthBadge.className = "health-meta-badge danger";
          healthBadge.textContent = "Critical Stock Depletions";
        } else if (lowStockItems.length > 0) {
          healthBadge.className = "health-meta-badge warning";
          healthBadge.textContent = "Attention Required";
        } else {
          healthBadge.className = "health-meta-badge";
          healthBadge.textContent = "Optimal Inventory Health";
        }
      }
    }

    // Stock Movement Visual Comparison
    const moveInEl = document.getElementById("movement-stock-in");
    const moveOutEl = document.getElementById("movement-stock-out");
    const netDeltaEl = document.getElementById("movement-net-delta");
    const fillIn = document.getElementById("movement-fill-in");
    const fillOut = document.getElementById("movement-fill-out");
    const ratioLabel = document.getElementById("movement-ratio-label");

    if (moveInEl) moveInEl.textContent = stockIn.toLocaleString();
    if (moveOutEl) moveOutEl.textContent = stockOut.toLocaleString();

    const netDelta = stockIn - stockOut;
    if (netDeltaEl) {
      netDeltaEl.textContent = `${netDelta >= 0 ? "+" : ""}${netDelta.toLocaleString()} Units`;
      netDeltaEl.style.color = netDelta >= 0 ? "var(--navy-primary)" : "var(--accent-red)";
    }

    const totalFlow = stockIn + stockOut;
    if (totalFlow > 0) {
      const inRatio = ((stockIn / totalFlow) * 100).toFixed(0);
      const outRatio = (100 - inRatio).toFixed(0);
      if (fillIn) fillIn.style.width = `${inRatio}%`;
      if (fillOut) fillOut.style.width = `${outRatio}%`;
      if (ratioLabel) ratioLabel.textContent = `${inRatio}% Inward / ${outRatio}% Outward`;
    } else {
      if (fillIn) fillIn.style.width = "50%";
      if (fillOut) fillOut.style.width = "50%";
      if (ratioLabel) ratioLabel.textContent = "0 Recorded Transactions";
    }

    // Push Low Stock to Attention Items
    lowStockList.forEach(item => {
      const isZero = Number(item.quantity_available) === 0;
      attentionItems.push({
        severity: isZero ? "critical" : "warning",
        badge: isZero ? "OUT OF STOCK" : "LOW STOCK",
        title: `${item.product_name} (${item.quantity_available} units available)`,
        desc: `Product ID: #${item.product_id} is at or below the safety threshold of 10 units.`,
        actionLabel: isZero ? "Create Reorder PO" : "View Inventory",
        actionUrl: isZero ? "purchase-orders.html" : "inventory.html"
      });
    });
  }

  function renderCoreMetricsOffline() {
    const totalProdEl = document.getElementById("kpi-total-products");
    const totalStockEl = document.getElementById("kpi-total-stock");
    const stockInEl = document.getElementById("kpi-stock-in");
    const lowStockEl = document.getElementById("kpi-low-stock");

    if (totalProdEl) totalProdEl.textContent = "--";
    if (totalStockEl) totalStockEl.textContent = "--";
    if (stockInEl) stockInEl.textContent = "--";
    if (lowStockEl) lowStockEl.textContent = "--";

    const healthBadge = document.getElementById("health-summary-badge");
    if (healthBadge) {
      healthBadge.className = "health-meta-badge warning";
      healthBadge.textContent = "Backend Offline";
    }
  }

  // 4. Render Inventory Module Health (from /api/reports/status)
  function renderInventoryStatus(statusData) {
    const invPill = document.getElementById("health-inventory-pill");
    const invDetail = document.getElementById("health-inventory-detail");

    if (invPill && statusData && statusData.status) {
      invPill.textContent = statusData.status;
      invPill.className = `status-pill ${statusData.status.toLowerCase()}`;
    }

    if (invDetail && statusData && statusData.message) {
      invDetail.textContent = statusData.message;
    }

    if (statusData && statusData.status === "ERROR") {
      attentionItems.push({
        severity: "critical",
        badge: "SYSTEM ERROR",
        title: "Inventory Module Error Reported",
        desc: statusData.message || "An issue was detected in the inventory calculation subsystem.",
        actionLabel: "System Status",
        actionUrl: "system-status.html"
      });
    }
  }

  function renderInventoryStatusOffline() {
    const invPill = document.getElementById("health-inventory-pill");
    const repPill = document.getElementById("health-reports-pill");
    const authPill = document.getElementById("health-auth-pill");
    const notifPill = document.getElementById("health-notif-pill");
    const dbPill = document.getElementById("health-db-pill");

    [invPill, repPill, authPill, notifPill, dbPill].forEach(pill => {
      if (pill) {
        pill.textContent = "OFFLINE";
        pill.className = "status-pill offline";
      }
    });
  }

  // 5. Render Notifications (from /api/notifications/)
  function renderNotifications(notifs) {
    const badgeEl = document.getElementById("topbar-notif-count");
    if (!Array.isArray(notifs)) return;

    const unreadCount = notifs.filter(n => !n.is_read).length;
    if (badgeEl) {
      badgeEl.textContent = unreadCount;
      badgeEl.style.display = unreadCount > 0 ? "inline-block" : "none";
    }

    if (unreadCount > 0) {
      attentionItems.push({
        severity: "info",
        badge: "NOTIFICATION",
        title: `${unreadCount} Unread System Notifications`,
        desc: "Automated alerts and order updates require administrative attention.",
        actionLabel: "View Notifications",
        actionUrl: "notifications.html"
      });
    }
  }

  function renderNotificationsOffline() {
    const badgeEl = document.getElementById("topbar-notif-count");
    if (badgeEl) badgeEl.style.display = "none";
  }

  // 6. Render Audit Logs (from /api/audit-logs/)
  function renderAuditLogs(logs) {
    const container = document.getElementById("recent-activity-container");
    if (!container) return;

    if (!Array.isArray(logs) || logs.length === 0) {
      container.innerHTML = `
        <div class="empty-state-notice">
          <span class="empty-state-icon">🛡️</span>
          <p class="empty-state-title">No Recent Audit Logs</p>
          <p class="empty-state-desc">No administrative system events recorded yet.</p>
        </div>
      `;
      return;
    }

    const recentLogs = logs.slice(0, 5);
    container.innerHTML = recentLogs.map(log => {
      const timeStr = log.action_time ? new Date(log.action_time).toLocaleString() : "Just now";
      return `
        <div class="activity-item">
          <span class="act-badge">${escapeHtml(log.table_name || "SYSTEM")}</span>
          <div class="act-content">
            <div class="act-text"><strong>${escapeHtml(log.action || "Action")}</strong> on record #${escapeHtml(String(log.record_id || ""))}</div>
            <div class="act-meta">User #${escapeHtml(String(log.user_id || "System"))} &bull; ${escapeHtml(timeStr)}</div>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderAuditLogsOffline() {
    const container = document.getElementById("recent-activity-container");
    if (container) {
      container.innerHTML = `
        <div class="empty-state-notice">
          <span class="empty-state-icon">📡</span>
          <p class="empty-state-title">Audit Trail Offline</p>
          <p class="empty-state-desc">Cannot fetch audit logs while Flask backend is unreachable.</p>
        </div>
      `;
    }
  }

  // 7. Render Aggregated "Needs Your Attention" Panel
  function renderAttentionPanel() {
    const container = document.getElementById("attention-items-container");
    const countBadge = document.getElementById("attention-total-badge");
    if (!container) return;

    if (countBadge) countBadge.textContent = `${attentionItems.length} Alerts`;

    if (attentionItems.length === 0) {
      container.innerHTML = `
        <div class="empty-state-notice">
          <span class="empty-state-icon">✅</span>
          <p class="empty-state-title">All Systems Operational & Healthy</p>
          <p class="empty-state-desc">Zero stockout warnings, pending approvals, or operational roadblocks detected.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = attentionItems.map(item => `
      <div class="attention-card ${escapeHtml(item.severity)}">
        <div class="att-left">
          <span class="att-severity-badge ${escapeHtml(item.severity)}">${escapeHtml(item.badge)}</span>
          <div>
            <div class="att-title">${escapeHtml(item.title)}</div>
            <div class="att-desc">${escapeHtml(item.desc)}</div>
          </div>
        </div>
        <a href="${escapeHtml(item.actionUrl)}" class="att-btn">${escapeHtml(item.actionLabel)} &rarr;</a>
      </div>
    `).join("");
  }

  // 8. Update Topbar & Banner State
  function updateConnectionStatus(isOnline) {
    const banner = document.getElementById("connection-banner");
    const pulse = document.getElementById("topbar-pulse");
    const statusText = document.getElementById("topbar-status-text");

    if (isOnline) {
      if (banner) banner.classList.add("hidden");
      if (pulse) pulse.className = "pulse-indicator";
      if (statusText) statusText.textContent = "SYSTEM OPERATIONAL";
    } else {
      if (banner) banner.classList.remove("hidden");
      if (pulse) pulse.className = "pulse-indicator offline";
      if (statusText) statusText.textContent = "OFFLINE (PORT 5000)";

      const bannerMsg = document.getElementById("banner-message");
      if (bannerMsg) {
        bannerMsg.textContent = "Flask REST API is currently offline at http://127.0.0.1:5000. Start backend server to view live data.";
      }
    }
  }

  // Utility: HTML Escaping
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initialize
  initOwnerSession();
  loadDashboardData();

  // Attach Refresh Buttons
  const syncBtn = document.getElementById("btn-sync-dashboard");
  if (syncBtn) {
    syncBtn.addEventListener("click", () => {
      syncBtn.disabled = true;
      syncBtn.innerHTML = '<span class="btn-icon">↻</span> Syncing...';
      loadDashboardData().finally(() => {
        setTimeout(() => {
          syncBtn.disabled = false;
          syncBtn.innerHTML = '<span class="btn-icon">↻</span> Sync Realtime Data';
        }, 600);
      });
    });
  }

  const retryBtn = document.getElementById("btn-banner-retry");
  if (retryBtn) retryBtn.addEventListener("click", loadDashboardData);
});

