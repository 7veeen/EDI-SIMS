// stock-transactions.js - Stock Movement & Audit Log

App.pages['stock-transactions'] = {
    transactions: [],
    filteredTransactions: [],

    render() {
        const container = document.createElement('div');
        const user = Auth.getUser();
        const canStockIn = user && ['Owner', 'Manager', 'Employee'].includes(user.role);
        const canStockOut = user && ['Owner', 'Manager', 'Employee'].includes(user.role);

        container.innerHTML = `
            <div class="page-header" style="margin-bottom: 24px;">
                <div>
                    <span class="eyebrow" style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; color: var(--primary);">WAREHOUSE & AUDIT</span>
                    <h1 style="font-size: 26px; font-weight: 800; margin: 4px 0 6px 0; color: var(--text-primary);">Stock Transactions 📋</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 14px;">Complete historical audit log of all inbound receipts, outbound issuances, and inventory adjustments.</p>
                </div>
                <div class="header-actions" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    ${canStockIn ? `
                        <button class="btn primary" id="btn-tx-receive" style="display: inline-flex; align-items: center; gap: 6px; padding: 9px 15px; border-radius: 8px; font-size: 13px; font-weight: 600;">
                            <i class='bx bx-log-in' style="font-size: 16px;"></i> Receive Stock
                        </button>
                    ` : ''}
                    ${canStockOut ? `
                        <button class="btn secondary" id="btn-tx-issue" style="display: inline-flex; align-items: center; gap: 6px; padding: 9px 15px; border-radius: 8px; font-size: 13px; font-weight: 600;">
                            <i class='bx bx-log-out' style="font-size: 16px;"></i> Issue Stock
                        </button>
                    ` : ''}
                    <button class="btn" id="btn-tx-refresh" style="display: inline-flex; align-items: center; gap: 6px; padding: 9px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #fff);">
                        <i class='bx bx-refresh' style="font-size: 16px;"></i> Refresh
                    </button>
                </div>
            </div>

            <!-- Transaction Summary KPIs -->
            <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div class="stat-card card" style="padding: 16px; border-radius: 12px; background: var(--card-bg, #fff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Total Transactions</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #e0f2fe; color: #0284c7; display: flex; align-items: center; justify-content: center; font-size: 18px;"><i class='bx bx-transfer-alt'></i></div>
                    </div>
                    <h2 id="tx-stat-total" style="font-size: 24px; font-weight: 800; margin: 10px 0 2px 0;">--</h2>
                    <div style="font-size: 12px; color: var(--text-secondary);">Recorded in ledger</div>
                </div>
                <div class="stat-card card" style="padding: 16px; border-radius: 12px; background: var(--card-bg, #fff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Stock-In (Received)</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #dcfce7; color: #16a34a; display: flex; align-items: center; justify-content: center; font-size: 18px;"><i class='bx bx-down-arrow-circle'></i></div>
                    </div>
                    <h2 id="tx-stat-in" style="font-size: 24px; font-weight: 800; margin: 10px 0 2px 0; color: #16a34a;">--</h2>
                    <div style="font-size: 12px; color: var(--text-secondary);">Total inbound items</div>
                </div>
                <div class="stat-card card" style="padding: 16px; border-radius: 12px; background: var(--card-bg, #fff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Stock-Out (Issued)</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; font-size: 18px;"><i class='bx bx-up-arrow-circle'></i></div>
                    </div>
                    <h2 id="tx-stat-out" style="font-size: 24px; font-weight: 800; margin: 10px 0 2px 0; color: #dc2626;">--</h2>
                    <div style="font-size: 12px; color: var(--text-secondary);">Total outbound items</div>
                </div>
                <div class="stat-card card" style="padding: 16px; border-radius: 12px; background: var(--card-bg, #fff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Adjustments</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: #fef3c7; color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 18px;"><i class='bx bx-slider'></i></div>
                    </div>
                    <h2 id="tx-stat-adj" style="font-size: 24px; font-weight: 800; margin: 10px 0 2px 0; color: #d97706;">--</h2>
                    <div style="font-size: 12px; color: var(--text-secondary);">Manual count adjustments</div>
                </div>
            </div>

            <!-- Filters Bar -->
            <div class="card" style="padding: 16px; border-radius: 12px; background: var(--card-bg, #fff); border: 1px solid var(--border); margin-bottom: 20px; display: flex; gap: 14px; align-items: center; flex-wrap: wrap;">
                <div class="global-search" style="flex: 1; min-width: 260px; margin: 0; background: var(--surface, #f8fafc); border: 1px solid var(--border); border-radius: 8px; display: flex; align-items: center; padding: 0 12px;">
                    <i class='bx bx-search' style="font-size: 18px; color: var(--text-secondary); margin-right: 8px;"></i>
                    <input type="text" id="tx-search-input" placeholder="Search by product, SKU, reference, user, or notes..." style="width: 100%; border: none; background: transparent; padding: 10px 0; font-size: 13px; outline: none;">
                </div>
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <select id="tx-type-filter" class="input" style="padding: 9px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; background: var(--card-bg, #fff); color: var(--text-primary); cursor: pointer;">
                        <option value="">All Movement Types</option>
                        <option value="STOCK_IN">Stock-In (Receipts)</option>
                        <option value="STOCK_OUT">Stock-Out (Issuances)</option>
                        <option value="ADJUSTMENT">Adjustments</option>
                    </select>
                </div>
            </div>

            <!-- Transactions Table -->
            <div class="card table-responsive" style="border-radius: 12px; background: var(--card-bg, #fff); border: 1px solid var(--border); overflow: hidden;">
                <table class="table" id="transactions-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--surface, #f8fafc); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary); text-align: left;">
                            <th style="padding: 12px 16px;">TX ID</th>
                            <th style="padding: 12px 16px;">Date & Time</th>
                            <th style="padding: 12px 16px;">Product</th>
                            <th style="padding: 12px 16px;">Type</th>
                            <th style="padding: 12px 16px; text-align: right;">Quantity</th>
                            <th style="padding: 12px 16px;">Reference</th>
                            <th style="padding: 12px 16px;">Recorded By</th>
                            <th style="padding: 12px 16px;">Notes / Reason</th>
                        </tr>
                    </thead>
                    <tbody id="transactions-tbody">
                        <tr>
                            <td colspan="8" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; vertical-align: middle; margin-right: 8px;"></i>
                                Loading transaction records...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    },

    async init() {
        await this.loadTransactions();

        // Search listener
        const searchInput = document.getElementById('tx-search-input');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.applyFilters();
                }, 250);
            });
        }

        // Type filter listener
        const typeFilter = document.getElementById('tx-type-filter');
        if (typeFilter) {
            typeFilter.addEventListener('change', () => {
                this.applyFilters();
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('btn-tx-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadTransactions();
            });
        }

        // Action buttons
        const receiveBtn = document.getElementById('btn-tx-receive');
        if (receiveBtn) {
            receiveBtn.addEventListener('click', () => {
                App.navigate('shipments');
            });
        }

        const issueBtn = document.getElementById('btn-tx-issue');
        if (issueBtn) {
            issueBtn.addEventListener('click', () => {
                App.navigate('inventory');
            });
        }
    },

    async loadTransactions() {
        const tbody = document.getElementById('transactions-tbody');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                    <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; vertical-align: middle; margin-right: 8px;"></i>
                    Loading transaction records...
                </td>
            </tr>
        `;

        try {
            const data = await Api.get('/inventory/transactions');
            this.transactions = (data && data.transactions) ? data.transactions : [];
            this.updateStats(this.transactions);
            this.applyFilters();
        } catch (err) {
            console.error('Failed to load transactions:', err);
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 32px; color: #dc2626;">
                        <i class='bx bx-error-circle' style="font-size: 28px; margin-bottom: 8px; display: block;"></i>
                        <div><strong>Failed to load transactions</strong></div>
                        <p style="font-size: 13px; color: var(--text-secondary); margin: 6px 0 14px 0;">${err.message || 'Please check your connection and try again.'}</p>
                        <button class="btn secondary" onclick="App.pages['stock-transactions'].loadTransactions()" style="padding: 6px 16px; font-size: 13px;">Retry</button>
                    </td>
                </tr>
            `;
        }
    },

    updateStats(txs) {
        let inQty = 0;
        let outQty = 0;
        let adjCount = 0;

        txs.forEach(t => {
            const type = (t.transaction_type || '').toUpperCase();
            const qty = Number(t.quantity) || 0;
            if (type === 'STOCK_IN') inQty += qty;
            else if (type === 'STOCK_OUT') outQty += qty;
            else if (type === 'ADJUSTMENT') adjCount += 1;
        });

        const totalEl = document.getElementById('tx-stat-total');
        if (totalEl) totalEl.textContent = txs.length.toLocaleString();

        const inEl = document.getElementById('tx-stat-in');
        if (inEl) inEl.textContent = `+${inQty.toLocaleString()}`;

        const outEl = document.getElementById('tx-stat-out');
        if (outEl) outEl.textContent = `-${outQty.toLocaleString()}`;

        const adjEl = document.getElementById('tx-stat-adj');
        if (adjEl) adjEl.textContent = adjCount.toLocaleString();
    },

    applyFilters() {
        const query = (document.getElementById('tx-search-input')?.value || '').toLowerCase().trim();
        const typeFilter = document.getElementById('tx-type-filter')?.value || '';

        this.filteredTransactions = this.transactions.filter(t => {
            if (typeFilter && (t.transaction_type || '').toUpperCase() !== typeFilter) {
                return false;
            }
            if (query) {
                const prodName = (t.product_name || '').toLowerCase();
                const sku = (t.sku || '').toLowerCase();
                const user = (t.username || '').toLowerCase();
                const notes = (t.notes || '').toLowerCase();
                const shp = (t.shipment_number || '').toLowerCase();
                const txId = String(t.transaction_id || '');
                return prodName.includes(query) || sku.includes(query) || user.includes(query) || notes.includes(query) || shp.includes(query) || txId.includes(query);
            }
            return true;
        });

        this.renderTable(this.filteredTransactions);
    },

    renderTable(items) {
        const tbody = document.getElementById('transactions-tbody');
        if (!tbody) return;

        if (!items || items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 48px 24px;">
                        <i class='bx bx-transfer-alt' style="font-size: 38px; color: var(--text-secondary); opacity: 0.5; margin-bottom: 10px; display: block;"></i>
                        <h4 style="margin: 0 0 6px 0; color: var(--text-primary);">No stock transactions found</h4>
                        <p style="margin: 0; font-size: 13px; color: var(--text-secondary);">No records match your selected filters or search terms.</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = items.map(t => {
            const type = (t.transaction_type || '').toUpperCase();
            let badgeStyle = 'background: #f1f5f9; color: #475569;';
            let typeLabel = t.transaction_type;
            let qtyDisplay = `${t.quantity}`;

            if (type === 'STOCK_IN') {
                badgeStyle = 'background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0;';
                typeLabel = 'Stock-In';
                qtyDisplay = `<span style="color: #16a34a; font-weight: 700;">+${t.quantity}</span>`;
            } else if (type === 'STOCK_OUT') {
                badgeStyle = 'background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca;';
                typeLabel = 'Stock-Out';
                qtyDisplay = `<span style="color: #dc2626; font-weight: 700;">-${t.quantity}</span>`;
            } else if (type === 'ADJUSTMENT') {
                badgeStyle = 'background: #fef3c7; color: #b45309; border: 1px solid #fde68a;';
                typeLabel = 'Adjustment';
                qtyDisplay = `<span style="color: #d97706; font-weight: 700;">${t.quantity}</span>`;
            }

            const formattedDate = t.transaction_date ? new Date(t.transaction_date).toLocaleString(undefined, {
                year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            }) : 'N/A';

            let refBadge = '<span style="color: var(--text-secondary); font-size: 12px;">--</span>';
            if (t.shipment_number) {
                refBadge = `<span class="badge" style="background: #e0f2fe; color: #0369a1; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;"><i class='bx bx-car' style="font-size: 11px;"></i> ${t.shipment_number}</span>`;
            } else if (t.purchase_order_id) {
                refBadge = `<span class="badge" style="background: #f3e8ff; color: #7e22ce; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;">PO #${t.purchase_order_id}</span>`;
            }

            return `
                <tr style="border-bottom: 1px solid var(--border); font-size: 13px;">
                    <td style="padding: 12px 16px; font-family: monospace; font-weight: 600; color: var(--text-secondary);">#${t.transaction_id}</td>
                    <td style="padding: 12px 16px; white-space: nowrap; color: var(--text-secondary); font-size: 12px;">${formattedDate}</td>
                    <td style="padding: 12px 16px;">
                        <div style="font-weight: 600; color: var(--text-primary);">${t.product_name || 'Unknown Product'}</div>
                        ${t.sku ? `<div style="font-size: 11px; color: var(--text-secondary); font-family: monospace;">SKU: ${t.sku}</div>` : ''}
                    </td>
                    <td style="padding: 12px 16px;">
                        <span style="display: inline-block; padding: 3px 9px; border-radius: 6px; font-size: 11px; font-weight: 700; ${badgeStyle}">
                            ${typeLabel}
                        </span>
                    </td>
                    <td style="padding: 12px 16px; text-align: right; font-size: 14px;">
                        ${qtyDisplay}
                    </td>
                    <td style="padding: 12px 16px;">
                        ${refBadge}
                    </td>
                    <td style="padding: 12px 16px;">
                        <div style="font-weight: 600; color: var(--text-primary);">${t.username || 'System'}</div>
                        ${t.user_role ? `<div style="font-size: 11px; color: var(--text-secondary);">${t.user_role}</div>` : ''}
                    </td>
                    <td style="padding: 12px 16px; max-width: 240px; color: var(--text-secondary); font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.notes || ''}">
                        ${t.notes || '--'}
                    </td>
                </tr>
            `;
        }).join('');
    }
};
