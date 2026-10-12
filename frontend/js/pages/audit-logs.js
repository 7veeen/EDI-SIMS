// audit-logs.js - Modernized Audit Logs Page with Search, Filtering & Server-Side Pagination

App.pages['audit-logs'] = {
    state: {
        page: 1,
        limit: 50,
        total: 0,
        totalPages: 0,
        search: '',
        action: 'All Actions',
        tableName: 'All Entities',
        startDate: '',
        endDate: '',
        logs: [],
        isLoading: false,
        searchDebounceTimer: null
    },

    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="actions-bar glass-panel" style="padding: 1.25rem; border-radius: 12px; margin-bottom: 1.5rem; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem;">
                    <div>
                        <h2 style="margin: 0; font-size: 20px; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 8px;">
                            <i class='bx bx-history text-primary'></i> Audit Logs
                        </h2>
                        <p style="color: var(--text-secondary, var(--gray)); margin: 4px 0 0 0; font-size: 0.9rem;">
                            Complete, tamper-evident security and operational audit trail
                        </p>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span id="audit-total-badge" class="badge" style="background: rgba(37, 99, 235, 0.1); color: var(--primary); font-size: 13px; font-weight: 600; padding: 6px 12px; border-radius: 20px;">
                            Total Logs: --
                        </span>
                        <button class="btn btn-secondary" id="audit-refresh-btn" title="Refresh logs" style="display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; font-size: 13px; border-radius: 8px; cursor: pointer;">
                            <i class='bx bx-refresh'></i> Refresh
                        </button>
                    </div>
                </div>

                <!-- Filter Controls Bar -->
                <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
                    <!-- Keyword Search -->
                    <div style="position: relative; flex: 1; min-width: 220px;">
                        <i class='bx bx-search' style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-secondary); font-size: 17px;"></i>
                        <input type="text" id="audit-search" placeholder="Search user, action, table, ID..." 
                            style="width: 100%; padding: 8px 12px 8px 34px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-main, #f9fafb); color: var(--text); font-size: 13px;">
                    </div>

                    <!-- Action Dropdown -->
                    <select id="audit-action-filter" style="padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #ffffff); color: var(--text); font-size: 13px; min-width: 150px; cursor: pointer;">
                        <option value="All Actions">All Actions</option>
                        <option value="STOCK_IN">STOCK_IN</option>
                        <option value="STOCK_OUT">STOCK_OUT</option>
                        <option value="INVENTORY_ADJUSTED">INVENTORY_ADJUSTED</option>
                        <option value="STOCK_REQUEST_CREATED">STOCK_REQUEST_CREATED</option>
                        <option value="STOCK_REQUEST_RESPONDED">STOCK_REQUEST_RESPONDED</option>
                        <option value="PO_CREATED">PO_CREATED</option>
                        <option value="PO_ACCEPTED">PO_ACCEPTED</option>
                        <option value="PO_REJECTED">PO_REJECTED</option>
                        <option value="QUOTATION_CREATED">QUOTATION_CREATED</option>
                        <option value="QUOTATION_SUBMITTED">QUOTATION_SUBMITTED</option>
                        <option value="QUOTATION_APPROVED">QUOTATION_APPROVED</option>
                        <option value="QUOTATION_REJECTED">QUOTATION_REJECTED</option>
                        <option value="SHIPMENT_CREATED">SHIPMENT_CREATED</option>
                        <option value="SHIPMENT_STATUS_CHANGED">SHIPMENT_STATUS_CHANGED</option>
                        <option value="EMPLOYEE_ASSIGNED">EMPLOYEE_ASSIGNED</option>
                        <option value="INVOICE_SUBMITTED">INVOICE_SUBMITTED</option>
                        <option value="INVOICE_APPROVED">INVOICE_APPROVED</option>
                        <option value="INVOICE_REJECTED">INVOICE_REJECTED</option>
                        <option value="INVOICE_CANCELLED">INVOICE_CANCELLED</option>
                        <option value="PAYMENT_RECORDED">PAYMENT_RECORDED</option>
                        <option value="CREATE_SUPPLIER">CREATE_SUPPLIER</option>
                        <option value="UPDATE_SUPPLIER">UPDATE_SUPPLIER</option>
                        <option value="DELETE_SUPPLIER">DELETE_SUPPLIER</option>
                        <option value="CREATE_USER">CREATE_USER</option>
                        <option value="CREATE_EMPLOYEE">CREATE_EMPLOYEE</option>
                        <option value="USER_UPDATED">USER_UPDATED</option>
                        <option value="USER_ROLE_CHANGED">USER_ROLE_CHANGED</option>
                        <option value="USER_DEACTIVATED">USER_DEACTIVATED</option>
                        <option value="USER_REACTIVATED">USER_REACTIVATED</option>
                        <option value="LOGIN">LOGIN</option>
                        <option value="PASSWORD_CHANGED">PASSWORD_CHANGED</option>
                        <option value="CREATE_PRODUCT">CREATE_PRODUCT</option>
                        <option value="UPDATE_PRODUCT">UPDATE_PRODUCT</option>
                        <option value="DEACTIVATE_PRODUCT">DEACTIVATE_PRODUCT</option>
                        <option value="DELETE_PRODUCT">DELETE_PRODUCT</option>
                        <option value="CREATE_CATEGORY">CREATE_CATEGORY</option>
                        <option value="UPDATE_CATEGORY">UPDATE_CATEGORY</option>
                        <option value="DELETE_CATEGORY">DELETE_CATEGORY</option>
                    </select>

                    <!-- Entity Dropdown -->
                    <select id="audit-table-filter" style="padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #ffffff); color: var(--text); font-size: 13px; min-width: 140px; cursor: pointer;">
                        <option value="All Entities">All Entities</option>
                        <option value="StockRequests">StockRequests</option>
                        <option value="Suppliers">Suppliers</option>
                        <option value="StockTransactions">StockTransactions</option>
                        <option value="Inventory">Inventory</option>
                        <option value="PurchaseOrders">PurchaseOrders</option>
                        <option value="SupplierQuotations">SupplierQuotations</option>
                        <option value="Shipments">Shipments</option>
                        <option value="SupplierInvoices">SupplierInvoices</option>
                        <option value="SupplierPayments">SupplierPayments</option>
                        <option value="Users">Users</option>
                        <option value="Products">Products</option>
                        <option value="Categories">Categories</option>
                    </select>

                    <!-- Start Date -->
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <label for="audit-start-date" style="font-size: 12px; color: var(--text-secondary); white-space: nowrap;">From:</label>
                        <input type="date" id="audit-start-date" style="padding: 7px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #ffffff); color: var(--text); font-size: 13px;">
                    </div>

                    <!-- End Date -->
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <label for="audit-end-date" style="font-size: 12px; color: var(--text-secondary); white-space: nowrap;">To:</label>
                        <input type="date" id="audit-end-date" style="padding: 7px 10px; border: 1px solid var(--border); border-radius: 8px; background: var(--card-bg, #ffffff); color: var(--text); font-size: 13px;">
                    </div>

                    <!-- Reset Filters Button -->
                    <button class="btn btn-secondary" id="audit-reset-btn" title="Reset all filters" style="padding: 8px 14px; font-size: 13px; border-radius: 8px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                        <i class='bx bx-reset'></i> Reset
                    </button>
                </div>
            </div>
            
            <!-- Table Container -->
            <div class="glass-panel table-container" style="border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); overflow: hidden;">
                <table id="audit-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Time</th>
                            <th>User</th>
                            <th>Action</th>
                            <th>Table</th>
                            <th>Record ID</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7" style="text-align: center; padding: 2rem;">Loading audit logs...</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- Pagination Bar -->
            <div id="audit-pagination-bar" class="pagination-container" style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; padding: 0.5rem 0; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 13px; color: var(--text-secondary);" id="audit-pagination-info">
                    Showing page 1 of 1 (0 total records)
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button class="btn btn-secondary" id="audit-prev-btn" disabled style="padding: 6px 12px; font-size: 13px; border-radius: 8px; display: inline-flex; align-items: center; gap: 4px; cursor: pointer;">
                        <i class='bx bx-chevron-left'></i> Previous
                    </button>
                    <span id="audit-page-indicator" style="font-size: 13px; font-weight: 600; padding: 0 8px;">Page 1</span>
                    <button class="btn btn-secondary" id="audit-next-btn" disabled style="padding: 6px 12px; font-size: 13px; border-radius: 8px; display: inline-flex; align-items: center; gap: 4px; cursor: pointer;">
                        Next <i class='bx bx-chevron-right'></i>
                    </button>
                </div>
            </div>
        `;
        return container;
    },

    async init() {
        this.bindEvents();
        await this.fetchLogs();
    },

    bindEvents() {
        const searchInput = document.getElementById('audit-search');
        const actionFilter = document.getElementById('audit-action-filter');
        const tableFilter = document.getElementById('audit-table-filter');
        const startDateInput = document.getElementById('audit-start-date');
        const endDateInput = document.getElementById('audit-end-date');
        const resetBtn = document.getElementById('audit-reset-btn');
        const refreshBtn = document.getElementById('audit-refresh-btn');
        const prevBtn = document.getElementById('audit-prev-btn');
        const nextBtn = document.getElementById('audit-next-btn');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.state.searchDebounceTimer);
                this.state.searchDebounceTimer = setTimeout(() => {
                    this.state.search = e.target.value.trim();
                    this.state.page = 1;
                    this.fetchLogs();
                }, 350);
            });
        }

        if (actionFilter) {
            actionFilter.addEventListener('change', (e) => {
                this.state.action = e.target.value;
                this.state.page = 1;
                this.fetchLogs();
            });
        }

        if (tableFilter) {
            tableFilter.addEventListener('change', (e) => {
                this.state.tableName = e.target.value;
                this.state.page = 1;
                this.fetchLogs();
            });
        }

        if (startDateInput) {
            startDateInput.addEventListener('change', (e) => {
                this.state.startDate = e.target.value;
                this.state.page = 1;
                this.fetchLogs();
            });
        }

        if (endDateInput) {
            endDateInput.addEventListener('change', (e) => {
                this.state.endDate = e.target.value;
                this.state.page = 1;
                this.fetchLogs();
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.state.search = '';
                this.state.action = 'All Actions';
                this.state.tableName = 'All Entities';
                this.state.startDate = '';
                this.state.endDate = '';
                this.state.page = 1;

                if (searchInput) searchInput.value = '';
                if (actionFilter) actionFilter.value = 'All Actions';
                if (tableFilter) tableFilter.value = 'All Entities';
                if (startDateInput) startDateInput.value = '';
                if (endDateInput) endDateInput.value = '';

                this.fetchLogs();
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.fetchLogs();
            });
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.state.page > 1) {
                    this.state.page--;
                    this.fetchLogs();
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (this.state.page < this.state.totalPages) {
                    this.state.page++;
                    this.fetchLogs();
                }
            });
        }
    },

    async fetchLogs() {
        const tbody = document.querySelector('#audit-table tbody');
        if (!tbody) return;

        this.state.isLoading = true;
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: var(--text-secondary);"><i class='bx bx-loader-alt bx-spin'></i> Loading audit logs...</td></tr>`;

        try {
            const queryParams = new URLSearchParams();
            queryParams.set('page', this.state.page);
            queryParams.set('limit', this.state.limit);

            if (this.state.search) {
                queryParams.set('search', this.state.search);
            }
            if (this.state.action && this.state.action !== 'All Actions') {
                queryParams.set('action', this.state.action);
            }
            if (this.state.tableName && this.state.tableName !== 'All Entities') {
                queryParams.set('table_name', this.state.tableName);
            }
            if (this.state.startDate) {
                queryParams.set('start_date', this.state.startDate);
            }
            if (this.state.endDate) {
                queryParams.set('end_date', this.state.endDate);
            }

            const data = await Api.get(`/audit-logs/?${queryParams.toString()}`);

            // Handle both paginated object and legacy array formats
            const logs = Array.isArray(data) ? data : (data?.logs || []);
            const total = Array.isArray(data) ? data.length : (data?.total !== undefined ? data.total : 0);
            const page = Array.isArray(data) ? 1 : (data?.page || 1);
            const totalPages = Array.isArray(data) ? 1 : (data?.total_pages !== undefined ? data.total_pages : 0);

            this.state.logs = logs;
            this.state.total = total;
            this.state.page = page;
            this.state.totalPages = totalPages;

            this.renderTable(logs);
            this.updatePaginationUI();

        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-danger" style="text-align: center; padding: 2rem;">Failed to load audit logs: ${Utils.escapeHtml(error.message || 'Unknown error')}</td></tr>`;
            this.updatePaginationUI();
        } finally {
            this.state.isLoading = false;
        }
    },

    renderTable(logs) {
        const tbody = document.querySelector('#audit-table tbody');
        if (!tbody) return;

        if (!logs || logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-secondary);">No audit logs found matching criteria.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => {
            const userDisplay = l.username || (l.user_id != null ? `User #${l.user_id}` : 'System');
            const roleBadge = l.role_name && l.role_name !== 'Unknown' 
                ? `<span style="font-size: 10px; color: var(--text-secondary); margin-left: 4px;">(${Utils.escapeHtml(l.role_name)})</span>` 
                : '';
            const recordIdDisplay = (l.record_id !== null && l.record_id !== undefined && l.record_id !== '') ? String(l.record_id) : '-';

            return `
                <tr class="audit-row" data-log-id="${l.log_id}" style="cursor: pointer; border-bottom: 1px solid var(--border); transition: background 0.15s;" title="Click to view full event details">
                    <td style="padding: 12px 14px; font-weight: 600; color: var(--primary);">#${Utils.escapeHtml(String(l.log_id || ''))}</td>
                    <td style="padding: 12px 14px; font-size: 13px; color: var(--text);">${Utils.formatDate(l.action_time)}</td>
                    <td style="padding: 12px 14px; font-size: 13px; font-weight: 500;">${Utils.escapeHtml(userDisplay)} ${roleBadge}</td>
                    <td style="padding: 12px 14px;">
                        <span class="badge" style="position: relative; top: 0; background: rgba(37, 99, 235, 0.08); color: var(--primary); font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px;">
                            ${Utils.escapeHtml(l.action || '-')}
                        </span>
                    </td>
                    <td style="padding: 12px 14px; font-size: 13px; font-family: monospace;">${Utils.escapeHtml(l.table_name || '-')}</td>
                    <td style="padding: 12px 14px; font-size: 13px;">${Utils.escapeHtml(recordIdDisplay)}</td>
                    <td style="padding: 12px 14px; font-size: 12px; color: var(--text-secondary); font-family: monospace;">${Utils.escapeHtml(l.ip_address || '-')}</td>
                </tr>
            `;
        }).join('');

        // Attach click listeners for event detail modal
        const rows = tbody.querySelectorAll('.audit-row');
        rows.forEach(row => {
            row.addEventListener('click', () => {
                const logId = parseInt(row.getAttribute('data-log-id'), 10);
                const logItem = this.state.logs.find(item => item.log_id === logId);
                if (logItem) {
                    this.showDetailsModal(logItem);
                }
            });
            row.addEventListener('mouseenter', () => {
                row.style.background = 'var(--surface-hover, rgba(0, 0, 0, 0.02))';
            });
            row.addEventListener('mouseleave', () => {
                row.style.background = '';
            });
        });
    },

    updatePaginationUI() {
        const totalBadge = document.getElementById('audit-total-badge');
        const infoEl = document.getElementById('audit-pagination-info');
        const indicatorEl = document.getElementById('audit-page-indicator');
        const prevBtn = document.getElementById('audit-prev-btn');
        const nextBtn = document.getElementById('audit-next-btn');

        const total = this.state.total;
        const page = this.state.page;
        const totalPages = this.state.totalPages;

        if (totalBadge) {
            totalBadge.textContent = `Total Logs: ${total.toLocaleString()}`;
        }

        if (infoEl) {
            if (total === 0) {
                infoEl.textContent = 'Showing 0 records';
            } else {
                infoEl.textContent = `Showing page ${page} of ${totalPages} (${total.toLocaleString()} total records)`;
            }
        }

        if (indicatorEl) {
            indicatorEl.textContent = totalPages > 0 ? `Page ${page} of ${totalPages}` : 'Page 1';
        }

        if (prevBtn) {
            prevBtn.disabled = (page <= 1);
            prevBtn.style.opacity = (page <= 1) ? '0.5' : '1';
        }

        if (nextBtn) {
            nextBtn.disabled = (page >= totalPages || totalPages === 0);
            nextBtn.style.opacity = (page >= totalPages || totalPages === 0) ? '0.5' : '1';
        }
    },

    showDetailsModal(logItem) {
        const recordIdDisplay = (logItem.record_id !== null && logItem.record_id !== undefined && logItem.record_id !== '')
            ? Utils.escapeHtml(String(logItem.record_id))
            : '<em>None</em>';
        const userDisplay = logItem.username || (logItem.user_id != null ? `User #${logItem.user_id}` : 'System');
        const roleDisplay = logItem.role_name && logItem.role_name !== 'Unknown' ? logItem.role_name : 'N/A';

        Modal.create({
            id: 'audit-detail-modal',
            title: `<i class='bx bx-file-find text-primary'></i> Audit Event #${Utils.escapeHtml(String(logItem.log_id || ''))}`,
            content: `
                <div style="display: flex; flex-direction: column; gap: 14px; font-size: 13.5px;">
                    <div style="display: grid; grid-template-columns: 130px 1fr; gap: 10px; align-items: center;">
                        <span style="font-weight: 600; color: var(--text-secondary);">Log ID:</span>
                        <span style="font-weight: 700; color: var(--primary);">#${Utils.escapeHtml(String(logItem.log_id || ''))}</span>

                        <span style="font-weight: 600; color: var(--text-secondary);">Event Timestamp:</span>
                        <span>${Utils.formatDate(logItem.action_time)}</span>

                        <span style="font-weight: 600; color: var(--text-secondary);">Actor:</span>
                        <span>
                            <strong>${Utils.escapeHtml(userDisplay)}</strong>
                            <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #059669; font-size: 11px; margin-left: 6px; padding: 2px 8px; border-radius: 4px;">
                                ${Utils.escapeHtml(roleDisplay)}
                            </span>
                            ${logItem.user_id != null ? `<span style="font-size: 11px; color: var(--text-secondary); margin-left: 4px;">(ID: ${logItem.user_id})</span>` : ''}
                        </span>

                        <span style="font-weight: 600; color: var(--text-secondary);">Action Verb:</span>
                        <span>
                            <span class="badge" style="background: rgba(37, 99, 235, 0.1); color: var(--primary); font-weight: 700; font-size: 12px; padding: 4px 10px; border-radius: 6px;">
                                ${Utils.escapeHtml(logItem.action || '-')}
                            </span>
                        </span>

                        <span style="font-weight: 600; color: var(--text-secondary);">Target Entity:</span>
                        <code style="padding: 2px 6px; background: var(--surface, #f8fafc); border-radius: 4px; border: 1px solid var(--border); font-size: 12.5px;">
                            ${Utils.escapeHtml(logItem.table_name || '-')}
                        </code>

                        <span style="font-weight: 600; color: var(--text-secondary);">Target Record ID:</span>
                        <span>${recordIdDisplay}</span>

                        <span style="font-weight: 600; color: var(--text-secondary);">Client IP Address:</span>
                        <code style="padding: 2px 6px; background: var(--surface, #f8fafc); border-radius: 4px; border: 1px solid var(--border); font-size: 12px;">
                            ${Utils.escapeHtml(logItem.ip_address || '127.0.0.1')}
                        </code>
                    </div>

                    <div style="margin-top: 8px; padding: 12px; background: rgba(59, 130, 246, 0.05); border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.15); font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
                        <i class='bx bx-shield-check text-primary' style="font-size: 15px; vertical-align: -2px;"></i>
                        <strong>Immutability Guarantee:</strong> Audit records are write-once append-only ledgers. Individual state diffs are omitted from storage to preserve lightweight integrity across high-throughput operations.
                    </div>
                </div>
            `,
            footer: `
                <div style="display: flex; justify-content: flex-end; width: 100%;">
                    <button type="button" class="btn btn-primary close-modal-btn" style="padding: 7px 18px; border-radius: 8px; cursor: pointer;">Close</button>
                </div>
            `,
            onOpen: (modalEl, closeModal) => {
                const btn = modalEl.querySelector('.close-modal-btn');
                if (btn) btn.addEventListener('click', closeModal);
            }
        });
    }
};
