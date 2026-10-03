// purchase-orders.js

App.pages['purchase-orders'] = {
    currentOrders: [],
    availableSuppliers: [],
    availableProducts: [],

    render() {
        const container = document.createElement('div');
        const user = Auth.getUser();
        const isSupplier = user && user.role === 'Supplier';

        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">PROCUREMENT</span>
                    <h1>Purchase Orders 📋</h1>
                    <p>${isSupplier ? 'Review, accept, and fulfill purchase orders assigned to your company.' : 'Manage supplier purchase orders, product allocations, and fulfillment lifecycles.'}</p>
                </div>
                <div class="header-actions">
                    <button class="btn secondary" id="btn-refresh-pos" title="Refresh Orders">
                        <i class='bx bx-refresh'></i> Refresh
                    </button>
                    ${!isSupplier ? `
                        <button class="btn primary" id="btn-create-po">
                            <i class='bx bx-plus'></i> Create PO
                        </button>
                    ` : ''}
                </div>
            </div>

            <!-- Metric Cards -->
            <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0;">
                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Total Orders</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(59, 130, 246, 0.1); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-receipt'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-po-total" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">All recorded POs</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Pending Response</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(245, 158, 11, 0.1); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-time-five'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-po-pending" style="font-size: 26px; font-weight: 700; margin: 0; color: #d97706;">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Awaiting supplier decision</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Accepted Orders</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(16, 185, 129, 0.1); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-check-double'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-po-accepted" style="font-size: 26px; font-weight: 700; margin: 0; color: #059669;">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">In progress or fulfilled</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Total Value</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(139, 92, 246, 0.1); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-dollar'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-po-value" style="font-size: 24px; font-weight: 700; margin: 0; color: #7c3aed;">₹0.00</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Cumulative commitment</span>
                    </div>
                </div>
            </div>

            <!-- Controls: Search & Filter -->
            <div class="card" style="padding: 16px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between;">
                <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; flex: 1;">
                    <div class="global-search" style="margin: 0; flex: 1; min-width: 240px; max-width: 400px; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="po-search" placeholder="Search by PO #, supplier, or creator..." style="background: transparent;">
                    </div>
                    <div style="min-width: 170px;">
                        <select id="po-status-filter" class="input" style="height: 42px; margin: 0;">
                            <option value="">All Statuses</option>
                            <option value="Pending">Pending Response</option>
                            <option value="Accepted">Accepted</option>
                            <option value="Rejected">Rejected</option>
                            <option value="Delivered">Delivered</option>
                        </select>
                    </div>
                </div>
                <div id="po-count-indicator" style="font-size: 13px; color: var(--text-secondary);">
                    Loading purchase orders...
                </div>
            </div>

            <!-- PO Table -->
            <div class="card table-responsive" style="margin-top: 10px;">
                <table class="table" id="pos-table">
                    <thead>
                        <tr>
                            <th>PO NUMBER</th>
                            <th>SUPPLIER</th>
                            <th>ORDER DATE</th>
                            <th>EXPECTED DELIVERY</th>
                            <th>ITEMS</th>
                            <th>TOTAL AMOUNT</th>
                            <th>STATUS</th>
                            <th style="text-align: right;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="8" style="text-align: center; padding: 32px; color: var(--text-secondary);">Loading purchase orders...</td></tr>
                    </tbody>
                </table>
            </div>
        `;

        return container;
    },

    async init() {
        this.loadPurchaseOrders();

        const searchInput = document.getElementById('po-search');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.loadPurchaseOrders(e.target.value, document.getElementById('po-status-filter')?.value);
                }, 300);
            });
        }

        const filterSelect = document.getElementById('po-status-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.loadPurchaseOrders(document.getElementById('po-search')?.value, e.target.value);
            });
        }

        const refreshBtn = document.getElementById('btn-refresh-pos');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadPurchaseOrders(document.getElementById('po-search')?.value, document.getElementById('po-status-filter')?.value);
            });
        }

        const createBtn = document.getElementById('btn-create-po');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                this.showCreatePOModal();
            });
        }
    },

    async loadPurchaseOrders(search = '', status = '') {
        const tbody = document.querySelector('#pos-table tbody');
        const countIndicator = document.getElementById('po-count-indicator');

        try {
            let url = '/purchase-orders/?';
            if (search) url += `search=${encodeURIComponent(search)}&`;
            if (status) url += `status=${encodeURIComponent(status)}&`;

            const data = await Api.get(url);
            const orders = data.purchase_orders || [];
            this.currentOrders = orders;

            // Update stats
            if (data.stats) {
                const s = data.stats;
                const statTotal = document.getElementById('stat-po-total');
                if (statTotal) statTotal.textContent = s.total_orders ?? 0;
                const statPending = document.getElementById('stat-po-pending');
                if (statPending) statPending.textContent = s.pending ?? 0;
                const statAccepted = document.getElementById('stat-po-accepted');
                if (statAccepted) statAccepted.textContent = s.accepted ?? 0;
                const statValue = document.getElementById('stat-po-value');
                if (statValue) statValue.textContent = `₹${(s.total_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            }

            if (countIndicator) {
                countIndicator.textContent = `Showing ${orders.length} order${orders.length === 1 ? '' : 's'}`;
            }

            if (orders.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" style="text-align: center; padding: 40px 16px;">
                            ${Utils.emptyState('bx-receipt', 'No Purchase Orders Found', search || status ? 'No orders match your filter criteria.' : 'No purchase orders have been placed yet.')}
                        </td>
                    </tr>
                `;
                return;
            }

            const user = Auth.getUser();
            const isSupplier = user && user.role === 'Supplier';

            tbody.innerHTML = orders.map(po => {
                let badgeClass = 'status-pending';
                if (po.status === 'Accepted' || po.status === 'Delivered') badgeClass = 'status-active';
                else if (po.status === 'Rejected') badgeClass = 'status-inactive';

                const formattedDelivery = po.expected_delivery || 'Not specified';
                const formattedDate = po.order_date || 'N/A';
                const canRespond = isSupplier && (po.status === 'Pending' || po.supplier_response === 'Pending');

                return `
                    <tr>
                        <td>
                            <strong style="color: var(--primary); font-family: monospace; font-size: 14px;">${po.po_number || `#${po.purchase_order_id}`}</strong>
                        </td>
                        <td>
                            <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(po.supplier_name)}</div>
                            <div style="font-size: 11px; color: var(--text-secondary);">${Utils.escapeHtml(po.contact_person || '')}</div>
                        </td>
                        <td style="font-size: 13px;">${formattedDate}</td>
                        <td style="font-size: 13px; color: var(--text-secondary);">${formattedDelivery}</td>
                        <td>
                            <span class="badge" style="background: #f1f5f9; color: #334155; font-weight: 600;">
                                ${po.total_items || 0} Items
                            </span>
                        </td>
                        <td><strong style="font-size: 14px;">₹${(po.total_amount || 0).toFixed(2)}</strong></td>
                        <td>
                            <span class="status-badge ${badgeClass}">
                                ${po.status}
                            </span>
                        </td>
                        <td style="text-align: right;">
                            <div class="action-buttons" style="justify-content: flex-end;">
                                <button class="btn-icon text-primary" onclick="App.pages['purchase-orders'].viewPODetails(${po.purchase_order_id})" title="View Details">
                                    <i class='bx bx-show'></i>
                                </button>
                                ${canRespond ? `
                                    <button class="btn-icon text-success" style="color: #059669;" onclick="App.pages['purchase-orders'].respondPO(${po.purchase_order_id}, 'Accepted')" title="Accept Order">
                                        <i class='bx bx-check-circle'></i>
                                    </button>
                                    <button class="btn-icon text-danger" onclick="App.pages['purchase-orders'].promptRejectPO(${po.purchase_order_id})" title="Reject Order">
                                        <i class='bx bx-x-circle'></i>
                                    </button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');

        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-danger" style="text-align: center; padding: 24px;">Failed to load purchase orders: ${error.message}</td></tr>`;
            if (countIndicator) countIndicator.textContent = 'Error loading orders';
        }
    },

    async viewPODetails(poId) {
        try {
            const data = await Api.get(`/purchase-orders/${poId}`);
            const po = data.purchase_order;
            if (!po) throw new Error("Purchase order details not found");

            const user = Auth.getUser();
            const isSupplier = user && user.role === 'Supplier';
            const canRespond = isSupplier && (po.status === 'Pending' || po.supplier_response === 'Pending');

            let badgeClass = 'status-pending';
            if (po.status === 'Accepted' || po.status === 'Delivered') badgeClass = 'status-active';
            else if (po.status === 'Rejected') badgeClass = 'status-inactive';

            const itemsHtml = po.items && po.items.length > 0 ? `
                <table class="table" style="margin-top: 10px; font-size: 13px;">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>PRODUCT</th>
                            <th>SKU</th>
                            <th>REQUIRED QTY</th>
                            <th>UNIT PRICE</th>
                            <th>SUBTOTAL</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${po.items.map((it, idx) => `
                            <tr>
                                <td style="color: var(--text-secondary);">${idx + 1}</td>
                                <td><strong>${Utils.escapeHtml(it.product_name)}</strong></td>
                                <td><span class="badge" style="background: #e2e8f0; color: #334155;">${Utils.escapeHtml(it.sku)}</span></td>
                                <td><strong>${it.quantity}</strong></td>
                                <td>₹${it.unit_price.toFixed(2)}</td>
                                <td><strong style="color: var(--primary);">₹${it.subtotal.toFixed(2)}</strong></td>
                            </tr>
                        `).join('')}
                    </tbody>
                    <tfoot>
                        <tr style="border-top: 2px solid var(--border); background: #f8fafc;">
                            <td colspan="5" style="text-align: right; font-weight: 700; font-size: 14px;">Total PO Amount:</td>
                            <td style="font-weight: 800; font-size: 15px; color: var(--primary);">₹${po.total_amount.toFixed(2)}</td>
                        </tr>
                    </tfoot>
                </table>
            ` : `<p style="color: var(--text-secondary); margin: 10px 0;">No items found in this purchase order.</p>`;

            const historyHtml = po.status_history && po.status_history.length > 0 ? `
                <div style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px;">
                    ${po.status_history.map(h => `
                        <div style="display: flex; gap: 12px; align-items: flex-start; padding: 10px 14px; background: #f8fafc; border-radius: 8px; border: 1px solid var(--border); font-size: 12px;">
                            <div style="width: 28px; height: 28px; border-radius: 50%; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0;">
                                <i class='bx bx-check'></i>
                            </div>
                            <div style="flex: 1;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <strong style="font-size: 13px; color: var(--text);">${Utils.escapeHtml(h.action)}</strong>
                                    <span style="color: var(--text-secondary); font-size: 11px;">${h.created_at ? new Date(h.created_at).toLocaleString() : ''}</span>
                                </div>
                                <div style="color: var(--text-secondary); margin-top: 2px;">
                                    Status: <span class="badge" style="font-size: 11px;">${h.status}</span> • By: <strong>${Utils.escapeHtml(h.changed_by || 'System')}</strong>
                                </div>
                                ${h.notes ? `<div style="margin-top: 4px; color: var(--text); font-style: italic;">"${Utils.escapeHtml(h.notes)}"</div>` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : `<p style="color: var(--text-secondary); font-size: 12px; margin: 8px 0;">No status events logged yet.</p>`;

            const contentHtml = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 14px; border-bottom: 1px solid var(--border);">
                    <div>
                        <h3 style="margin: 0; font-size: 18px; color: var(--text);">${po.po_number || `#${po.purchase_order_id}`}</h3>
                        <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                            Issued to: <strong>${Utils.escapeHtml(po.supplier_name)}</strong> • Created by: <strong>${Utils.escapeHtml(po.ordered_by_username || 'Manager')}</strong>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <span class="status-badge ${badgeClass}" style="font-size: 13px; padding: 4px 12px;">
                            ${po.status}
                        </span>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">
                            Date: ${po.order_date || 'N/A'}
                        </div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 14px 0; padding: 12px 14px; background: #f8fafc; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                    <div>
                        <span style="color: var(--text-secondary); font-size: 11px;">Contact Person:</span><br>
                        <strong>${Utils.escapeHtml(po.contact_person || '—')}</strong>
                    </div>
                    <div>
                        <span style="color: var(--text-secondary); font-size: 11px;">Email / Phone:</span><br>
                        <strong>${Utils.escapeHtml(po.supplier_email || po.supplier_phone || '—')}</strong>
                    </div>
                    <div>
                        <span style="color: var(--text-secondary); font-size: 11px;">Expected Delivery:</span><br>
                        <strong>${po.expected_delivery || 'Not specified'}</strong>
                    </div>
                    <div>
                        <span style="color: var(--text-secondary); font-size: 11px;">Supplier Response:</span><br>
                        <strong style="color: ${po.supplier_response === 'Accepted' ? '#059669' : (po.supplier_response === 'Rejected' ? '#dc2626' : '#d97706')};">
                            ${po.supplier_response} ${po.supplier_response_date ? `(${new Date(po.supplier_response_date).toLocaleDateString()})` : ''}
                        </strong>
                    </div>
                </div>

                ${po.rejection_reason ? `
                    <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); color: #dc2626; padding: 10px 14px; border-radius: 8px; margin-bottom: 14px; font-size: 13px;">
                        <i class='bx bx-error-circle'></i> <strong>Rejection Reason:</strong> ${Utils.escapeHtml(po.rejection_reason)}
                    </div>
                ` : ''}

                <div style="margin-top: 16px;">
                    <h4 style="margin: 0; font-size: 14px; font-weight: 600; color: var(--text);"><i class='bx bx-box'></i> Ordered Products & Quantities</h4>
                    ${itemsHtml}
                </div>

                <div style="margin-top: 18px;">
                    <h4 style="margin: 0; font-size: 14px; font-weight: 600; color: var(--text);"><i class='bx bx-history'></i> Order Lifecycle Audit History</h4>
                    ${historyHtml}
                </div>
            `;

            const footerHtml = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <div>
                        ${canRespond ? `
                            <button type="button" class="btn text-danger" style="border: 1px solid rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.05); color: #dc2626; padding: 8px 14px; border-radius: 6px; font-weight: 600;" id="modal-btn-reject">
                                <i class='bx bx-x-circle'></i> Reject Order
                            </button>
                            <button type="button" class="btn text-success" style="border: 1px solid rgba(16, 185, 129, 0.3); background: rgba(16, 185, 129, 0.08); color: #059669; padding: 8px 14px; border-radius: 6px; font-weight: 600; margin-left: 8px;" id="modal-btn-accept">
                                <i class='bx bx-check-circle'></i> Accept Order
                            </button>
                        ` : ''}
                    </div>
                    <button type="button" class="btn btn-primary close-modal">Close</button>
                </div>
            `;

            Modal.create({
                id: 'modal-po-details',
                title: `Purchase Order Details — ${po.po_number || `#${po.purchase_order_id}`}`,
                content: contentHtml,
                footer: footerHtml,
                onOpen: (modalEl, closeModal) => {
                    if (canRespond) {
                        const acceptBtn = modalEl.querySelector('#modal-btn-accept');
                        if (acceptBtn) {
                            acceptBtn.addEventListener('click', async () => {
                                closeModal();
                                await this.respondPO(poId, 'Accepted');
                            });
                        }

                        const rejectBtn = modalEl.querySelector('#modal-btn-reject');
                        if (rejectBtn) {
                            rejectBtn.addEventListener('click', () => {
                                closeModal();
                                this.promptRejectPO(poId);
                            });
                        }
                    }
                }
            });

        } catch (err) {
            Utils.showToast("Failed to load PO details: " + err.message, "error");
        }
    },

    async respondPO(poId, action, rejectionReason = null) {
        try {
            const payload = { response: action };
            if (action === 'Rejected') {
                payload.rejection_reason = rejectionReason;
            }

            await Api.patch(`/purchase-orders/${poId}/respond`, payload);
            Utils.showToast(`Purchase order successfully ${action.toLowerCase()}!`, "success");
            this.loadPurchaseOrders(
                document.getElementById('po-search')?.value || '',
                document.getElementById('po-status-filter')?.value || ''
            );
        } catch (err) {
            Utils.showToast(err.message || "Failed to update order response", "error");
        }
    },

    promptRejectPO(poId) {
        const promptHtml = `
            <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
                Please specify the reason for rejecting this purchase order. This reason will be recorded in the order audit log and made visible to the purchasing manager.
            </div>
            <div class="form-group">
                <label>Rejection Reason <span class="text-danger">*</span></label>
                <textarea id="modal-reject-reason" class="input" rows="3" placeholder="e.g. Stock shortage in manufacturing facility, cannot meet expected delivery date..." style="resize: vertical;"></textarea>
            </div>
        `;

        Modal.show({
            title: `Reject Purchase Order #${poId}`,
            content: promptHtml,
            saveText: 'Confirm Rejection',
            onSave: async (container) => {
                const reason = container.querySelector('#modal-reject-reason').value.trim();
                if (!reason) {
                    throw new Error("A rejection reason is required.");
                }
                await this.respondPO(poId, 'Rejected', reason);
            }
        });
    },

    async showCreatePOModal() {
        // Load active suppliers and active products
        let suppliers = [];
        let products = [];

        try {
            const [supData, prodData] = await Promise.all([
                Api.get('/suppliers/?status=Active'),
                Api.get('/products/?status=Active')
            ]);
            suppliers = Array.isArray(supData) ? supData : (supData.suppliers || []);
            products = prodData.products || [];
            this.availableSuppliers = suppliers;
            this.availableProducts = products;
        } catch (e) {
            Utils.showToast("Failed to load suppliers or products for order form", "error");
            return;
        }

        if (suppliers.length === 0) {
            Utils.showToast("No active suppliers found in directory. Please add or activate a supplier first.", "error");
            return;
        }

        if (products.length === 0) {
            Utils.showToast("No active products available in catalog.", "error");
            return;
        }

        const suppliersOptions = suppliers.map(s => `
            <option value="${s.supplier_id}">${Utils.escapeHtml(s.supplier_name)} (${Utils.escapeHtml(s.contact_person || 'No contact')})</option>
        `).join('');

        const modalHtml = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                    <label>Select Supplier <span class="text-danger">*</span></label>
                    <select id="modal-po-supplier" class="input" required>
                        <option value="">Select an active vendor...</option>
                        ${suppliersOptions}
                    </select>
                </div>
                <div class="form-group">
                    <label>Expected Delivery Date</label>
                    <input type="date" id="modal-po-delivery" class="input">
                </div>
            </div>

            <div style="margin-top: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <label style="font-weight: 600; font-size: 13px; color: var(--text);"><i class='bx bx-list-plus'></i> Order Items <span class="text-danger">*</span></label>
                    <button type="button" class="btn secondary" id="btn-add-item-row" style="padding: 4px 10px; font-size: 12px;">
                        <i class='bx bx-plus'></i> Add Line Item
                    </button>
                </div>

                <div id="po-items-container" style="display: flex; flex-direction: column; gap: 10px;">
                    <!-- Line items dynamically injected here -->
                </div>

                <div style="margin-top: 16px; padding: 12px 16px; background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 600; font-size: 14px; color: var(--text);">Calculated Order Total:</span>
                    <strong id="modal-po-calculated-total" style="font-size: 18px; color: var(--primary);">₹0.00</strong>
                </div>
            </div>
        `;

        const self = this;

        Modal.show({
            title: 'Create New Purchase Order',
            content: modalHtml,
            saveText: 'Issue Purchase Order',
            onSave: async (container) => {
                const supplierId = container.querySelector('#modal-po-supplier').value;
                const deliveryDate = container.querySelector('#modal-po-delivery').value;

                if (!supplierId) {
                    throw new Error("Please select a supplier");
                }

                const itemRows = container.querySelectorAll('.po-item-row');
                if (itemRows.length === 0) {
                    throw new Error("Please add at least one product item to the order");
                }

                const itemsPayload = [];
                for (const row of itemRows) {
                    const prodId = row.querySelector('.item-product-select').value;
                    const qtyVal = row.querySelector('.item-quantity-input').value;
                    const priceVal = row.querySelector('.item-price-input').value;

                    if (!prodId) throw new Error("Please select a product for all item rows");
                    const qty = parseInt(qtyVal);
                    if (!qty || qty <= 0) throw new Error("Item quantities must be greater than zero");

                    const itemObj = {
                        product_id: parseInt(prodId),
                        quantity: qty
                    };
                    if (priceVal && parseFloat(priceVal) >= 0) {
                        itemObj.unit_price = parseFloat(priceVal);
                    }
                    itemsPayload.push(itemObj);
                }

                const payload = {
                    supplier_id: parseInt(supplierId),
                    expected_delivery: deliveryDate || null,
                    items: itemsPayload
                };

                const res = await Api.post('/purchase-orders/', payload);
                Utils.showToast("Purchase order created and issued to vendor!", "success");
                self.loadPurchaseOrders(
                    document.getElementById('po-search')?.value || '',
                    document.getElementById('po-status-filter')?.value || ''
                );
            }
        });

        // Initialize dynamic items row behavior
        setTimeout(() => {
            const container = document.getElementById('po-items-container');
            const addRowBtn = document.getElementById('btn-add-item-row');

            const recalculateTotal = () => {
                let total = 0;
                container.querySelectorAll('.po-item-row').forEach(row => {
                    const price = parseFloat(row.querySelector('.item-price-input').value) || 0;
                    const qty = parseInt(row.querySelector('.item-quantity-input').value) || 0;
                    const subtotal = price * qty;
                    row.querySelector('.item-subtotal-display').textContent = `₹${subtotal.toFixed(2)}`;
                    total += subtotal;
                });
                const totalEl = document.getElementById('modal-po-calculated-total');
                if (totalEl) totalEl.textContent = `₹${total.toFixed(2)}`;
            };

            const addRow = () => {
                const row = document.createElement('div');
                row.className = 'po-item-row';
                row.style.cssText = 'display: grid; grid-template-columns: 2fr 1fr 1fr 1.2fr 36px; gap: 8px; align-items: center; background: #ffffff; padding: 8px; border: 1px solid var(--border); border-radius: 6px;';

                const prodOptions = this.availableProducts.map(p => `
                    <option value="${p.product_id}" data-price="${p.price}">${Utils.escapeHtml(p.product_name)} (${Utils.escapeHtml(p.sku)})</option>
                `).join('');

                row.innerHTML = `
                    <div>
                        <select class="input item-product-select" style="margin: 0; height: 38px;" required>
                            <option value="">Select product...</option>
                            ${prodOptions}
                        </select>
                    </div>
                    <div>
                        <input type="number" class="input item-quantity-input" min="1" value="1" placeholder="Qty" style="margin: 0; height: 38px;" required>
                    </div>
                    <div>
                        <input type="number" step="0.01" min="0" class="input item-price-input" placeholder="Price (₹)" style="margin: 0; height: 38px;">
                    </div>
                    <div style="font-weight: 700; color: var(--primary); font-size: 13px; text-align: right; padding-right: 6px;" class="item-subtotal-display">
                        ₹0.00
                    </div>
                    <div style="text-align: center;">
                        <button type="button" class="btn-icon text-danger btn-remove-item" style="padding: 4px;" title="Remove row">
                            <i class='bx bx-trash'></i>
                        </button>
                    </div>
                `;

                const prodSelect = row.querySelector('.item-product-select');
                const qtyInput = row.querySelector('.item-quantity-input');
                const priceInput = row.querySelector('.item-price-input');
                const removeBtn = row.querySelector('.btn-remove-item');

                prodSelect.addEventListener('change', () => {
                    const opt = prodSelect.options[prodSelect.selectedIndex];
                    const defaultPrice = opt ? opt.getAttribute('data-price') : 0;
                    if (defaultPrice) {
                        priceInput.value = parseFloat(defaultPrice).toFixed(2);
                    }
                    recalculateTotal();
                });

                qtyInput.addEventListener('input', recalculateTotal);
                priceInput.addEventListener('input', recalculateTotal);

                removeBtn.addEventListener('click', () => {
                    row.remove();
                    recalculateTotal();
                });

                container.appendChild(row);
            };

            if (addRowBtn) addRowBtn.addEventListener('click', addRow);

            // Add first initial item row
            addRow();
        }, 50);
    }
};
