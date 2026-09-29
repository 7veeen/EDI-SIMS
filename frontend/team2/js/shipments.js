/**
 * ====================================================================
 * SIMS TEAM 2 — SHIPMENTS & FULFILLMENT CONTROLLER
 * Soumya Module: Mark ready, enter details, mark shipped, update status,
 *                expected delivery, mark delivered, completed shipments
 * ====================================================================
 */
(function () {
  "use strict";

  const isFile = window.location.protocol === "file:";
  const API_BASE = isFile ? "http://localhost:5000/api/team2/supplier" : "/api/team2/supplier";

  function getSupplierId() {
    const p = new URLSearchParams(window.location.search).get("supplier_id");
    if (p) { localStorage.setItem("sims_active_supplier_id", p); return p; }
    return localStorage.getItem("sims_active_supplier_id") ||
           localStorage.getItem("supplier_id") || "4";
  }

  const state = {
    supplierId: getSupplierId(),
    activeShipments: [],
    readyOrders: [],
    completedShipments: [],
    currentTab: "active",
    currentShipmentId: null
  };

  let toastTimer = null;
  function toast(msg, type = "primary") {
    const el = document.getElementById("toast");
    const tx = document.getElementById("toastText");
    if (!el || !tx) return;
    tx.textContent = msg;
    el.className = "toast-notice " + type + " show";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 4000);
  }

  function fmtDate(d) {
    if (!d) return "N/A";
    try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }
    catch { return d; }
  }

  function fmtCurrency(v) {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(v) || 0);
  }

  function statusBadge(s) {
    const map = {
      "Ready for Shipment": "badge-ready",
      "Shipped": "badge-shipped",
      "In Transit": "badge-in-transit",
      "Out for Delivery": "badge-in-transit",
      "Delivered": "badge-delivered",
      "Pending": "badge-pending",
      "Delayed": "badge-delayed",
      "Cancelled": "badge-cancelled"
    };
    return `<span class="badge ${map[s] || "badge-pending"}">${s}</span>`;
  }

  function apiHeaders() {
    return {
      "Content-Type": "application/json",
      "X-Supplier-Id": state.supplierId,
      "X-User-Role": "supplier"
    };
  }

  // ============================================================
  // LOAD STATS
  // ============================================================
  async function loadStats() {
    try {
      const r = await fetch(`${API_BASE}/shipments/stats`, { headers: apiHeaders() });
      const d = await r.json();
      if (d.success) {
        const s = d.data;
        document.getElementById("statReady").textContent = s.ready_for_shipment_count || 0;
        document.getElementById("statInTransit").textContent = s.active_shipments_count || 0;
        document.getElementById("statDelivered").textContent = s.completed_shipments_count || 0;
        document.getElementById("statTotalPOs").textContent = s.total_previous_pos || 0;
        document.getElementById("statQuotations").textContent = s.total_previous_quotations || 0;
        document.getElementById("statOnTime").textContent = (s.on_time_delivery_rate || 0) + "%";
      }
    } catch (e) { console.warn("Stats error:", e); }
  }

  // ============================================================
  // ACTIVE SHIPMENTS
  // ============================================================
  async function loadActiveShipments() {
    const search = document.getElementById("searchInput").value.trim();
    const status = document.getElementById("statusFilter").value;
    show("activeLoading"); hide("activeEmpty"); hide("activeError"); hide("activeTableWrap");

    try {
      let url = `${API_BASE}/shipments?status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`;
      const r = await fetch(url, { headers: apiHeaders() });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      state.activeShipments = d.data || [];
      renderActiveTable(state.activeShipments);
      document.getElementById("cntActive").textContent = state.activeShipments.length;
      document.getElementById("activeCount").textContent = `${state.activeShipments.length} shipment(s)`;
    } catch (e) {
      hide("activeLoading");
      show("activeError");
      document.getElementById("activeErrorMsg").textContent = e.message;
    }
  }

  function renderActiveTable(rows) {
    hide("activeLoading");
    const tbody = document.getElementById("activeTableBody");
    if (!rows || rows.length === 0) { show("activeEmpty"); return; }
    show("activeTableWrap");
    tbody.innerHTML = rows.map(s => `
      <tr>
        <td><strong>${s.shipment_number}</strong></td>
        <td><span style="font-weight:600;color:var(--primary)">${s.po_number}</span></td>
        <td>${s.carrier}</td>
        <td><code style="font-size:11px;background:var(--bg-subtle);padding:2px 6px;border-radius:4px">${s.tracking_number}</code></td>
        <td>${statusBadge(s.status)}</td>
        <td>${fmtDate(s.expected_delivery)}</td>
        <td>${fmtCurrency(s.total_amount)}</td>
        <td>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
            <button class="btn btn-outline btn-sm" onclick="ShipmentsApp.viewShipment(${s.shipment_id})">Details</button>
            ${s.status !== "Delivered" ? `<button class="btn btn-sm" style="background:var(--orange-subtle);color:var(--orange);border:1px solid var(--orange-border)" onclick="ShipmentsApp.openStatusModal(${s.shipment_id})">Update Status</button>` : ""}
            ${s.status === "Ready for Shipment" ? `<button class="btn btn-primary btn-sm" onclick="ShipmentsApp.openMarkShipped(${s.shipment_id}, '${s.carrier || ""}', '${s.tracking_number || ""}')">Mark Shipped</button>` : ""}
            ${["Shipped","In Transit","Out for Delivery"].includes(s.status) ? `<button class="btn btn-success btn-sm" onclick="ShipmentsApp.quickMarkDelivered(${s.shipment_id})">Mark Delivered</button>` : ""}
          </div>
        </td>
      </tr>`).join("");
  }

  // ============================================================
  // READY TO SHIP
  // ============================================================
  async function loadReadyToShip() {
    show("readyLoading"); hide("readyEmpty"); hide("readyTableWrap");
    try {
      const r = await fetch(`${API_BASE}/shipments/ready-to-ship`, { headers: apiHeaders() });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      state.readyOrders = d.data || [];
      renderReadyTable(state.readyOrders);
      document.getElementById("cntReady").textContent = state.readyOrders.length;
    } catch (e) { hide("readyLoading"); toast("Failed to load ready orders: " + e.message, "error"); }
  }

  function renderReadyTable(rows) {
    hide("readyLoading");
    const tbody = document.getElementById("readyTableBody");
    if (!rows || rows.length === 0) { show("readyEmpty"); return; }
    show("readyTableWrap");
    tbody.innerHTML = rows.map(o => `
      <tr>
        <td><strong style="color:var(--primary)">${o.po_number}</strong></td>
        <td>${fmtDate(o.order_date)}</td>
        <td title="${o.items_summary}">${truncate(o.items_summary, 35)}</td>
        <td>${fmtCurrency(o.total_amount)}</td>
        <td>${fmtDate(o.expected_delivery)}</td>
        <td>${o.has_shipment ? statusBadge(o.shipment_status) : '<span class="badge badge-pending">Not Created</span>'}</td>
        <td>
          <div style="display:flex;gap:6px;">
            <button class="btn btn-orange btn-sm" onclick="ShipmentsApp.markReady(${o.purchase_order_id})">Mark Ready</button>
            <button class="btn btn-primary btn-sm" onclick="ShipmentsApp.openDetailsModal(${o.purchase_order_id})">Enter Details</button>
          </div>
        </td>
      </tr>`).join("");
  }

  // ============================================================
  // COMPLETED SHIPMENTS
  // ============================================================
  async function loadCompletedShipments() {
    show("completedLoading"); hide("completedEmpty"); hide("completedTableWrap");
    try {
      const r = await fetch(`${API_BASE}/shipments/completed`, { headers: apiHeaders() });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      state.completedShipments = d.data || [];
      renderCompletedTable(state.completedShipments);
      document.getElementById("cntCompleted").textContent = state.completedShipments.length;
    } catch (e) { hide("completedLoading"); toast("Failed to load completed: " + e.message, "error"); }
  }

  function renderCompletedTable(rows) {
    hide("completedLoading");
    const tbody = document.getElementById("completedTableBody");
    if (!rows || rows.length === 0) { show("completedEmpty"); return; }
    show("completedTableWrap");
    tbody.innerHTML = rows.map(s => `
      <tr>
        <td><strong>${s.shipment_number}</strong></td>
        <td><span style="font-weight:600;color:var(--primary)">${s.po_number}</span></td>
        <td>${s.carrier}</td>
        <td><code style="font-size:11px;background:var(--bg-subtle);padding:2px 6px;border-radius:4px">${s.tracking_number}</code></td>
        <td>${fmtDate(s.delivered_at)}</td>
        <td><span style="background:var(--success-subtle);color:var(--success);padding:3px 10px;border-radius:99px;font-size:12px;font-weight:700">${s.transit_duration_days || "—"} day(s)</span></td>
        <td>${fmtCurrency(s.total_amount)}</td>
        <td><button class="btn btn-outline btn-sm" onclick="ShipmentsApp.viewShipment(${s.shipment_id})">View</button></td>
      </tr>`).join("");
  }

  // ============================================================
  // SHIPMENT DETAIL MODAL
  // ============================================================
  async function viewShipment(id) {
    state.currentShipmentId = id;
    const modal = document.getElementById("shipmentModal");
    const body = document.getElementById("shipmentModalBody");
    const footer = document.getElementById("shipmentModalFooter");
    body.innerHTML = '<div class="state-container"><div class="spinner"></div></div>';
    footer.style.display = "none";
    openModal("shipmentModal");

    try {
      const r = await fetch(`${API_BASE}/shipments/${id}`, { headers: apiHeaders() });
      const d = await r.json();
      if (!d.success) throw new Error(d.message || "Not found");
      const s = d.data;
      document.getElementById("shipmentModalTitle").textContent = `Shipment ${s.shipment_number}`;

      body.innerHTML = `
        <div class="detail-section">
          <div class="detail-section-title">Shipment Info</div>
          <div class="detail-grid">
            <div class="detail-item"><div class="label">Shipment #</div><div class="value">${s.shipment_number}</div></div>
            <div class="detail-item"><div class="label">Status</div><div class="value">${statusBadge(s.status)}</div></div>
            <div class="detail-item"><div class="label">PO Number</div><div class="value" style="color:var(--primary);font-weight:700">${s.po_number}</div></div>
            <div class="detail-item"><div class="label">Total Amount</div><div class="value">${fmtCurrency(s.total_amount)}</div></div>
            <div class="detail-item"><div class="label">Carrier</div><div class="value">${s.carrier || "—"}</div></div>
            <div class="detail-item"><div class="label">Tracking #</div><div class="value">${s.tracking_number || "Pending"}</div></div>
            <div class="detail-item"><div class="label">Shipping Method</div><div class="value">${s.shipping_method || "—"}</div></div>
            <div class="detail-item"><div class="label">Package Count</div><div class="value">${s.package_count || "—"}</div></div>
            <div class="detail-item"><div class="label">Expected Delivery</div><div class="value">${fmtDate(s.expected_delivery)}</div></div>
            <div class="detail-item"><div class="label">Shipped At</div><div class="value">${fmtDate(s.shipped_at)}</div></div>
            <div class="detail-item"><div class="label">Delivered At</div><div class="value">${fmtDate(s.delivered_at)}</div></div>
            <div class="detail-item"><div class="label">Manager</div><div class="value">${s.manager_name || "—"}</div></div>
          </div>
          ${s.shipping_notes ? `<div style="margin-top:10px;font-size:12px;color:var(--text-muted);background:var(--bg-subtle);padding:10px 14px;border-radius:var(--radius-md)"><strong>Notes:</strong> ${s.shipping_notes}</div>` : ""}
        </div>

        ${s.items && s.items.length > 0 ? `
        <div class="detail-section">
          <div class="detail-section-title">Order Items (${s.items.length})</div>
          <table class="data-table" style="font-size:12px;">
            <thead><tr><th>Product</th><th>SKU</th><th>Qty</th><th>Unit Price</th><th>Subtotal</th></tr></thead>
            <tbody>${s.items.map(i => `<tr><td>${i.product_name}</td><td>${i.sku}</td><td>${i.quantity}</td><td>${fmtCurrency(i.unit_price)}</td><td>${fmtCurrency(i.subtotal)}</td></tr>`).join("")}</tbody>
          </table>
        </div>` : ""}

        ${s.history && s.history.length > 0 ? `
        <div class="detail-section">
          <div class="detail-section-title">Status Timeline</div>
          <div class="timeline">${s.history.map(h => `
            <div class="timeline-event ${h.status.toLowerCase().replace(/ /g, "-")}">
              <div class="timeline-event-header">
                <span class="timeline-event-action">${h.action}</span>
                <span class="timeline-event-time">${fmtDate(h.created_at)}</span>
              </div>
              <div class="timeline-event-loc">${h.location}</div>
              ${h.notes ? `<div class="timeline-event-notes">${h.notes}</div>` : ""}
            </div>`).join("")}</div>
        </div>` : ""}
      `;

      // Show actions
      footer.style.display = "flex";
      const btnShip = document.getElementById("btnMarkShipped");
      const btnDel = document.getElementById("btnMarkDelivered");
      const btnUpd = document.getElementById("btnUpdateStatus");
      btnUpd.onclick = () => { closeModal("shipmentModal"); openStatusModal(id); };
      if (s.status === "Ready for Shipment") {
        btnShip.style.display = "flex";
        btnShip.onclick = () => { closeModal("shipmentModal"); openMarkShipped(id, s.carrier, s.tracking_number); };
      } else { btnShip.style.display = "none"; }
      if (["Shipped","In Transit","Out for Delivery"].includes(s.status)) {
        btnDel.style.display = "flex";
        btnDel.onclick = () => { closeModal("shipmentModal"); quickMarkDelivered(id); };
      } else { btnDel.style.display = "none"; }
    } catch (e) {
      body.innerHTML = `<div class="state-container"><div class="state-title" style="color:var(--danger)">Error: ${e.message}</div></div>`;
    }
  }

  // ============================================================
  // MARK READY
  // ============================================================
  async function markReady(poId) {
    if (!confirm(`Mark PO-${String(poId).padStart(4,"0")} as Ready for Shipment?`)) return;
    try {
      const r = await fetch(`${API_BASE}/shipments/ready`, {
        method: "POST", headers: apiHeaders(),
        body: JSON.stringify({ purchase_order_id: poId, notes: "Goods verified, packaged, and ready for carrier dispatch" })
      });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      toast(`PO-${String(poId).padStart(4,"0")} marked ready for shipment!`, "success");
      loadAll();
    } catch (e) { toast("Error: " + e.message, "error"); }
  }

  // ============================================================
  // ENTER DETAILS MODAL
  // ============================================================
  function openDetailsModal(poId) {
    document.getElementById("formPoId").value = poId;
    document.getElementById("detailsModalTitle").textContent = `Enter Shipment Details — PO-${String(poId).padStart(4,"0")}`;
    document.getElementById("shipmentDetailsForm").reset();
    document.getElementById("formPoId").value = poId;
    openModal("detailsModal");
  }

  async function submitDetails() {
    const poId = document.getElementById("formPoId").value;
    const carrier = document.getElementById("formCarrier").value.trim();
    if (!carrier) { toast("Carrier name is required", "warning"); return; }
    const payload = {
      purchase_order_id: parseInt(poId),
      carrier,
      tracking_number: document.getElementById("formTrackingNumber").value.trim(),
      shipping_method: document.getElementById("formShippingMethod").value,
      expected_delivery: document.getElementById("formExpectedDelivery").value,
      package_count: parseInt(document.getElementById("formPackageCount").value) || 1,
      total_weight: parseFloat(document.getElementById("formTotalWeight").value) || null,
      shipping_notes: document.getElementById("formShippingNotes").value.trim()
    };
    try {
      const r = await fetch(`${API_BASE}/shipments/details`, {
        method: "POST", headers: apiHeaders(), body: JSON.stringify(payload)
      });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      closeModal("detailsModal");
      toast("Shipment details saved successfully!", "success");
      loadAll();
    } catch (e) { toast("Error: " + e.message, "error"); }
  }

  // ============================================================
  // STATUS UPDATE MODAL
  // ============================================================
  function openStatusModal(id) {
    state.currentShipmentId = id;
    document.getElementById("statusShipmentId").value = id;
    openModal("statusModal");
  }

  async function submitStatusUpdate() {
    const id = document.getElementById("statusShipmentId").value;
    const status = document.getElementById("newStatus").value;
    const location = document.getElementById("statusLocation").value.trim();
    const notes = document.getElementById("statusNotes").value.trim();
    try {
      const r = await fetch(`${API_BASE}/shipments/${id}/status`, {
        method: "PUT", headers: apiHeaders(),
        body: JSON.stringify({ status, location, notes })
      });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      closeModal("statusModal");
      toast(`Shipment status updated to "${status}"`, "success");
      loadAll();
    } catch (e) { toast("Error: " + e.message, "error"); }
  }

  // ============================================================
  // MARK SHIPPED MODAL
  // ============================================================
  function openMarkShipped(id, carrier, tracking) {
    document.getElementById("markShippedId").value = id;
    document.getElementById("shippedCarrier").value = carrier || "";
    document.getElementById("shippedTracking").value = tracking || "";
    openModal("markShippedModal");
  }

  async function confirmMarkShipped() {
    const id = document.getElementById("markShippedId").value;
    const payload = {
      carrier: document.getElementById("shippedCarrier").value.trim(),
      tracking_number: document.getElementById("shippedTracking").value.trim(),
      expected_delivery: document.getElementById("shippedDelivery").value,
      notes: document.getElementById("shippedNotes").value.trim()
    };
    try {
      const r = await fetch(`${API_BASE}/shipments/${id}/mark-shipped`, {
        method: "POST", headers: apiHeaders(), body: JSON.stringify(payload)
      });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      closeModal("markShippedModal");
      toast("Shipment marked as dispatched!", "success");
      loadAll();
    } catch (e) { toast("Error: " + e.message, "error"); }
  }

  // ============================================================
  // QUICK MARK DELIVERED
  // ============================================================
  async function quickMarkDelivered(id) {
    if (!confirm("Confirm this shipment has been delivered to the recipient?")) return;
    try {
      const r = await fetch(`${API_BASE}/shipments/${id}/mark-delivered`, {
        method: "POST", headers: apiHeaders(),
        body: JSON.stringify({ notes: "Delivered to recipient and confirmed by warehouse team" })
      });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      toast("Shipment marked as delivered!", "success");
      loadAll();
    } catch (e) { toast("Error: " + e.message, "error"); }
  }

  // ============================================================
  // UTILITIES
  // ============================================================
  function show(id) { const el = document.getElementById(id); if (el) el.style.display = ""; }
  function hide(id) { const el = document.getElementById(id); if (el) el.style.display = "none"; }
  function truncate(s, n) { if (!s) return "—"; return s.length > n ? s.substring(0, n) + "…" : s; }

  function openModal(id) { document.getElementById(id).classList.add("open"); }
  function closeModal(id) { document.getElementById(id).classList.remove("open"); }

  function switchTab(tab) {
    state.currentTab = tab;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    document.getElementById("panelActive").style.display = tab === "active" ? "" : "none";
    document.getElementById("panelReady").style.display = tab === "ready" ? "" : "none";
    document.getElementById("panelCompleted").style.display = tab === "completed" ? "" : "none";
    if (tab === "active") loadActiveShipments();
    else if (tab === "ready") loadReadyToShip();
    else if (tab === "completed") loadCompletedShipments();
  }

  function loadAll() {
    loadStats();
    loadActiveShipments();
    loadReadyToShip();
    loadCompletedShipments();
  }

  function loadSupplierInfo() {
    fetch(`${API_BASE}/purchase-orders/current-supplier`, { headers: apiHeaders() })
      .then(r => r.json()).then(d => {
        if (d.success && d.data) {
          const s = d.data;
          document.getElementById("sidebarUserName").textContent = s.company_name || "Supplier";
          document.getElementById("sidebarUserRole").textContent = `${s.contact_name || "Contact"} • ${s.status || "Active"}`;
          const initials = (s.company_name || "S").split(" ").map(w => w[0]).join("").substring(0, 2).toUpperCase();
          document.getElementById("sidebarAvatar").textContent = initials;
        }
      }).catch(() => {});
  }

  function init() {
    loadSupplierInfo();
    loadAll();

    // Sidebar toggle
    document.getElementById("sidebarToggleBtn").addEventListener("click", () =>
      document.getElementById("appSidebar").classList.toggle("open"));

    // Tabs
    document.querySelectorAll(".tab-btn").forEach(b =>
      b.addEventListener("click", () => switchTab(b.dataset.tab)));

    // Search + filter
    let searchTimer;
    document.getElementById("searchInput").addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => { if (state.currentTab === "active") loadActiveShipments(); }, 400);
    });
    document.getElementById("statusFilter").addEventListener("change", () => {
      if (state.currentTab === "active") loadActiveShipments();
    });

    // Refresh
    document.getElementById("btnRefresh").addEventListener("click", loadAll);

    // Close modals
    ["closeShipmentModal","closeDetailsModal","cancelDetailsModal",
     "closeStatusModal","cancelStatusModal",
     "closeMarkShippedModal","cancelMarkShipped"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener("click", () => {
        ["shipmentModal","detailsModal","statusModal","markShippedModal"].forEach(m => closeModal(m));
      });
    });

    // Submit handlers
    document.getElementById("submitDetailsForm").addEventListener("click", submitDetails);
    document.getElementById("submitStatusUpdate").addEventListener("click", submitStatusUpdate);
    document.getElementById("confirmMarkShipped").addEventListener("click", confirmMarkShipped);

    // Backdrop close
    document.querySelectorAll(".modal-overlay").forEach(o =>
      o.addEventListener("click", e => { if (e.target === o) o.classList.remove("open"); }));

    // Keyboard close
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") document.querySelectorAll(".modal-overlay").forEach(o => o.classList.remove("open"));
    });
  }

  window.ShipmentsApp = {
    viewShipment,
    openStatusModal,
    openMarkShipped,
    quickMarkDelivered,
    markReady,
    openDetailsModal,
    loadActiveShipments,
    loadReadyToShip,
    loadCompletedShipments
  };

  document.addEventListener("DOMContentLoaded", init);
})();
