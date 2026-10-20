// shipments.js - Step 5 Shipment & Delivery Management

App.pages['shipments'] = {
    currentShipments: [],
    eligiblePOs: [],
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
        const isSupplier = user && user.role === 'Supplier';
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');

        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">LOGISTICS &amp; FULFILLMENT</span>
                    <h1>Shipments 🚚</h1>
                    <p>${isSupplier 
                        ? 'Dispatch packages, assign carrier tracking, and report real-time transit updates for your orders.' 
                        : 'Monitor supplier dispatches, carrier tracking numbers, and warehouse delivery receipts.'}</p>
                </div>
                <div class="header-actions" style="display: flex; gap: 10px; align-items: center;">
                    <button class="btn secondary" id="btn-refresh-shipments" title="Refresh Shipments">
                        <i class='bx bx-refresh'></i> Refresh
                    </button>
                    ${isSupplier ? `
                        <button class="btn primary" id="btn-create-shipment">
                            <i class='bx bx-plus'></i> Create Shipment
                        </button>
                    ` : ''}
                </div>
            </div>

            <!-- KPI Metric Cards -->
            <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0;">
                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Ready for Dispatch</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(147, 51, 234, 0.1); color: #9333ea; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-package'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-ship-ready" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Awaiting courier pickup</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">In Transit</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(59, 130, 246, 0.1); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-car'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-ship-transit" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">En route to warehouse</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Delivered</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(16, 185, 129, 0.1); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-check-circle'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-ship-delivered" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Arrived at bay (pre-stock-in)</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Total Dispatches</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(99, 102, 241, 0.1); color: #4f46e5; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-layer'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-ship-total" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">All logistics records</span>
                    </div>
                </div>
            </div>

            <!-- Table Card & Filters -->
            <div class="card" style="border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border); overflow: hidden; margin-top: 10px; padding: 0;">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 280px;">
                        <div style="position: relative; flex: 1; max-width: 360px;">
                            <i class='bx bx-search' style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-secondary); font-size: 18px;"></i>
                            <input type="text" id="ship-search-input" placeholder="Search shipment #, tracking #, carrier, PO..." 
                                   style="width: 100%; padding: 8px 12px 8px 38px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-surface, #ffffff); color: var(--text); font-size: 13px;">
                        </div>
                        <select id="ship-status-filter" style="padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-surface, #ffffff); color: var(--text); font-size: 13px;">
                            <option value="">All Statuses</option>
                            <option value="Ready for Shipment">Ready for Shipment</option>
                            <option value="In Transit">In Transit / Dispatched</option>
                            <option value="Delivered">Delivered</option>
                            <option value="Delayed">Delayed</option>
                            <option value="Cancelled">Cancelled</option>
                        </select>
                    </div>

                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span id="ship-count-badge" style="font-size: 13px; color: var(--text-secondary);">Loading shipments...</span>
                    </div>
                </div>

                <div class="table-responsive shipments-table-container">
                    <table class="data-table" id="shipments-table" style="width: 100%; min-width: 980px; border-collapse: collapse; text-align: left;">
                        <thead>
                            <tr style="background: var(--bg-surface, #f9fafb); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
                                <th style="padding: 12px 16px; min-width: 140px;">SHIPMENT #</th>
                                <th style="padding: 12px 16px; min-width: 110px;">PURCHASE ORDER</th>
                                ${!isSupplier ? '<th style="padding: 12px 16px; min-width: 160px;">SUPPLIER</th>' : ''}
                                <th style="padding: 12px 16px; min-width: 160px;">CARRIER &amp; TRACKING</th>
                                ${!isSupplier ? '<th style="padding: 12px 16px; min-width: 140px;">ASSIGNED TO</th>' : ''}
                                <th style="padding: 12px 16px; min-width: 140px;">RECEIVING STATUS</th>
                                <th style="padding: 12px 16px; min-width: 100px;">STATUS</th>
                                <th class="col-actions cell-actions-center" style="padding: 12px 16px; min-width: 140px; text-align: center;">ACTIONS</th>
                            </tr>
                        </thead>
                        <tbody id="shipments-tbody">
                            <tr>
                                <td colspan="${isSupplier ? '7' : '9'}" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                    <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; margin-bottom: 8px;"></i>
                                    <div>Loading shipments from Supabase...</div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div id="shipments-pagination-container"></div>
        `;

        setTimeout(() => this.init(container), 0);
        return container;
    },

    async init(container) {
        this.page = 1;
        this.search = '';
        this.status = '';

        container = container || document.getElementById('content-area') || document;
        const refreshBtn = container.querySelector('#btn-refresh-shipments');
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadShipments());

        const searchInput = container.querySelector('#ship-search-input');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.page = 1;
                    this.search = e.target.value;
                    this.loadShipments();
                }, 300);
            });
        }

        const statusFilter = container.querySelector('#ship-status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.page = 1;
                this.status = e.target.value;
                this.loadShipments();
            });
        }

        const createBtn = container.querySelector('#btn-create-shipment');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.openCreateShipmentModal());
        }

        await this.loadShipments();
    },

    goToPage(newPage) {
        if (newPage < 1 || newPage > this.totalPages || newPage === this.page) return;
        this.page = newPage;
        this.loadShipments();
    },

    async loadShipments(searchTerm = null, statusFilterVal = null) {
        if (searchTerm !== null) this.search = searchTerm;
        if (statusFilterVal !== null) this.status = statusFilterVal;

        const thisReq = ++this.requestId;
        const tbody = document.getElementById('shipments-tbody');
        const countBadge = document.getElementById('ship-count-badge');
        const paginationContainer = document.getElementById('shipments-pagination-container');

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; margin-bottom: 8px;"></i>
                        <div>Loading shipments...</div>
                    </td>
                </tr>
            `;
        }

        try {
            let url = `/shipments/?page=${this.page}&page_size=${this.pageSize}`;
            if (this.search && this.search.trim()) url += `&search=${encodeURIComponent(this.search.trim())}`;
            if (this.status && this.status.trim()) url += `&status=${encodeURIComponent(this.status.trim())}`;

            const response = await Api.get(url);
            if (thisReq !== this.requestId) return; // Discard stale response

            const shipments = response.shipments || [];
            const stats = response.stats || {};

            this.currentShipments = shipments;
            this.total = response.total !== undefined ? response.total : (stats.total_shipments || shipments.length);
            this.totalPages = response.total_pages || Math.max(1, Math.ceil(this.total / this.pageSize));

            this.updateStats(stats);
            this.renderTable(shipments);

            if (countBadge) {
                const start = this.total > 0 ? (this.page - 1) * this.pageSize + 1 : 0;
                const end = Math.min(this.page * this.pageSize, this.total);
                countBadge.textContent = this.total > 0 ? `Showing ${start}–${end} of ${this.total} shipments` : 'No shipments';
            }

            // Render pagination controls
            if (paginationContainer && window.PaginationComponent) {
                paginationContainer.innerHTML = PaginationComponent.render({
                    total: this.total,
                    page: this.page,
                    pageSize: this.pageSize,
                    totalPages: this.totalPages,
                    label: 'shipments',
                    onPageChangeName: "App.pages['shipments'].goToPage"
                });
            }
        } catch (error) {
            if (thisReq !== this.requestId) return;
            console.error('Failed to load shipments:', error);
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="9" style="text-align: center; padding: 40px; color: var(--red);">
                            <i class='bx bx-error-circle' style="font-size: 28px; margin-bottom: 8px;"></i>
                            <div>Failed to load shipments: ${error.message || 'Server error'}</div>
                        </td>
                    </tr>
                `;
            }
            if (paginationContainer) paginationContainer.innerHTML = '';
        }
    },

    updateStats(stats) {
        const elReady = document.getElementById('stat-ship-ready');
        const elTransit = document.getElementById('stat-ship-transit');
        const elDelivered = document.getElementById('stat-ship-delivered');
        const elTotal = document.getElementById('stat-ship-total');

        if (elReady) elReady.textContent = String(stats.ready || 0).padStart(2, '0');
        if (elTransit) elTransit.textContent = String(stats.in_transit || 0).padStart(2, '0');
        if (elDelivered) elDelivered.textContent = String(stats.delivered || 0).padStart(2, '0');
        if (elTotal) elTotal.textContent = String(stats.total_shipments || 0).padStart(2, '0');
    },

    renderTable(shipments) {
        const tbody = document.getElementById('shipments-tbody');
        if (!tbody) return;

        const user = Auth.getUser();
        const isSupplier = user && user.role === 'Supplier';
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');
        const isEmployee = user && user.role === 'Employee';

        if (!shipments || shipments.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${isSupplier ? '7' : '9'}" style="text-align: center; padding: 50px 20px; color: var(--text-secondary);">
                        <i class='bx bx-car' style="font-size: 36px; color: var(--text-light); margin-bottom: 10px; display: block;"></i>
                        <div style="font-size: 15px; font-weight: 600; color: var(--text);">No shipments found</div>
                        <div style="font-size: 13px; margin-top: 4px;">${isEmployee ? 'You have no assigned shipments currently awaiting receipt.' : (isSupplier ? 'Dispatch packages for approved Purchase Orders to view shipments here.' : 'No supplier shipments have been created yet.')}</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = shipments.map(s => {
            const statusBadge = this.getStatusBadge(s.status);
            const isTerminal = s.status && (s.status.toLowerCase() === 'delivered' || s.status.toLowerCase() === 'cancelled');
            const isDelivered = s.status && s.status.toLowerCase() === 'delivered';

            const expQty = s.total_expected_quantity || 0;
            const recQty = s.total_received_quantity || 0;
            const remQty = s.total_remaining_quantity !== undefined ? s.total_remaining_quantity : Math.max(0, expQty - recQty);
            const recStatus = s.receiving_status || 'Pending Receipt';

            const currentUserId = user ? parseInt(user.id || user.user_id || 0) : 0;
            const isAssignedToCurrentUser = isEmployee && parseInt(s.assigned_employee_id) === currentUserId;
            const canStockIn = isDelivered && remQty > 0 && (isManagerOrOwner || isAssignedToCurrentUser);

            let receivingBadge = '';
            if (recStatus === 'Fully Received') {
                receivingBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; font-weight: 600;">
                    <i class='bx bx-check-double'></i> Fully Received (${recQty}/${expQty})
                </span>`;
            } else if (recStatus === 'Partially Received') {
                receivingBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 11px; font-weight: 600;">
                    <i class='bx bx-pie-chart-alt'></i> Received ${recQty}/${expQty} (${remQty} rem)
                </span>`;
            } else {
                receivingBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(107, 114, 128, 0.1); color: #64748b; font-size: 11px; font-weight: 500;">
                    <i class='bx bx-time'></i> ${isDelivered ? 'Pending Receipt' : 'In Transit'} (${expQty} units)
                </span>`;
            }

            let assignmentCol = '';
            if (!isSupplier) {
                if (isEmployee) {
                    assignmentCol = isAssignedToCurrentUser 
                        ? `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; font-weight: 600;"><i class='bx bx-user-check'></i> Assigned to you</span>`
                        : `<span style="color: var(--text-secondary); font-size: 12px;">${Utils.escapeHtml(s.assigned_employee_name || 'Unassigned')}</span>`;
                } else if (isManagerOrOwner) {
                    if (s.assigned_employee_name) {
                        assignmentCol = `
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span style="font-weight: 600; font-size: 12px; color: var(--text);">${Utils.escapeHtml(s.assigned_employee_name)}</span>
                                ${recStatus !== 'Fully Received' ? `
                                    <button class="btn-icon btn-action-assign" title="Reassign Employee" aria-label="Reassign employee for shipment ${s.shipment_id}" onclick="App.pages['shipments'].openAssignEmployeeModal(${s.shipment_id})"
                                            style="width: 26px; height: 26px; font-size: 13px; cursor: pointer;">
                                        <i class='bx bx-edit-alt'></i>
                                    </button>
                                ` : ''}
                            </div>
                        `;
                    } else {
                        assignmentCol = `
                            <button class="btn btn-sm" onclick="App.pages['shipments'].openAssignEmployeeModal(${s.shipment_id})"
                                    style="padding: 4px 8px; font-size: 11px; border-radius: 6px; background: rgba(79, 70, 229, 0.08); color: #4f46e5; border: 1px solid rgba(79, 70, 229, 0.2); cursor: pointer; font-weight: 600;">
                                <i class='bx bx-user-plus'></i> Assign Employee
                            </button>
                        `;
                    }
                } else {
                    assignmentCol = `<span style="font-size: 12px; color: var(--text-secondary);">${Utils.escapeHtml(s.assigned_employee_name || 'Unassigned')}</span>`;
                }
            }

            return `
                <tr style="border-bottom: 1px solid var(--border); transition: background 0.15s ease;" onmouseover="this.style.background='var(--bg-hover, rgba(0,0,0,0.02))'" onmouseout="this.style.background='transparent'">
                    <td style="padding: 14px 16px;">
                        <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(s.shipment_number)}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${s.created_at ? new Date(s.created_at).toLocaleDateString() : 'N/A'}</div>
                    </td>
                    <td style="padding: 14px 16px;">
                        <span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(59, 130, 246, 0.08); color: #2563eb; font-size: 12px; font-weight: 600;">
                            <i class='bx bx-receipt'></i> PO #${s.purchase_order_id}
                        </span>
                    </td>
                    ${!isSupplier ? `
                        <td style="padding: 14px 16px;">
                            <div style="font-weight: 500; color: var(--text);">${Utils.escapeHtml(s.supplier_name || 'Supplier')}</div>
                            <div style="font-size: 11px; color: var(--text-secondary);">${Utils.escapeHtml(s.supplier_email || '')}</div>
                        </td>
                    ` : ''}
                    <td style="padding: 14px 16px;">
                        <div style="font-weight: 600; font-size: 13px; color: var(--text); display: flex; align-items: center; gap: 6px;">
                            <i class='bx bx-send' style="color: #2563eb;"></i> ${Utils.escapeHtml(s.carrier)}
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-family: monospace; margin-top: 2px; word-break: break-all;">
                            ${s.tracking_number ? `TRK: ${Utils.escapeHtml(s.tracking_number)}` : 'No tracking'}
                        </div>
                    </td>
                    ${!isSupplier ? `
                        <td style="padding: 14px 16px;">
                            ${assignmentCol}
                        </td>
                    ` : ''}
                    <td style="padding: 14px 16px;">
                        ${receivingBadge}
                    </td>
                    <td style="padding: 14px 16px;">
                        ${statusBadge}
                    </td>
                    <td class="col-actions cell-actions-center" style="padding: 12px 16px; text-align: center;">
                        <div class="action-buttons" style="justify-content: center;">
                            <button class="btn-icon btn-action-view" title="View Shipment Details" aria-label="View shipment details for ${Utils.escapeHtml(s.shipment_number)}" onclick="App.pages['shipments'].openShipmentDetailsModal(${s.shipment_id})">
                                <i class='bx bx-show'></i>
                            </button>

                            ${canStockIn ? `
                                <button class="btn-icon btn-action-stockin text-success" title="Receive Stock / Stock-In" aria-label="Receive stock for shipment ${Utils.escapeHtml(s.shipment_number)}" onclick="App.pages['shipments'].openReceiveStockModal(${s.shipment_id})">
                                    <i class='bx bx-download'></i>
                                </button>
                            ` : ''}

                            ${isManagerOrOwner && !s.assigned_employee_id && recStatus !== 'Fully Received' ? `
                                <button class="btn-icon btn-action-assign" title="Assign Employee" aria-label="Assign employee to shipment ${Utils.escapeHtml(s.shipment_number)}" onclick="App.pages['shipments'].openAssignEmployeeModal(${s.shipment_id})">
                                    <i class='bx bx-user-plus'></i>
                                </button>
                            ` : ''}

                            ${!isTerminal && (isSupplier || isManagerOrOwner) ? `
                                <button class="btn-icon btn-action-status" title="Update Status" aria-label="Update status for shipment ${Utils.escapeHtml(s.shipment_number)}" onclick="App.pages['shipments'].openUpdateStatusModal(${s.shipment_id})">
                                    <i class='bx bx-refresh'></i>
                                </button>
                            ` : ''}

                            ${!isTerminal && isSupplier ? `
                                <button class="btn-icon btn-action-edit" title="Edit Shipment Details" aria-label="Edit shipment details for ${Utils.escapeHtml(s.shipment_number)}" onclick="App.pages['shipments'].openEditShipmentModal(${s.shipment_id})">
                                    <i class='bx bx-edit'></i>
                                </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    },

    getStatusBadge(status) {
        const s = (status || 'Ready for Shipment').toLowerCase();
        if (s === 'delivered') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; font-weight: 600;">
                <i class='bx bx-check-circle'></i> Delivered
            </span>`;
        }
        if (s === 'in transit' || s === 'dispatched' || s === 'shipped') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(59, 130, 246, 0.12); color: #2563eb; font-size: 11px; font-weight: 600;">
                <i class='bx bx-car'></i> In Transit
            </span>`;
        }
        if (s === 'ready for shipment') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(147, 51, 234, 0.12); color: #9333ea; font-size: 11px; font-weight: 600;">
                <i class='bx bx-package'></i> Ready
            </span>`;
        }
        if (s === 'delayed') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 11px; font-weight: 600;">
                <i class='bx bx-time'></i> Delayed
            </span>`;
        }
        if (s === 'cancelled') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(239, 68, 68, 0.12); color: #ef4444; font-size: 11px; font-weight: 600;">
                <i class='bx bx-x-circle'></i> Cancelled
            </span>`;
        }
        return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(107, 114, 128, 0.12); color: #4b5563; font-size: 11px; font-weight: 600;">
            ${status}
        </span>`;
    },

    // Supplier: Create Shipment Modal
    async openCreateShipmentModal(preselectedPoId = null) {
        try {
            // Fetch eligible accepted POs
            const poResp = await Api.get('/purchase-orders/');
            const orders = poResp.purchase_orders || [];
            const eligible = orders.filter(po => (po.supplier_response === 'Accepted' || po.status === 'Accepted'));

            if (eligible.length === 0) {
                const msg = 'No accepted Purchase Orders available. Shipments can only be created for accepted Purchase Orders.';
                if (typeof Utils !== 'undefined' && Utils.showToast) Utils.showToast(msg, 'warning');
                else if (typeof alert === 'function') alert(msg);
                return;
            }

            this.eligiblePOs = eligible;

            const targetPo = preselectedPoId ? eligible.find(po => String(po.purchase_order_id) === String(preselectedPoId)) : null;
            if (preselectedPoId && !targetPo) {
                const anyPo = orders.find(po => String(po.purchase_order_id) === String(preselectedPoId));
                const reason = anyPo ? `(Current Status: ${anyPo.status})` : '';
                if (typeof Utils !== 'undefined' && Utils.showToast) {
                    Utils.showToast(`Purchase Order #${preselectedPoId} is not eligible for dispatch ${reason}. Please select an accepted Purchase Order.`, 'warning');
                }
            }

            const content = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SELECT PURCHASE ORDER *</label>
                        <select id="modal-ship-po-select" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                            <option value="">-- Choose an accepted Purchase Order --</option>
                            ${eligible.map(po => `
                                <option value="${po.purchase_order_id}" ${preselectedPoId && String(po.purchase_order_id) === String(preselectedPoId) ? 'selected' : ''}>
                                    PO #${po.purchase_order_id} - ${po.order_date || 'N/A'} (Total: ₹${(po.total_amount || 0).toLocaleString('en-IN')})
                                </option>
                            `).join('')}
                        </select>
                    </div>

                    <div id="modal-ship-po-preview" style="display: none; padding: 14px; border-radius: 8px; background: var(--bg-surface, #f9fafb); border: 1px solid var(--border);">
                        <!-- Interactive PO product allocations injected here -->
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">LOGISTICS CARRIER *</label>
                            <input list="carriers-list" id="modal-ship-carrier" value="BlueDart Express" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                            <datalist id="carriers-list">
                                <option value="BlueDart Express">
                                <option value="FedEx Ground">
                                <option value="DHL Express">
                                <option value="Delhivery Logistics">
                                <option value="Standard Logistics">
                            </datalist>
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">TRACKING NUMBER</label>
                            <input type="text" id="modal-ship-tracking" placeholder="e.g. BD-892104523" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SHIPPING METHOD</label>
                            <select id="modal-ship-method" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                                <option value="Standard Ground">Standard Ground</option>
                                <option value="Express Cargo">Express Cargo</option>
                                <option value="Overnight Air">Overnight Air</option>
                                <option value="Heavy Freight">Heavy Freight</option>
                            </select>
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">INITIAL DISPATCH STATUS</label>
                            <select id="modal-ship-status" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                                <option value="Ready for Shipment">Ready for Shipment</option>
                                <option value="In Transit">In Transit (Dispatched)</option>
                            </select>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">PACKAGE COUNT</label>
                            <input type="number" id="modal-ship-pkg-count" min="1" value="1" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">TOTAL WEIGHT (KG)</label>
                            <input type="number" id="modal-ship-weight" step="0.1" min="0" placeholder="e.g. 12.5" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">ORIGIN DOCK / DISPATCH ADDRESS</label>
                            <input type="text" id="modal-ship-origin" value="Central Fulfillment Dock" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">DESTINATION WAREHOUSE / BAY</label>
                            <input type="text" id="modal-ship-dest" value="Central Inventory Receiving Bay 2" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                        </div>
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">EXPECTED DELIVERY DATE</label>
                        <input type="date" id="modal-ship-expected-delivery" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SHIPPING REMARKS</label>
                        <textarea id="modal-ship-notes" rows="2" placeholder="e.g. Handle with care, fragile components..." style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;"></textarea>
                    </div>
                </div>
            `;

            let currentPoRequestId = 0;
            let closeModalFn = null;

            const onSaveHandler = async (container, closeModal) => {
                const poSelect = document.getElementById('modal-ship-po-select');
                const poId = poSelect ? poSelect.value : '';
                if (!poId) {
                    throw new Error('Please select an accepted Purchase Order.');
                }

                const previewBox = document.getElementById('modal-ship-po-preview');
                if (!previewBox) {
                    throw new Error('Shipment allocation builder not initialized.');
                }

                const checkedBoxes = Array.from(previewBox.querySelectorAll('.alloc-item-checkbox:checked'));
                if (checkedBoxes.length === 0) {
                    const allRows = previewBox.querySelectorAll('tr.alloc-row, tr.alloc-row-disabled');
                    if (allRows.length > 0 && previewBox.querySelectorAll('.alloc-item-checkbox').length === 0) {
                        throw new Error('All products for this Purchase Order have already been fully allocated to existing shipments.');
                    }
                    throw new Error('Please select at least one product to allocate to this shipment consignment.');
                }

                const items = [];
                const seenPids = new Set();

                for (const cb of checkedBoxes) {
                    const pidStr = cb.getAttribute('data-product-id');
                    const pid = parseInt(pidStr, 10);
                    if (isNaN(pid) || pid <= 0) {
                        throw new Error('Invalid product selected in allocation.');
                    }

                    if (seenPids.has(pid)) {
                        throw new Error(`Duplicate product ID ${pid} selected in allocation.`);
                    }
                    seenPids.add(pid);

                    const qtyInput = previewBox.querySelector(`.alloc-qty-input[data-product-id="${pid}"]`);
                    const prodName = qtyInput ? (qtyInput.getAttribute('data-product-name') || `Product #${pid}`) : `Product #${pid}`;
                    const maxRem = parseInt(cb.getAttribute('data-max') || '0', 10);

                    if (!qtyInput) {
                        throw new Error(`Quantity input missing for ${prodName}.`);
                    }

                    const rawQty = qtyInput.value ? String(qtyInput.value).trim() : '';
                    if (!rawQty || !/^\d+$/.test(rawQty)) {
                        throw new Error(`Allocation quantity for "${prodName}" must be a valid positive integer.`);
                    }

                    const qty = parseInt(rawQty, 10);
                    if (qty <= 0) {
                        throw new Error(`Allocation quantity for "${prodName}" must be greater than zero.`);
                    }

                    if (maxRem > 0 && qty > maxRem) {
                        throw new Error(`Allocation quantity for "${prodName}" (${qty}) cannot exceed remaining allocatable quantity (${maxRem}).`);
                    }

                    const row = (cb && typeof cb.closest === 'function') ? cb.closest('tr') : null;
                    const skuEl = row ? row.querySelector('td:nth-child(2) div:nth-child(2)') : null;
                    const sku = skuEl ? skuEl.textContent.trim() : '';

                    items.push({
                        product_id: pid,
                        product_name: prodName,
                        sku: sku,
                        quantity: qty
                    });
                }

                const carrier = document.getElementById('modal-ship-carrier')?.value?.trim();
                if (!carrier) {
                    throw new Error('Please enter or select a logistics carrier.');
                }

                const trackingNumber = document.getElementById('modal-ship-tracking')?.value?.trim() || null;
                const method = document.getElementById('modal-ship-method')?.value || 'Standard Ground';
                const status = document.getElementById('modal-ship-status')?.value || 'Ready for Shipment';
                const pkgCountRaw = document.getElementById('modal-ship-pkg-count')?.value;
                const pkgCount = parseInt(pkgCountRaw, 10) || 1;
                if (pkgCount < 1) {
                    throw new Error('Package count must be at least 1.');
                }

                const weightVal = document.getElementById('modal-ship-weight')?.value;
                const totalWeight = weightVal && !isNaN(parseFloat(weightVal)) ? parseFloat(weightVal) : null;
                const origin = document.getElementById('modal-ship-origin')?.value?.trim() || 'Central Fulfillment Dock';
                const dest = document.getElementById('modal-ship-dest')?.value?.trim() || 'Central Inventory Receiving Bay 2';
                const expectedDelivery = document.getElementById('modal-ship-expected-delivery')?.value || null;
                const notes = document.getElementById('modal-ship-notes')?.value?.trim() || '';

                const selectedOption = (poSelect && poSelect.options) ? poSelect.options[poSelect.selectedIndex] : null;
                const poSummary = selectedOption ? (selectedOption.text || selectedOption.textContent) : `PO #${poId}`;

                const dispatchData = {
                    poId: parseInt(poId, 10),
                    poSummary,
                    carrier,
                    trackingNumber,
                    shippingMethod: method,
                    status,
                    packageCount: pkgCount,
                    totalWeight,
                    originAddress: origin,
                    destinationAddress: dest,
                    expectedDelivery,
                    shippingNotes: notes,
                    items
                };

                // Backward-compatibility hook for Phase D direct programmatic integration tests:
                if (typeof Modal.create !== 'function') {
                    const payload = {
                        purchase_order_id: parseInt(poId, 10),
                        carrier: carrier || 'Standard Logistics',
                        tracking_number: trackingNumber || null,
                        shipping_method: method,
                        status: status,
                        package_count: pkgCount,
                        total_weight: totalWeight,
                        origin_address: origin,
                        destination_address: dest,
                        expected_delivery: expectedDelivery,
                        shipping_notes: notes,
                        items: items.map(it => ({
                            product_id: it.product_id,
                            quantity: it.quantity
                        }))
                    };
                    const res = await Api.post('/shipments/', payload);
                    if (typeof Utils !== 'undefined' && Utils.showToast) {
                        Utils.showToast('Shipment created and dispatched successfully with product allocations', 'success');
                    }
                    if (typeof closeModal === 'function') closeModal();
                    else if (typeof closeModalFn === 'function') closeModalFn();
                    if (App.pages['shipments'] && typeof App.pages['shipments'].loadShipments === 'function') {
                        App.pages['shipments'].loadShipments();
                    }
                    return res;
                }

                // Standard Phase G review modal
                this.openPreDispatchReviewModal(dispatchData, closeModal || closeModalFn);
            };

            const footer = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <button type="button" class="btn btn-outline close-modal cancel-modal-btn">Cancel</button>
                    <button type="button" class="btn btn-primary save-modal-btn" id="modal-btn-to-review" style="background: #2563eb; border-color: #2563eb; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
                        Review &amp; Dispatch Consignment <i class='bx bx-right-arrow-alt'></i>
                    </button>
                </div>
            `;

            const modalOptions = {
                id: 'modal-create-shipment',
                title: 'Create & Dispatch Shipment 📦',
                content,
                footer,
                size: 'lg',
                saveText: 'Review & Dispatch Consignment',
                onSave: onSaveHandler,
                onOpen: (modalEl, closeModal) => {
                    closeModalFn = closeModal;
                }
            };

            if (typeof Modal !== 'undefined' && typeof Modal.show === 'function') {
                closeModalFn = Modal.show(modalOptions);
            } else if (typeof Modal !== 'undefined' && typeof Modal.create === 'function') {
                closeModalFn = Modal.create(modalOptions);
            }

            const poSelect = document.getElementById('modal-ship-po-select');
            const previewBox = document.getElementById('modal-ship-po-preview');
            const proceedBtn = document.getElementById('modal-btn-to-review') || (document.querySelector ? document.querySelector('.save-modal-btn') : null);

                    const updateAllocationSummary = () => {
                        if (!previewBox) return;
                        const checkedBoxes = Array.from(previewBox.querySelectorAll('.alloc-item-checkbox:checked'));
                        let totalUnits = 0;
                        checkedBoxes.forEach(cb => {
                            const pid = cb.getAttribute('data-product-id');
                            const inp = previewBox.querySelector(`.alloc-qty-input[data-product-id="${pid}"]`);
                            if (inp && inp.value && !isNaN(parseInt(inp.value, 10))) {
                                totalUnits += parseInt(inp.value, 10);
                            }
                        });

                        const countEl = previewBox.querySelector('#alloc-selected-count');
                        const unitsEl = previewBox.querySelector('#alloc-total-units');
                        const totalEligible = previewBox.querySelectorAll('.alloc-item-checkbox').length;

                        if (countEl) countEl.textContent = `${checkedBoxes.length} of ${totalEligible} product${totalEligible === 1 ? '' : 's'} selected`;
                        if (unitsEl) unitsEl.textContent = `Total Consignment Units: ${totalUnits}`;
                    };

                    poSelect.addEventListener('change', async (e) => {
                        const poId = e.target.value;
                        const thisReq = ++currentPoRequestId;

                        if (!poId) {
                            previewBox.style.display = 'none';
                            previewBox.innerHTML = '';
                            return;
                        }

                        try {
                            previewBox.style.display = 'block';
                            previewBox.innerHTML = `
                                <div style="text-align: center; padding: 24px; color: var(--text-secondary); font-size: 13px;">
                                    <i class='bx bx-loader-alt bx-spin' style="font-size: 22px; margin-bottom: 6px; display: block; color: #2563eb;"></i>
                                    Loading purchase order line items and allocation limits...
                                </div>
                            `;

                            const poData = await Api.get(`/purchase-orders/${poId}`);
                            if (thisReq !== currentPoRequestId) return; // Stale request discarded

                            const order = poData.purchase_order;
                            const items = (order && Array.isArray(order.items)) ? order.items : [];

                            if (items.length === 0) {
                                previewBox.innerHTML = `
                                    <div style="padding: 14px; text-align: center; color: var(--text-secondary);">
                                        <i class='bx bx-info-circle' style="font-size: 20px; color: #d97706;"></i>
                                        <div style="margin-top: 4px; font-size: 13px;">No items found in Purchase Order #${order.purchase_order_id}.</div>
                                    </div>
                                `;
                                return;
                            }

                            const escape = (str) => Utils.escapeHtml ? Utils.escapeHtml(str || '') : (str || '');

                            let rowsHtml = '';
                            let eligibleCount = 0;

                            items.forEach(item => {
                                const poQty = parseInt(item.quantity, 10) || 0;
                                const allocQty = item.allocated_quantity !== undefined ? parseInt(item.allocated_quantity, 10) : 0;
                                const remQty = item.remaining_quantity !== undefined ? parseInt(item.remaining_quantity, 10) : Math.max(0, poQty - allocQty);
                                const isFullyAllocated = remQty <= 0;

                                if (!isFullyAllocated) eligibleCount++;

                                rowsHtml += `
                                    <tr style="border-bottom: 1px solid var(--border); ${isFullyAllocated ? 'background: rgba(0,0,0,0.02); opacity: 0.65;' : ''}" class="${isFullyAllocated ? 'alloc-row-disabled' : 'alloc-row'}">
                                        <td style="padding: 8px 10px; text-align: center;">
                                            ${isFullyAllocated 
                                                ? `<input type="checkbox" disabled title="Fully allocated to other dispatches" style="cursor: not-allowed;">`
                                                : `<input type="checkbox" class="alloc-item-checkbox" data-product-id="${item.product_id}" data-max="${remQty}" checked style="cursor: pointer;">`
                                            }
                                        </td>
                                        <td style="padding: 8px 10px;">
                                            <div style="font-weight: 600; color: var(--text); font-size: 13px;">${escape(item.product_name)}</div>
                                            <div style="font-size: 11px; font-family: monospace; color: var(--text-secondary);">${escape(item.sku || 'N/A')}</div>
                                        </td>
                                        <td style="padding: 8px 10px; text-align: right; font-weight: 500;">${poQty}</td>
                                        <td style="padding: 8px 10px; text-align: right; color: var(--text-secondary);">${allocQty}</td>
                                        <td style="padding: 8px 10px; text-align: right; font-weight: 700; color: ${isFullyAllocated ? '#64748b' : '#059669'};">${remQty}</td>
                                        <td style="padding: 8px 10px; text-align: right;">
                                            ${isFullyAllocated 
                                                ? `<span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: rgba(100, 116, 139, 0.12); color: #64748b; font-size: 11px; font-weight: 600;">Fully Allocated</span>`
                                                : `<input type="number" class="alloc-qty-input" data-product-id="${item.product_id}" data-max="${remQty}" data-product-name="${escape(item.product_name)}"
                                                          min="1" max="${remQty}" step="1" value="${remQty}"
                                                          style="width: 100px; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border); font-size: 13px; font-weight: 600; text-align: right; background: var(--bg-surface, #ffffff); color: var(--text);">`
                                            }
                                        </td>
                                    </tr>
                                `;
                            });

                            previewBox.innerHTML = `
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid var(--border); padding-bottom: 8px;">
                                    <div>
                                        <div style="font-weight: 700; font-size: 14px; color: #1e40af;">PO #${order.purchase_order_id} Product Allocations</div>
                                        <div style="font-size: 12px; color: var(--text-secondary);">Order Date: ${order.order_date || 'N/A'} • Total Budget: ₹${(order.total_amount || 0).toLocaleString('en-IN')}</div>
                                    </div>
                                    <div style="font-size: 11px; padding: 4px 8px; border-radius: 6px; background: rgba(59, 130, 246, 0.1); color: #2563eb; font-weight: 600;">
                                        <i class='bx bx-check-shield'></i> Split Allocation Builder
                                    </div>
                                </div>

                                <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 10px;">
                                    Select the eligible products and quantities to allocate to this consignment.
                                </div>

                                <div style="border-radius: 8px; border: 1px solid var(--border); overflow: hidden; background: var(--card-bg, #ffffff);">
                                    <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
                                        <thead>
                                            <tr style="background: var(--bg-surface, #f8fafc); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                                <th style="padding: 8px 10px; width: 36px; text-align: center;">
                                                    <input type="checkbox" id="alloc-select-all" title="Select / Deselect All Products" ${eligibleCount > 0 ? 'checked' : 'disabled'} style="cursor: pointer;">
                                                </th>
                                                <th style="padding: 8px 10px;">Product &amp; SKU</th>
                                                <th style="padding: 8px 10px; text-align: right;">PO Qty</th>
                                                <th style="padding: 8px 10px; text-align: right;">Allocated</th>
                                                <th style="padding: 8px 10px; text-align: right;">Remaining</th>
                                                <th style="padding: 8px 10px; text-align: right; width: 130px;">Ship Quantity *</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${rowsHtml}
                                        </tbody>
                                    </table>
                                </div>

                                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 12px; font-weight: 600; color: var(--text-secondary);">
                                    <span id="alloc-selected-count">${eligibleCount} of ${items.length} products selected</span>
                                    <span id="alloc-total-units" style="color: #059669;">Total Consignment Units: 0</span>
                                </div>
                            `;

                            // Wire up checkbox toggles and quantity input handlers
                            const selectAllBox = previewBox.querySelector('#alloc-select-all');
                            const checkboxes = Array.from(previewBox.querySelectorAll('.alloc-item-checkbox'));
                            const qtyInputs = Array.from(previewBox.querySelectorAll('.alloc-qty-input'));

                            const syncRowState = (cb) => {
                                const pid = cb.getAttribute('data-product-id');
                                const maxRem = parseInt(cb.getAttribute('data-max') || '0', 10);
                                const inp = previewBox.querySelector(`.alloc-qty-input[data-product-id="${pid}"]`);
                                if (!inp) return;

                                if (cb.checked) {
                                    inp.disabled = false;
                                    inp.style.opacity = '1';
                                    if (!inp.value || parseInt(inp.value, 10) <= 0) {
                                        inp.value = maxRem;
                                    }
                                } else {
                                    inp.disabled = true;
                                    inp.style.opacity = '0.5';
                                }
                            };

                            checkboxes.forEach(cb => {
                                cb.addEventListener('change', () => {
                                    syncRowState(cb);
                                    if (selectAllBox) {
                                        selectAllBox.checked = checkboxes.every(c => c.checked);
                                        selectAllBox.indeterminate = checkboxes.some(c => c.checked) && !selectAllBox.checked;
                                    }
                                    updateAllocationSummary();
                                });
                            });

                            if (selectAllBox) {
                                selectAllBox.addEventListener('change', (ev) => {
                                    const isChecked = ev.target.checked;
                                    checkboxes.forEach(cb => {
                                        cb.checked = isChecked;
                                        syncRowState(cb);
                                    });
                                    updateAllocationSummary();
                                });
                            }

                            qtyInputs.forEach(inp => {
                                inp.addEventListener('input', () => {
                                    const maxRem = parseInt(inp.getAttribute('data-max') || '0', 10);
                                    const val = parseInt(inp.value, 10);
                                    if (maxRem > 0 && val > maxRem) {
                                        inp.value = maxRem;
                                        if (typeof Utils !== 'undefined' && Utils.showToast) {
                                            Utils.showToast(`Quantity capped at maximum remaining allocatable units (${maxRem}).`, 'warning');
                                        }
                                    }
                                    updateAllocationSummary();
                                });
                            });

                            updateAllocationSummary();

                        } catch (err) {
                            if (thisReq !== currentPoRequestId) return;
                            previewBox.innerHTML = `
                                <div style="padding: 12px; border-radius: 6px; background: rgba(239, 68, 68, 0.08); color: var(--red); font-size: 13px;">
                                    <i class='bx bx-error-circle'></i> Error loading purchase order line items: ${escape(err.message || 'Server error')}
                                </div>
                            `;
                        }
                    });

                    // Pre-select PO if specified
                    if (preselectedPoId && targetPo) {
                        poSelect.value = String(preselectedPoId);
                        poSelect.dispatchEvent(new Event('change'));
                    }

            // Proceed to Review & Confirmation
            if (proceedBtn) {
                proceedBtn.addEventListener('click', async () => {
                    try {
                        await onSaveHandler(document.getElementById('modal-create-shipment'), closeModalFn);
                    } catch (err) {
                        if (typeof Utils !== 'undefined' && Utils.showToast) {
                            Utils.showToast(err.message, 'error');
                        } else if (typeof alert === 'function') {
                            alert(err.message);
                        }
                    }
                });
            }

        } catch (err) {
            if (typeof Utils !== 'undefined' && Utils.showToast) {
                Utils.showToast(`Error opening shipment builder: ${err.message}`, 'error');
            } else if (typeof alert === 'function') {
                alert(`Error opening shipment builder: ${err.message}`);
            }
        }
    },

    // Step 2: Pre-Dispatch Review and Confirmation Modal
    openPreDispatchReviewModal(data, closeCreateModal) {
        const totalUnits = data.items.reduce((sum, item) => sum + item.quantity, 0);

        const content = `
            <div style="display: flex; flex-direction: column; gap: 14px; font-size: 13px;">
                <div style="background: rgba(37, 99, 235, 0.06); border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 8px; padding: 12px 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: #2563eb;">Target Purchase Order</div>
                            <div style="font-size: 15px; font-weight: 700; color: var(--text);">${Utils.escapeHtml(data.poSummary || `PO #${data.poId}`)}</div>
                        </div>
                        <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #059669; font-weight: 700; font-size: 11px; padding: 4px 10px;">
                            <i class='bx bx-check-circle'></i> Verified for Dispatch
                        </span>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: var(--bg-surface, #f8fafc); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px;">
                    <div>
                        <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Logistics Carrier &amp; Tracking</span>
                        <div style="font-weight: 600; color: var(--text); margin-top: 2px;">${Utils.escapeHtml(data.carrier || 'Standard Logistics')}</div>
                        <div style="font-size: 11px; font-family: monospace; color: var(--text-secondary);">${data.trackingNumber ? Utils.escapeHtml(data.trackingNumber) : 'No tracking number entered'}</div>
                    </div>
                    <div>
                        <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Method &amp; Initial Status</span>
                        <div style="font-weight: 600; color: var(--text); margin-top: 2px;">${Utils.escapeHtml(data.shippingMethod || 'Standard Ground')}</div>
                        <div style="font-size: 11px; color: #2563eb; font-weight: 600;">${Utils.escapeHtml(data.status || 'Ready for Shipment')}</div>
                    </div>
                    <div>
                        <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Origin ➔ Destination</span>
                        <div style="font-size: 12px; color: var(--text); margin-top: 2px;">${Utils.escapeHtml(data.originAddress || 'Origin Dock')} ➔ ${Utils.escapeHtml(data.destinationAddress || 'Warehouse Bay')}</div>
                    </div>
                    <div>
                        <span style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Packages, Weight &amp; Delivery</span>
                        <div style="font-size: 12px; color: var(--text); margin-top: 2px;">${data.packageCount} pkg${data.packageCount === 1 ? '' : 's'} • ${data.totalWeight ? data.totalWeight + ' kg' : 'Weight unrecorded'}</div>
                        <div style="font-size: 11px; color: var(--text-secondary);">Est. Arrival: ${data.expectedDelivery || 'Not specified'}</div>
                    </div>
                </div>

                <div style="border-radius: 8px; border: 1px solid var(--border); overflow: hidden;">
                    <div style="padding: 10px 14px; background: var(--bg-surface, #f1f5f9); border-bottom: 1px solid var(--border); font-weight: 700; font-size: 12px; color: var(--text); display: flex; justify-content: space-between; align-items: center;">
                        <span>CONSIGNMENT ALLOCATED PRODUCTS (${data.items.length})</span>
                        <span style="color: #059669; font-weight: 700;">Total Units: ${totalUnits}</span>
                    </div>
                    <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                        <thead>
                            <tr style="background: var(--card-bg, #ffffff); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 8px 12px; width: 36px; text-align: center;">#</th>
                                <th style="padding: 8px 12px; text-align: left;">Product Name</th>
                                <th style="padding: 8px 12px; text-align: left;">SKU</th>
                                <th style="padding: 8px 12px; text-align: right; width: 120px;">Dispatch Qty</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.items.map((it, idx) => `
                                <tr style="border-bottom: 1px solid var(--border);">
                                    <td style="padding: 8px 12px; text-align: center; color: var(--text-secondary);">${idx + 1}</td>
                                    <td style="padding: 8px 12px; font-weight: 600; color: var(--text);">${Utils.escapeHtml(it.product_name)}</td>
                                    <td style="padding: 8px 12px; font-family: monospace; color: var(--text-secondary);">${Utils.escapeHtml(it.sku || 'N/A')}</td>
                                    <td style="padding: 8px 12px; text-align: right; font-weight: 700; color: #059669; font-size: 13px;">${it.quantity}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="background: var(--bg-surface, #f8fafc); font-weight: 700;">
                                <td colspan="3" style="padding: 8px 12px; text-align: right; font-size: 12px;">Total Dispatched Units:</td>
                                <td style="padding: 8px 12px; text-align: right; font-size: 14px; color: #059669;">${totalUnits}</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                ${data.shippingNotes ? `
                    <div style="font-size: 12px; color: var(--text-secondary); background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <strong style="color: var(--text);">Remarks:</strong> "${Utils.escapeHtml(data.shippingNotes)}"
                    </div>
                ` : ''}

                <div style="padding: 10px 14px; border-radius: 6px; background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.2); font-size: 12px; color: #1e40af;">
                    <i class='bx bx-info-circle'></i> Confirming dispatch will atomically persist this consignment with <strong>${totalUnits} total units</strong> into official Shipment records and update remaining Purchase Order balances.
                </div>
            </div>
        `;

        const footer = `
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                <button type="button" class="btn btn-outline" id="modal-btn-review-back">
                    <i class='bx bx-left-arrow-alt'></i> Back to Edit
                </button>
                <button type="button" class="btn btn-primary" id="modal-btn-review-confirm" style="background: #059669; border-color: #059669; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
                    <i class='bx bx-check-double'></i> Confirm &amp; Dispatch Consignment
                </button>
            </div>
        `;

        Modal.create({
            id: 'modal-predispatch-review',
            title: 'Review & Confirm Shipment Dispatch 📋',
            content,
            footer,
            size: 'lg',
            onOpen: (reviewModalEl, closeReviewModal) => {
                const backBtn = reviewModalEl.querySelector('#modal-btn-review-back');
                const confirmBtn = reviewModalEl.querySelector('#modal-btn-review-confirm');

                if (backBtn) {
                    backBtn.addEventListener('click', () => {
                        closeReviewModal();
                    });
                }

                if (confirmBtn) {
                    let isSubmitting = false;
                    confirmBtn.addEventListener('click', async () => {
                        if (isSubmitting) return;
                        isSubmitting = true;
                        confirmBtn.disabled = true;
                        if (backBtn) backBtn.disabled = true;
                        confirmBtn.innerHTML = "<i class='bx bx-loader-alt bx-spin'></i> Dispatching Consignment...";

                        try {
                            const payload = {
                                purchase_order_id: parseInt(data.poId, 10),
                                carrier: data.carrier || 'Standard Logistics',
                                tracking_number: data.trackingNumber || null,
                                shipping_method: data.shippingMethod,
                                status: data.status,
                                package_count: data.packageCount,
                                total_weight: data.totalWeight,
                                origin_address: data.originAddress,
                                destination_address: data.destinationAddress,
                                expected_delivery: data.expectedDelivery,
                                shipping_notes: data.shippingNotes,
                                items: data.items.map(it => ({
                                    product_id: it.product_id,
                                    quantity: it.quantity
                                }))
                            };

                            const res = await Api.post('/shipments/', payload);

                            if (!res || !res.shipment || !res.shipment.shipment_id) {
                                throw new Error('Shipment was created, but server response did not include a valid shipment ID.');
                            }

                            const newShipmentId = res.shipment.shipment_id;
                            const newShipmentNum = res.shipment.shipment_number || ('#' + newShipmentId);

                            closeReviewModal();
                            if (closeCreateModal) closeCreateModal();

                            Utils.showToast(`Shipment ${newShipmentNum} dispatched successfully!`, 'success');

                            if (App.pages['shipments'] && typeof App.pages['shipments'].loadShipments === 'function') {
                                App.pages['shipments'].loadShipments();
                            }

                            // Open shipment details modal displaying generated shipment ID and allocated items
                            if (App.pages['shipments'] && typeof App.pages['shipments'].openShipmentDetailsModal === 'function') {
                                await App.pages['shipments'].openShipmentDetailsModal(newShipmentId);
                            }
                        } catch (err) {
                            isSubmitting = false;
                            confirmBtn.disabled = false;
                            if (backBtn) backBtn.disabled = false;
                            confirmBtn.innerHTML = "<i class='bx bx-check-double'></i> Confirm &amp; Dispatch Consignment";
                            Utils.showToast(err.message || 'Failed to dispatch shipment', 'error');
                        }
                    });
                }
            }
        });
    },

    // Update Status Modal
    async openUpdateStatusModal(shipmentId) {
        try {
            const data = await Api.get(`/shipments/${shipmentId}`);
            const s = data.shipment;

            const transitionsMap = {
                'ready for shipment': ['Dispatched', 'In Transit', 'Cancelled'],
                'dispatched': ['In Transit', 'Delayed', 'Delivered', 'Cancelled'],
                'in transit': ['Delivered', 'Delayed', 'Cancelled'],
                'delayed': ['In Transit', 'Delivered', 'Cancelled']
            };

            const currLower = (s.status || '').toLowerCase();
            const allowedNext = transitionsMap[currLower] || [];

            if (allowedNext.length === 0) {
                alert(`Shipment is in '${s.status}' status and cannot be transitioned further.`);
                return;
            }

            const content = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div style="padding: 12px; border-radius: 8px; background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2);">
                        <div style="font-weight: 700; font-size: 14px; color: #1e40af;">${s.shipment_number} (Carrier: ${s.carrier})</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Current Status: <strong>${s.status}</strong></div>
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">NEW STATUS *</label>
                        <select id="update-status-select" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                            ${allowedNext.map(st => `<option value="${st}">${st}</option>`).join('')}
                        </select>
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">CURRENT LOCATION</label>
                        <input type="text" id="update-status-location" placeholder="e.g. Regional Sorting Facility, Pune" 
                               style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">TRANSIT REMARKS / NOTES</label>
                        <textarea id="update-status-notes" rows="2" placeholder="e.g. Scanned at outbound dock, on schedule for arrival..." 
                                  style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;"></textarea>
                    </div>
                </div>
            `;

            Modal.show({
                title: 'Update Logistics Status 🔄',
                content,
                saveText: 'Update Status',
                onSave: async (closeModal) => {
                    const newStatus = document.getElementById('update-status-select').value;
                    const location = document.getElementById('update-status-location').value;
                    const notes = document.getElementById('update-status-notes').value;

                    try {
                        await Api.patch(`/shipments/${shipmentId}/status`, {
                            status: newStatus,
                            location: location || null,
                            notes: notes || null
                        });
                        closeModal();
                        alert(`Shipment status updated to '${newStatus}'.`);
                        App.pages['shipments'].loadShipments();
                    } catch (err) {
                        alert(`Status update failed: ${err.message}`);
                    }
                }
            });

        } catch (err) {
            alert(`Error loading shipment: ${err.message}`);
        }
    },

    // Edit Shipment Details Modal (Supplier only)
    async openEditShipmentModal(shipmentId) {
        try {
            const data = await Api.get(`/shipments/${shipmentId}`);
            const s = data.shipment;

            const content = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">CARRIER</label>
                            <input type="text" id="edit-ship-carrier" value="${s.carrier}" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">TRACKING NUMBER</label>
                            <input type="text" id="edit-ship-tracking" value="${s.tracking_number || ''}" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">PACKAGES</label>
                            <input type="number" id="edit-ship-pkg" min="1" value="${s.package_count || 1}" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">WEIGHT (KG)</label>
                            <input type="number" id="edit-ship-weight" step="0.1" value="${s.total_weight || ''}" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">EXPECTED DELIVERY</label>
                        <input type="date" id="edit-ship-expected" value="${s.expected_delivery || ''}" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SHIPPING NOTES</label>
                        <textarea id="edit-ship-notes" rows="2" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border);">${s.shipping_notes || ''}</textarea>
                    </div>
                </div>
            `;

            Modal.show({
                title: 'Edit Shipment Details ✏️',
                content,
                saveText: 'Save Details',
                onSave: async (closeModal) => {
                    const carrier = document.getElementById('edit-ship-carrier').value;
                    const tracking = document.getElementById('edit-ship-tracking').value;
                    const pkg = parseInt(document.getElementById('edit-ship-pkg').value);
                    const weight = document.getElementById('edit-ship-weight').value;
                    const expected = document.getElementById('edit-ship-expected').value;
                    const notes = document.getElementById('edit-ship-notes').value;

                    try {
                        await Api.put(`/shipments/${shipmentId}`, {
                            carrier: carrier || 'Standard Logistics',
                            tracking_number: tracking || '',
                            package_count: pkg || 1,
                            total_weight: weight ? parseFloat(weight) : null,
                            expected_delivery: expected || null,
                            shipping_notes: notes || ''
                        });
                        closeModal();
                        alert('Shipment details updated successfully.');
                        App.pages['shipments'].loadShipments();
                    } catch (err) {
                        alert(`Update failed: ${err.message}`);
                    }
                }
            });

        } catch (err) {
            alert(`Error opening shipment editor: ${err.message}`);
        }
    },

    // View Shipment Details Modal with OrderStatusHistory Audit Timeline & Receiving Progress
    async openShipmentDetailsModal(shipmentId) {
        try {
            const data = await Api.get(`/shipments/${shipmentId}`);
            const s = data.shipment;
            const po = s.purchase_order || { items: [] };
            const history = s.status_history || [];

            const statusBadge = this.getStatusBadge(s.status);
            const user = Auth.getUser();
            const currentUserId = user ? parseInt(user.id || user.user_id || 0) : 0;
            const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');
            const isAssignedEmployee = user && user.role === 'Employee' && parseInt(s.assigned_employee_id) === currentUserId;
            const isDelivered = s.status && s.status.toLowerCase() === 'delivered';
            const remQty = s.total_remaining_quantity !== undefined ? s.total_remaining_quantity : 0;
            const canStockIn = isDelivered && remQty > 0 && (isManagerOrOwner || isAssignedEmployee);

            let recBadge = '';
            const recStatus = s.receiving_status || 'Pending Receipt';
            if (recStatus === 'Fully Received') {
                recBadge = `<span style="padding: 3px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; font-weight: 600;"><i class='bx bx-check-double'></i> Fully Received</span>`;
            } else if (recStatus === 'Partially Received') {
                recBadge = `<span style="padding: 3px 8px; border-radius: 6px; background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 11px; font-weight: 600;"><i class='bx bx-pie-chart-alt'></i> Partially Received</span>`;
            } else {
                recBadge = `<span style="padding: 3px 8px; border-radius: 6px; background: rgba(107, 114, 128, 0.12); color: #4b5563; font-size: 11px; font-weight: 600;"><i class='bx bx-time'></i> Pending Receipt</span>`;
            }

            const content = `
                <div style="display: flex; flex-direction: column; gap: 16px;">
                    <!-- Header Block -->
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; padding: 16px; border-radius: 8px; background: var(--bg-surface, #f9fafb); border: 1px solid var(--border);">
                        <div>
                            <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Shipment Number</div>
                            <h2 style="font-size: 20px; font-weight: 700; margin: 4px 0; color: var(--text);">${s.shipment_number}</h2>
                            <div style="font-size: 12px; color: var(--text-secondary);">PO #${s.purchase_order_id} • Supplier: ${s.supplier_name}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="margin-bottom: 6px;">${statusBadge}</div>
                            <div style="font-size: 13px; font-weight: 600; color: #2563eb;">${s.carrier}</div>
                            <div style="font-size: 11px; font-family: monospace; color: var(--text-secondary);">${s.tracking_number || 'No tracking #'}</div>
                        </div>
                    </div>

                    <!-- Dispatch, Delivery & Assignment Details -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px;">
                        <div style="padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Origin &amp; Dispatch</div>
                            <div style="font-weight: 600; font-size: 13px; color: var(--text);">${s.origin_address || 'Origin Dock'}</div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                                Shipped: ${s.shipped_at ? new Date(s.shipped_at).toLocaleString() : 'Pending'}
                            </div>
                            <div style="font-size: 12px; color: var(--text-secondary);">
                                Method: ${s.shipping_method || 'Standard Ground'}
                            </div>
                        </div>

                        <div style="padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Destination &amp; Arrival</div>
                            <div style="font-weight: 600; font-size: 13px; color: var(--text);">${s.destination_address || 'Warehouse Bay'}</div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                                Est. Delivery: ${s.expected_delivery || 'Not specified'}
                            </div>
                            <div style="font-size: 12px; color: #059669; font-weight: 600;">
                                ${s.delivered_at ? `Delivered: ${new Date(s.delivered_at).toLocaleString()}` : ''}
                            </div>
                        </div>

                        <div style="padding: 12px; border-radius: 8px; border: 1px solid var(--border); background: rgba(248, 250, 252, 0.6);">
                            <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Warehouse Receipt &amp; Staff</div>
                            <div style="display: flex; align-items: center; gap: 6px; margin-top: 2px;">
                                <i class='bx bx-user' style="color: #4f46e5; font-size: 16px;"></i>
                                <span style="font-weight: 600; font-size: 13px; color: var(--text);">${s.assigned_employee_name || 'Unassigned'}</span>
                            </div>
                            <div style="margin-top: 6px;">
                                ${recBadge}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">
                                Rec: <strong>${s.total_received_quantity || 0}</strong> / Exp: <strong>${s.total_expected_quantity || 0}</strong>
                            </div>
                        </div>
                    </div>

                    <!-- Purchase Order Items & Receiving Quantities Table -->
                    <div style="border-radius: 8px; border: 1px solid var(--border); overflow: hidden;">
                        <div style="padding: 10px 14px; background: var(--bg-surface, #f9fafb); border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 600; font-size: 12px; text-transform: uppercase; color: var(--text-secondary);">
                                Shipment Contents &amp; Receiving Progress (${po.items.length} item${po.items.length === 1 ? '' : 's'})
                            </span>
                            <span style="font-size: 11px; color: var(--text-secondary);">
                                Total Expected: <strong>${s.total_expected_quantity || 0}</strong> • Received: <strong>${s.total_received_quantity || 0}</strong> • Remaining: <strong>${s.total_remaining_quantity || 0}</strong>
                            </span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                            <thead>
                                <tr style="background: rgba(0,0,0,0.01); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 8px 12px; text-align: left;">Product</th>
                                    <th style="padding: 8px 12px; text-align: left;">SKU</th>
                                    <th style="padding: 8px 12px; text-align: right;">Expected</th>
                                    <th style="padding: 8px 12px; text-align: right;">Received</th>
                                    <th style="padding: 8px 12px; text-align: right;">Remaining</th>
                                    <th style="padding: 8px 12px; text-align: center;">Receiving Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${po.items.map(item => {
                                    const exp = item.expected_quantity !== undefined ? item.expected_quantity : item.quantity;
                                    const rec = item.received_quantity || 0;
                                    const rem = item.remaining_quantity !== undefined ? item.remaining_quantity : Math.max(0, exp - rec);
                                    let itemStatusBadge = '';
                                    if (rec >= exp && exp > 0) {
                                        itemStatusBadge = `<span style="padding: 2px 6px; border-radius: 4px; background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; font-weight: 600;">Fully Received</span>`;
                                    } else if (rec > 0) {
                                        itemStatusBadge = `<span style="padding: 2px 6px; border-radius: 4px; background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 11px; font-weight: 600;">Partial (${rec}/${exp})</span>`;
                                    } else {
                                        itemStatusBadge = `<span style="padding: 2px 6px; border-radius: 4px; background: rgba(107, 114, 128, 0.1); color: #64748b; font-size: 11px;">Pending</span>`;
                                    }

                                    return `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 8px 12px; font-weight: 500;">${item.product_name}</td>
                                            <td style="padding: 8px 12px; font-family: monospace; color: var(--text-secondary); font-size: 12px;">${item.sku}</td>
                                            <td style="padding: 8px 12px; text-align: right; font-weight: 600;">${exp}</td>
                                            <td style="padding: 8px 12px; text-align: right; font-weight: 600; color: #059669;">${rec}</td>
                                            <td style="padding: 8px 12px; text-align: right; font-weight: 600; color: ${rem > 0 ? '#d97706' : 'var(--text-secondary)'};">${rem}</td>
                                            <td style="padding: 8px 12px; text-align: center;">${itemStatusBadge}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>

                    <!-- Chronological Logistics Audit Trail -->
                    <div style="border-radius: 8px; border: 1px solid var(--border); padding: 14px;">
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 10px;">
                            <i class='bx bx-history'></i> Shipment Status History
                        </div>
                        ${history.length === 0 ? `
                            <div style="font-size: 12px; color: var(--text-light);">No historical events recorded for this shipment yet.</div>
                        ` : `
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                ${history.map(h => `
                                    <div style="display: flex; gap: 10px; align-items: flex-start; font-size: 12px;">
                                        <div style="width: 8px; height: 8px; border-radius: 50%; background: #2563eb; margin-top: 5px; flex-shrink: 0;"></div>
                                        <div style="flex: 1;">
                                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                                <strong style="color: var(--text);">${h.action} (${h.status})</strong>
                                                <span style="color: var(--text-secondary); font-size: 11px;">${h.created_at ? new Date(h.created_at).toLocaleString() : ''}</span>
                                            </div>
                                            <div style="color: var(--text-secondary); margin-top: 2px;">
                                                ${h.location ? `<span>📍 ${h.location} • </span>` : ''}
                                                <span>${h.notes || 'Status updated'}</span>
                                                <span style="color: var(--text-light); margin-left: 6px;">[By ${h.changed_by || 'System'}]</span>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        `}
                    </div>
                </div>
            `;

            Modal.create({
                id: 'modal-shipment-details',
                title: 'Shipment Tracking Details 📍',
                content,
                footer: `
                    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                        <div>
                            ${canStockIn ? `
                                <button class="btn btn-primary receive-stock-direct-btn" style="background: #059669; border-color: #059669;">
                                    <i class='bx bx-download'></i> Receive Stock Now
                                </button>
                            ` : ''}
                        </div>
                        <button class="btn btn-outline close-details-btn">Close</button>
                    </div>
                `,
                onOpen: (overlay, closeModal) => {
                    overlay.querySelector('.close-details-btn').onclick = closeModal;
                    const stockInBtn = overlay.querySelector('.receive-stock-direct-btn');
                    if (stockInBtn) {
                        stockInBtn.onclick = () => {
                            closeModal();
                            App.pages['shipments'].openReceiveStockModal(shipmentId);
                        };
                    }
                }
            });

        } catch (err) {
            alert(`Error viewing shipment: ${err.message}`);
        }
    },

    // Manager / Owner: Assign Employee Modal
    async openAssignEmployeeModal(shipmentId) {
        try {
            const [usersData, shipData] = await Promise.all([
                Api.get('/users/?role=Employee'),
                Api.get(`/shipments/${shipmentId}`)
            ]);

            const s = shipData.shipment;
            const employees = (usersData.users || []).filter(u => u.status === 'Active');

            if (employees.length === 0) {
                alert('No active employees found to assign.');
                return;
            }

            const content = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div style="padding: 12px; border-radius: 8px; background: rgba(79, 70, 229, 0.05); border: 1px solid rgba(79, 70, 229, 0.2);">
                        <div style="font-weight: 700; font-size: 14px; color: #4f46e5;">${s.shipment_number}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">PO #${s.purchase_order_id} • Status: <strong>${s.status}</strong></div>
                        <div style="font-size: 12px; color: var(--text); margin-top: 4px;">
                            Current Assigned Staff: <strong>${s.assigned_employee_name || 'None (Unassigned)'}</strong>
                        </div>
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SELECT EMPLOYEE *</label>
                        <select id="assign-employee-select" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                            <option value="">-- Choose active warehouse employee --</option>
                            ${employees.map(emp => `
                                <option value="${emp.user_id}" ${s.assigned_employee_id === emp.user_id ? 'selected' : ''}>
                                    ${emp.username} (${emp.email})
                                </option>
                            `).join('')}
                        </select>
                        <small style="color: var(--text-secondary); font-size: 11px; margin-top: 4px; display: block;">
                            The assigned employee will have exclusive authorization to physically inspect and receive stock into inventory for this shipment.
                        </small>
                    </div>
                </div>
            `;

            Modal.show({
                title: 'Assign Warehouse Employee 👤',
                content,
                saveText: 'Assign Employee',
                onSave: async (container) => {
                    const empIdVal = document.getElementById('assign-employee-select').value;
                    if (!empIdVal) {
                        throw new Error('Please select an employee.');
                    }

                    await Api.patch(`/shipments/${shipmentId}/assign`, {
                        employee_id: parseInt(empIdVal)
                    });

                    Utils.showToast('Employee assigned to shipment successfully!', 'success');
                    App.pages['shipments'].loadShipments();
                }
            });

        } catch (err) {
            alert(`Error loading assignment modal: ${err.message}`);
        }
    },

    // Stock-In / Receive Stock Modal (Step 6 Goods Receipt)
    async openReceiveStockModal(shipmentId) {
        try {
            const data = await Api.get(`/shipments/${shipmentId}`);
            const s = data.shipment;
            const po = s.purchase_order || { items: [] };

            if (!s.status || s.status.toLowerCase() !== 'delivered') {
                alert(`Shipment is '${s.status}'. Stock-In is only allowed when shipment is 'Delivered'.`);
                return;
            }

            const items = po.items || [];
            const receivableItems = items.filter(it => (it.remaining_quantity !== undefined ? it.remaining_quantity : it.quantity) > 0);

            if (receivableItems.length === 0) {
                alert('All items in this shipment have already been fully received!');
                return;
            }

            const defaultItem = receivableItems[0];
            const defaultRemaining = defaultItem.remaining_quantity !== undefined ? defaultItem.remaining_quantity : defaultItem.quantity;

            const content = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <!-- Shipment Header Summary -->
                    <div style="padding: 12px; border-radius: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="font-weight: 700; font-size: 15px; color: #065f46;">${s.shipment_number}</div>
                            <span style="padding: 2px 8px; border-radius: 6px; background: #059669; color: white; font-size: 11px; font-weight: 600;">DELIVERED</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                            Supplier: <strong>${s.supplier_name}</strong> • Carrier: <strong>${s.carrier}</strong> (${s.tracking_number || 'No tracking'})
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                            Assigned Staff: <strong>${s.assigned_employee_name || 'Unassigned'}</strong>
                        </div>
                    </div>

                    <!-- Items Overview Table -->
                    <div style="border-radius: 8px; border: 1px solid var(--border); overflow: hidden;">
                        <div style="padding: 8px 12px; background: var(--bg-surface, #f9fafb); border-bottom: 1px solid var(--border); font-weight: 600; font-size: 11px; text-transform: uppercase; color: var(--text-secondary);">
                            Shipment Items Expected vs Received
                        </div>
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                            <thead>
                                <tr style="background: rgba(0,0,0,0.01); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px;">
                                    <th style="padding: 6px 10px; text-align: left;">Product</th>
                                    <th style="padding: 6px 10px; text-align: right;">Expected</th>
                                    <th style="padding: 6px 10px; text-align: right;">Received</th>
                                    <th style="padding: 6px 10px; text-align: right;">Remaining</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${items.map(it => {
                                    const exp = it.expected_quantity !== undefined ? it.expected_quantity : it.quantity;
                                    const rec = it.received_quantity || 0;
                                    const rem = it.remaining_quantity !== undefined ? it.remaining_quantity : Math.max(0, exp - rec);
                                    return `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 6px 10px; font-weight: 500;">${it.product_name}</td>
                                            <td style="padding: 6px 10px; text-align: right;">${exp}</td>
                                            <td style="padding: 6px 10px; text-align: right; color: #059669; font-weight: 600;">${rec}</td>
                                            <td style="padding: 6px 10px; text-align: right; font-weight: 600; color: ${rem > 0 ? '#d97706' : '#64748b'};">${rem}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>

                    <!-- Stock-In Input Form -->
                    <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 4px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SELECT PRODUCT TO RECEIVE *</label>
                            <select id="stockin-product-select" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                                ${receivableItems.map(it => {
                                    const rem = it.remaining_quantity !== undefined ? it.remaining_quantity : it.quantity;
                                    return `<option value="${it.product_id}" data-remaining="${rem}">${it.product_name} (${it.sku}) — Remaining: ${rem} units</option>`;
                                }).join('')}
                            </select>
                        </div>

                        <div>
                            <label style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">
                                <span>ACTUAL QUANTITY RECEIVED *</span>
                                <span id="stockin-max-hint" style="color: #059669; font-weight: 600;">Max: ${defaultRemaining} units</span>
                            </label>
                            <input type="number" id="stockin-quantity-input" min="1" max="${defaultRemaining}" value="${defaultRemaining}" 
                                   style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 14px; font-weight: 600;">
                            <small style="color: var(--text-secondary); font-size: 11px; margin-top: 4px; display: block;">
                                Supports partial receipt. Entering less than remaining keeps shipment open for future receipts.
                            </small>
                        </div>

                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">RECEIVING INSPECTION NOTES</label>
                            <textarea id="stockin-notes-input" rows="2" placeholder="e.g. Physical package intact, verified serials & batch numbers..." 
                                      style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;"></textarea>
                        </div>
                    </div>
                </div>
            `;

            Modal.show({
                title: 'Stock-In / Receive Goods 📥',
                content,
                saveText: 'Confirm Stock-In',
                onSave: async (container) => {
                    const prodSelect = document.getElementById('stockin-product-select');
                    const qtyInput = document.getElementById('stockin-quantity-input');
                    const notesInput = document.getElementById('stockin-notes-input');

                    const productId = parseInt(prodSelect.value);
                    const quantity = parseInt(qtyInput.value);
                    const notes = notesInput.value ? notesInput.value.trim() : '';

                    if (!productId) {
                        throw new Error('Please select a product.');
                    }
                    if (isNaN(quantity) || quantity <= 0) {
                        throw new Error('Quantity received must be a positive number.');
                    }

                    const selectedOpt = prodSelect.options[prodSelect.selectedIndex];
                    const maxRem = parseInt(selectedOpt.getAttribute('data-remaining') || '0');
                    if (quantity > maxRem) {
                        throw new Error(`Quantity (${quantity}) exceeds receivable remaining quantity (${maxRem}).`);
                    }

                    await Api.post('/inventory/stock-in', {
                        shipment_id: shipmentId,
                        product_id: productId,
                        quantity: quantity,
                        notes: notes || 'Received and verified at warehouse dock'
                    });

                    Utils.showToast(`Successfully stocked in ${quantity} units into inventory!`, 'success');
                    App.pages['shipments'].loadShipments();
                }
            });

            // Dynamic change handler for product dropdown to update max receivable
            setTimeout(() => {
                const prodSelect = document.getElementById('stockin-product-select');
                const qtyInput = document.getElementById('stockin-quantity-input');
                const maxHint = document.getElementById('stockin-max-hint');
                if (prodSelect && qtyInput) {
                    prodSelect.addEventListener('change', () => {
                        const selectedOpt = prodSelect.options[prodSelect.selectedIndex];
                        const maxRem = parseInt(selectedOpt.getAttribute('data-remaining') || '0');
                        qtyInput.max = maxRem;
                        qtyInput.value = maxRem;
                        if (maxHint) maxHint.textContent = `Max: ${maxRem} units`;
                    });
                }
            }, 50);

        } catch (err) {
            alert(`Error loading receiving modal: ${err.message}`);
        }
    }
};

