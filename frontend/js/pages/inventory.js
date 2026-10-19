// inventory.js

App.pages['inventory'] = {
    currentInventory: [],
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 1,
    search: '',
    status: '',
    requestId: 0,

    render() {
        const container = document.createElement('div');
        const user = Auth.getUser();
        const canStockOut = user && ['Owner', 'Manager', 'Employee'].includes(user.role);
        const canAdjust = user && ['Owner', 'Manager'].includes(user.role);
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">WAREHOUSE & STOCK</span>
                    <h1>Inventory Management 📊</h1>
                    <p>Monitor warehouse stock levels, issue outgoing stock, inspect goods receipts, and track complete transaction history.</p>
                </div>
                <div class="header-actions" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <button class="btn secondary" id="btn-transactions" style="display: inline-flex; align-items: center; gap: 6px; padding: 9px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;">
                        <i class='bx bx-history' style="font-size: 16px;"></i> Transaction History
                    </button>
                    ${canStockOut ? `
                        <button class="btn warning" id="btn-stock-out" style="display: inline-flex; align-items: center; gap: 6px; background: #ea580c; color: white; border: none; padding: 9px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer;">
                            <i class='bx bx-upload' style="font-size: 16px;"></i> Stock-Out
                        </button>
                    ` : ''}
                    ${canAdjust ? `
                        <button class="btn primary" id="btn-adjust-stock" style="display: inline-flex; align-items: center; gap: 6px; padding: 9px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;">
                            <i class='bx bx-transfer' style="font-size: 16px;"></i> Adjust Stock
                        </button>
                    ` : ''}
                </div>
            </div>

            <!-- Inventory Metric Stats -->
            <div class="stats-grid" style="margin-top: 20px;">
                <div class="stat-card">
                    <div class="stat-top">
                        <span>Total Tracked Items</span>
                        <div class="stat-icon blue"><i class='bx bx-package'></i></div>
                    </div>
                    <h2 id="stat-total-items">--</h2>
                    <div class="stat-bottom text-muted">Active catalog stock</div>
                </div>
                <div class="stat-card">
                    <div class="stat-top">
                        <span>In Stock</span>
                        <div class="stat-icon green"><i class='bx bx-check-shield'></i></div>
                    </div>
                    <h2 id="stat-in-stock">--</h2>
                    <div class="stat-bottom text-success"><i class='bx bx-check'></i> Healthy inventory</div>
                </div>
                <div class="stat-card">
                    <div class="stat-top">
                        <span>Low Stock Alerts</span>
                        <div class="stat-icon yellow"><i class='bx bx-error'></i></div>
                    </div>
                    <h2 id="stat-low-stock">--</h2>
                    <div class="stat-bottom warning-text"><i class='bx bx-time'></i> Below reorder level</div>
                </div>
                <div class="stat-card">
                    <div class="stat-top">
                        <span>Total Units</span>
                        <div class="stat-icon purple"><i class='bx bx-layer'></i></div>
                    </div>
                    <h2 id="stat-total-units">--</h2>
                    <div class="stat-bottom text-muted">Physical units on hand</div>
                </div>
            </div>

            <!-- Filter and Search Bar -->
            <div class="card" style="margin-top: 24px; padding: 16px; display: flex; gap: 16px; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                <div style="display: flex; gap: 12px; flex: 1; min-width: 280px;">
                    <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border); flex: 1;">
                        <i class='bx bx-search'></i>
                        <input type="text" id="inventory-search" placeholder="Search by SKU, product name..." style="background: transparent;">
                    </div>
                    <select id="inventory-status-filter" class="input" style="max-width: 180px; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px;">
                        <option value="">All Statuses</option>
                        <option value="in_stock">In Stock</option>
                        <option value="low_stock">Low Stock</option>
                        <option value="out_of_stock">Out of Stock</option>
                    </select>
                </div>
                <div>
                    <button class="btn" id="btn-refresh-inventory" style="background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-refresh'></i> Refresh
                    </button>
                </div>
            </div>
            
            <!-- Inventory Table -->
            <div class="card table-responsive" style="margin-top: 20px; overflow: hidden;">
                <table class="table" id="inventory-table">
                    <thead>
                        <tr>
                            <th>SKU</th>
                            <th>PRODUCT NAME</th>
                            <th>CATEGORY</th>
                            <th>AVAILABLE QTY</th>
                            <th>REORDER LEVEL</th>
                            <th>STOCK STATUS</th>
                            <th>LAST UPDATED</th>
                            <th style="text-align: center;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--text-secondary);">Loading inventory...</td></tr>
                    </tbody>
                </table>
                <div id="inventory-pagination-container"></div>
            </div>
        `;
        return container;
    },

    async init() {
        this.page = 1;
        this.search = '';
        this.status = '';
        this.loadInventory();

        const searchInput = document.getElementById('inventory-search');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.page = 1;
                    this.search = e.target.value;
                    this.loadInventory();
                }, 300);
            });
        }

        const filterSelect = document.getElementById('inventory-status-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.page = 1;
                this.status = e.target.value;
                this.loadInventory();
            });
        }

        const refreshBtn = document.getElementById('btn-refresh-inventory');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadInventory();
            });
        }

        const adjustBtn = document.getElementById('btn-adjust-stock');
        if (adjustBtn) {
            adjustBtn.addEventListener('click', () => {
                this.showAdjustModal();
            });
        }

        const stockOutBtn = document.getElementById('btn-stock-out');
        if (stockOutBtn) {
            stockOutBtn.addEventListener('click', () => {
                this.showStockOutModal();
            });
        }

        const txnBtn = document.getElementById('btn-transactions');
        if (txnBtn) {
            txnBtn.addEventListener('click', () => {
                this.showTransactionHistory();
            });
        }
    },

    goToPage(newPage) {
        if (newPage < 1 || newPage > this.totalPages || newPage === this.page) return;
        this.page = newPage;
        this.loadInventory();
    },

    async loadInventory(search = null, status = null) {
        if (search !== null) this.search = search;
        if (status !== null) this.status = status;

        const thisReq = ++this.requestId;
        const tbody = document.querySelector('#inventory-table tbody');
        const paginationContainer = document.getElementById('inventory-pagination-container');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--text-secondary);"><i class='bx bx-loader-alt bx-spin' style='margin-right: 6px; font-size: 16px;'></i> Loading inventory...</td></tr>`;
        }

        try {
            let url = `/inventory/?page=${this.page}&page_size=${this.pageSize}`;
            if (this.search) url += `&search=${encodeURIComponent(this.search)}`;
            if (this.status) url += `&status=${encodeURIComponent(this.status)}`;

            const data = await Api.get(url);
            if (thisReq !== this.requestId) return; // Discard stale response

            const items = data.inventory || [];
            this.currentInventory = items;
            this.total = data.total !== undefined ? data.total : (data.stats ? data.stats.total_items : items.length);
            this.totalPages = data.total_pages || Math.max(1, Math.ceil(this.total / this.pageSize));

            // Update stats
            if (data.stats) {
                const s = data.stats;
                const totEl = document.getElementById('stat-total-items');
                if (totEl) totEl.textContent = s.total_items ?? 0;
                const inEl = document.getElementById('stat-in-stock');
                if (inEl) inEl.textContent = s.in_stock ?? 0;
                const lowEl = document.getElementById('stat-low-stock');
                if (lowEl) lowEl.textContent = s.low_stock ?? 0;
                const unitsEl = document.getElementById('stat-total-units');
                if (unitsEl) unitsEl.textContent = s.total_quantity ?? 0;
            }

            if (items.length === 0) {
                if (tbody) {
                    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 28px; color: var(--text-secondary);">${Utils.emptyState('bx-package', 'No Inventory Items', 'No inventory items match your current filter or search criteria.')}</td></tr>`;
                }
                if (paginationContainer) paginationContainer.innerHTML = '';
                return;
            }

            const user = Auth.getUser();
            const canStockOut = user && ['Owner', 'Manager', 'Employee'].includes(user.role);
            const canAdjust = user && ['Owner', 'Manager'].includes(user.role);

            if (tbody) {
                tbody.innerHTML = items.map(item => {
                    let badgeClass = 'status-active';
                    if (item.stock_status === 'Low Stock') badgeClass = 'status-pending';
                    if (item.stock_status === 'Out of Stock') badgeClass = 'status-inactive';

                    const formattedDate = item.last_updated ? new Date(item.last_updated).toLocaleString() : 'N/A';

                    return `
                        <tr>
                            <td><strong>${Utils.escapeHtml(item.sku)}</strong></td>
                            <td>${Utils.escapeHtml(item.product_name)}</td>
                            <td><span class="badge" style="background: #e0e0e0; color: #333;">${Utils.escapeHtml(item.category_name || 'N/A')}</span></td>
                            <td><strong style="font-size: 15px; color: ${item.quantity_available <= item.reorder_level ? 'var(--red)' : 'var(--text)'};">${item.quantity_available}</strong></td>
                            <td>${item.reorder_level}</td>
                            <td>
                                <span class="status-badge ${badgeClass}">
                                    ${item.stock_status}
                                </span>
                            </td>
                            <td style="font-size: 12px; color: var(--text-secondary);">${formattedDate}</td>
                            <td style="text-align: center;">
                                <div style="display: inline-flex; gap: 6px; align-items: center; justify-content: center;">
                                    ${canStockOut ? `
                                        <button class="btn-icon" onclick="App.pages['inventory'].showStockOutModal(${item.product_id})" title="Stock-Out / Issue Stock"
                                                style="background: white; border: 1px solid #fed7aa; color: #ea580c; border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 14px;">
                                            <i class='bx bx-upload'></i>
                                        </button>
                                    ` : ''}
                                    <button class="btn-icon" onclick="App.pages['inventory'].showTransactionHistory(${item.product_id})" title="Transaction History"
                                            style="background: white; border: 1px solid var(--border); color: #4b5563; border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 14px;">
                                        <i class='bx bx-history'></i>
                                    </button>
                                    ${canAdjust ? `
                                        <button class="btn-icon" onclick="App.pages['inventory'].showAdjustModal(${item.inventory_id})" title="Adjust Stock"
                                                style="background: white; border: 1px solid var(--border); color: var(--primary); border-radius: 6px; padding: 4px 8px; cursor: pointer; font-size: 14px;">
                                            <i class='bx bx-transfer'></i>
                                        </button>
                                    ` : ''}
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            // Render pagination controls
            if (paginationContainer && window.PaginationComponent) {
                paginationContainer.innerHTML = PaginationComponent.render({
                    total: this.total,
                    page: this.page,
                    pageSize: this.pageSize,
                    totalPages: this.totalPages,
                    label: 'items',
                    onPageChangeName: "App.pages['inventory'].goToPage"
                });
            }

        } catch (error) {
            if (thisReq !== this.requestId) return;
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="8" class="text-danger" style="text-align: center; padding: 24px;">Failed to load inventory: ${Utils.escapeHtml(error.message || 'Error')}</td></tr>`;
            }
            if (paginationContainer) paginationContainer.innerHTML = '';
        }
    },

    // Stock-Out Modal (Step 6 Outgoing Stock)
    async showStockOutModal(productId = null) {
        let item = null;
        if (productId) {
            item = this.currentInventory.find(i => i.product_id === productId);
            if (!item) {
                try {
                    const data = await Api.get('/inventory/');
                    const allInv = data.inventory || [];
                    item = allInv.find(i => i.product_id === productId);
                } catch (e) {
                    console.error(e);
                }
            }
        }

        const modalHtml = `
            <div style="display: flex; flex-direction: column; gap: 14px;">
                ${item ? `
                    <div style="background: rgba(234, 88, 12, 0.06); border: 1px solid rgba(234, 88, 12, 0.25); padding: 14px; border-radius: 8px;">
                        <div style="font-weight: 700; font-size: 15px; color: #9a3412;">${Utils.escapeHtml(item.product_name)}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">SKU: <strong>${Utils.escapeHtml(item.sku)}</strong> • Category: ${Utils.escapeHtml(item.category_name || 'N/A')}</div>
                        <div style="margin-top: 8px; font-size: 13px;">
                            Current Available Stock: <strong id="stockout-current-avail" style="color: #ea580c; font-size: 16px;">${item.quantity_available}</strong> units
                        </div>
                    </div>
                ` : `
                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SELECT PRODUCT *</label>
                        <select id="modal-stockout-prod-select" class="input" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;" required>
                            <option value="">-- Choose inventory item --</option>
                            ${this.currentInventory.map(i => `
                                <option value="${i.product_id}" data-avail="${i.quantity_available}">
                                    ${Utils.escapeHtml(i.product_name)} (${Utils.escapeHtml(i.sku)}) — Avail: ${i.quantity_available}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                `}

                <div>
                    <label style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">
                        <span>QUANTITY TO STOCK-OUT *</span>
                        <span id="stockout-max-hint" style="color: #ea580c; font-weight: 600;">Max available: ${item ? item.quantity_available : 0} units</span>
                    </label>
                    <input type="number" id="modal-stockout-qty" class="input" min="1" max="${item ? item.quantity_available : 999999}" value="1" 
                           style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 14px; font-weight: 600;" required>
                    <small style="color: var(--text-secondary); font-size: 11px; margin-top: 4px; display: block;">
                        Inventory will decrease immediately and a STOCK_OUT transaction will be recorded atomically.
                    </small>
                </div>

                <div>
                    <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">DISPATCH / ISSUE REASON *</label>
                    <select id="modal-stockout-reason" class="input" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;" required>
                        <option value="Issued for production">Issued for production</option>
                        <option value="Customer order fulfillment">Customer order fulfillment</option>
                        <option value="Internal consumption / testing">Internal consumption / testing</option>
                        <option value="Damaged / expired stock write-off">Damaged / expired stock write-off</option>
                        <option value="Physical count reconciliation">Physical count reconciliation</option>
                        <option value="Other">Other</option>
                    </select>
                </div>

                <div>
                    <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">AUDIT NOTES</label>
                    <textarea id="modal-stockout-notes" rows="2" placeholder="e.g. Work order WO-409, batch verification complete..." 
                              style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;"></textarea>
                </div>
            </div>
        `;

        Modal.show({
            title: item ? `Stock-Out: ${Utils.escapeHtml(item.product_name)} 📤` : 'Stock-Out / Issue Inventory 📤',
            content: modalHtml,
            saveText: 'Confirm Stock-Out',
            onSave: async (container) => {
                const prodSelect = container.querySelector('#modal-stockout-prod-select');
                const targetPid = item ? item.product_id : parseInt(prodSelect?.value || '0');
                const qtyVal = container.querySelector('#modal-stockout-qty').value;
                const reason = container.querySelector('#modal-stockout-reason').value;
                const notes = container.querySelector('#modal-stockout-notes').value;

                if (!targetPid) {
                    throw new Error('Please select a product.');
                }

                if (!qtyVal || isNaN(qtyVal) || parseInt(qtyVal) <= 0) {
                    throw new Error('Please enter a positive numeric quantity.');
                }

                const qty = parseInt(qtyVal);

                await Api.post('/inventory/stock-out', {
                    product_id: targetPid,
                    quantity: qty,
                    reason: reason,
                    notes: notes ? notes.trim() : ''
                });

                Utils.showToast(`Successfully issued ${qty} units from inventory!`, 'success');
                this.loadInventory(document.getElementById('inventory-search')?.value, document.getElementById('inventory-status-filter')?.value);
            }
        });

        // If product dropdown is visible, update max hint dynamically
        setTimeout(() => {
            const prodSelect = document.getElementById('modal-stockout-prod-select');
            const qtyInput = document.getElementById('modal-stockout-qty');
            const maxHint = document.getElementById('stockout-max-hint');
            if (prodSelect && qtyInput) {
                prodSelect.addEventListener('change', () => {
                    const opt = prodSelect.options[prodSelect.selectedIndex];
                    const avail = parseInt(opt.getAttribute('data-avail') || '0');
                    qtyInput.max = avail;
                    if (maxHint) maxHint.textContent = `Max available: ${avail} units`;
                });
            }
        }, 50);
    },

    // Transaction History Modal (Step 6 Audit Trail)
    async showTransactionHistory(productId = null) {
        try {
            let url = '/inventory/transactions';
            if (productId) url += `?product_id=${productId}`;

            const data = await Api.get(url);
            const transactions = data.transactions || [];

            const renderRows = (txns) => {
                if (txns.length === 0) {
                    return `<tr><td colspan="7" style="text-align: center; padding: 30px; color: var(--text-secondary);">No stock transactions found matching criteria.</td></tr>`;
                }

                return txns.map(t => {
                    const isStockIn = t.transaction_type === 'STOCK_IN';
                    const typeBadge = isStockIn 
                        ? `<span style="padding: 2px 8px; border-radius: 4px; background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; font-weight: 700;"><i class='bx bx-down-arrow-alt'></i> STOCK_IN</span>`
                        : `<span style="padding: 2px 8px; border-radius: 4px; background: rgba(234, 88, 12, 0.12); color: #ea580c; font-size: 11px; font-weight: 700;"><i class='bx bx-up-arrow-alt'></i> STOCK_OUT</span>`;

                    const qtyDisplay = isStockIn 
                        ? `<strong style="color: #059669; font-size: 13px;">+${t.quantity}</strong>`
                        : `<strong style="color: #ea580c; font-size: 13px;">-${t.quantity}</strong>`;

                    let refInfo = '-';
                    if (t.shipment_number) {
                        refInfo = `<span style="font-weight: 600; color: #2563eb;">${Utils.escapeHtml(t.shipment_number)}</span>`;
                        if (t.purchase_order_id) refInfo += ` <span style="font-size: 11px; color: var(--text-secondary);">(PO #${t.purchase_order_id})</span>`;
                    } else if (t.notes) {
                        refInfo = `<span style="font-size: 12px; color: var(--text-secondary);">${Utils.escapeHtml(t.notes.substring(0, 30))}</span>`;
                    }

                    const dt = t.transaction_date ? new Date(t.transaction_date).toLocaleString() : 'N/A';

                    return `
                        <tr style="border-bottom: 1px solid var(--border); font-size: 12px;">
                            <td style="padding: 10px 12px; font-family: monospace; color: var(--text-secondary);">#TXN-${t.transaction_id}</td>
                            <td style="padding: 10px 12px;">
                                <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(t.product_name)}</div>
                                <div style="font-size: 11px; color: var(--text-secondary); font-family: monospace;">${Utils.escapeHtml(t.sku || '')}</div>
                            </td>
                            <td style="padding: 10px 12px;">${typeBadge}</td>
                            <td style="padding: 10px 12px; text-align: right;">${qtyDisplay}</td>
                            <td style="padding: 10px 12px;">${refInfo}</td>
                            <td style="padding: 10px 12px;">
                                <div style="font-weight: 500; color: var(--text);">${Utils.escapeHtml(t.user_name || 'System')}</div>
                                <div style="font-size: 10px; color: var(--text-secondary);">${Utils.escapeHtml(t.user_role || '')}</div>
                            </td>
                            <td style="padding: 10px 12px; color: var(--text-secondary); font-size: 11px;">${dt}</td>
                        </tr>
                    `;
                }).join('');
            };

            const content = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <!-- Filter Controls -->
                    <div style="display: flex; gap: 10px; align-items: center; justify-content: space-between; flex-wrap: wrap;">
                        <div style="display: flex; gap: 10px; align-items: center; flex: 1;">
                            <select id="modal-tx-type-filter" style="padding: 7px 10px; border-radius: 6px; border: 1px solid var(--border); font-size: 12px;">
                                <option value="">All Transaction Types</option>
                                <option value="STOCK_IN">STOCK_IN (Goods Receipt)</option>
                                <option value="STOCK_OUT">STOCK_OUT (Dispatched/Issued)</option>
                            </select>
                            <input type="text" id="modal-tx-search" placeholder="Search product, SKU, shipment..." 
                                   style="padding: 7px 10px; border-radius: 6px; border: 1px solid var(--border); font-size: 12px; flex: 1; max-width: 260px;">
                        </div>
                        <span id="modal-tx-count" style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">
                            ${transactions.length} record${transactions.length === 1 ? '' : 's'}
                        </span>
                    </div>

                    <!-- Scrollable Transactions Table -->
                    <div style="border-radius: 8px; border: 1px solid var(--border); max-height: 400px; overflow-y: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left;">
                            <thead style="position: sticky; top: 0; background: var(--bg-surface, #f9fafb); z-index: 1;">
                                <tr style="border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 10px 12px;">ID</th>
                                    <th style="padding: 10px 12px;">Product</th>
                                    <th style="padding: 10px 12px;">Type</th>
                                    <th style="padding: 10px 12px; text-align: right;">Quantity</th>
                                    <th style="padding: 10px 12px;">Reference</th>
                                    <th style="padding: 10px 12px;">Performed By</th>
                                    <th style="padding: 10px 12px;">Date &amp; Time</th>
                                </tr>
                            </thead>
                            <tbody id="modal-tx-tbody">
                                ${renderRows(transactions)}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            Modal.create({
                id: 'modal-stock-transactions',
                title: 'Inventory Stock Movement History 📋',
                content,
                footer: `<div style="display: flex; justify-content: flex-end; width: 100%;"><button class="btn btn-outline close-tx-btn">Close</button></div>`,
                onOpen: (overlay, closeModal) => {
                    overlay.querySelector('.close-tx-btn').onclick = closeModal;

                    const typeSelect = overlay.querySelector('#modal-tx-type-filter');
                    const searchInput = overlay.querySelector('#modal-tx-search');
                    const tbody = overlay.querySelector('#modal-tx-tbody');
                    const countSpan = overlay.querySelector('#modal-tx-count');

                    const applyFilters = () => {
                        const typeVal = typeSelect.value;
                        const query = (searchInput.value || '').toLowerCase().trim();

                        const filtered = transactions.filter(t => {
                            if (typeVal && t.transaction_type !== typeVal) return false;
                            if (query) {
                                const hay = `${t.product_name} ${t.sku} ${t.shipment_number || ''} ${t.notes || ''} ${t.user_name || ''}`.toLowerCase();
                                if (!hay.includes(query)) return false;
                            }
                            return true;
                        });

                        tbody.innerHTML = renderRows(filtered);
                        countSpan.textContent = `${filtered.length} record${filtered.length === 1 ? '' : 's'}`;
                    };

                    typeSelect.onchange = applyFilters;
                    searchInput.oninput = applyFilters;
                }
            });

        } catch (err) {
            alert(`Error loading transaction history: ${err.message}`);
        }
    },

    async showAdjustModal(inventoryId = null) {
        let item = null;
        let allItems = this.currentInventory || [];
        if (allItems.length === 0 || (inventoryId && !allItems.find(i => i.inventory_id === inventoryId))) {
            try {
                const data = await Api.get('/inventory/?page=1&page_size=100');
                allItems = data.inventory || [];
                this.currentInventory = allItems;
            } catch (err) {
                console.error(err);
            }
        }

        if (inventoryId) {
            item = allItems.find(i => i.inventory_id === inventoryId);
            if (!item) {
                try {
                    const data = await Api.get(`/inventory/${inventoryId}`);
                    item = data.inventory;
                } catch (err) {
                    Utils.showToast("Failed to load inventory record", "error");
                    return;
                }
            }
        }

        const initialStock = item ? item.quantity_available : 0;

        const modalHtml = `
            <div style="display: flex; flex-direction: column; gap: 4px;">
                ${!item ? `
                    <div class="form-group">
                        <label for="modal-adjust-item">SELECT PRODUCT TO ADJUST *</label>
                        <select id="modal-adjust-item" class="input" required>
                            <option value="">-- Choose inventory item --</option>
                            ${allItems.map(i => `
                                <option value="${i.inventory_id}" data-current="${i.quantity_available}" data-sku="${Utils.escapeHtml(i.sku)}" data-name="${Utils.escapeHtml(i.product_name)}" data-cat="${Utils.escapeHtml(i.category_name || 'N/A')}">
                                    ${Utils.escapeHtml(i.product_name)} (${Utils.escapeHtml(i.sku)}) — Stock: ${i.quantity_available}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                    <div class="adjust-stock-product-card" id="adjust-product-summary" style="display: none;">
                        <div class="card-title" id="adjust-summary-name"></div>
                        <div class="card-meta">
                            <span>SKU: <strong id="adjust-summary-sku" style="color: var(--text);"></strong></span>
                            <span>•</span>
                            <span>Category: <strong id="adjust-summary-cat" style="color: var(--text);"></strong></span>
                            <span>•</span>
                            <span>Current Stock: <strong id="adjust-current-stock-display" style="color: var(--primary); font-size: 14px;">0 units</strong></span>
                        </div>
                    </div>
                ` : `
                    <div class="adjust-stock-product-card" id="adjust-product-summary">
                        <div class="card-title">${Utils.escapeHtml(item.product_name)}</div>
                        <div class="card-meta">
                            <span>SKU: <strong style="color: var(--text);">${Utils.escapeHtml(item.sku)}</strong></span>
                            <span>•</span>
                            <span>Category: <strong style="color: var(--text);">${Utils.escapeHtml(item.category_name || 'N/A')}</strong></span>
                            <span>•</span>
                            <span>Current Stock: <strong id="adjust-current-stock-display" style="color: var(--primary); font-size: 14px;">${item.quantity_available} units</strong></span>
                        </div>
                    </div>
                `}

                <div class="form-group">
                    <label>ADJUSTMENT TYPE *</label>
                    <div class="adjust-type-toggle" id="adjust-type-buttons">
                        <button type="button" class="adjust-type-btn active" data-type="SET">
                            <i class='bx bx-check-double'></i> Set Exact Count
                        </button>
                        <button type="button" class="adjust-type-btn" data-type="ADD">
                            <i class='bx bx-plus-circle'></i> Add Stock (+)
                        </button>
                        <button type="button" class="adjust-type-btn" data-type="SUBTRACT">
                            <i class='bx bx-minus-circle'></i> Reduce Stock (-)
                        </button>
                    </div>
                    <input type="hidden" id="modal-adjust-type" value="SET">
                </div>

                <div class="form-group">
                    <label for="modal-adjust-qty">
                        <span id="adjust-qty-label">NEW PHYSICAL COUNT *</span>
                        <span style="font-size: 11px; font-weight: normal; color: var(--text-secondary);">Whole units &gt;= 0</span>
                    </label>
                    <input type="number" id="modal-adjust-qty" class="input" min="0" step="1" value="${initialStock}" required placeholder="Enter count">

                    <div class="adjust-calc-preview" id="adjust-calc-box">
                        <div style="font-size: 12.5px; color: var(--text);">
                            Current: <strong id="calc-current-val">${initialStock}</strong>
                            <span id="calc-symbol" style="margin: 0 4px; color: var(--text-secondary);">&rarr;</span>
                            Delta: <strong id="calc-delta-val">0</strong>
                        </div>
                        <div style="font-size: 13.5px; font-weight: 700;">
                            Resulting Stock: <span id="calc-result-val" style="color: var(--primary);">${initialStock} units</span>
                        </div>
                    </div>
                    <div id="adjust-error-alert" style="display: none; color: var(--danger, #ef4444); font-size: 12px; margin-top: 6px; font-weight: 600;">
                        <i class='bx bx-error-circle'></i> <span id="adjust-error-msg"></span>
                    </div>
                </div>

                <div class="form-group">
                    <label for="modal-adjust-reason">REASON FOR ADJUSTMENT *</label>
                    <select id="modal-adjust-reason" class="input" required>
                        <option value="Physical inventory count reconciliation">Physical inventory count reconciliation</option>
                        <option value="Damaged / expired stock write-off">Damaged / expired stock write-off</option>
                        <option value="Surplus / unrecorded stock found">Surplus / unrecorded stock found</option>
                        <option value="Customer return / Restock">Customer return / Restock</option>
                        <option value="Data entry correction">Data entry correction</option>
                        <option value="Internal warehouse movement">Internal warehouse movement</option>
                        <option value="Other">Other</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="modal-adjust-notes">AUDIT REMARKS / NOTES (OPTIONAL)</label>
                    <textarea id="modal-adjust-notes" class="input" rows="2" placeholder="e.g. Verified by warehouse supervisor during cycle count..."></textarea>
                    <small style="color: var(--text-secondary); font-size: 11.5px;">
                        Adjustments will update inventory stock and automatically generate a STOCK_IN / STOCK_OUT audit transaction record.
                    </small>
                </div>
            </div>
        `;

        Modal.show({
            title: item ? `Adjust Stock — ${Utils.escapeHtml(item.product_name)} ⚖️` : 'Adjust Inventory Stock ⚖️',
            content: modalHtml,
            saveText: 'Confirm Adjustment',
            onSave: async (container) => {
                const itemSelect = container.querySelector('#modal-adjust-item');
                const targetInvId = item ? item.inventory_id : parseInt(itemSelect?.value || '0');
                const type = container.querySelector('#modal-adjust-type')?.value || 'SET';
                const qtyVal = container.querySelector('#modal-adjust-qty')?.value;
                const reason = container.querySelector('#modal-adjust-reason')?.value || 'Stock Adjustment';
                const notes = container.querySelector('#modal-adjust-notes')?.value?.trim() || '';

                if (!targetInvId) {
                    throw new Error("Please select an inventory item to adjust.");
                }

                if (qtyVal === '' || isNaN(qtyVal) || parseInt(qtyVal) < 0) {
                    throw new Error("Please enter a valid non-negative integer quantity.");
                }

                const currentStockVal = parseInt(container.querySelector('#calc-current-val')?.textContent || '0');
                const enteredQty = parseInt(qtyVal);
                let resultingQty = enteredQty;

                if (type === 'ADD') {
                    resultingQty = currentStockVal + enteredQty;
                } else if (type === 'SUBTRACT') {
                    resultingQty = currentStockVal - enteredQty;
                }

                if (resultingQty < 0) {
                    throw new Error(`Inventory stock cannot be negative. Resulting quantity would be ${resultingQty} units.`);
                }

                const combinedNotes = notes ? `${reason} — ${notes}` : reason;

                await Api.put(`/inventory/${targetInvId}`, {
                    quantity_available: resultingQty,
                    notes: combinedNotes
                });

                Utils.showToast(`Stock updated to ${resultingQty} units successfully!`, "success");
                this.loadInventory(
                    document.getElementById('inventory-search')?.value,
                    document.getElementById('inventory-status-filter')?.value
                );
            }
        });

        // Initialize dynamic calculations and listeners after modal renders
        setTimeout(() => {
            const itemSelect = document.getElementById('modal-adjust-item');
            const summaryCard = document.getElementById('adjust-product-summary');
            const summaryName = document.getElementById('adjust-summary-name');
            const summarySku = document.getElementById('adjust-summary-sku');
            const summaryCat = document.getElementById('adjust-summary-cat');
            const currentStockDisplay = document.getElementById('adjust-current-stock-display');
            const currentValEl = document.getElementById('calc-current-val');
            const deltaValEl = document.getElementById('calc-delta-val');
            const resultValEl = document.getElementById('calc-result-val');
            const qtyInput = document.getElementById('modal-adjust-qty');
            const qtyLabel = document.getElementById('adjust-qty-label');
            const typeInput = document.getElementById('modal-adjust-type');
            const typeBtns = document.querySelectorAll('#adjust-type-buttons .adjust-type-btn');
            const calcBox = document.getElementById('adjust-calc-box');
            const errAlert = document.getElementById('adjust-error-alert');
            const errMsg = document.getElementById('adjust-error-msg');

            const recalculate = () => {
                let currentStock = item ? item.quantity_available : 0;
                if (!item && itemSelect) {
                    const opt = itemSelect.options[itemSelect.selectedIndex];
                    if (opt && opt.value) {
                        currentStock = parseInt(opt.getAttribute('data-current') || '0');
                        if (summaryCard) summaryCard.style.display = 'block';
                        if (summaryName) summaryName.textContent = opt.getAttribute('data-name') || '';
                        if (summarySku) summarySku.textContent = opt.getAttribute('data-sku') || '';
                        if (summaryCat) summaryCat.textContent = opt.getAttribute('data-cat') || '';
                        if (currentStockDisplay) currentStockDisplay.textContent = `${currentStock} units`;
                    } else {
                        if (summaryCard) summaryCard.style.display = 'none';
                    }
                }

                if (currentValEl) currentValEl.textContent = currentStock;

                const type = typeInput ? typeInput.value : 'SET';
                const enteredVal = parseInt(qtyInput?.value || '0');
                const validEntered = isNaN(enteredVal) ? 0 : Math.max(0, enteredVal);

                let delta = 0;
                let resulting = currentStock;

                if (type === 'SET') {
                    delta = validEntered - currentStock;
                    resulting = validEntered;
                } else if (type === 'ADD') {
                    delta = validEntered;
                    resulting = currentStock + validEntered;
                } else if (type === 'SUBTRACT') {
                    delta = -validEntered;
                    resulting = currentStock - validEntered;
                }

                if (deltaValEl) {
                    deltaValEl.textContent = delta >= 0 ? `+${delta}` : `${delta}`;
                }

                if (resultValEl) {
                    resultValEl.textContent = `${resulting} units`;
                }

                if (resulting < 0) {
                    if (calcBox) calcBox.classList.add('error');
                    if (errAlert && errMsg) {
                        errAlert.style.display = 'block';
                        errMsg.textContent = `Resulting stock cannot be negative (would be ${resulting} units).`;
                    }
                    if (resultValEl) resultValEl.style.color = 'var(--danger, #ef4444)';
                } else {
                    if (calcBox) calcBox.classList.remove('error');
                    if (errAlert) errAlert.style.display = 'none';
                    if (resultValEl) resultValEl.style.color = 'var(--primary, #078f72)';
                }
            };

            typeBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    typeBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const selectedType = btn.getAttribute('data-type');
                    if (typeInput) typeInput.value = selectedType;

                    if (qtyLabel) {
                        if (selectedType === 'SET') {
                            qtyLabel.textContent = 'NEW PHYSICAL COUNT *';
                            if (qtyInput) qtyInput.placeholder = 'Enter new total count';
                        } else if (selectedType === 'ADD') {
                            qtyLabel.textContent = 'QUANTITY TO ADD (+) *';
                            if (qtyInput) qtyInput.placeholder = 'e.g. 50';
                        } else if (selectedType === 'SUBTRACT') {
                            qtyLabel.textContent = 'QUANTITY TO REDUCE (-) *';
                            if (qtyInput) qtyInput.placeholder = 'e.g. 10';
                        }
                    }

                    recalculate();
                });
            });

            if (itemSelect) itemSelect.addEventListener('change', recalculate);
            if (qtyInput) {
                qtyInput.addEventListener('input', recalculate);
                qtyInput.addEventListener('change', recalculate);
            }

            recalculate();
        }, 50);
    }
};

