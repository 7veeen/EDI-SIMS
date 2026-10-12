// payments.js - SIMS Supplier Invoices & Payments Management (Phase 3)

App.pages['payments'] = {
    currentTab: 'invoices', // 'invoices' | 'payments'
    
    // Invoices state
    invoices: [],
    invoiceStats: {
        total_invoices: 0,
        total_amount: 0.0,
        total_paid: 0.0,
        total_outstanding: 0.0,
        status_counts: {}
    },
    invoiceFilters: {
        search: '',
        status: '',
        date_from: '',
        date_to: '',
        page: 1,
        limit: 15
    },
    invoicePagination: {
        page: 1,
        limit: 15,
        total_count: 0,
        total_pages: 1
    },

    // Payments state
    paymentsList: [],
    paymentStats: {
        total_payments: 0,
        total_disbursed: 0.0
    },
    paymentFilters: {
        search: '',
        payment_method: '',
        date_from: '',
        date_to: '',
        page: 1,
        limit: 15
    },
    paymentPagination: {
        page: 1,
        limit: 15,
        total_count: 0,
        total_pages: 1
    },

    // Cache
    cachedPOs: [],
    cachedApprovedInvoices: [],

    render() {
        const user = Auth.getUser();
        const role = user ? user.role : '';
        const isSupplier = role === 'Supplier';
        const isManagerOrOwner = role === 'Owner' || role === 'Manager';

        const container = document.createElement('div');
        container.className = 'page-payments-root';
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">ACCOUNTS PAYABLE &amp; PROCUREMENT</span>
                    <h1>${isSupplier ? 'Invoices &amp; Payments 💳' : 'Supplier Invoices &amp; Disbursements 💳'}</h1>
                    <p>${isSupplier 
                        ? 'Submit invoices for delivered &amp; received goods, track approval status, and view payment vouchers.' 
                        : 'Review supplier invoice submissions, authorize approvals, record disbursements, and monitor financial ledgers.'}
                    </p>
                </div>
                <div class="header-actions">
                    <button class="btn secondary" id="btn-refresh-finance" title="Refresh financial records">
                        <i class='bx bx-refresh'></i> Refresh
                    </button>
                    ${isSupplier ? `
                        <button class="btn primary" id="btn-open-submit-invoice">
                            <i class='bx bx-plus-circle'></i> Submit Invoice
                        </button>
                    ` : ''}
                    ${isManagerOrOwner ? `
                        <button class="btn primary" id="btn-open-record-payment">
                            <i class='bx bx-credit-card'></i> Record Payment
                        </button>
                    ` : ''}
                </div>
            </div>

            <!-- Tab Navigation Bar -->
            <div class="financial-tabs-bar">
                <button type="button" class="financial-tab-btn ${this.currentTab === 'invoices' ? 'active' : ''}" id="tab-btn-invoices">
                    <i class='bx bx-receipt'></i> Invoices
                    <span class="tab-count" id="badge-invoice-count">0</span>
                </button>
                <button type="button" class="financial-tab-btn ${this.currentTab === 'payments' ? 'active' : ''}" id="tab-btn-payments">
                    <i class='bx bx-wallet'></i> ${isSupplier ? 'Payment History' : 'Disbursement Ledger'}
                    <span class="tab-count" id="badge-payment-count">0</span>
                </button>
            </div>

            <!-- Active Tab Content Area -->
            <div id="financial-tab-content">
                <!-- Dynamically populated by switchTab -->
            </div>
        `;

        return container;
    },

    async init() {
        this.setupTabListeners();
        this.setupHeaderActions();
        await this.loadActiveTabContent();
    },

    setupTabListeners() {
        const btnInvoices = document.getElementById('tab-btn-invoices');
        const btnPayments = document.getElementById('tab-btn-payments');

        if (btnInvoices) {
            btnInvoices.addEventListener('click', () => {
                if (this.currentTab !== 'invoices') {
                    this.currentTab = 'invoices';
                    this.updateTabButtons();
                    this.renderInvoicesTab();
                }
            });
        }

        if (btnPayments) {
            btnPayments.addEventListener('click', () => {
                if (this.currentTab !== 'payments') {
                    this.currentTab = 'payments';
                    this.updateTabButtons();
                    this.renderPaymentsTab();
                }
            });
        }
    },

    updateTabButtons() {
        const btnInvoices = document.getElementById('tab-btn-invoices');
        const btnPayments = document.getElementById('tab-btn-payments');
        if (btnInvoices) {
            btnInvoices.classList.toggle('active', this.currentTab === 'invoices');
        }
        if (btnPayments) {
            btnPayments.classList.toggle('active', this.currentTab === 'payments');
        }
    },

    setupHeaderActions() {
        const refreshBtn = document.getElementById('btn-refresh-finance');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                const icon = refreshBtn.querySelector('i');
                if (icon) icon.classList.add('bx-spin');
                await this.loadActiveTabContent();
                if (icon) icon.classList.remove('bx-spin');
                Utils.showToast("Financial data refreshed", "success");
            });
        }

        const submitInvoiceBtn = document.getElementById('btn-open-submit-invoice');
        if (submitInvoiceBtn) {
            submitInvoiceBtn.addEventListener('click', () => {
                this.openSubmitInvoiceModal();
            });
        }

        const recordPaymentBtn = document.getElementById('btn-open-record-payment');
        if (recordPaymentBtn) {
            recordPaymentBtn.addEventListener('click', () => {
                this.openRecordPaymentModal();
            });
        }
    },

    async loadActiveTabContent() {
        if (this.currentTab === 'invoices') {
            await this.renderInvoicesTab();
        } else {
            await this.renderPaymentsTab();
        }
    },

    // =========================================================
    // INVOICES TAB LOGIC
    // =========================================================

    async renderInvoicesTab() {
        const contentArea = document.getElementById('financial-tab-content');
        if (!contentArea) return;

        const user = Auth.getUser();
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');

        contentArea.innerHTML = `
            <!-- Stat Ribbon -->
            <div class="fin-stats-grid">
                <div class="fin-stat-card">
                    <div class="fin-stat-header">
                        <span class="fin-stat-title">Total Invoiced</span>
                        <div class="fin-stat-icon primary"><i class='bx bx-receipt'></i></div>
                    </div>
                    <div>
                        <div class="fin-stat-value" id="stat-inv-total-amount">₹0.00</div>
                        <span class="fin-stat-desc" id="stat-inv-total-count">0 recorded invoices</span>
                    </div>
                </div>

                <div class="fin-stat-card">
                    <div class="fin-stat-header">
                        <span class="fin-stat-title">Pending / Submitted</span>
                        <div class="fin-stat-icon warning"><i class='bx bx-time-five'></i></div>
                    </div>
                    <div>
                        <div class="fin-stat-value" id="stat-inv-pending-count" style="color: #d97706;">0</div>
                        <span class="fin-stat-desc">Awaiting management approval</span>
                    </div>
                </div>

                <div class="fin-stat-card">
                    <div class="fin-stat-header">
                        <span class="fin-stat-title">Total Paid</span>
                        <div class="fin-stat-icon success"><i class='bx bx-check-double'></i></div>
                    </div>
                    <div>
                        <div class="fin-stat-value" id="stat-inv-paid-amount" style="color: #059669;">₹0.00</div>
                        <span class="fin-stat-desc" id="stat-inv-paid-count">0 paid invoices</span>
                    </div>
                </div>

                <div class="fin-stat-card">
                    <div class="fin-stat-header">
                        <span class="fin-stat-title">Outstanding Due</span>
                        <div class="fin-stat-icon purple"><i class='bx bx-rupee'></i></div>
                    </div>
                    <div>
                        <div class="fin-stat-value" id="stat-inv-outstanding-amount" style="color: #7c3aed;">₹0.00</div>
                        <span class="fin-stat-desc">Remaining payable balance</span>
                    </div>
                </div>
            </div>

            <!-- Search & Filters -->
            <div class="card" style="padding: 16px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between;">
                <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; flex: 1;">
                    <div class="global-search" style="margin: 0; flex: 1; min-width: 240px; max-width: 360px; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="inv-search-input" placeholder="Search by Invoice #, PO #, or supplier..." value="${Utils.escapeHtml(this.invoiceFilters.search)}" style="background: transparent;">
                    </div>

                    <div style="min-width: 160px;">
                        <select id="inv-status-select" class="input" style="height: 42px; margin: 0;">
                            <option value="">All Statuses</option>
                            <option value="Submitted" ${this.invoiceFilters.status === 'Submitted' ? 'selected' : ''}>Submitted</option>
                            <option value="Approved" ${this.invoiceFilters.status === 'Approved' ? 'selected' : ''}>Approved</option>
                            <option value="Partially Paid" ${this.invoiceFilters.status === 'Partially Paid' ? 'selected' : ''}>Partially Paid</option>
                            <option value="Paid" ${this.invoiceFilters.status === 'Paid' ? 'selected' : ''}>Paid</option>
                            <option value="Rejected" ${this.invoiceFilters.status === 'Rejected' ? 'selected' : ''}>Rejected</option>
                            <option value="Cancelled" ${this.invoiceFilters.status === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
                        </select>
                    </div>

                    <div style="display: flex; align-items: center; gap: 6px;">
                        <input type="date" id="inv-date-from" class="input" style="height: 42px; margin: 0; width: 140px;" value="${this.invoiceFilters.date_from}" title="Date From">
                        <span style="color: var(--text-secondary);">-</span>
                        <input type="date" id="inv-date-to" class="input" style="height: 42px; margin: 0; width: 140px;" value="${this.invoiceFilters.date_to}" title="Date To">
                    </div>

                    <button type="button" class="btn secondary" id="btn-reset-inv-filters" style="height: 42px; padding: 0 14px;" title="Reset filters">
                        <i class='bx bx-reset'></i> Reset
                    </button>
                </div>

                <div id="inv-count-indicator" style="font-size: 13px; color: var(--text-secondary);">
                    Loading invoices...
                </div>
            </div>

            <!-- Invoices Table -->
            <div class="card table-responsive" style="margin-top: 10px;">
                <table class="table" id="invoices-table">
                    <thead>
                        <tr>
                            <th>INVOICE #</th>
                            ${isManagerOrOwner ? '<th>SUPPLIER</th>' : ''}
                            <th>PURCHASE ORDER</th>
                            <th>SHIPMENT</th>
                            <th>INVOICE / DUE DATE</th>
                            <th>TOTAL AMOUNT</th>
                            <th>PAID / BALANCE</th>
                            <th>STATUS</th>
                            <th style="text-align: right;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody id="invoices-tbody">
                        <tr><td colspan="${isManagerOrOwner ? 9 : 8}" style="text-align: center; padding: 36px; color: var(--text-secondary);">
                            <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; vertical-align: middle;"></i> Loading invoices...
                        </td></tr>
                    </tbody>
                </table>

                <div class="fin-pagination-bar" id="invoices-pagination-bar" style="display: none;">
                    <span id="inv-page-info" style="font-size: 13px; color: var(--text-secondary);"></span>
                    <div style="display: flex; gap: 8px;">
                        <button type="button" class="fin-page-btn" id="btn-inv-prev"><i class='bx bx-chevron-left'></i> Previous</button>
                        <button type="button" class="fin-page-btn" id="btn-inv-next">Next <i class='bx bx-chevron-right'></i></button>
                    </div>
                </div>
            </div>
        `;

        this.attachInvoiceFilterListeners();
        await this.loadInvoicesData();
    },

    attachInvoiceFilterListeners() {
        const searchInput = document.getElementById('inv-search-input');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.invoiceFilters.search = e.target.value.trim();
                    this.invoiceFilters.page = 1;
                    this.loadInvoicesData();
                }, 350);
            });
        }

        const statusSelect = document.getElementById('inv-status-select');
        if (statusSelect) {
            statusSelect.addEventListener('change', (e) => {
                this.invoiceFilters.status = e.target.value;
                this.invoiceFilters.page = 1;
                this.loadInvoicesData();
            });
        }

        const dateFromInput = document.getElementById('inv-date-from');
        if (dateFromInput) {
            dateFromInput.addEventListener('change', (e) => {
                this.invoiceFilters.date_from = e.target.value;
                this.invoiceFilters.page = 1;
                this.loadInvoicesData();
            });
        }

        const dateToInput = document.getElementById('inv-date-to');
        if (dateToInput) {
            dateToInput.addEventListener('change', (e) => {
                this.invoiceFilters.date_to = e.target.value;
                this.invoiceFilters.page = 1;
                this.loadInvoicesData();
            });
        }

        const resetBtn = document.getElementById('btn-reset-inv-filters');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.invoiceFilters = { search: '', status: '', date_from: '', date_to: '', page: 1, limit: 15 };
                if (searchInput) searchInput.value = '';
                if (statusSelect) statusSelect.value = '';
                if (dateFromInput) dateFromInput.value = '';
                if (dateToInput) dateToInput.value = '';
                this.loadInvoicesData();
            });
        }

        const prevBtn = document.getElementById('btn-inv-prev');
        const nextBtn = document.getElementById('btn-inv-next');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.invoiceFilters.page > 1) {
                    this.invoiceFilters.page--;
                    this.loadInvoicesData();
                }
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (this.invoiceFilters.page < this.invoicePagination.total_pages) {
                    this.invoiceFilters.page++;
                    this.loadInvoicesData();
                }
            });
        }
    },

    async loadInvoicesData() {
        const tbody = document.getElementById('invoices-tbody');
        const countIndicator = document.getElementById('inv-count-indicator');
        const paginationBar = document.getElementById('invoices-pagination-bar');
        const pageInfo = document.getElementById('inv-page-info');
        const prevBtn = document.getElementById('btn-inv-prev');
        const nextBtn = document.getElementById('btn-inv-next');

        const user = Auth.getUser();
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');
        const isSupplier = user && user.role === 'Supplier';

        try {
            const params = {
                search: this.invoiceFilters.search,
                status: this.invoiceFilters.status,
                date_from: this.invoiceFilters.date_from,
                date_to: this.invoiceFilters.date_to,
                page: this.invoiceFilters.page,
                limit: this.invoiceFilters.limit
            };

            const data = await Api.getInvoices(params);
            this.invoices = data.invoices || [];
            this.invoiceStats = data.stats || {};
            this.invoicePagination = data.pagination || { page: 1, limit: 15, total_count: this.invoices.length, total_pages: 1 };

            // Update tab badge
            const badge = document.getElementById('badge-invoice-count');
            if (badge) badge.textContent = this.invoicePagination.total_count || 0;

            // Update metric cards
            this.updateInvoiceStatCards();

            if (countIndicator) {
                countIndicator.textContent = `Showing ${this.invoices.length} of ${this.invoicePagination.total_count} invoices`;
            }

            if (!tbody) return;

            if (this.invoices.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="${isManagerOrOwner ? 9 : 8}" style="text-align: center; padding: 48px 24px;">
                            ${Utils.emptyState('bx-receipt', 'No Invoices Found', 'No supplier invoices match your current search and filter criteria.')}
                            ${isSupplier ? `
                                <div style="margin-top: 16px;">
                                    <button class="btn primary" onclick="App.pages['payments'].openSubmitInvoiceModal()">
                                        <i class='bx bx-plus-circle'></i> Submit First Invoice
                                    </button>
                                </div>
                            ` : ''}
                        </td>
                    </tr>
                `;
                if (paginationBar) paginationBar.style.display = 'none';
                return;
            }

            // Populate table rows
            tbody.innerHTML = this.invoices.map(inv => {
                const badgeHtml = this.getStatusBadge(inv.status);
                const isOverdue = inv.status !== 'Paid' && inv.status !== 'Cancelled' && inv.due_date && new Date(inv.due_date) < new Date();
                
                // Consequential action permissions
                const canApprove = isManagerOrOwner && inv.status === 'Submitted';
                const canReject = isManagerOrOwner && inv.status === 'Submitted';
                const canPay = isManagerOrOwner && (inv.status === 'Approved' || inv.status === 'Partially Paid');
                const canCancel = (isSupplier && inv.status === 'Submitted') || 
                                  (isManagerOrOwner && (inv.status === 'Submitted' || inv.status === 'Approved') && (Number(inv.total_paid) === 0));

                return `
                    <tr id="inv-row-${inv.invoice_id}">
                        <td>
                            <strong style="color: var(--text); font-size: 14px;">${Utils.escapeHtml(inv.invoice_number)}</strong>
                            <div style="font-size: 11px; color: var(--text-secondary);">ID #${inv.invoice_id}</div>
                        </td>
                        ${isManagerOrOwner ? `
                            <td>
                                <strong>${Utils.escapeHtml(inv.supplier_name || 'Supplier')}</strong>
                                <div style="font-size: 11px; color: var(--text-secondary);">ID #${inv.supplier_id}</div>
                            </td>
                        ` : ''}
                        <td>
                            <span style="font-weight: 600; color: var(--primary);"><i class='bx bx-file-blank'></i> ${Utils.escapeHtml(inv.po_number || `PO #${inv.purchase_order_id}`)}</span>
                            <div style="font-size: 11px; color: var(--text-secondary);">PO Total: ₹${Number(inv.po_total || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                        </td>
                        <td>
                            ${inv.shipment_id ? `
                                <span class="badge" style="background: rgba(59, 130, 246, 0.1); color: #2563eb; font-size: 11px;">
                                    <i class='bx bx-car'></i> ${Utils.escapeHtml(inv.tracking_number || `Shipment #${inv.shipment_id}`)}
                                </span>
                            ` : `<span style="color: var(--text-secondary); font-size: 12px;">PO-Level Receipt</span>`}
                        </td>
                        <td>
                            <div style="font-size: 13px; font-weight: 500;">${inv.invoice_date || '-'}</div>
                            <div style="font-size: 11px; ${isOverdue ? 'color: #dc2626; font-weight: 700;' : 'color: var(--text-secondary);'}">
                                ${isOverdue ? '<i class="bx bx-error-circle"></i> Overdue: ' : 'Due: '}${inv.due_date || '-'}
                            </div>
                        </td>
                        <td>
                            <div style="font-weight: 700; font-size: 14px; color: var(--text);">₹${Number(inv.total_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                            <div style="font-size: 11px; color: var(--text-secondary);">Sub: ₹${Number(inv.subtotal).toFixed(2)} | Tax: ₹${Number(inv.tax_amount).toFixed(2)}</div>
                        </td>
                        <td>
                            <div style="font-size: 12px; color: #059669; font-weight: 600;">Paid: ₹${Number(inv.total_paid || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                            <div style="font-size: 12px; color: ${Number(inv.remaining_balance) > 0 ? '#7c3aed' : 'var(--text-secondary)'}; font-weight: 700;">
                                Bal: ₹${Number(inv.remaining_balance || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}
                            </div>
                        </td>
                        <td>
                            ${badgeHtml}
                        </td>
                        <td style="text-align: right;">
                            <div class="fin-action-group">
                                <button type="button" class="fin-btn-icon" title="View Invoice Details" onclick="App.pages['payments'].viewInvoiceDetails(${inv.invoice_id})">
                                    <i class='bx bx-show'></i>
                                </button>
                                ${canPay ? `
                                    <button type="button" class="fin-btn-icon pay" title="Record Payment" onclick="App.pages['payments'].openRecordPaymentModal(${inv.invoice_id})">
                                        <i class='bx bx-credit-card'></i>
                                    </button>
                                ` : ''}
                                ${canApprove ? `
                                    <button type="button" class="fin-btn-icon success" title="Approve Invoice" onclick="App.pages['payments'].promptApproveInvoice(${inv.invoice_id}, '${Utils.escapeHtml(inv.invoice_number)}', ${inv.total_amount})">
                                        <i class='bx bx-check'></i>
                                    </button>
                                ` : ''}
                                ${canReject ? `
                                    <button type="button" class="fin-btn-icon danger" title="Reject Invoice" onclick="App.pages['payments'].promptRejectInvoice(${inv.invoice_id}, '${Utils.escapeHtml(inv.invoice_number)}')">
                                        <i class='bx bx-x'></i>
                                    </button>
                                ` : ''}
                                ${canCancel ? `
                                    <button type="button" class="fin-btn-icon" title="Cancel Invoice" onclick="App.pages['payments'].promptCancelInvoice(${inv.invoice_id}, '${Utils.escapeHtml(inv.invoice_number)}')">
                                        <i class='bx bx-block'></i>
                                    </button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');

            // Pagination setup
            if (paginationBar) {
                paginationBar.style.display = 'flex';
                const curPage = this.invoicePagination.page;
                const totalPages = this.invoicePagination.total_pages;
                if (pageInfo) {
                    pageInfo.textContent = `Page ${curPage} of ${totalPages} (${this.invoicePagination.total_count} total invoices)`;
                }
                if (prevBtn) prevBtn.disabled = curPage <= 1;
                if (nextBtn) nextBtn.disabled = curPage >= totalPages;
            }

        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="${isManagerOrOwner ? 9 : 8}" class="text-danger" style="text-align: center; padding: 24px;">Failed to load invoices: ${Utils.escapeHtml(err.message || 'Server error')}</td></tr>`;
            if (countIndicator) countIndicator.textContent = 'Error loading invoices';
        }
    },

    updateInvoiceStatCards() {
        const stats = this.invoiceStats;
        const totalAmtEl = document.getElementById('stat-inv-total-amount');
        const totalCountEl = document.getElementById('stat-inv-total-count');
        const pendingCountEl = document.getElementById('stat-inv-pending-count');
        const paidAmtEl = document.getElementById('stat-inv-paid-amount');
        const paidCountEl = document.getElementById('stat-inv-paid-count');
        const outAmtEl = document.getElementById('stat-inv-outstanding-amount');

        if (totalAmtEl) totalAmtEl.textContent = Utils.formatCurrency(stats.total_amount || 0);
        if (totalCountEl) totalCountEl.textContent = `${stats.total_invoices || 0} recorded invoices`;
        
        const counts = stats.status_counts || {};
        if (pendingCountEl) pendingCountEl.textContent = counts['Submitted'] || 0;
        if (paidAmtEl) paidAmtEl.textContent = Utils.formatCurrency(stats.total_paid || 0);
        if (paidCountEl) paidCountEl.textContent = `${counts['Paid'] || 0} fully paid, ${counts['Partially Paid'] || 0} partial`;
        if (outAmtEl) outAmtEl.textContent = Utils.formatCurrency(stats.total_outstanding || 0);
    },

    getStatusBadge(status) {
        switch (status) {
            case 'Submitted':
                return `<span class="fin-badge fin-badge-submitted"><i class='bx bx-time'></i> Submitted</span>`;
            case 'Approved':
                return `<span class="fin-badge fin-badge-approved"><i class='bx bx-check'></i> Approved</span>`;
            case 'Partially Paid':
                return `<span class="fin-badge fin-badge-partially-paid"><i class='bx bx-adjust'></i> Partially Paid</span>`;
            case 'Paid':
                return `<span class="fin-badge fin-badge-paid"><i class='bx bx-check-double'></i> Paid</span>`;
            case 'Rejected':
                return `<span class="fin-badge fin-badge-rejected"><i class='bx bx-x-circle'></i> Rejected</span>`;
            case 'Cancelled':
                return `<span class="fin-badge fin-badge-cancelled"><i class='bx bx-block'></i> Cancelled</span>`;
            default:
                return `<span class="fin-badge" style="background: #e2e8f0; color: #475569;">${Utils.escapeHtml(status || 'Unknown')}</span>`;
        }
    },

    // =========================================================
    // PAYMENTS TAB LOGIC
    // =========================================================

    async renderPaymentsTab() {
        const contentArea = document.getElementById('financial-tab-content');
        if (!contentArea) return;

        const user = Auth.getUser();
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');

        contentArea.innerHTML = `
            <!-- Stat Ribbon -->
            <div class="fin-stats-grid">
                <div class="fin-stat-card">
                    <div class="fin-stat-header">
                        <span class="fin-stat-title">Total Disbursed</span>
                        <div class="fin-stat-icon success"><i class='bx bx-wallet'></i></div>
                    </div>
                    <div>
                        <div class="fin-stat-value" id="stat-pay-total-amount" style="color: #059669;">₹0.00</div>
                        <span class="fin-stat-desc" id="stat-pay-total-count">0 recorded disbursements</span>
                    </div>
                </div>

                <div class="fin-stat-card">
                    <div class="fin-stat-header">
                        <span class="fin-stat-title">Disbursement Ledger</span>
                        <div class="fin-stat-icon primary"><i class='bx bx-credit-card'></i></div>
                    </div>
                    <div>
                        <div class="fin-stat-value" id="stat-pay-record-count">0</div>
                        <span class="fin-stat-desc">Completed accounts payable payments</span>
                    </div>
                </div>

                <div class="fin-stat-card">
                    <div class="fin-stat-header">
                        <span class="fin-stat-title">Corporate Settlement</span>
                        <div class="fin-stat-icon info"><i class='bx bx-shield-quarter'></i></div>
                    </div>
                    <div>
                        <div class="fin-stat-value" style="font-size: 18px; color: #2563eb;">NEFT &bull; RTGS &bull; UPI</div>
                        <span class="fin-stat-desc">Direct corporate payment methods</span>
                    </div>
                </div>
            </div>

            <!-- Search & Filters -->
            <div class="card" style="padding: 16px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between;">
                <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; flex: 1;">
                    <div class="global-search" style="margin: 0; flex: 1; min-width: 240px; max-width: 360px; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="pay-search-input" placeholder="Search by Reference #, Invoice #, or supplier..." value="${Utils.escapeHtml(this.paymentFilters.search)}" style="background: transparent;">
                    </div>

                    <div style="min-width: 190px;">
                        <select id="pay-method-select" class="input" style="height: 42px; margin: 0;">
                            <option value="">All Payment Methods</option>
                            <option value="Bank Transfer / NEFT" ${this.paymentFilters.payment_method === 'Bank Transfer / NEFT' ? 'selected' : ''}>Bank Transfer / NEFT</option>
                            <option value="RTGS" ${this.paymentFilters.payment_method === 'RTGS' ? 'selected' : ''}>RTGS</option>
                            <option value="Cheque" ${this.paymentFilters.payment_method === 'Cheque' ? 'selected' : ''}>Cheque</option>
                            <option value="UPI" ${this.paymentFilters.payment_method === 'UPI' ? 'selected' : ''}>UPI</option>
                            <option value="Wire Transfer" ${this.paymentFilters.payment_method === 'Wire Transfer' ? 'selected' : ''}>Wire Transfer</option>
                            <option value="Cash" ${this.paymentFilters.payment_method === 'Cash' ? 'selected' : ''}>Cash</option>
                            <option value="Other" ${this.paymentFilters.payment_method === 'Other' ? 'selected' : ''}>Other</option>
                        </select>
                    </div>

                    <div style="display: flex; align-items: center; gap: 6px;">
                        <input type="date" id="pay-date-from" class="input" style="height: 42px; margin: 0; width: 140px;" value="${this.paymentFilters.date_from}" title="Date From">
                        <span style="color: var(--text-secondary);">-</span>
                        <input type="date" id="pay-date-to" class="input" style="height: 42px; margin: 0; width: 140px;" value="${this.paymentFilters.date_to}" title="Date To">
                    </div>

                    <button type="button" class="btn secondary" id="btn-reset-pay-filters" style="height: 42px; padding: 0 14px;" title="Reset filters">
                        <i class='bx bx-reset'></i> Reset
                    </button>
                </div>

                <div id="pay-count-indicator" style="font-size: 13px; color: var(--text-secondary);">
                    Loading payments...
                </div>
            </div>

            <!-- Payments Table -->
            <div class="card table-responsive" style="margin-top: 10px;">
                <table class="table" id="payments-table">
                    <thead>
                        <tr>
                            <th>PAYMENT REF</th>
                            <th>INVOICE #</th>
                            ${isManagerOrOwner ? '<th>SUPPLIER</th>' : ''}
                            <th>PAYMENT DATE</th>
                            <th>AMOUNT PAID</th>
                            <th>PAYMENT METHOD</th>
                            <th>RECORDED BY</th>
                            <th style="text-align: right;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody id="payments-tbody">
                        <tr><td colspan="${isManagerOrOwner ? 8 : 7}" style="text-align: center; padding: 36px; color: var(--text-secondary);">
                            <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; vertical-align: middle;"></i> Loading payments...
                        </td></tr>
                    </tbody>
                </table>

                <div class="fin-pagination-bar" id="payments-pagination-bar" style="display: none;">
                    <span id="pay-page-info" style="font-size: 13px; color: var(--text-secondary);"></span>
                    <div style="display: flex; gap: 8px;">
                        <button type="button" class="fin-page-btn" id="btn-pay-prev"><i class='bx bx-chevron-left'></i> Previous</button>
                        <button type="button" class="fin-page-btn" id="btn-pay-next">Next <i class='bx bx-chevron-right'></i></button>
                    </div>
                </div>
            </div>
        `;

        this.attachPaymentFilterListeners();
        await this.loadPaymentsData();
    },

    attachPaymentFilterListeners() {
        const searchInput = document.getElementById('pay-search-input');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.paymentFilters.search = e.target.value.trim();
                    this.paymentFilters.page = 1;
                    this.loadPaymentsData();
                }, 350);
            });
        }

        const methodSelect = document.getElementById('pay-method-select');
        if (methodSelect) {
            methodSelect.addEventListener('change', (e) => {
                this.paymentFilters.payment_method = e.target.value;
                this.paymentFilters.page = 1;
                this.loadPaymentsData();
            });
        }

        const dateFromInput = document.getElementById('pay-date-from');
        if (dateFromInput) {
            dateFromInput.addEventListener('change', (e) => {
                this.paymentFilters.date_from = e.target.value;
                this.paymentFilters.page = 1;
                this.loadPaymentsData();
            });
        }

        const dateToInput = document.getElementById('pay-date-to');
        if (dateToInput) {
            dateToInput.addEventListener('change', (e) => {
                this.paymentFilters.date_to = e.target.value;
                this.paymentFilters.page = 1;
                this.loadPaymentsData();
            });
        }

        const resetBtn = document.getElementById('btn-reset-pay-filters');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.paymentFilters = { search: '', payment_method: '', date_from: '', date_to: '', page: 1, limit: 15 };
                if (searchInput) searchInput.value = '';
                if (methodSelect) methodSelect.value = '';
                if (dateFromInput) dateFromInput.value = '';
                if (dateToInput) dateToInput.value = '';
                this.loadPaymentsData();
            });
        }

        const prevBtn = document.getElementById('btn-pay-prev');
        const nextBtn = document.getElementById('btn-pay-next');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.paymentFilters.page > 1) {
                    this.paymentFilters.page--;
                    this.loadPaymentsData();
                }
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (this.paymentFilters.page < this.paymentPagination.total_pages) {
                    this.paymentFilters.page++;
                    this.loadPaymentsData();
                }
            });
        }
    },

    async loadPaymentsData() {
        const tbody = document.getElementById('payments-tbody');
        const countIndicator = document.getElementById('pay-count-indicator');
        const paginationBar = document.getElementById('payments-pagination-bar');
        const pageInfo = document.getElementById('pay-page-info');
        const prevBtn = document.getElementById('btn-pay-prev');
        const nextBtn = document.getElementById('btn-pay-next');

        const user = Auth.getUser();
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');

        try {
            const params = {
                search: this.paymentFilters.search,
                payment_method: this.paymentFilters.payment_method,
                date_from: this.paymentFilters.date_from,
                date_to: this.paymentFilters.date_to,
                page: this.paymentFilters.page,
                limit: this.paymentFilters.limit
            };

            const data = await Api.getPayments(params);
            this.paymentsList = data.payments || [];
            this.paymentStats = data.stats || {};
            this.paymentPagination = data.pagination || { page: 1, limit: 15, total_count: this.paymentsList.length, total_pages: 1 };

            // Update badge
            const badge = document.getElementById('badge-payment-count');
            if (badge) badge.textContent = this.paymentPagination.total_count || 0;

            // Update stats
            const totalAmtEl = document.getElementById('stat-pay-total-amount');
            const totalCountEl = document.getElementById('stat-pay-total-count');
            const recordCountEl = document.getElementById('stat-pay-record-count');
            if (totalAmtEl) totalAmtEl.textContent = Utils.formatCurrency(this.paymentStats.total_disbursed || 0);
            if (totalCountEl) totalCountEl.textContent = `${this.paymentPagination.total_count || 0} recorded disbursements`;
            if (recordCountEl) recordCountEl.textContent = this.paymentPagination.total_count || 0;

            if (countIndicator) {
                countIndicator.textContent = `Showing ${this.paymentsList.length} of ${this.paymentPagination.total_count} payments`;
            }

            if (!tbody) return;

            if (this.paymentsList.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="${isManagerOrOwner ? 8 : 7}" style="text-align: center; padding: 48px 24px;">
                            ${Utils.emptyState('bx-wallet', 'No Payment Records', 'No payment disbursement records match your current filters.')}
                            ${isManagerOrOwner ? `
                                <div style="margin-top: 16px;">
                                    <button class="btn primary" onclick="App.pages['payments'].openRecordPaymentModal()">
                                        <i class='bx bx-credit-card'></i> Record Disbursement
                                    </button>
                                </div>
                            ` : ''}
                        </td>
                    </tr>
                `;
                if (paginationBar) paginationBar.style.display = 'none';
                return;
            }

            // Render table rows
            tbody.innerHTML = this.paymentsList.map(pay => {
                return `
                    <tr id="pay-row-${pay.payment_id}">
                        <td>
                            <strong style="color: var(--primary); font-family: monospace; font-size: 13px;">${Utils.escapeHtml(pay.payment_reference)}</strong>
                            <div style="font-size: 11px; color: var(--text-secondary);">Disbursement #${pay.payment_id}</div>
                        </td>
                        <td>
                            <a href="javascript:void(0)" onclick="App.pages['payments'].viewInvoiceDetails(${pay.invoice_id})" style="font-weight: 600; color: var(--text); text-decoration: underline;">
                                ${Utils.escapeHtml(pay.invoice_number)}
                            </a>
                            <div style="font-size: 11px; color: var(--text-secondary);">${this.getStatusBadge(pay.invoice_status)}</div>
                        </td>
                        ${isManagerOrOwner ? `
                            <td>
                                <strong>${Utils.escapeHtml(pay.supplier_name || 'Supplier')}</strong>
                                <div style="font-size: 11px; color: var(--text-secondary);">ID #${pay.supplier_id}</div>
                            </td>
                        ` : ''}
                        <td>
                            <span style="font-weight: 500;">${pay.payment_date || '-'}</span>
                            <div style="font-size: 11px; color: var(--text-secondary);">${pay.created_at ? Utils.formatDate(pay.created_at) : ''}</div>
                        </td>
                        <td>
                            <strong style="color: #059669; font-size: 15px;">₹${Number(pay.amount_paid).toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
                        </td>
                        <td>
                            <span class="fin-method-pill">
                                <i class='bx bx-check-shield'></i> ${Utils.escapeHtml(pay.payment_method)}
                            </span>
                        </td>
                        <td>
                            <div style="font-size: 13px; font-weight: 600;">${Utils.escapeHtml(pay.recorded_by_name || 'System')}</div>
                            <div style="font-size: 11px; color: var(--text-secondary);">User ID #${pay.recorded_by}</div>
                        </td>
                        <td style="text-align: right;">
                            <div class="fin-action-group">
                                <button type="button" class="fin-btn-icon" title="View Disbursement Voucher" onclick="App.pages['payments'].viewPaymentVoucher(${pay.payment_id})">
                                    <i class='bx bx-receipt'></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');

            // Pagination setup
            if (paginationBar) {
                paginationBar.style.display = 'flex';
                const curPage = this.paymentPagination.page;
                const totalPages = this.paymentPagination.total_pages;
                if (pageInfo) {
                    pageInfo.textContent = `Page ${curPage} of ${totalPages} (${this.paymentPagination.total_count} total payments)`;
                }
                if (prevBtn) prevBtn.disabled = curPage <= 1;
                if (nextBtn) nextBtn.disabled = curPage >= totalPages;
            }

        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="${isManagerOrOwner ? 8 : 7}" class="text-danger" style="text-align: center; padding: 24px;">Failed to load payments: ${Utils.escapeHtml(err.message || 'Server error')}</td></tr>`;
            if (countIndicator) countIndicator.textContent = 'Error loading payments';
        }
    },

    // =========================================================
    // MODAL: SUBMIT INVOICE (Supplier Only)
    // =========================================================

    async openSubmitInvoiceModal() {
        const todayStr = new Date().toISOString().split('T')[0];
        const thirtyDaysAhead = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

        Modal.create({
            id: 'modalSubmitInvoice',
            title: '<i class="bx bx-receipt"></i> Submit Supplier Invoice',
            content: `
                <div class="fin-alert-banner info" style="margin-bottom: 16px;">
                    <i class='bx bx-info-circle' style="font-size: 20px;"></i>
                    <div>
                        <strong>Goods Receipt Prerequisite:</strong>
                        <div style="font-size: 12px; margin-top: 2px;">
                            Invoices may only be submitted for Purchase Orders with verified goods delivery and recorded warehouse stock receipt (STOCK_IN).
                        </div>
                    </div>
                </div>

                <form id="form-submit-invoice">
                    <div class="fin-form-grid">
                        <div class="fin-form-group" style="grid-column: 1 / -1;">
                            <label class="fin-form-label" for="inp-sub-po">
                                <span>Purchase Order <span class="required">*</span></span>
                                <span style="font-size: 11px; font-weight: normal; color: var(--text-secondary);" id="po-cap-hint"></span>
                            </label>
                            <select id="inp-sub-po" class="fin-form-select" required>
                                <option value="">Loading eligible Purchase Orders...</option>
                            </select>
                            <span class="fin-form-help">Select the Purchase Order associated with this invoice.</span>
                        </div>

                        <div class="fin-form-group" style="grid-column: 1 / -1;">
                            <label class="fin-form-label" for="inp-sub-shipment">
                                <span>Shipment Reference (Optional / Specific Delivery)</span>
                            </label>
                            <select id="inp-sub-shipment" class="fin-form-select">
                                <option value="">All Delivered Goods / No Specific Shipment</option>
                            </select>
                            <span class="fin-form-help" id="shipment-status-help">Select a specific delivered shipment, or leave as general receipt if applicable.</span>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-sub-inv-number">
                                <span>Invoice Number <span class="required">*</span></span>
                            </label>
                            <input type="text" id="inp-sub-inv-number" class="fin-form-input" placeholder="e.g. INV-2026-001" required maxlength="100">
                            <span class="fin-form-help">Must be unique to your supplier profile.</span>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-sub-inv-date">
                                <span>Invoice Date <span class="required">*</span></span>
                            </label>
                            <input type="date" id="inp-sub-inv-date" class="fin-form-input" value="${todayStr}" required>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-sub-due-date">
                                <span>Payment Due Date <span class="required">*</span></span>
                            </label>
                            <input type="date" id="inp-sub-due-date" class="fin-form-input" value="${thirtyDaysAhead}" required>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-sub-subtotal">
                                <span>Subtotal (₹) <span class="required">*</span></span>
                            </label>
                            <input type="number" id="inp-sub-subtotal" class="fin-form-input" min="0.01" step="0.01" placeholder="0.00" required>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-sub-tax">
                                <span>Tax Amount (₹)</span>
                            </label>
                            <input type="number" id="inp-sub-tax" class="fin-form-input" min="0.00" step="0.01" value="0.00">
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-sub-total">
                                <span>Total Amount (₹) <span class="required">*</span></span>
                            </label>
                            <input type="number" id="inp-sub-total" class="fin-form-input" min="0.01" step="0.01" placeholder="0.00" readonly style="background: #f1f5f9; font-weight: 700; color: var(--primary);">
                            <span class="fin-form-help">Calculated automatically (Subtotal + Tax).</span>
                        </div>

                        <div class="fin-form-group" style="grid-column: 1 / -1;">
                            <label class="fin-form-label" for="inp-sub-notes">
                                <span>Notes / Reference Details</span>
                            </label>
                            <textarea id="inp-sub-notes" class="fin-form-textarea" rows="2" placeholder="Optional delivery remarks or payment instructions..."></textarea>
                        </div>
                    </div>

                    <!-- Live Calculation Ribbon -->
                    <div class="fin-calc-preview">
                        <div class="fin-calc-item">
                            <span class="fin-calc-label">Subtotal</span>
                            <span class="fin-calc-value" id="calc-preview-subtotal">₹0.00</span>
                        </div>
                        <div style="font-size: 18px; color: var(--text-secondary); font-weight: 700;">+</div>
                        <div class="fin-calc-item">
                            <span class="fin-calc-label">Tax</span>
                            <span class="fin-calc-value" id="calc-preview-tax">₹0.00</span>
                        </div>
                        <div style="font-size: 18px; color: var(--text-secondary); font-weight: 700;">=</div>
                        <div class="fin-calc-item">
                            <span class="fin-calc-label">Total Payable</span>
                            <span class="fin-calc-value highlight" id="calc-preview-total">₹0.00</span>
                        </div>
                    </div>

                    <div id="sub-inv-error" class="fin-alert-banner danger" style="display: none;"></div>

                    <div class="modal-footer" style="padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px;">
                        <button type="button" class="btn secondary" id="btn-cancel-submit-inv">Cancel</button>
                        <button type="submit" class="btn primary" id="btn-do-submit-inv">
                            <i class='bx bx-check-circle'></i> Submit Invoice
                        </button>
                    </div>
                </form>
            `,
            onOpen: async (modalEl, closeModal) => {
                const cancelBtn = modalEl.querySelector('#btn-cancel-submit-inv');
                if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

                const form = modalEl.querySelector('#form-submit-invoice');
                const poSelect = modalEl.querySelector('#inp-sub-po');
                const shipmentSelect = modalEl.querySelector('#inp-sub-shipment');
                const subtotalInput = modalEl.querySelector('#inp-sub-subtotal');
                const taxInput = modalEl.querySelector('#inp-sub-tax');
                const totalInput = modalEl.querySelector('#inp-sub-total');
                const errBox = modalEl.querySelector('#sub-inv-error');
                const submitBtn = modalEl.querySelector('#btn-do-submit-inv');

                // Live math recalculation
                const recalculate = () => {
                    const sub = Math.max(0, parseFloat(subtotalInput.value) || 0);
                    const tax = Math.max(0, parseFloat(taxInput.value) || 0);
                    const tot = (sub + tax).toFixed(2);
                    totalInput.value = tot;

                    const previewSub = modalEl.querySelector('#calc-preview-subtotal');
                    const previewTax = modalEl.querySelector('#calc-preview-tax');
                    const previewTot = modalEl.querySelector('#calc-preview-total');
                    if (previewSub) previewSub.textContent = `₹${sub.toFixed(2)}`;
                    if (previewTax) previewTax.textContent = `₹${tax.toFixed(2)}`;
                    if (previewTot) previewTot.textContent = `₹${tot}`;
                };

                subtotalInput.addEventListener('input', recalculate);
                taxInput.addEventListener('input', recalculate);

                // Fetch eligible POs for this Supplier
                try {
                    const poData = await Api.get('/purchase-orders/');
                    const pos = (poData && poData.purchase_orders) ? poData.purchase_orders : [];
                    
                    if (pos.length === 0) {
                        poSelect.innerHTML = `<option value="">No Purchase Orders found for your supplier account</option>`;
                    } else {
                        poSelect.innerHTML = `<option value="">-- Select a Purchase Order --</option>` + pos.map(po => {
                            return `<option value="${po.purchase_order_id}" data-total="${po.total_amount}" data-status="${po.status}">
                                ${Utils.escapeHtml(po.order_number)} — Total: ₹${Number(po.total_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})} (${po.status})
                            </option>`;
                        }).join('');
                    }
                } catch (poErr) {
                    poSelect.innerHTML = `<option value="">Error loading Purchase Orders: ${Utils.escapeHtml(poErr.message)}</option>`;
                }

                // Handle PO change to fetch eligible shipments
                poSelect.addEventListener('change', async (e) => {
                    const poId = e.target.value;
                    const selectedOpt = poSelect.options[poSelect.selectedIndex];
                    const poCapHint = modalEl.querySelector('#po-cap-hint');
                    const shipmentHelp = modalEl.querySelector('#shipment-status-help');

                    if (!poId) {
                        shipmentSelect.innerHTML = `<option value="">All Delivered Goods / No Specific Shipment</option>`;
                        if (poCapHint) poCapHint.textContent = '';
                        return;
                    }

                    if (poCapHint && selectedOpt) {
                        poCapHint.textContent = `PO Total Cap: ₹${Number(selectedOpt.dataset.total || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
                    }

                    shipmentSelect.innerHTML = `<option value="">Loading shipments...</option>`;
                    try {
                        const shpData = await Api.get(`/shipments?po_id=${poId}`);
                        const shps = (shpData && shpData.shipments) ? shpData.shipments : [];
                        
                        // Filter delivered shipments with received status
                        const eligibleShps = shps.filter(s => s.status === 'Delivered');

                        let optionsHtml = `<option value="">All Delivered Goods / No Specific Shipment</option>`;
                        if (eligibleShps.length > 0) {
                            optionsHtml += eligibleShps.map(s => `
                                <option value="${s.shipment_id}">
                                    ${Utils.escapeHtml(s.tracking_number || `Shipment #${s.shipment_id}`)} (${s.status} — ${s.receiving_status || 'Received'})
                                </option>
                            `).join('');
                            if (shipmentHelp) {
                                shipmentHelp.innerHTML = `<span style="color: #059669;"><i class='bx bx-check-circle'></i> Found ${eligibleShps.length} delivered shipment(s) on this PO.</span>`;
                            }
                        } else {
                            if (shipmentHelp) {
                                shipmentHelp.innerHTML = `<span style="color: #d97706;"><i class='bx bx-error'></i> No shipments marked as 'Delivered' yet. Invoices require delivered &amp; received goods.</span>`;
                            }
                        }
                        shipmentSelect.innerHTML = optionsHtml;
                    } catch (shpErr) {
                        shipmentSelect.innerHTML = `<option value="">All Delivered Goods / No Specific Shipment</option>`;
                    }
                });

                // Handle form submit
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    if (errBox) {
                        errBox.style.display = 'none';
                        errBox.textContent = '';
                    }

                    const poId = poSelect.value;
                    const shipmentIdVal = shipmentSelect.value;
                    const invoiceNumber = modalEl.querySelector('#inp-sub-inv-number').value.trim();
                    const invoiceDate = modalEl.querySelector('#inp-sub-inv-date').value;
                    const dueDate = modalEl.querySelector('#inp-sub-due-date').value;
                    const subtotal = parseFloat(subtotalInput.value) || 0;
                    const taxAmount = parseFloat(taxInput.value) || 0;
                    const totalAmount = parseFloat(totalInput.value) || 0;
                    const notes = modalEl.querySelector('#inp-sub-notes').value.trim();

                    if (!poId) {
                        errBox.textContent = "Please select a valid Purchase Order";
                        errBox.style.display = 'flex';
                        return;
                    }

                    if (!invoiceNumber) {
                        errBox.textContent = "Invoice number is required";
                        errBox.style.display = 'flex';
                        return;
                    }

                    if (dueDate < invoiceDate) {
                        errBox.textContent = "Due date must be on or after invoice date";
                        errBox.style.display = 'flex';
                        return;
                    }

                    if (subtotal <= 0) {
                        errBox.textContent = "Subtotal must be greater than zero";
                        errBox.style.display = 'flex';
                        return;
                    }

                    if (Math.abs(totalAmount - (subtotal + taxAmount)) > 0.001) {
                        errBox.textContent = "Total amount must equal Subtotal plus Tax Amount";
                        errBox.style.display = 'flex';
                        return;
                    }

                    const payload = {
                        purchase_order_id: parseInt(poId),
                        invoice_number: invoiceNumber,
                        invoice_date: invoiceDate,
                        due_date: dueDate,
                        subtotal: subtotal.toFixed(2),
                        tax_amount: taxAmount.toFixed(2),
                        total_amount: totalAmount.toFixed(2),
                        notes: notes || null
                    };

                    if (shipmentIdVal) {
                        payload.shipment_id = parseInt(shipmentIdVal);
                    }

                    try {
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Submitting...`;

                        await Api.submitInvoice(payload);
                        Utils.showToast("Invoice submitted successfully! Awaiting manager approval.", "success");
                        closeModal();
                        await App.pages['payments'].loadInvoicesData();
                    } catch (submitErr) {
                        errBox.textContent = submitErr.message || "Failed to submit invoice";
                        errBox.style.display = 'flex';
                    } finally {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = `<i class='bx bx-check-circle'></i> Submit Invoice`;
                    }
                });
            }
        });
    },

    // =========================================================
    // MODAL: INVOICE DETAILS & PAYMENT HISTORY
    // =========================================================

    async viewInvoiceDetails(invoiceId) {
        try {
            const data = await Api.getInvoice(invoiceId);
            const inv = data.invoice;
            if (!inv) throw new Error("Invoice details not found");

            const user = Auth.getUser();
            const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');
            const isSupplier = user && user.role === 'Supplier';

            const canApprove = isManagerOrOwner && inv.status === 'Submitted';
            const canReject = isManagerOrOwner && inv.status === 'Submitted';
            const canPay = isManagerOrOwner && (inv.status === 'Approved' || inv.status === 'Partially Paid');
            const canCancel = (isSupplier && inv.status === 'Submitted') || 
                              (isManagerOrOwner && (inv.status === 'Submitted' || inv.status === 'Approved') && (Number(inv.total_paid) === 0));

            const paymentsList = inv.payments || [];

            Modal.create({
                id: 'modalInvoiceDetails',
                title: `<i class='bx bx-receipt'></i> Invoice Details: ${Utils.escapeHtml(inv.invoice_number)}`,
                content: `
                    <!-- Header Banner -->
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 14px; margin-bottom: 16px;">
                        <div>
                            <h2 style="margin: 0; font-size: 20px; color: var(--text);">${Utils.escapeHtml(inv.invoice_number)}</h2>
                            <span style="font-size: 12px; color: var(--text-secondary);">Supplier: <strong>${Utils.escapeHtml(inv.supplier_name)}</strong> (ID #${inv.supplier_id})</span>
                        </div>
                        <div>
                            ${this.getStatusBadge(inv.status)}
                        </div>
                    </div>

                    ${inv.status === 'Rejected' && inv.rejection_reason ? `
                        <div class="fin-alert-banner danger">
                            <i class='bx bx-x-circle' style="font-size: 20px;"></i>
                            <div>
                                <strong>Rejection Reason:</strong>
                                <div style="margin-top: 2px;">${Utils.escapeHtml(inv.rejection_reason)}</div>
                            </div>
                        </div>
                    ` : ''}

                    ${inv.status === 'Cancelled' ? `
                        <div class="fin-alert-banner warning">
                            <i class='bx bx-block' style="font-size: 20px;"></i>
                            <div>
                                <strong>Cancelled Invoice:</strong>
                                <div style="margin-top: 2px;">This invoice was cancelled and cannot accept payment disbursements.</div>
                            </div>
                        </div>
                    ` : ''}

                    <!-- Procurement Linkage Section -->
                    <div class="fin-detail-section">
                        <div class="fin-detail-title"><i class='bx bx-link'></i> Procurement Linkage</div>
                        <div class="fin-detail-grid">
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Purchase Order</span>
                                <span class="fin-field-value" style="color: var(--primary);">
                                    <i class='bx bx-file-blank'></i> ${Utils.escapeHtml(inv.po_number || `PO #${inv.purchase_order_id}`)}
                                </span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">PO Commitment Total</span>
                                <span class="fin-field-value">₹${Number(inv.po_total || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Linked Shipment</span>
                                <span class="fin-field-value">
                                    ${inv.shipment_id ? `<i class='bx bx-car'></i> ${Utils.escapeHtml(inv.tracking_number || `Shipment #${inv.shipment_id}`)}` : 'PO-Level Receipt'}
                                </span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Submission Date</span>
                                <span class="fin-field-value">${inv.invoice_date || '-'}</span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Due Date</span>
                                <span class="fin-field-value">${inv.due_date || '-'}</span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Created By</span>
                                <span class="fin-field-value">${Utils.escapeHtml(inv.created_by_name || 'User')} (${Utils.formatDate(inv.created_at)})</span>
                            </div>
                        </div>
                    </div>

                    <!-- Financial Breakdown Section -->
                    <div class="fin-detail-section">
                        <div class="fin-detail-title"><i class='bx bx-calculator'></i> Financial Breakdown</div>
                        <div class="fin-balance-ribbon">
                            <div class="fin-balance-item">
                                <span class="fin-balance-label">Total Invoiced</span>
                                <span class="fin-balance-amt">₹${Number(inv.total_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                                <span style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Sub: ₹${Number(inv.subtotal).toFixed(2)} + Tax: ₹${Number(inv.tax_amount).toFixed(2)}</span>
                            </div>
                            <div class="fin-balance-item">
                                <span class="fin-balance-label">Total Disbursed</span>
                                <span class="fin-balance-amt" style="color: #059669;">₹${Number(inv.total_paid).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                                <span style="font-size: 11px; color: #059669; margin-top: 2px;">${paymentsList.length} payment(s)</span>
                            </div>
                            <div class="fin-balance-item">
                                <span class="fin-balance-label">Outstanding Due</span>
                                <span class="fin-balance-amt remaining">₹${Number(inv.remaining_balance).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                                <span style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Balance remaining</span>
                            </div>
                        </div>
                    </div>

                    ${inv.notes ? `
                        <div class="fin-detail-section">
                            <div class="fin-detail-title"><i class='bx bx-notepad'></i> Invoice Notes</div>
                            <p style="background: #f8fafc; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px; margin: 0;">
                                ${Utils.escapeHtml(inv.notes)}
                            </p>
                        </div>
                    ` : ''}

                    <!-- Payment History Section -->
                    <div class="fin-detail-section">
                        <div class="fin-detail-title" style="justify-content: space-between;">
                            <span><i class='bx bx-history'></i> Payment Disbursement History (${paymentsList.length})</span>
                            ${canPay ? `
                                <button type="button" class="btn primary" style="padding: 4px 10px; font-size: 12px;" onclick="Modal.closeAll(); App.pages['payments'].openRecordPaymentModal(${inv.invoice_id});">
                                    <i class='bx bx-plus'></i> Disburse Payment
                                </button>
                            ` : ''}
                        </div>

                        ${paymentsList.length > 0 ? `
                            <div class="table-responsive" style="border: 1px solid var(--border); border-radius: 8px;">
                                <table class="table" style="font-size: 13px; margin: 0;">
                                    <thead>
                                        <tr style="background: #f8fafc;">
                                            <th>REFERENCE #</th>
                                            <th>PAYMENT DATE</th>
                                            <th>AMOUNT PAID</th>
                                            <th>METHOD</th>
                                            <th>RECORDED BY</th>
                                            <th>ACTIONS</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${paymentsList.map(p => `
                                            <tr>
                                                <td><strong style="color: var(--primary); font-family: monospace;">${Utils.escapeHtml(p.payment_reference)}</strong></td>
                                                <td>${p.payment_date || '-'}</td>
                                                <td><strong style="color: #059669;">₹${Number(p.amount_paid).toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong></td>
                                                <td><span class="fin-method-pill">${Utils.escapeHtml(p.payment_method)}</span></td>
                                                <td>${Utils.escapeHtml(p.recorded_by_name || 'User')}</td>
                                                <td>
                                                    <button type="button" class="fin-btn-icon" title="View Voucher" onclick="Modal.closeAll(); App.pages['payments'].viewPaymentVoucher(${p.payment_id});">
                                                        <i class='bx bx-receipt'></i>
                                                    </button>
                                                </td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        ` : `
                            <div style="background: #f8fafc; border: 1px dashed var(--border); border-radius: 8px; padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                                <i class='bx bx-wallet' style="font-size: 24px; vertical-align: middle; margin-right: 6px;"></i>
                                No disbursements recorded yet for this invoice.
                            </div>
                        `}
                    </div>

                    <!-- Consequential Actions Footer -->
                    <div class="modal-footer" style="padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px; flex-wrap: wrap;">
                        <button type="button" class="btn secondary" id="btn-close-inv-detail">Close</button>
                        
                        ${canCancel ? `
                            <button type="button" class="btn secondary" style="color: #dc2626; border-color: rgba(239, 68, 68, 0.4);" onclick="Modal.closeAll(); App.pages['payments'].promptCancelInvoice(${inv.invoice_id}, '${Utils.escapeHtml(inv.invoice_number)}');">
                                <i class='bx bx-block'></i> Cancel Invoice
                            </button>
                        ` : ''}

                        ${canReject ? `
                            <button type="button" class="btn secondary" style="color: #dc2626; border-color: rgba(239, 68, 68, 0.4);" onclick="Modal.closeAll(); App.pages['payments'].promptRejectInvoice(${inv.invoice_id}, '${Utils.escapeHtml(inv.invoice_number)}');">
                                <i class='bx bx-x-circle'></i> Reject
                            </button>
                        ` : ''}

                        ${canApprove ? `
                            <button type="button" class="btn primary" style="background: #059669; border-color: #059669;" onclick="Modal.closeAll(); App.pages['payments'].promptApproveInvoice(${inv.invoice_id}, '${Utils.escapeHtml(inv.invoice_number)}', ${inv.total_amount});">
                                <i class='bx bx-check-circle'></i> Approve Invoice
                            </button>
                        ` : ''}

                        ${canPay ? `
                            <button type="button" class="btn primary" onclick="Modal.closeAll(); App.pages['payments'].openRecordPaymentModal(${inv.invoice_id});">
                                <i class='bx bx-credit-card'></i> Record Payment
                            </button>
                        ` : ''}
                    </div>
                `,
                onOpen: (modalEl, closeModal) => {
                    const closeBtn = modalEl.querySelector('#btn-close-inv-detail');
                    if (closeBtn) closeBtn.addEventListener('click', closeModal);
                }
            });

        } catch (err) {
            Utils.showToast(err.message || "Failed to load invoice details", "error");
        }
    },

    // =========================================================
    // APPROVAL / REJECTION / CANCELLATION HANDLERS
    // =========================================================

    promptApproveInvoice(invoiceId, invoiceNumber, totalAmount) {
        Modal.create({
            id: 'modalApproveInvoice',
            title: '<i class="bx bx-check-circle" style="color: #059669;"></i> Approve Supplier Invoice',
            content: `
                <div style="padding: 10px 0;">
                    <p style="font-size: 15px; margin-bottom: 12px;">
                        Are you sure you want to approve invoice <strong>${Utils.escapeHtml(invoiceNumber)}</strong>?
                    </p>
                    <div class="fin-calc-preview" style="margin-bottom: 16px;">
                        <span class="fin-calc-label">Approved Disbursement Cap:</span>
                        <span class="fin-calc-value highlight" style="color: #059669;">₹${Number(totalAmount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                    </div>
                    <p style="font-size: 12px; color: var(--text-secondary); margin: 0;">
                        Once approved, corporate payment disbursements may be recorded against this invoice up to the total amount.
                    </p>
                </div>
                <div class="modal-footer" style="padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px;">
                    <button type="button" class="btn secondary" id="btn-cancel-approve">Cancel</button>
                    <button type="button" class="btn primary" id="btn-confirm-approve" style="background: #059669; border-color: #059669;">
                        <i class='bx bx-check'></i> Confirm Approval
                    </button>
                </div>
            `,
            onOpen: (modalEl, closeModal) => {
                const cancelBtn = modalEl.querySelector('#btn-cancel-approve');
                const confirmBtn = modalEl.querySelector('#btn-confirm-approve');

                if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
                if (confirmBtn) {
                    confirmBtn.addEventListener('click', async () => {
                        try {
                            confirmBtn.disabled = true;
                            confirmBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Approving...`;
                            await Api.approveInvoice(invoiceId);
                            Utils.showToast(`Invoice ${invoiceNumber} approved successfully`, "success");
                            closeModal();
                            await App.pages['payments'].loadInvoicesData();
                        } catch (err) {
                            Utils.showToast(err.message || "Failed to approve invoice", "error");
                            confirmBtn.disabled = false;
                            confirmBtn.innerHTML = `<i class='bx bx-check'></i> Confirm Approval`;
                        }
                    });
                }
            }
        });
    },

    promptRejectInvoice(invoiceId, invoiceNumber) {
        Modal.create({
            id: 'modalRejectInvoice',
            title: '<i class="bx bx-x-circle" style="color: #dc2626;"></i> Reject Supplier Invoice',
            content: `
                <div style="padding: 10px 0;">
                    <p style="font-size: 14px; margin-bottom: 12px;">
                        Rejecting invoice <strong>${Utils.escapeHtml(invoiceNumber)}</strong> will return it to the supplier. A detailed reason is required.
                    </p>
                    <div class="fin-form-group">
                        <label class="fin-form-label" for="inp-reject-reason">
                            <span>Rejection Reason <span class="required">*</span></span>
                        </label>
                        <textarea id="inp-reject-reason" class="fin-form-textarea" rows="3" placeholder="Provide reason (e.g. pricing discrepancy, unverified shipment items, incorrect tax calculation)..." required></textarea>
                    </div>
                    <div id="reject-error" class="fin-alert-banner danger" style="display: none; margin-top: 10px;"></div>
                </div>
                <div class="modal-footer" style="padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px;">
                    <button type="button" class="btn secondary" id="btn-cancel-reject">Cancel</button>
                    <button type="button" class="btn primary" id="btn-confirm-reject" style="background: #dc2626; border-color: #dc2626;">
                        <i class='bx bx-x'></i> Confirm Rejection
                    </button>
                </div>
            `,
            onOpen: (modalEl, closeModal) => {
                const cancelBtn = modalEl.querySelector('#btn-cancel-reject');
                const confirmBtn = modalEl.querySelector('#btn-confirm-reject');
                const reasonInput = modalEl.querySelector('#inp-reject-reason');
                const errBox = modalEl.querySelector('#reject-error');

                if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
                if (confirmBtn) {
                    confirmBtn.addEventListener('click', async () => {
                        const reason = reasonInput.value.trim();
                        if (!reason) {
                            errBox.textContent = "Rejection reason is mandatory.";
                            errBox.style.display = 'flex';
                            return;
                        }

                        try {
                            confirmBtn.disabled = true;
                            confirmBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Rejecting...`;
                            await Api.rejectInvoice(invoiceId, reason);
                            Utils.showToast(`Invoice ${invoiceNumber} rejected`, "warning");
                            closeModal();
                            await App.pages['payments'].loadInvoicesData();
                        } catch (err) {
                            errBox.textContent = err.message || "Failed to reject invoice";
                            errBox.style.display = 'flex';
                            confirmBtn.disabled = false;
                            confirmBtn.innerHTML = `<i class='bx bx-x'></i> Confirm Rejection`;
                        }
                    });
                }
            }
        });
    },

    promptCancelInvoice(invoiceId, invoiceNumber) {
        Modal.create({
            id: 'modalCancelInvoice',
            title: '<i class="bx bx-block" style="color: #64748b;"></i> Cancel Invoice',
            content: `
                <div style="padding: 10px 0;">
                    <p style="font-size: 14px; margin-bottom: 12px;">
                        Are you sure you want to cancel invoice <strong>${Utils.escapeHtml(invoiceNumber)}</strong>?
                    </p>
                    <div class="fin-form-group">
                        <label class="fin-form-label" for="inp-cancel-reason">
                            <span>Cancellation Note (Optional)</span>
                        </label>
                        <input type="text" id="inp-cancel-reason" class="fin-form-input" placeholder="e.g. Invoiced wrong purchase order, re-submitting...">
                    </div>
                </div>
                <div class="modal-footer" style="padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px;">
                    <button type="button" class="btn secondary" id="btn-abort-cancel">Back</button>
                    <button type="button" class="btn primary" id="btn-confirm-cancel">
                        <i class='bx bx-check'></i> Confirm Cancellation
                    </button>
                </div>
            `,
            onOpen: (modalEl, closeModal) => {
                const cancelBtn = modalEl.querySelector('#btn-abort-cancel');
                const confirmBtn = modalEl.querySelector('#btn-confirm-cancel');
                const reasonInput = modalEl.querySelector('#inp-cancel-reason');

                if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
                if (confirmBtn) {
                    confirmBtn.addEventListener('click', async () => {
                        const reason = reasonInput.value.trim();
                        try {
                            confirmBtn.disabled = true;
                            confirmBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Cancelling...`;
                            await Api.cancelInvoice(invoiceId, reason);
                            Utils.showToast(`Invoice ${invoiceNumber} cancelled`, "info");
                            closeModal();
                            await App.pages['payments'].loadInvoicesData();
                        } catch (err) {
                            Utils.showToast(err.message || "Failed to cancel invoice", "error");
                            confirmBtn.disabled = false;
                            confirmBtn.innerHTML = `<i class='bx bx-check'></i> Confirm Cancellation`;
                        }
                    });
                }
            }
        });
    },

    // =========================================================
    // MODAL: RECORD PAYMENT DISBURSEMENT (Owner/Manager Only)
    // =========================================================

    async openRecordPaymentModal(preselectedInvoiceId = null) {
        const todayStr = new Date().toISOString().split('T')[0];

        Modal.create({
            id: 'modalRecordPayment',
            title: '<i class="bx bx-credit-card"></i> Record Payment Disbursement',
            content: `
                <div class="fin-alert-banner info" style="margin-bottom: 16px;">
                    <i class='bx bx-shield-check' style="font-size: 20px;"></i>
                    <div>
                        <strong>Internal Accounts Payable Ledger:</strong>
                        <div style="font-size: 12px; margin-top: 2px;">
                            This records settlement disbursements in the corporate accounts payable ledger. Online payment gateways are not used.
                        </div>
                    </div>
                </div>

                <form id="form-record-payment">
                    <div class="fin-form-grid">
                        <div class="fin-form-group" style="grid-column: 1 / -1;">
                            <label class="fin-form-label" for="inp-pay-invoice">
                                <span>Target Invoice (Approved or Partially Paid) <span class="required">*</span></span>
                            </label>
                            <select id="inp-pay-invoice" class="fin-form-select" required>
                                <option value="">Loading eligible invoices...</option>
                            </select>
                        </div>

                        <!-- Financial Context Ribbon for Selected Invoice -->
                        <div class="fin-balance-ribbon" style="grid-column: 1 / -1; margin-bottom: 8px;">
                            <div class="fin-balance-item">
                                <span class="fin-balance-label">Invoice Total</span>
                                <span class="fin-balance-amt" id="pay-ctx-total">₹0.00</span>
                            </div>
                            <div class="fin-balance-item">
                                <span class="fin-balance-label">Already Paid</span>
                                <span class="fin-balance-amt" id="pay-ctx-paid" style="color: #059669;">₹0.00</span>
                            </div>
                            <div class="fin-balance-item">
                                <span class="fin-balance-label">Max Allowed (Balance)</span>
                                <span class="fin-balance-amt remaining" id="pay-ctx-balance">₹0.00</span>
                            </div>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-pay-amount">
                                <span>Amount to Disburse (₹) <span class="required">*</span></span>
                            </label>
                            <input type="number" id="inp-pay-amount" class="fin-form-input" min="0.01" step="0.01" placeholder="0.00" required>
                            <span class="fin-form-help" id="pay-amt-help">Must be greater than 0 and not exceed remaining balance.</span>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-pay-date">
                                <span>Payment Date <span class="required">*</span></span>
                            </label>
                            <input type="date" id="inp-pay-date" class="fin-form-input" value="${todayStr}" required>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-pay-method">
                                <span>Payment Method <span class="required">*</span></span>
                            </label>
                            <select id="inp-pay-method" class="fin-form-select" required>
                                <option value="Bank Transfer / NEFT">Bank Transfer / NEFT</option>
                                <option value="RTGS">RTGS</option>
                                <option value="Cheque">Cheque</option>
                                <option value="UPI">UPI</option>
                                <option value="Wire Transfer">Wire Transfer</option>
                                <option value="Cash">Cash</option>
                                <option value="Other">Other</option>
                            </select>
                        </div>

                        <div class="fin-form-group">
                            <label class="fin-form-label" for="inp-pay-ref">
                                <span>Payment Reference # <span class="required">*</span></span>
                            </label>
                            <input type="text" id="inp-pay-ref" class="fin-form-input" placeholder="e.g. UTR-98234190, CHQ-445102, UPI-20261012" required maxlength="100">
                            <span class="fin-form-help">UTR number, cheque serial, or transaction reference.</span>
                        </div>

                        <div class="fin-form-group" style="grid-column: 1 / -1;">
                            <label class="fin-form-label" for="inp-pay-notes">
                                <span>Payment Notes</span>
                            </label>
                            <textarea id="inp-pay-notes" class="fin-form-textarea" rows="2" placeholder="Optional bank confirmation remarks, accounts reference, or cheque clearance notes..."></textarea>
                        </div>
                    </div>

                    <div id="pay-error-box" class="fin-alert-banner danger" style="display: none; margin-top: 12px;"></div>

                    <div class="modal-footer" style="padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px;">
                        <button type="button" class="btn secondary" id="btn-cancel-record-pay">Cancel</button>
                        <button type="submit" class="btn primary" id="btn-do-record-pay">
                            <i class='bx bx-check-double'></i> Record Disbursement
                        </button>
                    </div>
                </form>
            `,
            onOpen: async (modalEl, closeModal) => {
                const cancelBtn = modalEl.querySelector('#btn-cancel-record-pay');
                if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

                const invoiceSelect = modalEl.querySelector('#inp-pay-invoice');
                const amountInput = modalEl.querySelector('#inp-pay-amount');
                const form = modalEl.querySelector('#form-record-payment');
                const errBox = modalEl.querySelector('#pay-error-box');
                const submitBtn = modalEl.querySelector('#btn-do-record-pay');

                const ctxTotalEl = modalEl.querySelector('#pay-ctx-total');
                const ctxPaidEl = modalEl.querySelector('#pay-ctx-paid');
                const ctxBalEl = modalEl.querySelector('#pay-ctx-balance');
                const amtHelp = modalEl.querySelector('#pay-amt-help');

                let eligibleInvoices = [];

                // Fetch Approved & Partially Paid invoices
                try {
                    const [resApproved, resPartial] = await Promise.all([
                        Api.getInvoices({ status: 'Approved', limit: 100 }),
                        Api.getInvoices({ status: 'Partially Paid', limit: 100 })
                    ]);

                    const appList = (resApproved && resApproved.invoices) ? resApproved.invoices : [];
                    const partList = (resPartial && resPartial.invoices) ? resPartial.invoices : [];
                    
                    const combined = [...appList, ...partList];
                    // De-duplicate by invoice_id
                    const seen = new Set();
                    eligibleInvoices = combined.filter(inv => {
                        if (seen.has(inv.invoice_id)) return false;
                        seen.add(inv.invoice_id);
                        return true;
                    });

                    if (eligibleInvoices.length === 0) {
                        invoiceSelect.innerHTML = `<option value="">No Approved or Partially Paid invoices available</option>`;
                    } else {
                        invoiceSelect.innerHTML = `<option value="">-- Select Invoice to Pay --</option>` + eligibleInvoices.map(inv => {
                            const isSelected = preselectedInvoiceId && String(inv.invoice_id) === String(preselectedInvoiceId);
                            return `<option value="${inv.invoice_id}" ${isSelected ? 'selected' : ''}>
                                ${Utils.escapeHtml(inv.invoice_number)} — ${Utils.escapeHtml(inv.supplier_name)} (Bal: ₹${Number(inv.remaining_balance).toLocaleString('en-IN', {minimumFractionDigits: 2})})
                            </option>`;
                        }).join('');

                        // If preselected, trigger change
                        if (preselectedInvoiceId) {
                            setTimeout(() => {
                                invoiceSelect.dispatchEvent(new Event('change'));
                            }, 50);
                        }
                    }
                } catch (loadErr) {
                    invoiceSelect.innerHTML = `<option value="">Error loading invoices: ${Utils.escapeHtml(loadErr.message)}</option>`;
                }

                // Handle invoice selection change
                invoiceSelect.addEventListener('change', () => {
                    const selectedId = invoiceSelect.value;
                    const selectedInv = eligibleInvoices.find(inv => String(inv.invoice_id) === String(selectedId));

                    if (!selectedInv) {
                        if (ctxTotalEl) ctxTotalEl.textContent = '₹0.00';
                        if (ctxPaidEl) ctxPaidEl.textContent = '₹0.00';
                        if (ctxBalEl) ctxBalEl.textContent = '₹0.00';
                        amountInput.value = '';
                        amountInput.max = '';
                        return;
                    }

                    const total = Number(selectedInv.total_amount || 0);
                    const paid = Number(selectedInv.total_paid || 0);
                    const bal = Number(selectedInv.remaining_balance || (total - paid));

                    if (ctxTotalEl) ctxTotalEl.textContent = Utils.formatCurrency(total);
                    if (ctxPaidEl) ctxPaidEl.textContent = Utils.formatCurrency(paid);
                    if (ctxBalEl) ctxBalEl.textContent = Utils.formatCurrency(bal);

                    // Prefill amount with remaining balance
                    amountInput.value = bal.toFixed(2);
                    amountInput.max = bal.toFixed(2);
                    if (amtHelp) {
                        amtHelp.textContent = `Max payable balance: ₹${bal.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
                    }
                });

                // Handle form submit
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    if (errBox) {
                        errBox.style.display = 'none';
                        errBox.textContent = '';
                    }

                    const invoiceId = invoiceSelect.value;
                    const amountPaid = parseFloat(amountInput.value);
                    const paymentDate = modalEl.querySelector('#inp-pay-date').value;
                    const paymentMethod = modalEl.querySelector('#inp-pay-method').value;
                    const paymentRef = modalEl.querySelector('#inp-pay-ref').value.trim();
                    const notes = modalEl.querySelector('#inp-pay-notes').value.trim();

                    if (!invoiceId) {
                        errBox.textContent = "Please select a target invoice";
                        errBox.style.display = 'flex';
                        return;
                    }

                    if (isNaN(amountPaid) || amountPaid <= 0) {
                        errBox.textContent = "Amount paid must be greater than zero";
                        errBox.style.display = 'flex';
                        return;
                    }

                    const selectedInv = eligibleInvoices.find(inv => String(inv.invoice_id) === String(invoiceId));
                    if (selectedInv && amountPaid > Number(selectedInv.remaining_balance)) {
                        errBox.textContent = `Amount cannot exceed remaining invoice balance of ₹${Number(selectedInv.remaining_balance).toFixed(2)}`;
                        errBox.style.display = 'flex';
                        return;
                    }

                    if (!paymentRef) {
                        errBox.textContent = "Payment reference number is mandatory";
                        errBox.style.display = 'flex';
                        return;
                    }

                    const payload = {
                        invoice_id: parseInt(invoiceId),
                        amount_paid: amountPaid.toFixed(2),
                        payment_date: paymentDate,
                        payment_method: paymentMethod,
                        payment_reference: paymentRef,
                        notes: notes || null
                    };

                    try {
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> Recording...`;

                        await Api.recordPayment(payload);
                        Utils.showToast("Payment recorded successfully!", "success");
                        closeModal();

                        // Refresh current view & cache
                        if (App.pages['payments'].currentTab === 'invoices') {
                            await App.pages['payments'].loadInvoicesData();
                        } else {
                            await App.pages['payments'].loadPaymentsData();
                        }
                    } catch (payErr) {
                        errBox.textContent = payErr.message || "Failed to record payment disbursement";
                        errBox.style.display = 'flex';
                    } finally {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = `<i class='bx bx-check-double'></i> Record Disbursement`;
                    }
                });
            }
        });
    },

    // =========================================================
    // MODAL: PAYMENT VOUCHER / RECEIPT
    // =========================================================

    async viewPaymentVoucher(paymentId) {
        try {
            const data = await Api.getPayment(paymentId);
            const pay = data.payment;
            if (!pay) throw new Error("Payment voucher not found");

            Modal.create({
                id: 'modalPaymentVoucher',
                title: `<i class='bx bx-receipt'></i> Disbursement Voucher #${pay.payment_id}`,
                content: `
                    <div class="fin-voucher-card">
                        <div class="fin-voucher-header">
                            <div>
                                <div class="fin-voucher-logo">
                                    <i class='bx bx-shield-quarter' style="font-size: 24px;"></i>
                                    <span>SMART INVENTORY (SIMS)</span>
                                </div>
                                <span style="font-size: 12px; color: var(--text-secondary);">ACCOUNTS PAYABLE DISBURSEMENT VOUCHER</span>
                            </div>
                            <div class="fin-voucher-amount">
                                <span style="font-size: 11px; text-transform: uppercase; color: var(--text-secondary); font-weight: 700;">Amount Disbursed</span>
                                <h2>₹${Number(pay.amount_paid).toLocaleString('en-IN', {minimumFractionDigits: 2})}</h2>
                            </div>
                        </div>

                        <div class="fin-detail-grid" style="margin-bottom: 16px;">
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Reference Number</span>
                                <span class="fin-field-value" style="font-family: monospace; color: var(--primary);">
                                    ${Utils.escapeHtml(pay.payment_reference)}
                                </span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Payment Date</span>
                                <span class="fin-field-value">${pay.payment_date || '-'}</span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Settlement Method</span>
                                <span class="fin-field-value">
                                    <span class="fin-method-pill">${Utils.escapeHtml(pay.payment_method)}</span>
                                </span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Supplier Payee</span>
                                <span class="fin-field-value">${Utils.escapeHtml(pay.supplier_name || 'Supplier')} (ID #${pay.supplier_id})</span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Settled Invoice</span>
                                <span class="fin-field-value">
                                    ${Utils.escapeHtml(pay.invoice_number)} (${this.getStatusBadge(pay.invoice_status)})
                                </span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Invoice Total</span>
                                <span class="fin-field-value">₹${Number(pay.invoice_total || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Disbursed By</span>
                                <span class="fin-field-value">${Utils.escapeHtml(pay.recorded_by_name || 'Finance Team')} (ID #${pay.recorded_by})</span>
                            </div>
                            <div class="fin-detail-field">
                                <span class="fin-field-label">Timestamp</span>
                                <span class="fin-field-value">${pay.created_at ? Utils.formatDate(pay.created_at) : '-'}</span>
                            </div>
                        </div>

                        ${pay.notes ? `
                            <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; font-size: 13px; margin-bottom: 16px;">
                                <strong style="color: var(--text-secondary); font-size: 11px; text-transform: uppercase; display: block; margin-bottom: 4px;">Voucher Remarks</strong>
                                ${Utils.escapeHtml(pay.notes)}
                            </div>
                        ` : ''}

                        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed var(--border); padding-top: 14px; font-size: 11px; color: var(--text-secondary);">
                            <span>Verified Corporate Disbursement &bull; Non-reversing Record</span>
                            <span>SIMS AP Voucher #${pay.payment_id}</span>
                        </div>
                    </div>

                    <div class="modal-footer" style="padding-top: 14px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px;">
                        <button type="button" class="btn secondary" id="btn-close-voucher">Close</button>
                    </div>
                `,
                onOpen: (modalEl, closeModal) => {
                    const closeBtn = modalEl.querySelector('#btn-close-voucher');
                    if (closeBtn) closeBtn.addEventListener('click', closeModal);
                }
            });

        } catch (err) {
            Utils.showToast(err.message || "Failed to load payment voucher", "error");
        }
    }
};
