// View: Procurement Section (Suppliers, Purchase Orders, Quotations)
const ProcurementView = {
  // 1. Suppliers View
  renderSuppliers() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Supplier Directory</h2>
              <p>Maintain vendor profiles, contact representatives, and procurement contracts</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-add-supplier')">
                ${Icons.plus} Add New Supplier
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search suppliers..." oninput="App.filterTable(this, 'table-suppliers')"/>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-suppliers">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Supplier Name</th>
                  <th>Contact Person</th>
                  <th>Work Phone</th>
                  <th>Email Address</th>
                  <th>Total Orders</th>
                  <th>Status</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${Store.suppliers.map(s => `
                  <tr>
                    <td><input type="checkbox" class="table-checkbox" /></td>
                    <td>
                      <div class="entity-cell">
                        <div class="entity-icon-avatar" style="background: rgba(59, 130, 246, 0.12); color: #2563eb;">${s.supplier_name.charAt(0)}</div>
                        <div class="entity-name">${s.supplier_name}</div>
                      </div>
                    </td>
                    <td><strong>${s.contact_person}</strong></td>
                    <td>${s.phone}</td>
                    <td><a href="mailto:${s.email}" style="color: #2563eb; text-decoration: none;">${s.email}</a></td>
                    <td><span class="status-pill role">${s.total_orders || 1} Orders</span></td>
                    <td><span class="status-pill active">${s.status}</span></td>
                    <td style="text-align: right;">
                      <div class="table-actions" style="justify-content: flex-end;">
                        <button class="action-icon-btn" title="Edit">${Icons.edit}</button>
                        <button class="action-icon-btn danger" title="Delete" onclick="App.deleteSupplier(${s.supplier_id})">${Icons.trash}</button>
                      </div>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.suppliers.length} of ${Store.suppliers.length} entries</div>
            <div class="pagination-controls">
              <button class="page-btn">${Icons.chevronLeft}</button>
              <button class="page-btn active">1</button>
              <button class="page-btn">${Icons.chevronRight}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  // 2. Purchase Orders View
  renderPurchaseOrders() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Purchase Orders (PO)</h2>
              <p>Track purchase order approval flows, deliveries, and fulfillment state</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-create-po')">
                ${Icons.plus} Create Purchase Order
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search purchase orders..." oninput="App.filterTable(this, 'table-pos')"/>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-pos">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>PO Reference</th>
                  <th>Supplier</th>
                  <th>Order Date</th>
                  <th>Expected Delivery</th>
                  <th>Ordered By</th>
                  <th>Total Amount</th>
                  <th>Status</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${Store.purchaseOrders.map(po => {
                  const statusClass = po.status.toLowerCase();
                  return `
                    <tr>
                      <td><input type="checkbox" class="table-checkbox" /></td>
                      <td><code>${po.po_number || 'PO-2026-00' + po.purchase_order_id}</code></td>
                      <td><strong>${po.supplier_name}</strong></td>
                      <td>${po.order_date}</td>
                      <td>${po.expected_delivery}</td>
                      <td><span class="status-pill role">${po.ordered_by}</span></td>
                      <td><strong style="font-size: 14px;">₹${Number(po.total_amount).toLocaleString()}</strong></td>
                      <td><span class="status-pill ${statusClass}">${po.status}</span></td>
                      <td style="text-align: right;">
                        <div class="table-actions" style="justify-content: flex-end;">
                          <button class="action-icon-btn" title="View Details">${Icons.search}</button>
                          <button class="action-icon-btn" title="Download">${Icons.download}</button>
                        </div>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.purchaseOrders.length} of ${Store.purchaseOrders.length} entries</div>
            <div class="pagination-controls">
              <button class="page-btn">${Icons.chevronLeft}</button>
              <button class="page-btn active">1</button>
              <button class="page-btn">${Icons.chevronRight}</button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  // 3. Quotations View
  renderQuotations() {
    return `
      <div class="view-section">
        <div class="action-card">
          <div class="action-header">
            <div class="action-title-group">
              <h2>Supplier Quotations</h2>
              <p>Review supplier quotation bids, unit pricing, validity dates, and approve bids</p>
            </div>
            <div class="action-controls">
              <button class="btn-primary" onclick="App.openModal('modal-add-quotation')">
                ${Icons.plus} Submit Quotation
              </button>
            </div>
          </div>

          <div class="filter-bar">
            <div class="search-wrapper">
              <span class="search-icon-left">${Icons.search}</span>
              <input type="text" class="table-search-input" placeholder="Search quotations..." oninput="App.filterTable(this, 'table-quotes')"/>
            </div>
          </div>

          <div class="data-table-container">
            <table class="sims-table" id="table-quotes">
              <thead>
                <tr>
                  <th style="width: 40px;"><input type="checkbox" class="table-checkbox" /></th>
                  <th>Quotation ID</th>
                  <th>Supplier</th>
                  <th>Target Product</th>
                  <th>Quoted Unit Price</th>
                  <th>Quantity</th>
                  <th>Valid Until</th>
                  <th>Status</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${Store.quotations.map(q => {
                  const statusClass = q.status.toLowerCase();
                  return `
                    <tr>
                      <td><input type="checkbox" class="table-checkbox" /></td>
                      <td><code>QUOTE-#${q.quotation_id}</code></td>
                      <td><strong>${q.supplier_name}</strong></td>
                      <td>${q.product_name}</td>
                      <td><strong>₹${Number(q.quoted_price).toFixed(2)}</strong></td>
                      <td>${q.quantity} units</td>
                      <td>${q.valid_until}</td>
                      <td><span class="status-pill ${statusClass}">${q.status}</span></td>
                      <td style="text-align: right;">
                        <div class="table-actions" style="justify-content: flex-end;">
                          ${q.status === 'Pending' ? `
                            <button class="btn-primary" style="padding: 3px 10px; font-size: 11px;" onclick="App.approveQuotation(${q.quotation_id})">Approve</button>
                          ` : `<span class="status-pill completed">Processed</span>`}
                        </div>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>

          <div class="pagination-bar">
            <div class="pagination-info">Showing 1 to ${Store.quotations.length} of ${Store.quotations.length} entries</div>
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

