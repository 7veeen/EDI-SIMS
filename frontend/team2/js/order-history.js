/**
 * ====================================================================
 * SIMS TEAM 2 — ORDER & STATUS HISTORY CONTROLLER
 * Soumya Module: Previous purchase orders, previous quotations,
 *                completed shipments, order/status lifecycle history
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

  const state = { supplierId: getSupplierId(), currentTab: "pos", poHistory: [] };

  let toastTimer;
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
    if (!d) return "—";
    try { return new Date(d).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); }
    catch { return d; }
  }

  function fmtCurrency(v) {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(v) || 0);
  }

  function statusBadge(s) {
    const map = {
      "Accepted": "badge-accepted", "Delivered": "badge-delivered",
      "Rejected": "badge-rejected", "Pending": "badge-pending",
      "Expired": "badge-expired", "Shipped": "badge-shipped",
      "In Transit": "badge-in-transit", "Under Review": "badge-pending",
      "Cancelled": "badge-cancelled", "Ready for Shipment": "badge-ready"
    };
    return `<span class="badge ${map[s] || "badge-pending"}">${s || "—"}</span>`;
  }

  function apiHeaders() {
    return { "Content-Type": "application/json", "X-Supplier-Id": state.supplierId, "X-User-Role": "supplier" };
  }

  function show(id) { const e = document.getElementById(id); if (e) e.style.display = ""; }
  function hide(id) { const e = document.getElementById(id); if (e) e.style.display = "none"; }

  // ============================================================
  // PREVIOUS PURCHASE ORDERS
  // ============================================================
  async function loadPreviousPOs() {
    const search = document.getElementById("searchInput").value.trim();
    const status = document.getElementById("statusFilter").value;
    show("posLoading"); hide("posEmpty"); hide("posTableWrap");

    try {
      let url = `${API_BASE}/history/purchase-orders?status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`;
      const r = await fetch(url, { headers: apiHeaders() });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      state.poHistory = d.data || [];
      renderPOsTable(state.poHistory);
      document.getElementById("cntPOs").textContent = state.poHistory.length;

      // Populate PO filter for timeline tab
      const poFilterSel = document.getElementById("poFilter");
      poFilterSel.innerHTML = '<option value="">All Orders</option>';
      state.poHistory.forEach(po => {
        const opt = document.createElement("option");
        opt.value = po.purchase_order_id;
        opt.textContent = po.po_number;
        poFilterSel.appendChild(opt);
      });
    } catch (e) {
      hide("posLoading"); show("posEmpty");
      toast("Failed to load purchase orders: " + e.message, "error");
    }
  }

  function renderPOsTable(rows) {
    hide("posLoading");
    const tbody = document.getElementById("posTableBody");
    if (!rows || rows.length === 0) { show("posEmpty"); return; }
    show("posTableWrap");
    tbody.innerHTML = rows.map(po => `
      <tr>
        <td><strong style="color:var(--primary)">${po.po_number}</strong></td>
        <td>${fmtDate(po.order_date)}</td>
        <td title="${po.items_summary || ""}" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${po.items_summary || "—"}</td>
        <td><strong>${fmtCurrency(po.total_amount)}</strong></td>
        <td>${fmtDate(po.expected_delivery)}</td>
        <td>${statusBadge(po.status)}</td>
        <td>${statusBadge(po.supplier_response)}
          ${po.rejection_reason ? `<div style="font-size:10.5px;color:var(--danger);margin-top:3px" title="${po.rejection_reason}">↳ ${po.rejection_reason.substring(0,40)}…</div>` : ""}
        </td>
        <td>
          ${po.shipment_number ? `
            <div style="font-size:12px"><strong>${po.shipment_number}</strong></div>
            <div style="font-size:11px;color:var(--text-muted)">${po.carrier || ""} ${po.tracking_number ? `• ${po.tracking_number}` : ""}</div>
            ${statusBadge(po.shipment_status)}
          ` : '<span style="color:var(--text-dim);font-size:12px">No Shipment</span>'}
        </td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="HistoryApp.viewPOTimeline(${po.purchase_order_id})">View Timeline</button>
        </td>
      </tr>`).join("");
  }

  // ============================================================
  // PREVIOUS QUOTATIONS
  // ============================================================
  async function loadPreviousQuotations() {
    const search = document.getElementById("searchInput").value.trim();
    const status = document.getElementById("statusFilter").value;
    show("quotLoading"); hide("quotEmpty"); hide("quotTableWrap");

    try {
      let url = `${API_BASE}/history/quotations?status=${encodeURIComponent(status)}&search=${encodeURIComponent(search)}`;
      const r = await fetch(url, { headers: apiHeaders() });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      const rows = d.data || [];
      renderQuotTable(rows);
      document.getElementById("cntQuotations").textContent = rows.length;
    } catch (e) {
      hide("quotLoading"); show("quotEmpty");
      toast("Failed to load quotations: " + e.message, "error");
    }
  }

  function renderQuotTable(rows) {
    hide("quotLoading");
    const tbody = document.getElementById("quotTableBody");
    if (!rows || rows.length === 0) { show("quotEmpty"); return; }
    show("quotTableWrap");
    tbody.innerHTML = rows.map(q => `
      <tr>
        <td><strong>${q.quotation_number}</strong></td>
        <td><strong>${q.product_name}</strong></td>
        <td><code style="font-size:11px;background:var(--bg-subtle);padding:2px 6px;border-radius:4px">${q.sku}</code></td>
        <td><span style="background:var(--primary-subtle);color:var(--primary);padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600">${q.category_name}</span></td>
        <td>${fmtCurrency(q.quoted_price)}</td>
        <td>${q.quantity}</td>
        <td><strong>${fmtCurrency(q.total_amount)}</strong></td>
        <td>${fmtDate(q.quotation_date)}</td>
        <td>${q.valid_until ? fmtDate(q.valid_until) : '<span style="color:var(--text-dim)">—</span>'}</td>
        <td>${statusBadge(q.status)}</td>
      </tr>`).join("");
  }

  // ============================================================
  // ORDER STATUS HISTORY TIMELINE
  // ============================================================
  async function loadTimeline(poId) {
    show("tlLoading"); hide("tlEmpty"); hide("tlContent");

    let url = `${API_BASE}/history/all`;
    if (poId) url += `?purchase_order_id=${poId}`;

    try {
      const r = await fetch(url, { headers: apiHeaders() });
      const d = await r.json();
      if (!d.success) throw new Error(d.message);
      const rows = d.data || [];
      renderTimeline(rows);
      document.getElementById("cntTimeline").textContent = rows.length;
    } catch (e) {
      hide("tlLoading");
      show("tlEmpty");
      toast("Failed to load history: " + e.message, "error");
    }
  }

  function renderTimeline(rows) {
    hide("tlLoading");
    const list = document.getElementById("timelineList");
    if (!rows || rows.length === 0) { show("tlEmpty"); return; }
    show("tlContent");

    const statusClass = s => {
      if (!s) return "";
      const sl = s.toLowerCase();
      if (sl.includes("deliver")) return "delivered";
      if (sl.includes("ship") || sl.includes("transit")) return "shipped";
      if (sl.includes("ready")) return "ready";
      return "";
    };

    list.innerHTML = rows.map(h => `
      <div class="timeline-event ${statusClass(h.status)}">
        <div class="timeline-event-header">
          <span class="timeline-event-action">${h.action}</span>
          <span class="timeline-event-time">${fmtDate(h.created_at)}</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px;margin-top:4px;flex-wrap:wrap;">
          <span style="font-size:11px;font-weight:700;background:var(--primary-subtle);color:var(--primary);padding:2px 8px;border-radius:99px">${h.po_number}</span>
          ${h.shipment_number ? `<span style="font-size:11px;background:var(--bg-subtle);color:var(--text-muted);padding:2px 8px;border-radius:99px">${h.shipment_number}</span>` : ""}
          ${statusBadge(h.status)}
          ${h.previous_status ? `<span style="font-size:11px;color:var(--text-dim)">← ${h.previous_status}</span>` : ""}
        </div>
        <div class="timeline-event-loc" style="margin-top:4px">📍 ${h.location || "Fulfillment Facility"} &nbsp;•&nbsp; 👤 ${h.changed_by}</div>
        ${h.notes ? `<div class="timeline-event-notes">${h.notes}</div>` : ""}
      </div>`).join("");
  }

  function viewPOTimeline(poId) {
    switchTab("timeline");
    document.getElementById("poFilter").value = poId;
    loadTimeline(poId);
  }

  // ============================================================
  // TABS & INIT
  // ============================================================
  function switchTab(tab) {
    state.currentTab = tab;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
    document.getElementById("panelPOs").style.display = tab === "pos" ? "" : "none";
    document.getElementById("panelQuotations").style.display = tab === "quotations" ? "" : "none";
    document.getElementById("panelTimeline").style.display = tab === "timeline" ? "" : "none";
    if (tab === "pos") loadPreviousPOs();
    else if (tab === "quotations") loadPreviousQuotations();
    else if (tab === "timeline") loadTimeline();
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
    loadPreviousPOs();
    loadPreviousQuotations();
    loadTimeline();

    document.getElementById("sidebarToggleBtn").addEventListener("click", () =>
      document.getElementById("appSidebar").classList.toggle("open"));

    document.querySelectorAll(".tab-btn").forEach(b =>
      b.addEventListener("click", () => switchTab(b.dataset.tab)));

    document.getElementById("btnRefresh").addEventListener("click", () => {
      if (state.currentTab === "pos") loadPreviousPOs();
      else if (state.currentTab === "quotations") loadPreviousQuotations();
      else loadTimeline(document.getElementById("poFilter").value || undefined);
    });

    let searchTimer;
    document.getElementById("searchInput").addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        if (state.currentTab === "pos") loadPreviousPOs();
        else if (state.currentTab === "quotations") loadPreviousQuotations();
      }, 400);
    });

    document.getElementById("statusFilter").addEventListener("change", () => {
      if (state.currentTab === "pos") loadPreviousPOs();
      else if (state.currentTab === "quotations") loadPreviousQuotations();
    });

    document.getElementById("poFilter").addEventListener("change", e => {
      loadTimeline(e.target.value || undefined);
    });
  }

  window.HistoryApp = { viewPOTimeline };

  document.addEventListener("DOMContentLoaded", init);
})();
