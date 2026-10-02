// View: Operations Section (Stock Transactions)
const OperationsView = {
  renderStockTransactions() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Stock Movement Transactions</h2>
              <p>Physical audit log of all incoming stock receipts and outgoing warehouse dispatches</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-record-transaction')">
                ${Icons.plus} Record Stock Transaction
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search transactions..." oninput="App.filterTable(this, 'table-transactions')"/>
            </div>
            <div style="display: flex; gap: 8px;">
              <span class="status-pill active">STOCK_IN: +80 units</span>
              <span class="status-pill cancel">STOCK_OUT: -15 units</span>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-transactions">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Transaction ID</th>
                  <th>Product Details</th>
                  <th>Movement Type</th>
                  <th>Quantity</th>
                  <th>Reference / PO</th>
                  <th>Handled By</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                ${Store.transactions.map(t => {
                  const isIn = t.transaction_type === 'STOCK_IN';
                  return `
                    <tr>
                      <td><input type="checkbox" class="table-checkbox" /></td>
                      <td><code>TRX-#${t.transaction_id}</code></td>
                      <td>
                        <div class="entity-cell">
                          <div class="entity-icon-avatar" style="background: ${isIn ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)'}; color: ${isIn ? '#10b981' : '#ef4444'};">
                            ${isIn ? '↓' : '↑'}
                          </div>
                          <div>
                            <div class="entity-name">${t.product_name}</div>
                            <div class="entity-sub">${t.sku}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span class="status-pill ${isIn ? 'active' : 'cancel'}">
                          ${t.transaction_type}
                        </span>
                      </td>
                      <td>
                        <strong style="font-size: 14px; color: ${isIn ? '#10b981' : '#ef4444'};">
                          ${isIn ? '+' : '-'}${t.quantity} units
                        </strong>
                      </td>
                      <td><span class="status-pill role">${t.po_ref}</span></td>
                      <td><strong>${t.user}</strong></td>
                      <td style="color: #64748b;">${t.date}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.transactions.length} of ${Store.transactions.length} entries</div>
            <div class="pagination-controls">
              <button class="page-btn">${Icons.chevronLeft}</button>
              <button class="page-btn active">1</button>
              <button class="page-btn">${Icons.chevronRight}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }
};

