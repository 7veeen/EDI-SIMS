// Page Behavior: Audit Logs
document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.getElementById("audit-tbody");

  async function loadAuditLogs() {
    try {
      const data = await API.request("/api/audit-logs/");
      if (data && tbody) {
        if (data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 16px;">No audit records found.</td></tr>';
        } else {
          tbody.innerHTML = data.map(l => `
            <tr>
              <td>#${l.log_id}</td>
              <td>${l.user_id}</td>
              <td><span class="status-pill neutral">${l.action}</span></td>
              <td><code>${l.table_name}</code></td>
              <td>#${l.record_id}</td>
              <td>${l.ip_address || 'N/A'}</td>
              <td style="color: #64748b;">${l.action_time}</td>
            </tr>
          `).join("");
        }
      }
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #b45309; padding: 16px;">Start backend at http://127.0.0.1:5000 to load audit logs.</td></tr>';
      }
    }
  }

  loadAuditLogs();
});
