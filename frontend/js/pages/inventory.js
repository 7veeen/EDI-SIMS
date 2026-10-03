// inventory.js

App.pages['inventory'] = {
    currentInventory: [],

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
            <div class="card table-responsive" style="margin-top: 20px;">
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
            </div>
        `;
        return container;
    },

    async init() {
        this.loadInventory();

        const searchInput = document.getElementById('inventory-search');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.loadInventory(e.target.value, document.getElementById('inventory-status-filter')?.value);
                }, 300);
            });
        }

        const filterSelect = document.getElementById('inventory-status-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.loadInventory(document.getElementById('inventory-search')?.value, e.target.value);
            });
        }

        const refreshBtn = document.getElementById('btn-refresh-inventory');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadInventory(document.getElementById('inventory-search')?.value, document.getElementById('inventory-status-filter')?.value);
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

    async loadInventory(search = '', status = '') {
        const tbody = document.querySelector('#inventory-table tbody');
        try {
            let url = '/inventory/?';
            if (search) url += `search=${encodeURIComponent(search)}&`;
            if (status) url += `status=${encodeURIComponent(status)}&`;

            const data = await Api.get(url);
            const items = data.inventory || [];
            this.currentInventory = items;

            // Update stats
            if (data.stats) {
                document.getElementById('stat-total-items').textContent = data.stats.total_items ?? 0;
                document.getElementById('stat-in-stock').textContent = data.stats.in_stock ?? 0;
                document.getElementById('stat-low-stock').textContent = data.stats.low_stock ?? 0;
                document.getElementById('stat-total-units').textContent = data.stats.total_quantity ?? 0;
            }

            if (items.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--text-secondary);">No inventory items found matching criteria.</td></tr>`;
                return;
            }

            const user = Auth.getUser();
            const canStockOut = user && ['Owner', 'Manager', 'Employee'].includes(user.role);
            const canAdjust = user && ['Owner', 'Manager'].includes(user.role);

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

        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-danger" style="text-align: center;">Failed to load inventory: ${error.message}</td></tr>`;
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
        if (inventoryId) {
            item = this.currentInventory.find(i => i.inventory_id === inventoryId);
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

        const modalHtml = `
            ${!item ? `
            <div class="form-group">
                <label>Select Product</label>
                <select id="modal-adjust-item" class="input" required>
                    <option value="">Choose item...</option>
                    ${this.currentInventory.map(i => `<option value="${i.inventory_id}">${Utils.escapeHtml(i.product_name)} (${Utils.escapeHtml(i.sku)}) - Current: ${i.quantity_available}</option>`).join('')}
                </select>
            </div>
            ` : `
            <div style="background: #f8fafc; border: 1px solid var(--border); padding: 14px; border-radius: 8px; margin-bottom: 16px;">
                <div style="font-weight: 600; font-size: 15px; color: var(--text);">${Utils.escapeHtml(item.product_name)}</div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">SKU: ${Utils.escapeHtml(item.sku)} • Category: ${Utils.escapeHtml(item.category_name)}</div>
                <div style="margin-top: 8px; font-size: 14px;">Current Available Quantity: <strong style="color: var(--primary);">${item.quantity_available}</strong></div>
            </div>
            `}
            <div class="form-group">
                <label>New Available Quantity</label>
                <input type="number" id="modal-adjust-qty" class="input" min="0" value="${item ? item.quantity_available : 0}" required placeholder="Enter new quantity">
                <small style="color: var(--text-secondary); font-size: 11px;">Adjustment will automatically log a STOCK_IN / STOCK_OUT audit transaction.</small>
            </div>
            <div class="form-group">
                <label>Adjustment Notes (Optional)</label>
                <input type="text" id="modal-adjust-notes" class="input" placeholder="e.g. Physical inventory count reconciliation">
            </div>
        `;

        Modal.show({
            title: item ? `Adjust Stock — ${Utils.escapeHtml(item.product_name)}` : 'Adjust Inventory Stock',
            content: modalHtml,
            onSave: async (container) => {
                const targetInvId = item ? item.inventory_id : parseInt(container.querySelector('#modal-adjust-item').value);
                const newQtyVal = container.querySelector('#modal-adjust-qty').value;
                const notes = container.querySelector('#modal-adjust-notes').value;

                if (!targetInvId) {
                    throw new Error("Please select an inventory item");
                }

                if (newQtyVal === '' || isNaN(newQtyVal)) {
                    throw new Error("Please enter a valid quantity");
                }

                const newQty = parseInt(newQtyVal);
                if (newQty < 0) {
                    throw new Error("Quantity cannot be negative");
                }

                await Api.put(`/inventory/${targetInvId}`, {
                    quantity_available: newQty,
                    notes: notes
                });

                Utils.showToast("Stock adjusted successfully", "success");
                this.loadInventory(document.getElementById('inventory-search')?.value, document.getElementById('inventory-status-filter')?.value);
            }
        });
    }
};

