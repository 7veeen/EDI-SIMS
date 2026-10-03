// suppliers.js

App.pages['suppliers'] = {
    currentSuppliers: [],

    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">PROCUREMENT</span>
                    <h1>Suppliers 🏢</h1>
                    <p>Manage vendor profiles, contact representatives, and procurement relations.</p>
                </div>
                <div class="header-actions">
                    <button class="btn secondary" id="btn-refresh-suppliers" title="Refresh Supplier Directory">
                        <i class='bx bx-refresh'></i> Refresh
                    </button>
                    <button class="btn primary" id="btn-add-supplier">
                        <i class='bx bx-plus'></i> Add Supplier
                    </button>
                </div>
            </div>

            <!-- Metric Cards -->
            <div class="stats-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0;">
                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Total Suppliers</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(59, 130, 246, 0.1); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-buildings'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-total-suppliers" style="font-size: 26px; font-weight: 700; margin: 0; color: var(--text);">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Registered vendors</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Active Vendors</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(16, 185, 129, 0.1); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-check-shield'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-active-suppliers" style="font-size: 26px; font-weight: 700; margin: 0; color: #059669;">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Ready for orders</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Portal Accounts</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(139, 92, 246, 0.1); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-user-check'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-linked-accounts" style="font-size: 26px; font-weight: 700; margin: 0; color: #7c3aed;">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Linked portal logins</span>
                    </div>
                </div>

                <div class="card stat-card" style="padding: 16px 20px; border-radius: 12px; background: var(--card-bg, #ffffff); border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Total PO Orders</span>
                        <div style="width: 36px; height: 36px; border-radius: 8px; background: rgba(245, 158, 11, 0.1); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                            <i class='bx bx-receipt'></i>
                        </div>
                    </div>
                    <div style="margin-top: 10px;">
                        <h2 id="stat-total-orders" style="font-size: 26px; font-weight: 700; margin: 0; color: #d97706;">0</h2>
                        <span style="font-size: 12px; color: var(--text-secondary);">Recorded orders</span>
                    </div>
                </div>
            </div>

            <!-- Controls: Search & Filter -->
            <div class="card" style="padding: 16px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 14px; align-items: center; justify-content: space-between;">
                <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; flex: 1;">
                    <div class="global-search" style="margin: 0; flex: 1; min-width: 240px; max-width: 400px; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="supplier-search" placeholder="Search by name, contact, email or phone..." style="background: transparent;">
                    </div>
                    <div style="min-width: 170px;">
                        <select id="supplier-status-filter" class="input" style="height: 42px; margin: 0;">
                            <option value="">All Statuses</option>
                            <option value="Active">Active Only</option>
                            <option value="Inactive">Inactive Only</option>
                        </select>
                    </div>
                </div>
                <div id="supplier-count-indicator" style="font-size: 13px; color: var(--text-secondary);">
                    Loading suppliers...
                </div>
            </div>

            <!-- Table -->
            <div class="card table-responsive" style="margin-top: 10px;">
                <table class="table" id="suppliers-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>SUPPLIER / COMPANY</th>
                            <th>CONTACT PERSON</th>
                            <th>WORK PHONE</th>
                            <th>EMAIL ADDRESS</th>
                            <th>PORTAL USER</th>
                            <th>ORDERS</th>
                            <th>STATUS</th>
                            <th style="text-align: right;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="9" style="text-align: center; padding: 32px; color: var(--text-secondary);">Loading supplier directory...</td></tr>
                    </tbody>
                </table>
            </div>
        `;

        return container;
    },

    async init() {
        this.loadSuppliers();

        const searchInput = document.getElementById('supplier-search');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.loadSuppliers(e.target.value, document.getElementById('supplier-status-filter')?.value);
                }, 300);
            });
        }

        const filterSelect = document.getElementById('supplier-status-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.loadSuppliers(document.getElementById('supplier-search')?.value, e.target.value);
            });
        }

        const refreshBtn = document.getElementById('btn-refresh-suppliers');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadSuppliers(document.getElementById('supplier-search')?.value, document.getElementById('supplier-status-filter')?.value);
            });
        }

        const addBtn = document.getElementById('btn-add-supplier');
        if (addBtn) {
            const user = Auth.getUser();
            if (user && !['Owner', 'Manager'].includes(user.role)) {
                addBtn.style.display = 'none';
            } else {
                addBtn.addEventListener('click', () => {
                    this.showSupplierModal();
                });
            }
        }
    },

    async loadSuppliers(search = '', status = '') {
        const tbody = document.querySelector('#suppliers-table tbody');
        const countIndicator = document.getElementById('supplier-count-indicator');

        try {
            let url = '/suppliers/?';
            if (search) url += `search=${encodeURIComponent(search)}&`;
            if (status) url += `status=${encodeURIComponent(status)}&`;

            const data = await Api.get(url);
            const suppliers = Array.isArray(data) ? data : (data.suppliers || []);
            this.currentSuppliers = suppliers;

            // Update Metric Cards
            const total = suppliers.length;
            const activeCount = suppliers.filter(s => s.status === 'Active').length;
            const linkedCount = suppliers.filter(s => s.user_id).length;
            const totalOrders = suppliers.reduce((sum, s) => sum + (parseInt(s.total_orders) || 0), 0);

            const statTotal = document.getElementById('stat-total-suppliers');
            if (statTotal) statTotal.textContent = total;
            const statActive = document.getElementById('stat-active-suppliers');
            if (statActive) statActive.textContent = activeCount;
            const statLinked = document.getElementById('stat-linked-accounts');
            if (statLinked) statLinked.textContent = linkedCount;
            const statOrders = document.getElementById('stat-total-orders');
            if (statOrders) statOrders.textContent = totalOrders;

            if (countIndicator) {
                countIndicator.textContent = `Showing ${total} supplier${total === 1 ? '' : 's'}`;
            }

            if (suppliers.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="9" style="text-align: center; padding: 40px 16px;">
                            ${Utils.emptyState('bx-buildings', 'No Suppliers Found', search || status ? 'No suppliers match your current filter criteria.' : 'No suppliers have been added to the directory yet.')}
                        </td>
                    </tr>
                `;
                return;
            }

            const user = Auth.getUser();
            const canEdit = user && ['Owner', 'Manager'].includes(user.role);

            tbody.innerHTML = suppliers.map(s => {
                const initial = s.supplier_name ? s.supplier_name.charAt(0).toUpperCase() : 'S';
                const statusBadge = s.status === 'Active' ? 'status-active' : 'status-inactive';

                return `
                    <tr>
                        <td style="color: var(--text-secondary); font-size: 13px;">#${s.supplier_id}</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 34px; height: 34px; border-radius: 8px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">
                                    ${initial}
                                </div>
                                <div>
                                    <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(s.supplier_name)}</div>
                                </div>
                            </div>
                        </td>
                        <td><strong>${Utils.escapeHtml(s.contact_person || '—')}</strong></td>
                        <td style="font-size: 13px;">${Utils.escapeHtml(s.phone || '—')}</td>
                        <td style="font-size: 13px;">
                            ${s.email ? `<a href="mailto:${Utils.escapeHtml(s.email)}" style="color: var(--primary); text-decoration: none;"><i class='bx bx-envelope'></i> ${Utils.escapeHtml(s.email)}</a>` : '—'}
                        </td>
                        <td>
                            ${s.username ? `
                                <span class="badge" style="background: rgba(139, 92, 246, 0.12); color: #7c3aed; font-weight: 600;">
                                    <i class='bx bx-user'></i> ${Utils.escapeHtml(s.username)}
                                </span>
                            ` : `<span style="color: var(--text-secondary); font-size: 12px;">Not Linked</span>`}
                        </td>
                        <td>
                            <span class="badge" style="background: #f1f5f9; color: #475569; font-weight: 600;">
                                ${s.total_orders || 0} POs
                            </span>
                        </td>
                        <td>
                            <span class="status-badge ${statusBadge}">
                                ${s.status}
                            </span>
                        </td>
                        <td style="text-align: right;">
                            <div class="action-buttons" style="justify-content: flex-end;">
                                <button class="btn-icon text-primary" onclick="App.pages['suppliers'].viewSupplierDetails(${s.supplier_id})" title="View Details">
                                    <i class='bx bx-show'></i>
                                </button>
                                ${canEdit ? `
                                    <button class="btn-icon text-primary" onclick="App.pages['suppliers'].showSupplierModal(${s.supplier_id})" title="Edit Supplier">
                                        <i class='bx bx-edit'></i>
                                    </button>
                                    <button class="btn-icon text-danger" onclick="App.pages['suppliers'].deleteSupplier(${s.supplier_id})" title="Delete / Deactivate">
                                        <i class='bx bx-trash'></i>
                                    </button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');

        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-danger" style="text-align: center; padding: 24px;">Failed to load suppliers: ${error.message}</td></tr>`;
            if (countIndicator) countIndicator.textContent = 'Error loading directory';
        }
    },

    async viewSupplierDetails(supplierId) {
        try {
            const data = await Api.get(`/suppliers/${supplierId}`);
            const s = data.supplier;
            if (!s) throw new Error("Supplier details unavailable");

            const ordersHtml = (s.recent_orders && s.recent_orders.length > 0) ? `
                <table class="table" style="margin-top: 8px; font-size: 13px;">
                    <thead>
                        <tr>
                            <th>PO #</th>
                            <th>Date</th>
                            <th>Amount</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${s.recent_orders.map(o => `
                            <tr>
                                <td>#${o.purchase_order_id}</td>
                                <td>${o.order_date || 'N/A'}</td>
                                <td><strong>₹${o.total_amount.toFixed(2)}</strong></td>
                                <td><span class="status-badge ${o.status === 'Received' ? 'status-active' : 'status-pending'}">${o.status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : `<p style="color: var(--text-secondary); font-size: 13px; margin: 8px 0;">No purchase orders recorded yet.</p>`;

            const quotesHtml = (s.recent_quotations && s.recent_quotations.length > 0) ? `
                <table class="table" style="margin-top: 8px; font-size: 13px;">
                    <thead>
                        <tr>
                            <th>Quote #</th>
                            <th>Product</th>
                            <th>Price</th>
                            <th>Qty</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${s.recent_quotations.map(q => `
                            <tr>
                                <td>#${q.quotation_id}</td>
                                <td>${Utils.escapeHtml(q.product_name)}</td>
                                <td>₹${q.quoted_price.toFixed(2)}</td>
                                <td>${q.quantity}</td>
                                <td><span class="status-badge ${q.status === 'Accepted' ? 'status-active' : 'status-pending'}">${q.status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            ` : `<p style="color: var(--text-secondary); font-size: 13px; margin: 8px 0;">No quotations submitted yet.</p>`;

            const contentHtml = `
                <div style="display: flex; gap: 16px; align-items: center; padding-bottom: 16px; border-bottom: 1px solid var(--border);">
                    <div style="width: 50px; height: 50px; border-radius: 12px; background: rgba(59, 130, 246, 0.15); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 700;">
                        ${s.supplier_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <h3 style="margin: 0; font-size: 18px; color: var(--text);">${Utils.escapeHtml(s.supplier_name)}</h3>
                        <div style="font-size: 13px; color: var(--text-secondary); margin-top: 3px;">
                            Supplier ID: #${s.supplier_id} • Status: <span class="status-badge ${s.status === 'Active' ? 'status-active' : 'status-inactive'}">${s.status}</span>
                        </div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0; padding: 14px; background: #f8fafc; border-radius: 8px; border: 1px solid var(--border); font-size: 13px;">
                    <div>
                        <span style="color: var(--text-secondary);">Contact Representative:</span><br>
                        <strong>${Utils.escapeHtml(s.contact_person || 'Not specified')}</strong>
                    </div>
                    <div>
                        <span style="color: var(--text-secondary);">Work Phone:</span><br>
                        <strong>${Utils.escapeHtml(s.phone || 'Not specified')}</strong>
                    </div>
                    <div>
                        <span style="color: var(--text-secondary);">Email Address:</span><br>
                        <strong>${Utils.escapeHtml(s.email || 'Not specified')}</strong>
                    </div>
                    <div>
                        <span style="color: var(--text-secondary);">Portal User Link:</span><br>
                        <strong>${s.username ? `<i class='bx bx-user'></i> ${Utils.escapeHtml(s.username)}` : 'None linked'}</strong>
                    </div>
                </div>

                <div style="margin-top: 18px;">
                    <h4 style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: var(--text);"><i class='bx bx-receipt'></i> Recent Purchase Orders (${s.total_orders || 0} Total)</h4>
                    ${ordersHtml}
                </div>

                <div style="margin-top: 18px;">
                    <h4 style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; color: var(--text);"><i class='bx bx-file'></i> Recent Quotations (${s.total_quotations || 0} Total)</h4>
                    ${quotesHtml}
                </div>
            `;

            Modal.create({
                id: 'modal-supplier-details',
                title: `Vendor Profile — ${Utils.escapeHtml(s.supplier_name)}`,
                content: contentHtml,
                footer: `
                    <div style="display: flex; justify-content: flex-end; width: 100%;">
                        <button type="button" class="btn btn-primary close-modal">Close</button>
                    </div>
                `
            });

        } catch (err) {
            Utils.showToast("Failed to load supplier details: " + err.message, "error");
        }
    },

    async showSupplierModal(supplierId = null) {
        let supplier = null;
        if (supplierId) {
            try {
                const data = await Api.get(`/suppliers/${supplierId}`);
                supplier = data.supplier;
            } catch (err) {
                Utils.showToast("Failed to load supplier details: " + err.message, "error");
                return;
            }
        }

        // Load available supplier users for dropdown
        let usersDropdownHtml = '<option value="">No linked user account</option>';
        try {
            const url = supplierId ? `/suppliers/users?supplier_id=${supplierId}` : '/suppliers/users';
            const usersData = await Api.get(url);
            const users = usersData.users || [];
            usersDropdownHtml += users.map(u => {
                const isSelected = supplier && supplier.user_id === u.user_id;
                return `<option value="${u.user_id}" ${isSelected ? 'selected' : ''}>${Utils.escapeHtml(u.username)} (${Utils.escapeHtml(u.email || 'No email')})</option>`;
            }).join('');
        } catch (e) {
            usersDropdownHtml = '<option value="">Unable to load user accounts</option>';
        }

        const modalHtml = `
            <div class="form-group">
                <label>Company / Supplier Name <span class="text-danger">*</span></label>
                <input type="text" id="modal-supplier-name" class="input" value="${supplier ? Utils.escapeHtml(supplier.supplier_name) : ''}" required placeholder="e.g. Apex Global Distributors">
            </div>
            <div class="form-group">
                <label>Contact Representative</label>
                <input type="text" id="modal-supplier-contact" class="input" value="${supplier ? Utils.escapeHtml(supplier.contact_person) : ''}" placeholder="e.g. Rahul Sharma">
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                <div class="form-group">
                    <label>Work Phone</label>
                    <input type="text" id="modal-supplier-phone" class="input" value="${supplier ? Utils.escapeHtml(supplier.phone) : ''}" placeholder="+91 98765 43210">
                </div>
                <div class="form-group">
                    <label>Email Address</label>
                    <input type="email" id="modal-supplier-email" class="input" value="${supplier ? Utils.escapeHtml(supplier.email) : ''}" placeholder="vendor@example.com">
                </div>
            </div>
            <div class="form-group">
                <label>Link to Supplier Portal Login Account</label>
                <select id="modal-supplier-user" class="input">
                    ${usersDropdownHtml}
                </select>
                <small style="color: var(--text-secondary); font-size: 11px;">Connects this vendor profile to a login user account with role 'Supplier'.</small>
            </div>
            <div class="form-group">
                <label>Vendor Status</label>
                <select id="modal-supplier-status" class="input">
                    <option value="Active" ${!supplier || supplier.status === 'Active' ? 'selected' : ''}>Active</option>
                    <option value="Inactive" ${supplier && supplier.status === 'Inactive' ? 'selected' : ''}>Inactive</option>
                </select>
            </div>
        `;

        Modal.show({
            title: supplier ? `Edit Supplier — ${Utils.escapeHtml(supplier.supplier_name)}` : 'Add New Supplier',
            content: modalHtml,
            saveText: supplier ? 'Save Changes' : 'Create Supplier',
            onSave: async (container) => {
                const name = container.querySelector('#modal-supplier-name').value.trim();
                const contact = container.querySelector('#modal-supplier-contact').value.trim();
                const phone = container.querySelector('#modal-supplier-phone').value.trim();
                const email = container.querySelector('#modal-supplier-email').value.trim();
                const status = container.querySelector('#modal-supplier-status').value;
                const userVal = container.querySelector('#modal-supplier-user').value;

                if (!name) {
                    throw new Error("Company / Supplier Name is required");
                }

                const payload = {
                    supplier_name: name,
                    contact_person: contact || null,
                    phone: phone || null,
                    email: email || null,
                    status: status,
                    user_id: userVal ? parseInt(userVal) : null
                };

                if (supplier) {
                    await Api.put(`/suppliers/${supplierId}`, payload);
                    Utils.showToast("Supplier updated successfully", "success");
                } else {
                    await Api.post('/suppliers/', payload);
                    Utils.showToast("Supplier created successfully", "success");
                }

                this.loadSuppliers(
                    document.getElementById('supplier-search')?.value || '',
                    document.getElementById('supplier-status-filter')?.value || ''
                );
            }
        });
    },

    async deleteSupplier(supplierId) {
        if (!confirm('Are you sure you want to delete or deactivate this supplier?')) return;

        try {
            const resp = await Api.delete(`/suppliers/${supplierId}`);
            const msg = resp.message || (resp.deactivated ? "Supplier deactivated" : "Supplier deleted");
            Utils.showToast(msg, "success");
            this.loadSuppliers(
                document.getElementById('supplier-search')?.value || '',
                document.getElementById('supplier-status-filter')?.value || ''
            );
        } catch (error) {
            Utils.showToast(error.message || "Failed to delete supplier", "error");
        }
    }
};
