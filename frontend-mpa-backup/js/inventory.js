// Page Behavior: Dashboard
document.addEventListener("DOMContentLoaded", async () => {
  const stockEl = document.getElementById("metric-stock");
  const prodEl = document.getElementById("metric-products");
  const stockInEl = document.getElementById("metric-stock-in");
  const lowStockEl = document.getElementById("metric-low-stock");
  const lowStockTbody = document.getElementById("dash-low-stock-tbody");

  async function loadDashboardMetrics() {
    try {
      const data = await API.request("/api/dashboard/employee");
      if (data) {
        if (stockEl) stockEl.textContent = data.total_stock !== undefined ? data.total_stock.toLocaleString() : "--";
        if (prodEl) prodEl.textContent = data.total_products !== undefined ? data.total_products : "--";
        if (stockInEl) stockInEl.textContent = data.stock_in !== undefined ? data.stock_in : "--";
        if (lowStockEl) lowStockEl.textContent = data.low_stock_products ? data.low_stock_products.length : 0;

        if (lowStockTbody && data.low_stock_products) {
          if (data.low_stock_products.length === 0) {
            lowStockTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #10b981; padding: 16px;">Zero low-stock items! All stock levels healthy.</td></tr>';
          } else {
            lowStockTbody.innerHTML = data.low_stock_products.map(item => `
              <tr>
                <td>#${item.product_id}</td>
                <td><strong>${item.product_name}</strong></td>
                <td><strong style="color: #ef4444;">${item.quantity_available} units</strong></td>
                <td><span class="status-pill warning">LOW STOCK</span></td>
              </tr>
            `).join("");
          }
        }
      }
    } catch (err) {
      console.warn("Could not reach /api/dashboard/employee. Showing offline indicators.");
      if (lowStockTbody) {
        lowStockTbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #b45309; padding: 16px;">Backend offline or token required. Start backend server at http://127.0.0.1:5000</td></tr>';
      }
    }
  }

  loadDashboardMetrics();

  const refreshBtn = document.getElementById("btn-refresh-dash");
  if (refreshBtn) refreshBtn.addEventListener("click", loadDashboardMetrics);
});
