// stock-requests.js - Step 2/Supplier Portal Stock Requests Module

App.pages['stock-requests'] = {
    currentRequests: [],
    suppliersList: [],
    productsList: [],
    filters: {
        search: '',
        status: 'All Status',
        priority: 'All Priority',
        sort: 'latest'
    },

    render() {
        const container = document.createElement('div');
        const user = Auth.getUser() || {};
        const isSupplier = user.role === 'Supplier';
        const isManagerOrOwner = user.role === 'Owner' || user.role === 'Manager';

        container.innerHTML = `
            <div class="page-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <span class="eyebrow" style="font-size: 11px; font-weight: 700; letter-spacing: 1px; color: var(--primary); text-transform: uppercase;">PROCUREMENT WORKFLOW</span>
                    <h1 style="font-size: 24px; font-weight: 700; margin: 4px 0; color: var(--text);">Stock Requests 📋</h1>
                    <p style="color: var(--text-light); margin: 0; font-size: 14px;">
                        ${isSupplier 
                            ? 'Review incoming stock requests, respond with availability, and submit quotation pricing.' 
                            : 'Create and track stock requests sent to suppliers, monitor fulfillment responses, and review quotations.'}
                    </p>
                </div>
                <div class="header-actions" style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <button class="btn secondary" id="btn-refresh-stock-reqs" title="Refresh list" style="background: var(--card-bg, #ffffff); border: 1px solid var(--border); color: var(--text); padding: 8px 14px; border-radius: 8px; display: inline-flex; align-items: center; gap: 6px; cursor: pointer;">
                        <i class='bx bx-refresh' style="font-size: 18px;"></i> Refresh
                    </button>
                    <button class="btn secondary" id="btn-export-stock-reqs" title="Export CSV" style="background: var(--card-bg, #ffffff); border: 1px solid var(--border); color: var(--text); padding: 8px 14px; border-radius: 8px; display: inline-flex; align-items: center; gap: 6px; cursor: pointer;">
                        <i class='bx bx-export' style="font-size: 18px;"></i> Export CSV
                    </button>
                    ${isManagerOrOwner ? `
                        <button class="btn btn-primary" id="btn-create-stock-req" style="background: var(--primary); color: white; border: none; padding: 8px 16px; border-radius: 8px; display: inline-flex; align-items: center; gap: 6px; font-weight: 600; cursor: pointer;">
                            <i class='bx bx-plus' style="font-size: 18px;"></i> New Stock Request
                        </button>
                    ` : ''}
                </div>
            </div>

            <!-- KPI Summary Cards -->
            <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 1.5rem;">
                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-light);">Open / Pending</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-time-five'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="kpi-sr-pending" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-light);">Awaiting response</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-light);">Accepted</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(16, 185, 129, 0.12); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-check-circle'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="kpi-sr-accepted" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-light);">Confirmed by supplier</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-light);">Quoted</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-receipt'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="kpi-sr-quoted" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-light);">Quotation linked</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-light);">Total Requests</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-git-pull-request'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="kpi-sr-total" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-light);">Active records</span>
                    </div>
                </div>
            </div>

            <!-- Filters Bar -->
            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 10px; background: var(--card-bg, #ffffff); border: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
                <div class="search-box" style="position: relative; flex: 1; min-width: 260px;">
                    <i class='bx bx-search' style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-light); font-size: 18px;"></i>
                    <input type="text" id="sr-search-input" placeholder="Search request #, product, or notes..." style="width: 100%; padding: 9px 12px 9px 38px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-main, #f9fafb); color: var(--text); font-size: 14px;">
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                    <select id="sr-filter-status" style="padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #ffffff); color: var(--text); font-size: 13px; cursor: pointer;">
                        <option value="All Status">All Status</option>
                        <option value="Pending">Pending</option>
                        <option value="Accepted">Accepted</option>
                        <option value="Quoted">Quoted</option>
                        <option value="Rejected">Rejected</option>
                    </select>

                    <select id="sr-filter-priority" style="padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #ffffff); color: var(--text); font-size: 13px; cursor: pointer;">
                        <option value="All Priority">All Priority</option>
                        <option value="Urgent">Urgent</option>
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                    </select>

                    <select id="sr-filter-sort" style="padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #ffffff); color: var(--text); font-size: 13px; cursor: pointer;">
                        <option value="latest">Latest First</option>
                        <option value="oldest">Oldest First</option>
                        <option value="highest_qty">Highest Quantity</option>
                        <option value="required_date">Required Date</option>
                    </select>
                </div>
            </div>

            <!-- Table Card -->
            <div class="card table-responsive" style="border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border); overflow: hidden;">
                <div style="padding: 14px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <span id="sr-table-counter" style="font-size: 13px; font-weight: 600; color: var(--text);">
                        0 Requests <span style="color: var(--text-light); font-weight: normal; margin-left: 8px;">Loading real-time records...</span>
                    </span>
                    <span style="font-size: 12px; color: var(--text-light);">
                        <i class='bx bx-check-shield' style="color: var(--success, #10b981);"></i> JWT Supplier-Isolated
                    </span>
                </div>
                <table class="data-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: var(--bg-main, #f9fafb); text-align: left; font-size: 12px; color: var(--text-light); text-transform: uppercase;">
                            <th style="padding: 12px 16px;">REQUEST ID</th>
                            <th style="padding: 12px 16px;">PRODUCT & ITEMS</th>
                            ${isManagerOrOwner ? '<th style="padding: 12px 16px;">SUPPLIER</th>' : '<th style="padding: 12px 16px;">REQUESTED BY</th>'}
                            <th style="padding: 12px 16px;">QUANTITY</th>
                            <th style="padding: 12px 16px;">REQUIRED DATE</th>
                            <th style="padding: 12px 16px;">PRIORITY</th>
                            <th style="padding: 12px 16px;">STATUS</th>
                            <th style="padding: 12px 16px; text-align: right;">ACTION</th>
                        </tr>
                    </thead>
                    <tbody id="stock-requests-tbody">
                        <tr>
                            <td colspan="8" style="text-align: center; padding: 40px; color: var(--text-light);">
                                <i class='bx bx-loader-alt bx-spin' style="font-size: 28px; display: block; margin-bottom: 8px;"></i>
                                Loading stock requests...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;

        this.initEventListeners(container);
        this.fetchStockRequests(container);

        return container;
    },

    initEventListeners(container) {
        const refreshBtn = container.querySelector('#btn-refresh-stock-reqs');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                refreshBtn.querySelector('i').classList.add('bx-spin');
                this.fetchStockRequests(container).finally(() => {
                    setTimeout(() => refreshBtn.querySelector('i').classList.remove('bx-spin'), 400);
                });
            });
        }

        const exportBtn = container.querySelector('#btn-export-stock-reqs');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportCSV());
        }

        const createBtn = container.querySelector('#btn-create-stock-req');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.openCreateModal(container));
        }

        const searchInput = container.querySelector('#sr-search-input');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.filters.search = e.target.value.toLowerCase().trim();
                    this.applyFiltersAndRender(container);
                }, 200);
            });
        }

        const statusSelect = container.querySelector('#sr-filter-status');
        if (statusSelect) {
            statusSelect.addEventListener('change', (e) => {
                this.filters.status = e.target.value;
                this.applyFiltersAndRender(container);
            });
        }

        const prioritySelect = container.querySelector('#sr-filter-priority');
        if (prioritySelect) {
            prioritySelect.addEventListener('change', (e) => {
                this.filters.priority = e.target.value;
                this.applyFiltersAndRender(container);
            });
        }

        const sortSelect = container.querySelector('#sr-filter-sort');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.filters.sort = e.target.value;
                this.applyFiltersAndRender(container);
            });
        }
    },

    async fetchStockRequests(container) {
        const tbody = container.querySelector('#stock-requests-tbody');
        const counterEl = container.querySelector('#sr-table-counter');

        try {
            // Fetch real database records from dedicated Stock Requests API
            const response = await Api.get('/stock-requests/');
            const requests = response?.stock_requests || (Array.isArray(response) ? response : []);

            this.currentRequests = requests;
            this.updateKPIs(container, requests);
            this.applyFiltersAndRender(container);

        } catch (error) {
            console.error("Error fetching stock requests:", error);
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="8" style="text-align: center; padding: 40px;">
                            <div style="display: inline-flex; flex-direction: column; align-items: center; gap: 8px;">
                                <i class='bx bx-error-circle' style="font-size: 36px; color: #ef4444;"></i>
                                <span style="font-weight: 600; color: var(--text);">Unable to load stock requests</span>
                                <span style="font-size: 13px; color: var(--text-light);">${error.message || 'Please check your connection and try again.'}</span>
                                <button class="btn btn-outline" style="margin-top: 8px; padding: 6px 14px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer;" onclick="App.pages['stock-requests'].fetchStockRequests(document.querySelector('.page.active'))">
                                    <i class='bx bx-refresh'></i> Retry
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }
            if (counterEl) {
                counterEl.innerHTML = `<span style="color: #ef4444;">Connection failed</span>`;
            }
        }
    },

    updateKPIs(container, requests) {
        const pendingEl = container.querySelector('#kpi-sr-pending');
        const acceptedEl = container.querySelector('#kpi-sr-accepted');
        const quotedEl = container.querySelector('#kpi-sr-quoted');
        const totalEl = container.querySelector('#kpi-sr-total');

        if (!pendingEl) return;

        const pendingCount = requests.filter(r => (r.status || '').toLowerCase() === 'pending').length;
        const acceptedCount = requests.filter(r => (r.status || '').toLowerCase() === 'accepted').length;
        const quotedCount = requests.filter(r => (r.status || '').toLowerCase() === 'quoted').length;

        pendingEl.textContent = pendingCount;
        acceptedEl.textContent = acceptedCount;
        quotedEl.textContent = quotedCount;
        totalEl.textContent = requests.length;
    },

    applyFiltersAndRender(container) {
        const tbody = container.querySelector('#stock-requests-tbody');
        const counterEl = container.querySelector('#sr-table-counter');
        const user = Auth.getUser() || {};
        const isManagerOrOwner = user.role === 'Owner' || user.role === 'Manager';
        const isSupplier = user.role === 'Supplier';

        if (!tbody) return;

        let filtered = [...this.currentRequests];

        // 1. Status Filter
        if (this.filters.status && this.filters.status !== 'All Status') {
            filtered = filtered.filter(r => (r.status || '').toLowerCase() === this.filters.status.toLowerCase());
        }

        // 2. Priority Filter
        if (this.filters.priority && this.filters.priority !== 'All Priority') {
            filtered = filtered.filter(r => (r.priority || '').toLowerCase() === this.filters.priority.toLowerCase());
        }

        // 3. Search Filter
        if (this.filters.search) {
            const q = this.filters.search;
            filtered = filtered.filter(r => {
                const reqNum = (r.request_number || '').toLowerCase();
                const primaryProd = (r.primary_product || '').toLowerCase();
                const supName = (r.supplier_name || '').toLowerCase();
                const reqName = (r.requested_by_name || '').toLowerCase();
                const notes = (r.notes || '').toLowerCase();
                const itemsMatch = (r.items || []).some(it => 
                    (it.product_name || '').toLowerCase().includes(q) || 
                    (it.sku || '').toLowerCase().includes(q)
                );
                return reqNum.includes(q) || primaryProd.includes(q) || supName.includes(q) || reqName.includes(q) || notes.includes(q) || itemsMatch;
            });
        }

        // 4. Sorting
        filtered.sort((a, b) => {
            if (this.filters.sort === 'oldest') {
                return new Date(a.created_at || 0) - new Date(b.created_at || 0);
            }
            if (this.filters.sort === 'highest_qty') {
                return (b.total_quantity || 0) - (a.total_quantity || 0);
            }
            if (this.filters.sort === 'required_date') {
                return new Date(a.required_date || '9999-12-31') - new Date(b.required_date || '9999-12-31');
            }
            // default latest
            return new Date(b.created_at || 0) - new Date(a.created_at || 0);
        });

        // Update counter text
        if (counterEl) {
            counterEl.innerHTML = `
                ${filtered.length} Requests
                <span style="color: var(--text-light); font-weight: normal; margin-left: 8px;">
                    ${filtered.length === this.currentRequests.length ? 'Updated just now' : `Filtered from ${this.currentRequests.length} total`}
                </span>
            `;
        }

        // Render Table or Empty State
        tbody.innerHTML = '';

        if (filtered.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 48px 20px;">
                        <div class="empty-state" style="padding: 0;">
                            <i class='bx bx-git-pull-request' style="font-size: 44px; color: var(--text-light); opacity: 0.6; display: block; margin-bottom: 12px;"></i>
                            <h3 style="margin: 0 0 6px 0; font-size: 16px; font-weight: 600; color: var(--text);">No stock requests available.</h3>
                            <p style="color: var(--text-light); margin: 0; font-size: 13px;">
                                ${this.currentRequests.length === 0 
                                    ? (isSupplier ? 'You have no open stock requests from management.' : 'No stock requests have been issued yet. Click "New Stock Request" to create one.')
                                    : 'No requests match your selected filters. Try clearing search or status filters.'}
                            </p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        filtered.forEach(req => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid var(--border)';
            tr.style.transition = 'background 0.15s ease';

            // Priority badge styling
            const priorityLower = (req.priority || 'Medium').toLowerCase();
            let priorityBg = 'rgba(245, 158, 11, 0.12)';
            let priorityColor = '#d97706';
            if (priorityLower === 'urgent') {
                priorityBg = 'rgba(239, 68, 68, 0.14)';
                priorityColor = '#dc2626';
            } else if (priorityLower === 'high') {
                priorityBg = 'rgba(249, 115, 22, 0.14)';
                priorityColor = '#ea580c';
            } else if (priorityLower === 'low') {
                priorityBg = 'rgba(107, 114, 128, 0.12)';
                priorityColor = '#4b5563';
            }

            // Status badge styling
            const statusLower = (req.status || 'Pending').toLowerCase();
            let statusBg = 'rgba(245, 158, 11, 0.12)';
            let statusColor = '#d97706';
            let statusLabel = 'Pending Response';

            if (statusLower === 'accepted') {
                statusBg = 'rgba(16, 185, 129, 0.14)';
                statusColor = '#059669';
                statusLabel = 'Accepted';
            } else if (statusLower === 'quoted') {
                statusBg = 'rgba(139, 92, 246, 0.14)';
                statusColor = '#7c3aed';
                statusLabel = 'Quoted';
            } else if (statusLower === 'rejected') {
                statusBg = 'rgba(239, 68, 68, 0.14)';
                statusColor = '#dc2626';
                statusLabel = 'Rejected';
            }

            // Date formatting
            const reqDateStr = req.required_date 
                ? new Date(req.required_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
                : 'Not specified';

            const createdDateStr = req.created_at
                ? new Date(req.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
                : 'Recent';

            // Items summary
            const itemsCount = req.items_count || (req.items ? req.items.length : 1);
            const extraItemsBadge = itemsCount > 1 
                ? `<span style="font-size: 11px; background: rgba(59, 130, 246, 0.12); color: #2563eb; padding: 2px 6px; border-radius: 4px; margin-left: 6px; font-weight: 600;">+${itemsCount - 1} more</span>` 
                : '';

            tr.innerHTML = `
                <td style="padding: 14px 16px;">
                    <div style="font-weight: 700; color: var(--text); font-size: 14px;">${req.request_number}</div>
                    <div style="font-size: 12px; color: var(--text-light);">Created ${createdDateStr}</div>
                </td>
                <td style="padding: 14px 16px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 32px; height: 32px; border-radius: 6px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 12px;">
                            ${(req.primary_product || 'PR').substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                            <div style="font-weight: 600; color: var(--text); font-size: 13px;">
                                ${req.primary_product || 'Product Item'}
                                ${extraItemsBadge}
                            </div>
                            <div style="font-size: 11px; color: var(--text-light); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                ${req.notes || 'No specific notes'}
                            </div>
                        </div>
                    </div>
                </td>
                <td style="padding: 14px 16px;">
                    <div style="font-weight: 600; color: var(--text); font-size: 13px;">
                        ${isManagerOrOwner ? (req.supplier_name || 'Supplier') : (req.requested_by_name || 'Management')}
                    </div>
                    <div style="font-size: 11px; color: var(--text-light);">
                        ${isManagerOrOwner ? (req.supplier_email || '') : 'Inventory Controller'}
                    </div>
                </td>
                <td style="padding: 14px 16px; font-weight: 600; color: var(--text); font-size: 13px;">
                    ${req.total_quantity || 0} units
                </td>
                <td style="padding: 14px 16px;">
                    <div style="font-size: 13px; color: var(--text);">${reqDateStr}</div>
                    ${priorityLower === 'urgent' ? '<span style="font-size: 10px; color: #dc2626; font-weight: 600; text-transform: uppercase;">Time sensitive</span>' : ''}
                </td>
                <td style="padding: 14px 16px;">
                    <span style="display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; background: ${priorityBg}; color: ${priorityColor};">
                        ${req.priority || 'Medium'}
                    </span>
                </td>
                <td style="padding: 14px 16px;">
                    <span style="display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; background: ${statusBg}; color: ${statusColor};">
                        ${statusLabel}
                    </span>
                </td>
                <td style="padding: 14px 16px; text-align: right;">
                    <div style="display: inline-flex; gap: 6px; align-items: center; justify-content: flex-end;">
                        <button class="btn btn-sm btn-view-sr" data-id="${req.stock_request_id}" style="background: var(--card-bg, #ffffff); border: 1px solid var(--border); color: var(--text); padding: 5px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" title="View Details">
                            <i class='bx bx-show'></i> Details
                        </button>
                        ${isSupplier && statusLower === 'pending' ? `
                            <button class="btn btn-sm btn-respond-sr" data-id="${req.stock_request_id}" style="background: var(--primary, #2563eb); color: white; border: none; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" title="Respond to Request">
                                <i class='bx bx-reply'></i> Respond
                            </button>
                        ` : ''}
                        ${statusLower === 'quoted' ? `
                            <button class="btn btn-sm btn-quote-sr" data-id="${req.stock_request_id}" style="background: rgba(139, 92, 246, 0.12); color: #7c3aed; border: 1px solid rgba(139, 92, 246, 0.3); padding: 5px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" title="View Linked Quotation">
                                <i class='bx bx-receipt'></i> Quote
                            </button>
                        ` : ''}
                    </div>
                </td>
            `;

            // Hover effect
            tr.addEventListener('mouseenter', () => tr.style.background = 'var(--bg-main, #f9fafb)');
            tr.addEventListener('mouseleave', () => tr.style.background = 'transparent');

            tbody.appendChild(tr);
        });

        // Attach action handlers
        tbody.querySelectorAll('.btn-view-sr').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                this.openDetailsModal(id);
            });
        });

        tbody.querySelectorAll('.btn-respond-sr').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                this.openRespondModal(id, container);
            });
        });

        tbody.querySelectorAll('.btn-quote-sr').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = parseInt(btn.dataset.id);
                this.openDetailsModal(id);
            });
        });
    },

    async openDetailsModal(stockRequestId) {
        try {
            const response = await Api.get(`/stock-requests/${stockRequestId}`);
            const sr = response?.stock_request;

            if (!sr) {
                Utils.showToast('Stock request details could not be found.', 'error');
                return;
            }

            const itemsRows = (sr.items || []).map((it, idx) => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 10px 12px; font-size: 13px; color: var(--text-light);">${idx + 1}</td>
                    <td style="padding: 10px 12px;">
                        <div style="font-weight: 600; font-size: 13px; color: var(--text);">${it.product_name}</div>
                        <div style="font-size: 11px; color: var(--text-light);">SKU: ${it.sku || 'N/A'} • ${it.category_name || 'Standard'}</div>
                    </td>
                    <td style="padding: 10px 12px; font-size: 13px; font-weight: 700; color: var(--text); text-align: center;">${it.requested_quantity} units</td>
                    <td style="padding: 10px 12px; font-size: 13px; color: var(--text-light); text-align: right;">₹${(it.reference_price || 0).toLocaleString()}</td>
                </tr>
            `).join('');

            const quoteBox = sr.quotation ? `
                <div style="margin-top: 1.2rem; padding: 14px; border-radius: 8px; background: rgba(139, 92, 246, 0.08); border: 1px solid rgba(139, 92, 246, 0.25);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 700; color: #7c3aed; font-size: 13px; display: inline-flex; align-items: center; gap: 6px;">
                            <i class='bx bx-receipt'></i> Linked Quotation #${sr.quotation.quotation_number}
                        </span>
                        <span style="padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; background: rgba(139, 92, 246, 0.2); color: #7c3aed;">
                            ${sr.quotation.status}
                        </span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-size: 12px;">
                        <div>
                            <span style="color: var(--text-light); display: block;">Quoted Price</span>
                            <span style="font-weight: 700; color: var(--text);">₹${(sr.quotation.quoted_price || 0).toFixed(2)}/unit</span>
                        </div>
                        <div>
                            <span style="color: var(--text-light); display: block;">Total Amount</span>
                            <span style="font-weight: 700; color: #059669;">₹${(sr.quotation.total_amount || 0).toLocaleString()}</span>
                        </div>
                        <div>
                            <span style="color: var(--text-light); display: block;">Submitted Date</span>
                            <span style="font-weight: 600; color: var(--text);">${sr.quotation.quotation_date || 'N/A'}</span>
                        </div>
                    </div>
                </div>
            ` : '';

            const responseBox = sr.supplier_response_notes ? `
                <div style="margin-top: 1rem; padding: 12px; border-radius: 8px; background: var(--bg-main, #f9fafb); border: 1px solid var(--border);">
                    <div style="font-size: 12px; font-weight: 600; color: var(--text-light); margin-bottom: 4px; text-transform: uppercase;">
                        Supplier Response (${sr.responded_at ? new Date(sr.responded_at).toLocaleString() : 'Recorded'}):
                    </div>
                    <div style="font-size: 13px; color: var(--text); font-style: italic;">"${sr.supplier_response_notes}"</div>
                </div>
            ` : '';

            const content = `
                <div style="display: flex; flex-direction: column; gap: 1rem;">
                    <!-- Top meta grid -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; padding: 14px; border-radius: 8px; background: var(--bg-main, #f9fafb); border: 1px solid var(--border);">
                        <div>
                            <span style="font-size: 11px; color: var(--text-light); display: block; text-transform: uppercase;">Request Reference</span>
                            <span style="font-size: 15px; font-weight: 700; color: var(--text);">${sr.request_number}</span>
                        </div>
                        <div>
                            <span style="font-size: 11px; color: var(--text-light); display: block; text-transform: uppercase;">Status</span>
                            <span style="font-size: 13px; font-weight: 700; color: var(--primary);">${sr.status}</span>
                        </div>
                        <div>
                            <span style="font-size: 11px; color: var(--text-light); display: block; text-transform: uppercase;">Priority</span>
                            <span style="font-size: 13px; font-weight: 700; color: ${sr.priority === 'Urgent' ? '#dc2626' : 'var(--text)'};">${sr.priority}</span>
                        </div>
                        <div>
                            <span style="font-size: 11px; color: var(--text-light); display: block; text-transform: uppercase;">Required Date</span>
                            <span style="font-size: 13px; font-weight: 600; color: var(--text);">${sr.required_date || 'None specified'}</span>
                        </div>
                    </div>

                    <!-- Supplier & Requester info -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div style="padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                            <span style="font-size: 11px; color: var(--text-light); text-transform: uppercase; font-weight: 600;">Supplier Information</span>
                            <div style="font-weight: 700; color: var(--text); margin-top: 4px;">${sr.supplier_name}</div>
                            <div style="font-size: 12px; color: var(--text-light);">${sr.supplier_email || 'No email'} • ${sr.supplier_phone || ''}</div>
                        </div>
                        <div style="padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                            <span style="font-size: 11px; color: var(--text-light); text-transform: uppercase; font-weight: 600;">Requested By</span>
                            <div style="font-weight: 700; color: var(--text); margin-top: 4px;">${sr.requested_by_name}</div>
                            <div style="font-size: 12px; color: var(--text-light);">Created: ${new Date(sr.created_at).toLocaleString()}</div>
                        </div>
                    </div>

                    ${sr.notes ? `
                        <div style="padding: 12px; border-radius: 8px; background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2);">
                            <span style="font-size: 11px; font-weight: 700; color: #2563eb; text-transform: uppercase;">Manager Notes & Specification</span>
                            <p style="margin: 4px 0 0 0; font-size: 13px; color: var(--text);">${sr.notes}</p>
                        </div>
                    ` : ''}

                    <!-- Products Table -->
                    <div>
                        <div style="font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 8px; display: flex; justify-content: space-between;">
                            <span>Requested Products (${sr.items_count || 1})</span>
                            <span style="color: var(--primary);">Total: ${sr.total_quantity || 0} units</span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid var(--border); border-radius: 6px; overflow: hidden;">
                            <thead style="background: var(--bg-main, #f9fafb); font-size: 11px; text-transform: uppercase; color: var(--text-light);">
                                <tr>
                                    <th style="padding: 8px 12px; text-align: left;">#</th>
                                    <th style="padding: 8px 12px; text-align: left;">Product</th>
                                    <th style="padding: 8px 12px; text-align: center;">Requested Qty</th>
                                    <th style="padding: 8px 12px; text-align: right;">Ref Price</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${itemsRows}
                            </tbody>
                        </table>
                    </div>

                    ${responseBox}
                    ${quoteBox}
                </div>
            `;

            Modal.create({
                id: 'modal-sr-details',
                title: `Stock Request: ${sr.request_number}`,
                content: content,
                footer: `
                    <div style="display: flex; justify-content: flex-end; gap: 10px; width: 100%;">
                        <button type="button" class="btn btn-outline close-details-btn" style="padding: 8px 16px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer;">Close</button>
                    </div>
                `,
                onOpen: (modalEl, closeModal) => {
                    modalEl.querySelector('.close-details-btn').addEventListener('click', closeModal);
                }
            });

        } catch (error) {
            Utils.showToast(error.message || 'Failed to load stock request details.', 'error');
        }
    },

    openRespondModal(stockRequestId, container) {
        Modal.create({
            id: 'modal-respond-stock-req',
            title: 'Respond to Stock Request',
            content: `
                <form id="sr-respond-form" style="display: flex; flex-direction: column; gap: 14px;">
                    <div>
                        <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px; color: var(--text);">Your Response Decision <span style="color: #ef4444;">*</span></label>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <label style="display: flex; align-items: center; gap: 8px; padding: 12px; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; background: var(--bg-main, #f9fafb);">
                                <input type="radio" name="sr_action" value="Accept" checked style="accent-color: #059669;">
                                <div>
                                    <strong style="color: #059669; display: block; font-size: 13px;">Accept Request</strong>
                                    <span style="font-size: 11px; color: var(--text-light);">We can supply this stock</span>
                                </div>
                            </label>
                            <label style="display: flex; align-items: center; gap: 8px; padding: 12px; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; background: var(--bg-main, #f9fafb);">
                                <input type="radio" name="sr_action" value="Reject" style="accent-color: #dc2626;">
                                <div>
                                    <strong style="color: #dc2626; display: block; font-size: 13px;">Reject Request</strong>
                                    <span style="font-size: 11px; color: var(--text-light);">Cannot supply at this time</span>
                                </div>
                            </label>
                        </div>
                    </div>

                    <div id="sr-quote-section" style="padding: 14px; border-radius: 8px; background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.25);">
                        <div style="font-size: 13px; font-weight: 700; color: #2563eb; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
                            <i class='bx bx-receipt'></i> Optional Quotation Generation
                        </div>
                        <p style="font-size: 12px; color: var(--text-light); margin: 0 0 10px 0;">
                            Providing a unit price will automatically generate a formal Supplier Quotation connected to this stock request for manager approval.
                        </p>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div>
                                <label style="font-size: 12px; font-weight: 600; color: var(--text); display: block; margin-bottom: 4px;">Quoted Price per Unit (₹)</label>
                                <input type="number" id="sr_quoted_price" step="0.01" min="0.01" placeholder="e.g. 450.00" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                            </div>
                            <div>
                                <label style="font-size: 12px; font-weight: 600; color: var(--text); display: block; margin-bottom: 4px;">Quote Valid Until</label>
                                <input type="date" id="sr_valid_until" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                            </div>
                        </div>
                    </div>

                    <div>
                        <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px; color: var(--text);">Response Notes / Delivery Timeline</label>
                        <textarea id="sr_response_notes" rows="3" placeholder="Provide fulfillment notes, expected shipment availability, or reason if rejecting..." style="width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; color: var(--text); background: var(--card-bg, #ffffff);"></textarea>
                    </div>

                    <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);">
                        <button type="button" class="btn btn-outline cancel-respond-btn" style="padding: 8px 16px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer;">Cancel</button>
                        <button type="submit" id="btn-submit-respond" class="btn btn-primary" style="background: var(--primary, #2563eb); color: white; border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600; cursor: pointer;">
                            Submit Response
                        </button>
                    </div>
                </form>
            `,
            onOpen: (modalEl, closeModal) => {
                const form = modalEl.querySelector('#sr-respond-form');
                const cancelBtn = modalEl.querySelector('.cancel-respond-btn');
                const submitBtn = modalEl.querySelector('#btn-submit-respond');
                const quoteSection = modalEl.querySelector('#sr-quote-section');
                const actionRadios = modalEl.querySelectorAll('input[name="sr_action"]');
                const validUntilInput = modalEl.querySelector('#sr_valid_until');

                // Default valid_until to 14 days from now
                const d = new Date();
                d.setDate(d.getDate() + 14);
                if (validUntilInput) {
                    validUntilInput.value = d.toISOString().split('T')[0];
                }

                // Toggle quotation section if rejected
                actionRadios.forEach(radio => {
                    radio.addEventListener('change', () => {
                        if (radio.value === 'Reject') {
                            quoteSection.style.display = 'none';
                        } else {
                            quoteSection.style.display = 'block';
                        }
                    });
                });

                cancelBtn.addEventListener('click', closeModal);

                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const action = modalEl.querySelector('input[name="sr_action"]:checked').value;
                    const notes = modalEl.querySelector('#sr_response_notes').value.trim();
                    const quotedPriceVal = modalEl.querySelector('#sr_quoted_price').value.trim();
                    const validUntilVal = modalEl.querySelector('#sr_valid_until').value;

                    const payload = {
                        action: action,
                        notes: notes
                    };

                    if (action === 'Accept' && quotedPriceVal) {
                        const price = parseFloat(quotedPriceVal);
                        if (isNaN(price) || price <= 0) {
                            Utils.showToast('Please enter a valid positive quoted price.', 'error');
                            return;
                        }
                        payload.quoted_price = price;
                        if (validUntilVal) {
                            payload.valid_until = validUntilVal;
                        }
                    }

                    try {
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Submitting...';

                        const result = await Api.patch(`/stock-requests/${stockRequestId}/respond`, payload);
                        
                        Utils.showToast(result.message || 'Response recorded successfully!', 'success');
                        closeModal();
                        
                        // Refresh stock requests table
                        this.fetchStockRequests(container);

                        // If dashboard is active, refresh supplier dashboard
                        if (typeof App.pages['dashboard']?.render === 'function') {
                            // Dashboard can update on next visit
                        }
                    } catch (err) {
                        Utils.showToast(err.message || 'Failed to submit response.', 'error');
                    } finally {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = 'Submit Response';
                    }
                });
            }
        });
    },

    async openCreateModal(container) {
        try {
            // Load suppliers and products for manager to create stock request
            const [supRes, prodRes] = await Promise.all([
                Api.get('/suppliers/'),
                Api.get('/products/')
            ]);

            const suppliers = supRes?.suppliers || (Array.isArray(supRes) ? supRes : []);
            const products = prodRes?.products || (Array.isArray(prodRes) ? prodRes : []);

            if (suppliers.length === 0) {
                Utils.showToast('No registered suppliers found. Please add a supplier first.', 'error');
                return;
            }

            if (products.length === 0) {
                Utils.showToast('No active products found. Please add products first.', 'error');
                return;
            }

            const supplierOptions = suppliers.map(s => `
                <option value="${s.supplier_id}">${s.supplier_name} (${s.contact_person || s.email || 'Supplier'})</option>
            `).join('');

            const productOptions = products.map(p => `
                <option value="${p.product_id}">${p.product_name} (${p.sku || 'SKU N/A'}) - In Stock: ${p.stock_quantity || 0}</option>
            `).join('');

            Modal.create({
                id: 'modal-create-stock-req',
                title: 'Create New Stock Request',
                content: `
                    <form id="form-create-stock-req" style="display: flex; flex-direction: column; gap: 14px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px; color: var(--text);">Select Supplier <span style="color: #ef4444;">*</span></label>
                                <select id="csr-supplier-id" required style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                                    ${supplierOptions}
                                </select>
                            </div>
                            <div>
                                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px; color: var(--text);">Priority <span style="color: #ef4444;">*</span></label>
                                <select id="csr-priority" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                                    <option value="Medium">Medium</option>
                                    <option value="High">High</option>
                                    <option value="Urgent">Urgent</option>
                                    <option value="Low">Low</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px; color: var(--text);">Required Delivery Date</label>
                            <input type="date" id="csr-required-date" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                        </div>

                        <!-- Products line items builder -->
                        <div style="border: 1px solid var(--border); border-radius: 8px; padding: 12px; background: var(--bg-main, #f9fafb);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <label style="font-size: 13px; font-weight: 700; color: var(--text);">Requested Products & Quantities <span style="color: #ef4444;">*</span></label>
                                <button type="button" id="btn-add-csr-item" style="background: white; border: 1px solid var(--border); padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-plus'></i> Add Item
                                </button>
                            </div>
                            <div id="csr-items-container" style="display: flex; flex-direction: column; gap: 8px;">
                                <!-- Item Row 1 -->
                                <div class="csr-item-row" style="display: grid; grid-template-columns: 2fr 1fr 30px; gap: 8px; align-items: center;">
                                    <select class="csr-prod-select" required style="padding: 7px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                                        ${productOptions}
                                    </select>
                                    <input type="number" class="csr-qty-input" required min="1" value="25" placeholder="Qty" style="padding: 7px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                                    <button type="button" class="btn-remove-csr-item" style="border: none; background: transparent; color: #ef4444; font-size: 18px; cursor: pointer;" title="Remove item">
                                        <i class='bx bx-trash'></i>
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div>
                            <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px; color: var(--text);">Notes & Restock Instructions</label>
                            <textarea id="csr-notes" rows="2" placeholder="e.g. Urgent restock required for upcoming seasonal demand..." style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;"></textarea>
                        </div>

                        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border);">
                            <button type="button" class="btn btn-outline cancel-csr-btn" style="padding: 8px 16px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer;">Cancel</button>
                            <button type="submit" id="btn-submit-csr" class="btn btn-primary" style="background: var(--primary, #2563eb); color: white; border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600; cursor: pointer;">
                                Issue Stock Request
                            </button>
                        </div>
                    </form>
                `,
                onOpen: (modalEl, closeModal) => {
                    const form = modalEl.querySelector('#form-create-stock-req');
                    const cancelBtn = modalEl.querySelector('.cancel-csr-btn');
                    const submitBtn = modalEl.querySelector('#btn-submit-csr');
                    const itemsContainer = modalEl.querySelector('#csr-items-container');
                    const addItemBtn = modalEl.querySelector('#btn-add-csr-item');

                    // Default required date to 7 days from now
                    const defDate = new Date();
                    defDate.setDate(defDate.getDate() + 7);
                    const reqDateInput = modalEl.querySelector('#csr-required-date');
                    if (reqDateInput) {
                        reqDateInput.value = defDate.toISOString().split('T')[0];
                    }

                    // Add line item row
                    addItemBtn.addEventListener('click', () => {
                        const row = document.createElement('div');
                        row.className = 'csr-item-row';
                        row.style.cssText = 'display: grid; grid-template-columns: 2fr 1fr 30px; gap: 8px; align-items: center;';
                        row.innerHTML = `
                            <select class="csr-prod-select" required style="padding: 7px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                                ${productOptions}
                            </select>
                            <input type="number" class="csr-qty-input" required min="1" value="20" placeholder="Qty" style="padding: 7px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px;">
                            <button type="button" class="btn-remove-csr-item" style="border: none; background: transparent; color: #ef4444; font-size: 18px; cursor: pointer;" title="Remove item">
                                <i class='bx bx-trash'></i>
                            </button>
                        `;
                        row.querySelector('.btn-remove-csr-item').addEventListener('click', () => {
                            if (itemsContainer.querySelectorAll('.csr-item-row').length > 1) {
                                row.remove();
                            } else {
                                Utils.showToast('A stock request must contain at least one product item.', 'error');
                            }
                        });
                        itemsContainer.appendChild(row);
                    });

                    // First row remove handler
                    itemsContainer.querySelector('.btn-remove-csr-item').addEventListener('click', (e) => {
                        if (itemsContainer.querySelectorAll('.csr-item-row').length > 1) {
                            e.currentTarget.closest('.csr-item-row').remove();
                        } else {
                            Utils.showToast('A stock request must contain at least one product item.', 'error');
                        }
                    });

                    cancelBtn.addEventListener('click', closeModal);

                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const supplierId = parseInt(modalEl.querySelector('#csr-supplier-id').value);
                        const priority = modalEl.querySelector('#csr-priority').value;
                        const reqDate = modalEl.querySelector('#csr-required-date').value;
                        const notes = modalEl.querySelector('#csr-notes').value.trim();

                        const rows = itemsContainer.querySelectorAll('.csr-item-row');
                        const items = [];

                        rows.forEach(r => {
                            const pId = parseInt(r.querySelector('.csr-prod-select').value);
                            const qty = parseInt(r.querySelector('.csr-qty-input').value);
                            if (pId && qty > 0) {
                                items.push({ product_id: pId, requested_quantity: qty });
                            }
                        });

                        if (items.length === 0) {
                            Utils.showToast('Please add at least one valid product item.', 'error');
                            return;
                        }

                        const payload = {
                            supplier_id: supplierId,
                            priority: priority,
                            required_date: reqDate || null,
                            notes: notes,
                            items: items
                        };

                        try {
                            submitBtn.disabled = true;
                            submitBtn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Creating...';

                            const res = await Api.post('/stock-requests/', payload);
                            Utils.showToast(res.message || 'Stock request created successfully!', 'success');
                            closeModal();
                            this.fetchStockRequests(container);
                        } catch (err) {
                            Utils.showToast(err.message || 'Failed to create stock request.', 'error');
                        } finally {
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = 'Issue Stock Request';
                        }
                    });
                }
            });

        } catch (err) {
            Utils.showToast(err.message || 'Failed to initialize request form.', 'error');
        }
    },

    exportCSV() {
        if (!this.currentRequests || this.currentRequests.length === 0) {
            Utils.showToast('No records available to export.', 'info');
            return;
        }

        const headers = ['Request Number', 'Supplier', 'Primary Product', 'Total Quantity', 'Priority', 'Status', 'Required Date', 'Created Date'];
        const csvRows = [headers.join(',')];

        this.currentRequests.forEach(r => {
            const row = [
                `"${r.request_number || ''}"`,
                `"${(r.supplier_name || '').replace(/"/g, '""')}"`,
                `"${(r.primary_product || '').replace(/"/g, '""')}"`,
                r.total_quantity || 0,
                `"${r.priority || ''}"`,
                `"${r.status || ''}"`,
                `"${r.required_date || ''}"`,
                `"${r.created_at || ''}"`
            ];
            csvRows.push(row.join(','));
        });

        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `Stock_Requests_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
};
