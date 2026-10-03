// quotations.js - Step 4 Supplier Quotations & Manager/Owner Approval

App.pages['quotations'] = {
    currentQuotations: [],
    eligiblePOs: [],

    render() {
        const container = document.createElement('div');
        const user = Auth.getUser();
        const isSupplier = user && user.role === 'Supplier';
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');

        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">PROCUREMENT</span>
                    <h1>Quotations 💼</h1>
                    <p>${isSupplier 
                        ? 'Submit pricing and supply offers against accepted Purchase Orders.' 
                        : 'Review supplier quotations, compare competing bids, and approve procurement terms.'}</p>
                </div>
                <div class="header-actions" style="display: flex; gap: 10px; align-items: center;">
                    <button class="btn secondary" id="btn-refresh-quotes" title="Refresh Quotations">
                        <i class='bx bx-refresh'></i> Refresh
                    </button>
                    ${isManagerOrOwner ? `
                        <button class="btn secondary" id="btn-compare-quotes" title="Compare bids for a Purchase Order" style="background: white; border: 1px solid var(--border);">
                            <i class='bx bx-git-compare'></i> Compare Bids
                        </button>
                    ` : ''}
                    ${isSupplier ? `
                        <button class="btn primary" id="btn-create-quote">
                            <i class='bx bx-plus'></i> New Quotation
                        </button>
                    ` : ''}
                </div>
            </div>

            <!-- KPI Summary Cards -->
            <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0;">
                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Drafts</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(107, 114, 128, 0.1); color: #4b5563; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-edit-alt'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-quote-drafts" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">In progress / editable</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Submitted</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(59, 130, 246, 0.1); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-send'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-quote-submitted" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Under review by manager</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Approved</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(16, 185, 129, 0.1); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-check-double'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-quote-approved" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Selected for fulfillment</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Total Value</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(99, 102, 241, 0.1); color: #4f46e5; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-dollar-circle'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-quote-value" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">₹0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Active quote volume</span>
                    </div>
                </div>
            </div>

            <!-- Table Card & Filters -->
            <div class="card table-responsive" style="border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border); overflow: hidden;">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 280px;">
                        <div style="position: relative; flex: 1; max-width: 360px;">
                            <i class='bx bx-search' style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-secondary); font-size: 18px;"></i>
                            <input type="text" id="quote-search-input" placeholder="Search quotation #, PO, supplier, or product..." 
                                   style="width: 100%; padding: 8px 12px 8px 38px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-surface, #ffffff); color: var(--text); font-size: 13px;">
                        </div>
                        <select id="quote-status-filter" style="padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-surface, #ffffff); color: var(--text); font-size: 13px;">
                            <option value="">All Statuses</option>
                            <option value="Draft">Draft</option>
                            <option value="Submitted">Submitted</option>
                            <option value="Approved">Approved</option>
                            <option value="Rejected">Rejected</option>
                        </select>
                    </div>

                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span id="quote-count-badge" style="font-size: 13px; color: var(--text-secondary);">Loading quotations...</span>
                    </div>
                </div>

                <table class="data-table" style="width: 100%; border-collapse: collapse; text-align: left;">
                    <thead>
                        <tr style="background: var(--bg-surface, #f9fafb); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
                            <th style="padding: 12px 16px;">QUOTATION</th>
                            <th style="padding: 12px 16px;">PURCHASE ORDER</th>
                            ${!isSupplier ? '<th style="padding: 12px 16px;">SUPPLIER</th>' : ''}
                            <th style="padding: 12px 16px;">PRODUCT OFFERED</th>
                            <th style="padding: 12px 16px; text-align: right;">OFFERED QTY</th>
                            <th style="padding: 12px 16px; text-align: right;">UNIT PRICE</th>
                            <th style="padding: 12px 16px; text-align: right;">TOTAL</th>
                            <th style="padding: 12px 16px;">VALID UNTIL</th>
                            <th style="padding: 12px 16px;">STATUS</th>
                            <th style="padding: 12px 16px; text-align: center;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody id="quotations-tbody">
                        <tr>
                            <td colspan="${isSupplier ? '9' : '10'}" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; margin-bottom: 8px;"></i>
                                <div>Loading quotations from Supabase...</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;

        setTimeout(() => this.init(container), 0);
        return container;
    },

    async init(container) {
        const refreshBtn = container.querySelector('#btn-refresh-quotes');
        if (refreshBtn) refreshBtn.addEventListener('click', () => this.loadQuotations());

        const searchInput = container.querySelector('#quote-search-input');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => this.loadQuotations(e.target.value), 300);
            });
        }

        const statusFilter = container.querySelector('#quote-status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => this.loadQuotations(searchInput ? searchInput.value : '', e.target.value));
        }

        const createBtn = container.querySelector('#btn-create-quote');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.openCreateQuotationModal());
        }

        const compareBtn = container.querySelector('#btn-compare-quotes');
        if (compareBtn) {
            compareBtn.addEventListener('click', () => this.openCompareQuotationsModal());
        }

        await this.loadQuotations();
    },

    async loadQuotations(searchTerm = '', statusFilterVal = '') {
        try {
            let url = '/quotations/';
            const params = new URLSearchParams();
            if (searchTerm && searchTerm.trim()) params.append('search', searchTerm.trim());
            if (statusFilterVal && statusFilterVal.trim()) params.append('status', statusFilterVal.trim());
            if (params.toString()) url += `?${params.toString()}`;

            const response = await Api.get(url);
            const quotes = response.quotations || [];
            const stats = response.stats || {};

            this.currentQuotations = quotes;
            this.updateStats(stats);
            this.renderTable(quotes);

            const countBadge = document.getElementById('quote-count-badge');
            if (countBadge) {
                countBadge.textContent = `${quotes.length} quotation${quotes.length === 1 ? '' : 's'}`;
            }
        } catch (error) {
            console.error('Failed to load quotations:', error);
            const tbody = document.getElementById('quotations-tbody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" style="text-align: center; padding: 40px; color: var(--red);">
                            <i class='bx bx-error-circle' style="font-size: 28px; margin-bottom: 8px;"></i>
                            <div>Failed to load quotations: ${error.message || 'Server error'}</div>
                        </td>
                    </tr>
                `;
            }
        }
    },

    updateStats(stats) {
        const elDrafts = document.getElementById('stat-quote-drafts');
        const elSubmitted = document.getElementById('stat-quote-submitted');
        const elApproved = document.getElementById('stat-quote-approved');
        const elValue = document.getElementById('stat-quote-value');

        if (elDrafts) elDrafts.textContent = String(stats.drafts || 0).padStart(2, '0');
        if (elSubmitted) elSubmitted.textContent = String(stats.submitted || 0).padStart(2, '0');
        if (elApproved) elApproved.textContent = String(stats.approved || 0).padStart(2, '0');
        if (elValue) elValue.textContent = `₹${(stats.total_value || 0).toLocaleString('en-IN')}`;
    },

    renderTable(quotes) {
        const tbody = document.getElementById('quotations-tbody');
        if (!tbody) return;

        const user = Auth.getUser();
        const isSupplier = user && user.role === 'Supplier';
        const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');

        if (!quotes || quotes.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${isSupplier ? '9' : '10'}" style="text-align: center; padding: 50px 20px; color: var(--text-secondary);">
                        <i class='bx bx-file-blank' style="font-size: 36px; color: var(--text-light); margin-bottom: 10px; display: block;"></i>
                        <div style="font-size: 15px; font-weight: 600; color: var(--text);">No quotations found</div>
                        <div style="font-size: 13px; margin-top: 4px;">${isSupplier ? 'Submit quotations against accepted Purchase Orders to start negotiation.' : 'No supplier quotations submitted yet.'}</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = quotes.map(q => {
            const statusBadge = this.getStatusBadge(q.status);
            const formattedTotal = (q.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
            const formattedPrice = (q.quoted_price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
            const qNum = q.quotation_number || `QT-2026-${String(q.quotation_id).padStart(4, '0')}`;
            const dateStr = q.quotation_date || 'N/A';
            const validUntilStr = q.valid_until || 'No expiry';

            const isDraft = q.status && q.status.toLowerCase() === 'draft';
            const isSubmitted = q.status && q.status.toLowerCase() === 'submitted';

            return `
                <tr style="border-bottom: 1px solid var(--border); transition: background 0.15s ease;" onmouseover="this.style.background='var(--bg-hover, rgba(0,0,0,0.02))'" onmouseout="this.style.background='transparent'">
                    <td style="padding: 14px 16px;">
                        <div style="font-weight: 600; color: var(--text);">${qNum}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${dateStr}</div>
                    </td>
                    <td style="padding: 14px 16px;">
                        ${q.purchase_order_id ? `
                            <span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(59, 130, 246, 0.08); color: #2563eb; font-size: 12px; font-weight: 600;">
                                <i class='bx bx-receipt'></i> PO #${q.purchase_order_id}
                            </span>
                        ` : '<span style="color: var(--text-light); font-size: 12px;">Direct Quote</span>'}
                    </td>
                    ${!isSupplier ? `
                        <td style="padding: 14px 16px;">
                            <div style="font-weight: 500; color: var(--text);">${q.supplier_name || 'Supplier'}</div>
                            <div style="font-size: 11px; color: var(--text-secondary);">${q.supplier_email || ''}</div>
                        </td>
                    ` : ''}
                    <td style="padding: 14px 16px;">
                        <div style="font-weight: 500; color: var(--text);">${q.product_name}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-family: monospace;">SKU: ${q.product_sku || 'N/A'}</div>
                    </td>
                    <td style="padding: 14px 16px; text-align: right; font-weight: 600; color: var(--text);">
                        ${q.quantity}
                    </td>
                    <td style="padding: 14px 16px; text-align: right; color: var(--text-secondary); font-size: 13px;">
                        ₹${formattedPrice}
                    </td>
                    <td style="padding: 14px 16px; text-align: right; font-weight: 700; color: var(--text);">
                        ₹${formattedTotal}
                    </td>
                    <td style="padding: 14px 16px; font-size: 12px; color: var(--text-secondary);">
                        ${validUntilStr}
                    </td>
                    <td style="padding: 14px 16px;">
                        ${statusBadge}
                    </td>
                    <td style="padding: 14px 16px; text-align: center;">
                        <div style="display: inline-flex; gap: 6px; align-items: center;">
                            <button class="btn btn-icon-small" title="View Quotation Details" onclick="App.pages['quotations'].openQuotationDetailsModal(${q.quotation_id})"
                                    style="background: white; border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; cursor: pointer; color: var(--text-secondary);">
                                <i class='bx bx-show' style="font-size: 16px;"></i>
                            </button>

                            ${isSupplier && isDraft ? `
                                <button class="btn btn-icon-small" title="Edit Draft" onclick="App.pages['quotations'].openEditDraftModal(${q.quotation_id})"
                                        style="background: white; border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; cursor: pointer; color: #2563eb;">
                                    <i class='bx bx-edit' style="font-size: 16px;"></i>
                                </button>
                                <button class="btn btn-icon-small" title="Submit Quotation" onclick="App.pages['quotations'].submitDraft(${q.quotation_id})"
                                        style="background: #2563eb; color: white; border: none; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 12px; display: inline-flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-send'></i> Submit
                                </button>
                            ` : ''}

                            ${isManagerOrOwner && isSubmitted ? `
                                <button class="btn btn-icon-small" title="Approve Offer" onclick="App.pages['quotations'].approveQuotation(${q.quotation_id})"
                                        style="background: #059669; color: white; border: none; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 12px; display: inline-flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-check'></i> Approve
                                </button>
                                <button class="btn btn-icon-small" title="Reject Offer" onclick="App.pages['quotations'].rejectQuotation(${q.quotation_id})"
                                        style="background: white; border: 1px solid #ef4444; color: #ef4444; border-radius: 6px; padding: 6px 8px; cursor: pointer;">
                                    <i class='bx bx-x' style="font-size: 16px;"></i>
                                </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    },

    getStatusBadge(status) {
        const s = (status || 'Pending').toLowerCase();
        if (s === 'approved' || s === 'accepted') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; font-weight: 600;">
                <i class='bx bx-check-circle'></i> Approved
            </span>`;
        }
        if (s === 'submitted') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(59, 130, 246, 0.12); color: #2563eb; font-size: 11px; font-weight: 600;">
                <i class='bx bx-time'></i> Submitted
            </span>`;
        }
        if (s === 'draft') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(107, 114, 128, 0.12); color: #4b5563; font-size: 11px; font-weight: 600;">
                <i class='bx bx-pencil'></i> Draft
            </span>`;
        }
        if (s === 'rejected' || s === 'expired') {
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(239, 68, 68, 0.12); color: #ef4444; font-size: 11px; font-weight: 600;">
                <i class='bx bx-x-circle'></i> ${status}
            </span>`;
        }
        return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 6px; background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 11px; font-weight: 600;">
            <i class='bx bx-time-five'></i> ${status}
        </span>`;
    },

    // Supplier: Create Quotation Modal
    async openCreateQuotationModal() {
        try {
            // Fetch Supplier's accepted POs
            const poResp = await Api.get('/purchase-orders/');
            const orders = poResp.purchase_orders || [];
            // Filter to accepted orders
            const eligible = orders.filter(po => (po.supplier_response === 'Accepted' || po.status === 'Accepted'));

            if (eligible.length === 0) {
                alert('No accepted Purchase Orders available. Quotations can only be created for Purchase Orders you have accepted.');
                return;
            }

            this.eligiblePOs = eligible;

            const content = `
                <div style="display: flex; flex-direction: column; gap: 16px;">
                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SELECT ACCEPTED PURCHASE ORDER *</label>
                        <select id="modal-quote-po-select" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-surface, #ffffff); font-size: 14px;">
                            <option value="">-- Choose a Purchase Order --</option>
                            ${eligible.map(po => `
                                <option value="${po.purchase_order_id}">PO #${po.purchase_order_id} - ${po.order_date} (Total: ₹${(po.total_amount || 0).toLocaleString('en-IN')})</option>
                            `).join('')}
                        </select>
                    </div>

                    <div id="modal-po-preview-box" style="display: none; padding: 14px; border-radius: 8px; background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2);">
                        <div style="font-weight: 600; font-size: 13px; color: #1e40af; margin-bottom: 6px;">Original Purchase Order Requirements</div>
                        <div id="modal-po-items-list" style="display: flex; flex-direction: column; gap: 10px;">
                            <!-- Dynamically loaded -->
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">VALID UNTIL</label>
                            <input type="date" id="modal-quote-valid-until" style="width: 100%; padding: 9px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">TOTAL OFFER PREVIEW</label>
                            <div id="modal-quote-grand-total" style="padding: 9px 12px; border-radius: 8px; background: var(--bg-surface, #f3f4f6); font-weight: 700; font-size: 16px; color: var(--text);">₹0.00</div>
                        </div>
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">NOTES / PROPOSAL REMARKS</label>
                        <textarea id="modal-quote-notes" rows="2" placeholder="e.g., Bulk supply discount, includes freight to warehouse..." 
                                  style="width: 100%; padding: 9px 12px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;"></textarea>
                    </div>
                </div>
            `;

            const footer = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <button type="button" class="btn btn-outline" id="modal-quote-cancel-btn">Cancel</button>
                    <div style="display: flex; gap: 10px;">
                        <button type="button" class="btn secondary" id="modal-quote-save-draft-btn" style="background: white; border: 1px solid var(--border);">
                            <i class='bx bx-save'></i> Save Draft
                        </button>
                        <button type="button" class="btn primary" id="modal-quote-submit-btn">
                            <i class='bx bx-send'></i> Submit Quotation
                        </button>
                    </div>
                </div>
            `;

            Modal.create({
                id: 'modal-create-quotation',
                title: 'Create Supplier Quotation 📝',
                content,
                footer,
                onOpen: (overlay, closeModal) => {
                    overlay.querySelector('#modal-quote-cancel-btn').onclick = closeModal;

                    const poSelect = overlay.querySelector('#modal-quote-po-select');
                    const previewBox = overlay.querySelector('#modal-po-preview-box');
                    const itemsContainer = overlay.querySelector('#modal-po-items-list');

                    let selectedPODetails = null;

                    poSelect.addEventListener('change', async (e) => {
                        const poId = e.target.value;
                        if (!poId) {
                            previewBox.style.display = 'none';
                            itemsContainer.innerHTML = '';
                            return;
                        }

                        try {
                            previewBox.style.display = 'block';
                            itemsContainer.innerHTML = '<div>Loading items...</div>';
                            const poData = await Api.get(`/purchase-orders/${poId}`);
                            selectedPODetails = poData.purchase_order;

                            itemsContainer.innerHTML = selectedPODetails.items.map((item, idx) => `
                                <div class="quote-item-row" data-product-id="${item.product_id}" style="padding: 10px; border-radius: 6px; background: white; border: 1px solid var(--border); display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 10px; align-items: center;">
                                    <div>
                                        <div style="font-weight: 600; font-size: 13px;">${item.product_name}</div>
                                        <div style="font-size: 11px; color: var(--text-secondary);">Target: ${item.quantity} units @ ₹${item.unit_price}</div>
                                    </div>
                                    <div>
                                        <label style="font-size: 10px; font-weight: 600; color: var(--text-secondary);">OFFERED QTY</label>
                                        <input type="number" class="item-qty" min="1" value="${item.quantity}" 
                                               style="width: 100%; padding: 6px; border-radius: 4px; border: 1px solid var(--border); font-size: 12px;">
                                    </div>
                                    <div>
                                        <label style="font-size: 10px; font-weight: 600; color: var(--text-secondary);">UNIT PRICE (₹)</label>
                                        <input type="number" class="item-price" step="0.01" min="0" value="${item.unit_price}" 
                                               style="width: 100%; padding: 6px; border-radius: 4px; border: 1px solid var(--border); font-size: 12px;">
                                    </div>
                                    <div style="text-align: right;">
                                        <label style="font-size: 10px; font-weight: 600; color: var(--text-secondary);">SUBTOTAL</label>
                                        <div class="item-subtotal" style="font-weight: 700; font-size: 13px; color: var(--text); margin-top: 4px;">
                                            ₹${(item.quantity * item.unit_price).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                        </div>
                                    </div>
                                </div>
                            `).join('');

                            const recalculateGrandTotal = () => {
                                let grandTotal = 0;
                                overlay.querySelectorAll('.quote-item-row').forEach(row => {
                                    const qty = parseFloat(row.querySelector('.item-qty').value) || 0;
                                    const price = parseFloat(row.querySelector('.item-price').value) || 0;
                                    const sub = qty * price;
                                    grandTotal += sub;
                                    row.querySelector('.item-subtotal').textContent = `₹${sub.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                                });
                                overlay.querySelector('#modal-quote-grand-total').textContent = `₹${grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                            };

                            overlay.querySelectorAll('.item-qty, .item-price').forEach(input => {
                                input.addEventListener('input', recalculateGrandTotal);
                            });

                            recalculateGrandTotal();

                        } catch (err) {
                            itemsContainer.innerHTML = `<div style="color: var(--red);">Error loading PO items: ${err.message}</div>`;
                        }
                    });

                    const handleSaveOrSubmit = async (initialStatus) => {
                        const poId = poSelect.value;
                        if (!poId) {
                            alert('Please select a Purchase Order.');
                            return;
                        }

                        const itemRows = overlay.querySelectorAll('.quote-item-row');
                        if (itemRows.length === 0) {
                            alert('Please select a valid Purchase Order with items.');
                            return;
                        }

                        const items = [];
                        let hasInvalid = false;
                        itemRows.forEach(row => {
                            const productId = parseInt(row.getAttribute('data-product-id'));
                            const qty = parseInt(row.querySelector('.item-qty').value);
                            const price = parseFloat(row.querySelector('.item-price').value);

                            if (!qty || qty <= 0 || price < 0 || isNaN(price)) {
                                hasInvalid = true;
                            }
                            items.push({
                                product_id: productId,
                                quantity: qty,
                                quoted_price: price
                            });
                        });

                        if (hasInvalid) {
                            alert('Please ensure all offered quantities are > 0 and unit prices are valid non-negative numbers.');
                            return;
                        }

                        const payload = {
                            purchase_order_id: parseInt(poId),
                            items,
                            valid_until: overlay.querySelector('#modal-quote-valid-until').value || null,
                            notes: overlay.querySelector('#modal-quote-notes').value || '',
                            status: initialStatus
                        };

                        try {
                            const resp = await Api.post('/quotations/', payload);
                            closeModal();
                            alert(initialStatus === 'Draft' 
                                ? 'Quotation saved as Draft. You can edit and submit it later.' 
                                : 'Quotation submitted successfully to Manager/Owner for review!');
                            App.pages['quotations'].loadQuotations();
                        } catch (err) {
                            alert(`Error: ${err.message || 'Failed to create quotation'}`);
                        }
                    };

                    overlay.querySelector('#modal-quote-save-draft-btn').onclick = () => handleSaveOrSubmit('Draft');
                    overlay.querySelector('#modal-quote-submit-btn').onclick = () => handleSaveOrSubmit('Submitted');
                }
            });

        } catch (error) {
            alert(`Error opening quotation builder: ${error.message}`);
        }
    },

    // Edit Draft Quotation Modal
    async openEditDraftModal(quotationId) {
        try {
            const data = await Api.get(`/quotations/${quotationId}`);
            const q = data.quotation;

            const content = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div style="padding: 12px; border-radius: 8px; background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2);">
                        <div style="font-weight: 600; font-size: 14px; color: #1e40af;">${q.quotation_number} - Product: ${q.product_name}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Original PO Required: ${q.original_po_quantity || 'N/A'} units</div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">OFFERED QUANTITY *</label>
                            <input type="number" id="edit-draft-qty" min="1" value="${q.quantity}" style="width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">OFFERED UNIT PRICE (₹) *</label>
                            <input type="number" id="edit-draft-price" step="0.01" min="0" value="${q.quoted_price}" style="width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">VALID UNTIL</label>
                            <input type="date" id="edit-draft-valid" value="${q.valid_until || ''}" style="width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">CALCULATED TOTAL</label>
                            <div id="edit-draft-total-display" style="padding: 8px 10px; border-radius: 8px; background: var(--bg-surface, #f3f4f6); font-weight: 700; font-size: 15px;">₹${(q.total_amount || 0).toLocaleString('en-IN')}</div>
                        </div>
                    </div>

                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">NOTES</label>
                        <textarea id="edit-draft-notes" rows="2" style="width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--border);">${q.notes || ''}</textarea>
                    </div>
                </div>
            `;

            Modal.show({
                title: 'Edit Draft Quotation ✏️',
                content,
                saveText: 'Save Changes',
                onSave: async (closeModal) => {
                    const qty = parseInt(document.getElementById('edit-draft-qty').value);
                    const price = parseFloat(document.getElementById('edit-draft-price').value);
                    const validUntil = document.getElementById('edit-draft-valid').value;
                    const notes = document.getElementById('edit-draft-notes').value;

                    if (!qty || qty <= 0 || price < 0 || isNaN(price)) {
                        alert('Please enter a valid positive quantity and non-negative price.');
                        return;
                    }

                    try {
                        await Api.put(`/quotations/${quotationId}`, {
                            quantity: qty,
                            quoted_price: price,
                            valid_until: validUntil || null,
                            notes: notes || ''
                        });
                        closeModal();
                        App.pages['quotations'].loadQuotations();
                    } catch (err) {
                        alert(`Error updating draft: ${err.message}`);
                    }
                }
            });

            const qtyInp = document.getElementById('edit-draft-qty');
            const priceInp = document.getElementById('edit-draft-price');
            const totalDisp = document.getElementById('edit-draft-total-display');
            const recalc = () => {
                const total = (parseFloat(qtyInp.value) || 0) * (parseFloat(priceInp.value) || 0);
                totalDisp.textContent = `₹${total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
            };
            qtyInp.addEventListener('input', recalc);
            priceInp.addEventListener('input', recalc);

        } catch (err) {
            alert(`Error opening quotation: ${err.message}`);
        }
    },

    // Submit Draft
    async submitDraft(quotationId) {
        if (!confirm('Submit this quotation to Manager/Owner? Once submitted, it cannot be modified.')) return;
        try {
            await Api.post(`/quotations/${quotationId}/submit`);
            alert('Quotation submitted successfully!');
            this.loadQuotations();
        } catch (err) {
            alert(`Error submitting quotation: ${err.message}`);
        }
    },

    // View Quotation Details Modal
    async openQuotationDetailsModal(quotationId) {
        try {
            const data = await Api.get(`/quotations/${quotationId}`);
            const q = data.quotation;

            const user = Auth.getUser();
            const isManagerOrOwner = user && (user.role === 'Owner' || user.role === 'Manager');
            const isSubmitted = q.status && q.status.toLowerCase() === 'submitted';

            const statusBadge = this.getStatusBadge(q.status);
            const totalFormatted = (q.total_amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });
            const priceFormatted = (q.quoted_price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 });

            const content = `
                <div style="display: flex; flex-direction: column; gap: 16px;">
                    <!-- Header Summary -->
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; padding: 16px; border-radius: 8px; background: var(--bg-surface, #f9fafb); border: 1px solid var(--border);">
                        <div>
                            <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Quotation Number</div>
                            <h2 style="font-size: 20px; font-weight: 700; margin: 4px 0; color: var(--text);">${q.quotation_number}</h2>
                            <div style="font-size: 12px; color: var(--text-secondary);">Dated: ${q.quotation_date || 'N/A'} • Valid Until: ${q.valid_until || 'No expiry'}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="margin-bottom: 6px;">${statusBadge}</div>
                            <div style="font-size: 22px; font-weight: 700; color: var(--text);">₹${totalFormatted}</div>
                        </div>
                    </div>

                    <!-- PO & Supplier Details -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                        <div style="padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Purchase Order Reference</div>
                            <div style="font-weight: 600; font-size: 14px; color: #2563eb;">PO #${q.purchase_order_id || 'N/A'}</div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Original PO Date: ${q.po_order_date || 'N/A'}</div>
                            <div style="font-size: 12px; color: var(--text-secondary);">Original PO Budget: ₹${(q.po_total || 0).toLocaleString('en-IN')}</div>
                        </div>

                        <div style="padding: 12px; border-radius: 8px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Supplier Details</div>
                            <div style="font-weight: 600; font-size: 14px; color: var(--text);">${q.supplier_name}</div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Contact: ${q.contact_person || 'N/A'}</div>
                            <div style="font-size: 12px; color: var(--text-secondary);">${q.supplier_email || ''} • ${q.supplier_phone || ''}</div>
                        </div>
                    </div>

                    <!-- Product & Offer Comparison Table -->
                    <div style="border-radius: 8px; border: 1px solid var(--border); overflow: hidden;">
                        <div style="padding: 10px 14px; background: var(--bg-surface, #f9fafb); border-bottom: 1px solid var(--border); font-weight: 600; font-size: 12px; text-transform: uppercase; color: var(--text-secondary);">
                            Offer Breakdown vs Baseline Requirements
                        </div>
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                            <thead>
                                <tr style="background: rgba(0,0,0,0.01); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px;">
                                    <th style="padding: 8px 12px; text-align: left;">Product</th>
                                    <th style="padding: 8px 12px; text-align: right;">Target Qty</th>
                                    <th style="padding: 8px 12px; text-align: right;">Offered Qty</th>
                                    <th style="padding: 8px 12px; text-align: right;">Target Unit Price</th>
                                    <th style="padding: 8px 12px; text-align: right;">Offered Unit Price</th>
                                    <th style="padding: 8px 12px; text-align: right;">Line Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td style="padding: 10px 12px; font-weight: 600;">
                                        ${q.product_name}
                                        <div style="font-size: 11px; color: var(--text-secondary); font-family: monospace;">SKU: ${q.product_sku || 'N/A'}</div>
                                    </td>
                                    <td style="padding: 10px 12px; text-align: right; color: var(--text-secondary);">
                                        ${q.original_po_quantity !== null ? q.original_po_quantity : 'N/A'}
                                    </td>
                                    <td style="padding: 10px 12px; text-align: right; font-weight: 700; color: ${q.original_po_quantity && q.quantity !== q.original_po_quantity ? '#d97706' : 'var(--text)'};">
                                        ${q.quantity}
                                        ${q.original_po_quantity && q.quantity !== q.original_po_quantity ? '<div style="font-size: 10px; color: #d97706;">(adjusted)</div>' : ''}
                                    </td>
                                    <td style="padding: 10px 12px; text-align: right; color: var(--text-secondary);">
                                        ${q.original_po_unit_price !== null ? `₹${q.original_po_unit_price}` : 'N/A'}
                                    </td>
                                    <td style="padding: 10px 12px; text-align: right; font-weight: 600; color: var(--text);">
                                        ₹${priceFormatted}
                                    </td>
                                    <td style="padding: 10px 12px; text-align: right; font-weight: 700; color: var(--text);">
                                        ₹${totalFormatted}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    ${q.notes ? `
                        <div style="padding: 10px 14px; border-radius: 8px; background: var(--bg-surface, #f9fafb); border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Proposal Remarks</div>
                            <div style="font-size: 13px; margin-top: 4px; color: var(--text);">${q.notes}</div>
                        </div>
                    ` : ''}

                    ${q.approved_by_username ? `
                        <div style="padding: 10px 14px; border-radius: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2);">
                            <div style="font-size: 11px; font-weight: 600; color: #059669; text-transform: uppercase;">Approval Audit</div>
                            <div style="font-size: 13px; margin-top: 4px; color: var(--text);">Approved by <strong>${q.approved_by_username}</strong> on ${q.approved_at || 'Recorded'}</div>
                        </div>
                    ` : ''}

                    ${q.rejection_reason ? `
                        <div style="padding: 10px 14px; border-radius: 8px; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2);">
                            <div style="font-size: 11px; font-weight: 600; color: #ef4444; text-transform: uppercase;">Rejection Audit</div>
                            <div style="font-size: 13px; margin-top: 4px; color: var(--text);">${q.rejection_reason}</div>
                        </div>
                    ` : ''}
                </div>
            `;

            const footer = `
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                    <button type="button" class="btn btn-outline" id="modal-details-close-btn">Close</button>
                    ${isManagerOrOwner && isSubmitted ? `
                        <div style="display: flex; gap: 10px;">
                            <button type="button" class="btn" id="modal-details-reject-btn" style="background: white; border: 1px solid #ef4444; color: #ef4444;">
                                <i class='bx bx-x'></i> Reject Offer
                            </button>
                            <button type="button" class="btn primary" id="modal-details-approve-btn" style="background: #059669;">
                                <i class='bx bx-check'></i> Approve & Select Offer
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;

            Modal.create({
                id: 'modal-quotation-details',
                title: 'Quotation Details 🔍',
                content,
                footer,
                onOpen: (overlay, closeModal) => {
                    overlay.querySelector('#modal-details-close-btn').onclick = closeModal;

                    const approveBtn = overlay.querySelector('#modal-details-approve-btn');
                    if (approveBtn) {
                        approveBtn.onclick = () => {
                            closeModal();
                            App.pages['quotations'].approveQuotation(quotationId);
                        };
                    }

                    const rejectBtn = overlay.querySelector('#modal-details-reject-btn');
                    if (rejectBtn) {
                        rejectBtn.onclick = () => {
                            closeModal();
                            App.pages['quotations'].rejectQuotation(quotationId);
                        };
                    }
                }
            });

        } catch (err) {
            alert(`Error opening quotation details: ${err.message}`);
        }
    },

    // Manager / Owner: Approve Quotation
    async approveQuotation(quotationId) {
        if (!confirm('Are you sure you want to approve this quotation? Any other competing quotations for this Purchase Order item will automatically be rejected.')) {
            return;
        }

        try {
            const resp = await Api.patch(`/quotations/${quotationId}/approve`);
            alert(resp.message || 'Quotation approved successfully!');
            this.loadQuotations();
        } catch (err) {
            alert(`Approval failed: ${err.message || 'Error approving quotation'}`);
        }
    },

    // Manager / Owner: Reject Quotation
    async rejectQuotation(quotationId) {
        const reason = prompt('Please enter a rejection reason (optional):', 'Price too high or terms not acceptable');
        if (reason === null) return; // user cancelled prompt

        try {
            await Api.patch(`/quotations/${quotationId}/reject`, { rejection_reason: reason });
            alert('Quotation rejected successfully.');
            this.loadQuotations();
        } catch (err) {
            alert(`Rejection failed: ${err.message || 'Error rejecting quotation'}`);
        }
    },

    // Manager / Owner: Compare Quotations Modal
    async openCompareQuotationsModal() {
        try {
            // Get all POs
            const poResp = await Api.get('/purchase-orders/');
            const orders = poResp.purchase_orders || [];

            const content = `
                <div style="display: flex; flex-direction: column; gap: 16px;">
                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">SELECT PURCHASE ORDER TO COMPARE BIDS</label>
                        <select id="modal-compare-po-select" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                            <option value="">-- Choose a Purchase Order --</option>
                            ${orders.map(po => `
                                <option value="${po.purchase_order_id}">PO #${po.purchase_order_id} - ${po.supplier_name} - ${po.order_date} (Budget: ₹${(po.total_amount || 0).toLocaleString('en-IN')})</option>
                            `).join('')}
                        </select>
                    </div>

                    <div id="modal-compare-container" style="display: none;">
                        <!-- Comparison results injected here -->
                    </div>
                </div>
            `;

            Modal.create({
                id: 'modal-compare-quotations',
                title: 'Compare Supplier Bids ⚖️',
                content,
                footer: `<div style="display: flex; justify-content: flex-end; width: 100%;"><button class="btn btn-outline close-compare-btn">Close</button></div>`,
                onOpen: (overlay, closeModal) => {
                    overlay.querySelector('.close-compare-btn').onclick = closeModal;

                    const poSelect = overlay.querySelector('#modal-compare-po-select');
                    const compContainer = overlay.querySelector('#modal-compare-container');

                    poSelect.addEventListener('change', async (e) => {
                        const poId = e.target.value;
                        if (!poId) {
                            compContainer.style.display = 'none';
                            return;
                        }

                        try {
                            compContainer.style.display = 'block';
                            compContainer.innerHTML = '<div style="padding: 20px; text-align: center;"><i class="bx bx-loader-alt bx-spin"></i> Loading bid comparison...</div>';

                            const resp = await Api.get(`/quotations/compare?po_id=${poId}`);
                            const comp = resp.comparison;

                            if (!comp || comp.quotations.length === 0) {
                                compContainer.innerHTML = `
                                    <div style="padding: 30px; text-align: center; color: var(--text-secondary); background: var(--bg-surface, #f9fafb); border-radius: 8px;">
                                        <i class='bx bx-info-circle' style="font-size: 28px; margin-bottom: 6px;"></i>
                                        <div>No quotations submitted for PO #${poId} yet.</div>
                                    </div>
                                `;
                                return;
                            }

                            compContainer.innerHTML = `
                                <div style="display: flex; flex-direction: column; gap: 14px;">
                                    <div style="padding: 12px; border-radius: 8px; background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2);">
                                        <div style="font-weight: 700; font-size: 13px; color: #1e40af;">PO #${poId} Baseline Budget: ₹${(comp.purchase_order.total_amount || 0).toLocaleString('en-IN')}</div>
                                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Total Competing Bids: ${comp.total_quotations}</div>
                                    </div>

                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;">
                                        ${comp.quotations.map(q => {
                                            const isApproved = q.status && (q.status.toLowerCase() === 'approved' || q.status.toLowerCase() === 'accepted');
                                            const isSubmitted = q.status && q.status.toLowerCase() === 'submitted';
                                            return `
                                                <div style="padding: 14px; border-radius: 8px; border: 2px solid ${isApproved ? '#059669' : 'var(--border)'}; background: ${isApproved ? 'rgba(16, 185, 129, 0.03)' : 'white'}; display: flex; flex-direction: column; justify-content: space-between;">
                                                    <div>
                                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                                            <strong style="font-size: 14px;">${q.quotation_number}</strong>
                                                            ${App.pages['quotations'].getStatusBadge(q.status)}
                                                        </div>
                                                        <div style="font-size: 13px; font-weight: 600; color: var(--text);">${q.supplier_name}</div>
                                                        <div style="font-size: 11px; color: var(--text-secondary);">${q.supplier_email || ''}</div>
                                                        
                                                        <hr style="border: none; border-top: 1px solid var(--border); margin: 10px 0;">
                                                        
                                                        <div style="font-size: 12px;"><strong>Product:</strong> ${q.product_name}</div>
                                                        <div style="font-size: 12px; margin-top: 2px;"><strong>Offered Quantity:</strong> ${q.offered_quantity} units</div>
                                                        <div style="font-size: 12px; margin-top: 2px;"><strong>Unit Price:</strong> ₹${(q.quoted_price || 0).toLocaleString('en-IN')}</div>
                                                        <div style="font-size: 15px; font-weight: 700; color: var(--text); margin-top: 8px;">Total: ₹${(q.total_amount || 0).toLocaleString('en-IN')}</div>
                                                    </div>

                                                    <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid var(--border);">
                                                        ${isSubmitted ? `
                                                            <button class="btn primary" style="width: 100%; font-size: 12px; padding: 7px; background: #059669;" onclick="Modal.closeAll(); App.pages['quotations'].approveQuotation(${q.quotation_id})">
                                                                <i class='bx bx-check'></i> Select & Approve
                                                            </button>
                                                        ` : isApproved ? `
                                                            <div style="text-align: center; color: #059669; font-weight: 600; font-size: 12px;">
                                                                <i class='bx bx-badge-check'></i> Approved Bid
                                                            </div>
                                                        ` : `
                                                            <div style="text-align: center; color: var(--text-secondary); font-size: 12px;">${q.status}</div>
                                                        `}
                                                    </div>
                                                </div>
                                            `;
                                        }).join('')}
                                    </div>
                                </div>
                            `;
                        } catch (err) {
                            compContainer.innerHTML = `<div style="color: var(--red);">Error comparing quotes: ${err.message}</div>`;
                        }
                    });
                }
            });

        } catch (err) {
            alert(`Error opening bid comparison: ${err.message}`);
        }
    }
};
