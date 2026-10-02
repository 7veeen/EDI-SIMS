// Page Behavior: System Status
document.addEventListener("DOMContentLoaded", async () => {
  const container = document.getElementById("status-container");

  async function loadStatus() {
    try {
      const data = await API.request("/api/reports/status");
      if (data && container) {
        container.innerHTML = `
          <div class="status-module-card">
            <div class="status-module-header">
              <strong>Module: Inventory</strong>
              <span class="status-pill success">${data.status}</span>
            </div>
            <p style="color: #64748b; font-size: 13px;">${data.message}</p>
            <div style="margin-top: 8px; font-size: 11px; color: #94a3b8;">Progress: ${data.progress}% | Updated: ${data.updated_at}</div>
          </div>
        `;
      }
    } catch (err) {
      if (container) {
        container.innerHTML = '<p style="color: #b45309;">Start backend at http://127.0.0.1:5000 to view system health.</p>';
      }
    }
  }

  loadStatus();
});
