// Page Behavior: Reports
document.addEventListener("DOMContentLoaded", async () => {
  const tbody = document.getElementById("reports-tbody");
  const genBtn = document.getElementById("btn-gen-report");

  async function loadReports() {
    try {
      const data = await API.request("/api/reports/");
      if (data && tbody) {
        if (data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 16px;">No reports generated yet.</td></tr>';
        } else {
          tbody.innerHTML = data.map(r => `
            <tr>
              <td>#${r.report_id}</td>
              <td><strong>${r.report_name}</strong></td>
              <td><span class="status-pill neutral">${r.report_type}</span></td>
              <td>${r.generated_by}</td>
              <td style="color: #64748b;">${r.generated_on}</td>
            </tr>
          `).join("");
        }
      }
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #b45309; padding: 16px;">Start backend at http://127.0.0.1:5000 to view reports.</td></tr>';
      }
    }
  }

  if (genBtn) {
    genBtn.addEventListener("click", async () => {
      try {
        const res = await API.request("/api/reports/generate", {
          method: "POST",
          body: JSON.stringify({ report_name: "Inventory Report " + new Date().toLocaleDateString(), report_type: "Inventory", generated_by: 1 })
        });
        alert("Report generated successfully!");
        loadReports();
      } catch (err) {
        alert("Report generation failed: " + err.message);
      }
    });
  }

  loadReports();
});
