// users.js

App.pages['users'] = {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    search: '',
    sortBy: 'user_id',
    sortOrder: 'asc',
    debounceTimer: null,

    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">ADMINISTRATION</span>
                    <h1>User Management 👥</h1>
                    <p>Manage system access and roles.</p>
                </div>
                <div class="header-actions">
                    <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="users-search" placeholder="Search users by name or email..." style="background: transparent;">
                    </div>
                    <button class="btn primary" id="btn-create-user">
                        <i class='bx bx-plus'></i> New User
                    </button>
                </div>
            </div>
            
            <div class="card table-responsive" style="margin-top: 20px; overflow: hidden;">
                <table class="table" id="users-table">
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="user_id">ID <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="username">USERNAME <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="email">EMAIL <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="role">ROLE <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="status">STATUS <i class='bx bx-sort'></i></th>
                            <th style="text-align: right;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="6" style="text-align: center; padding: 28px; color: var(--text-secondary);">Loading users...</td></tr>
                    </tbody>
                </table>
                <div class="table-pagination" id="users-pagination">
                    <div class="pagination-info" id="users-pagination-info">Showing 0 of 0 users</div>
                    <div class="pagination-controls" id="users-pagination-controls"></div>
                </div>
            </div>
        `;
        return container;
    },

    async init() {
        this.page = 1;
        this.search = '';
        this.sortBy = 'user_id';
        this.sortOrder = 'asc';

        this.setupSortingHeaders();
        this.loadUsers();
        
        const searchInput = document.getElementById('users-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.search = e.target.value.trim();
                    this.page = 1;
                    this.loadUsers();
                }, 300);
            });
        }

        const createBtn = document.getElementById('btn-create-user');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.showCreateModal());
        }
    },

    setupSortingHeaders() {
        const ths = document.querySelectorAll('#users-table th.sortable');
        ths.forEach(th => {
            th.addEventListener('click', () => {
                const sortField = th.dataset.sort;
                if (this.sortBy === sortField) {
                    this.sortOrder = (this.sortOrder === 'asc' ? 'desc' : 'asc');
                } else {
                    this.sortBy = sortField;
                    this.sortOrder = 'asc';
                }
                this.updateSortHeaderIcons();
                this.loadUsers();
            });
        });
        this.updateSortHeaderIcons();
    },

    updateSortHeaderIcons() {
        const ths = document.querySelectorAll('#users-table th.sortable');
        ths.forEach(th => {
            const icon = th.querySelector('i');
            if (!icon) return;
            if (th.dataset.sort === this.sortBy) {
                th.classList.add('sorted');
                icon.className = this.sortOrder === 'asc' ? 'bx bx-sort-up' : 'bx bx-sort-down';
            } else {
                th.classList.remove('sorted');
                icon.className = 'bx bx-sort';
            }
        });
    },

    async loadUsers() {
        const tbody = document.querySelector('#users-table tbody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-secondary);"><i class='bx bx-loader-alt bx-spin' style='margin-right: 6px; font-size: 16px;'></i> Loading users...</td></tr>`;

        try {
            let url = `/users/?page=${this.page}&page_size=${this.pageSize}&sort_by=${encodeURIComponent(this.sortBy)}&sort_order=${this.sortOrder}`;
            if (this.search) {
                url += `&search=${encodeURIComponent(this.search)}`;
            }
            
            const data = await Api.get(url);
            const users = data.users || [];
            this.total = data.total !== undefined ? data.total : users.length;
            this.totalPages = data.total_pages || Math.max(1, Math.ceil(this.total / this.pageSize));

            if (users.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-secondary);">No users found.</td></tr>`;
                this.renderPagination();
                return;
            }

            const currentUser = Auth.getUser() || {};
            const currentUserId = parseInt(currentUser.id || 0);
            const isOwner = currentUser.role === 'Owner';
            const isManager = currentUser.role === 'Manager';

            tbody.innerHTML = users.map(u => {
                const targetUserId = parseInt(u.user_id);
                const isSelf = targetUserId === currentUserId;

                // Edit permission:
                let canEdit = false;
                if (isOwner) {
                    canEdit = true;
                } else if (isManager) {
                    canEdit = !isSelf && (u.role === 'Employee' || u.role === 'Supplier');
                }

                // Status toggle permissions
                let canToggle = false;
                if (isOwner) {
                    canToggle = !isSelf;
                } else if (isManager) {
                    canToggle = !isSelf && (u.role === 'Employee' || u.role === 'Supplier');
                }

                let roleBadgeColor = 'var(--primary)';
                if (u.role === 'Owner') roleBadgeColor = '#815bc7';
                if (u.role === 'Manager') roleBadgeColor = '#3478d4';
                if (u.role === 'Supplier') roleBadgeColor = '#e99b18';

                return `
                    <tr>
                        <td><strong>#${u.user_id}</strong></td>
                        <td>${Utils.escapeHtml(u.username)} ${isSelf ? '<span style="font-size: 11px; color: var(--primary); font-weight: 600;">(You)</span>' : ''}</td>
                        <td>${Utils.escapeHtml(u.email)}</td>
                        <td><span class="badge" style="background: ${roleBadgeColor}; color: white; font-weight: 600;">${u.role}</span></td>
                        <td>
                            <span class="status-badge ${u.status === 'Active' ? 'status-active' : 'status-inactive'}">
                                ${u.status}
                            </span>
                        </td>
                        <td style="text-align: right;">
                            <div class="table-actions" style="justify-content: flex-end;">
                                ${canEdit ? `
                                    <button class="btn-icon" 
                                        onclick="App.pages['users'].showEditModal(${u.user_id})" 
                                        title="Edit User">
                                        <i class='bx bx-edit-alt'></i>
                                    </button>
                                ` : ''}
                                ${canToggle ? `
                                    <button class="btn-icon ${u.status === 'Active' ? 'text-danger' : 'text-success'}" 
                                        onclick="App.pages['users'].toggleStatus(${u.user_id}, '${u.status}', '${Utils.escapeHtml(u.username)}', '${u.role}')" 
                                        title="${u.status === 'Active' ? 'Deactivate User' : 'Activate User'}">
                                        <i class='bx ${u.status === 'Active' ? 'bx-block' : 'bx-check-circle'}'></i>
                                    </button>
                                ` : (isSelf ? `
                                    <span class="protected-badge"><i class='bx bx-lock-alt'></i> Protected</span>
                                ` : '')}
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');

            this.renderPagination();
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-danger" style="text-align: center; padding: 24px;">Failed to load users: ${Utils.escapeHtml(error.message || 'Error')}</td></tr>`;
            this.renderPagination();
        }
    },

    renderPagination() {
        const infoEl = document.getElementById('users-pagination-info');
        const controlsEl = document.getElementById('users-pagination-controls');
        if (!infoEl || !controlsEl) return;

        if (this.total === 0) {
            infoEl.textContent = 'Showing 0 users';
            controlsEl.innerHTML = '';
            return;
        }

        const start = (this.page - 1) * this.pageSize + 1;
        const end = Math.min(this.page * this.pageSize, this.total);
        infoEl.textContent = `Showing ${start}–${end} of ${this.total} users`;

        let html = `
            <button class="pagination-btn" ${this.page <= 1 ? 'disabled' : ''} onclick="App.pages['users'].goToPage(${this.page - 1})">
                <i class='bx bx-chevron-left'></i> Previous
            </button>
        `;

        for (let p = 1; p <= this.totalPages; p++) {
            if (p === 1 || p === this.totalPages || (p >= this.page - 1 && p <= this.page + 1)) {
                html += `
                    <button class="pagination-btn ${p === this.page ? 'active' : ''}" onclick="App.pages['users'].goToPage(${p})">
                        ${p}
                    </button>
                `;
            } else if (p === this.page - 2 || p === this.page + 2) {
                html += `<span style="padding: 0 4px; color: var(--text-light);">...</span>`;
            }
        }

        html += `
            <button class="pagination-btn" ${this.page >= this.totalPages ? 'disabled' : ''} onclick="App.pages['users'].goToPage(${this.page + 1})">
                Next <i class='bx bx-chevron-right'></i>
            </button>
        `;

        controlsEl.innerHTML = html;
    },

    goToPage(pageNum) {
        if (pageNum < 1 || pageNum > this.totalPages || pageNum === this.page) return;
        this.page = pageNum;
        this.loadUsers();
    },

    async toggleStatus(id, currentStatus, username, role) {
        const newStatus = currentStatus === 'Active' ? 'Inactive' : 'Active';
        const actionWord = newStatus === 'Inactive' ? 'deactivate' : 'activate';
        const confirmMsg = `Are you sure you want to ${actionWord} user "${username || id}"?`;

        if (!confirm(confirmMsg)) return;

        try {
            await Api.put(`/users/${id}/status`, { status: newStatus });
            Utils.showToast(`User "${username}" status updated to ${newStatus}`, "success");
            this.loadUsers();
        } catch (error) {
            Utils.showToast(error.message || "Failed to update user status", "error");
        }
    },

    async showEditModal(id) {
        try {
            const data = await Api.get(`/users/${id}`);
            const user = data.user;
            if (!user) {
                Utils.showToast("User not found", "error");
                return;
            }

            const currentUser = Auth.getUser() || {};
            const currentUserId = parseInt(currentUser.id || 0);
            const isSelf = parseInt(user.user_id) === currentUserId;
            const isOwner = currentUser.role === 'Owner';
            const isManager = currentUser.role === 'Manager';

            let roleInputHtml = '';
            if (isSelf) {
                roleInputHtml = `
                    <input type="text" id="eu_role" class="input" value="${user.role}" disabled style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-hover); color: var(--text-secondary); cursor: not-allowed;">
                    <span style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Your role cannot be modified.</span>
                `;
            } else if (isOwner) {
                roleInputHtml = `
                    <select id="eu_role" class="input" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--white);">
                        <option value="Owner" ${user.role === 'Owner' ? 'selected' : ''}>Owner</option>
                        <option value="Manager" ${user.role === 'Manager' ? 'selected' : ''}>Manager</option>
                        <option value="Employee" ${user.role === 'Employee' ? 'selected' : ''}>Employee</option>
                        <option value="Supplier" ${user.role === 'Supplier' ? 'selected' : ''}>Supplier</option>
                    </select>
                `;
            } else if (isManager) {
                roleInputHtml = `
                    <select id="eu_role" class="input" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--white);">
                        <option value="Employee" ${user.role === 'Employee' ? 'selected' : ''}>Employee</option>
                        <option value="Supplier" ${user.role === 'Supplier' ? 'selected' : ''}>Supplier</option>
                    </select>
                `;
            }

            Modal.create({
                id: 'editUserModal',
                title: `Edit User: ${Utils.escapeHtml(user.username)}`,
                content: `
                    <form id="edit-user-form" style="display: flex; flex-direction: column; gap: 1.25rem;">
                        <div class="form-group" style="display: flex; flex-direction: column; gap: 0.5rem;">
                            <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Username</label>
                            <input type="text" id="eu_username" class="input" value="${Utils.escapeHtml(user.username)}" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                        <div class="form-group" style="display: flex; flex-direction: column; gap: 0.5rem;">
                            <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Email Address</label>
                            <input type="email" id="eu_email" class="input" value="${Utils.escapeHtml(user.email)}" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border);">
                        </div>
                        <div class="form-group" style="display: flex; flex-direction: column; gap: 0.5rem;">
                            <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Role</label>
                            ${roleInputHtml}
                        </div>
                        <div id="eu_error" class="error-text hidden" style="color: var(--red); font-size: 13px; text-align: center;"></div>
                        <div class="modal-footer" style="padding-top: 1.5rem; margin-top: 0.5rem; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 1rem;">
                            <button type="button" class="btn cancel-btn" style="background: white; border: 1px solid var(--border); padding: 10px 20px;">Cancel</button>
                            <button type="submit" class="btn primary" style="padding: 10px 20px;">Save Changes</button>
                        </div>
                    </form>
                `,
                onOpen: (modalEl, close) => {
                    modalEl.querySelector('.cancel-btn').addEventListener('click', close);
                    const form = modalEl.querySelector('#edit-user-form');
                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();

                        const newUsername = modalEl.querySelector('#eu_username').value.trim();
                        const newEmail = modalEl.querySelector('#eu_email').value.trim();
                        const roleEl = modalEl.querySelector('#eu_role');
                        const newRole = isSelf ? user.role : (roleEl ? roleEl.value : user.role);

                        if (!isSelf && newRole !== user.role) {
                            const confirmRole = confirm(`You are changing this user's role from ${user.role} to ${newRole}. Continue?`);
                            if (!confirmRole) return;
                        }

                        const payload = {
                            username: newUsername,
                            email: newEmail
                        };
                        if (!isSelf && newRole) {
                            payload.role = newRole;
                        }

                        const errEl = modalEl.querySelector('#eu_error');
                        const btn = form.querySelector('button[type="submit"]');

                        try {
                            btn.disabled = true;
                            btn.innerHTML = 'Saving...';

                            await Api.put(`/users/${id}`, payload);
                            Utils.showToast("User updated successfully", "success");
                            this.loadUsers();
                            close();
                        } catch (err) {
                            errEl.textContent = err.message || "Failed to update user";
                            errEl.classList.remove('hidden');
                            btn.disabled = false;
                            btn.innerHTML = 'Save Changes';
                        }
                    });
                }
            });
        } catch (err) {
            Utils.showToast(err.message || "Failed to load user details", "error");
        }
    },

    showCreateModal() {
        const currentUser = Auth.getUser() || {};
        const isOwner = currentUser.role === 'Owner';

        let roleOptionsHtml = '';
        if (isOwner) {
            roleOptionsHtml = `
                <option value="Owner">Owner</option>
                <option value="Manager">Manager</option>
                <option value="Employee" selected>Employee</option>
                <option value="Supplier">Supplier</option>
            `;
        } else {
            roleOptionsHtml = `
                <option value="Employee" selected>Employee</option>
                <option value="Supplier">Supplier</option>
            `;
        }

        Modal.create({
            id: 'createUserModal',
            title: 'Create New User',
            content: `
                <form id="create-user-form" style="display: flex; flex-direction: column; gap: 1.25rem;">
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Username</label>
                        <input type="text" id="cu_username" class="input" placeholder="e.g. jdoe123" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Email Address</label>
                        <input type="email" id="cu_email" class="input" placeholder="e.g. john@example.com" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Initial Password</label>
                        <input type="password" id="cu_password" class="input" minlength="8" placeholder="Minimum 8 characters" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.5rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Assign Role</label>
                        <select id="cu_role" class="input" required style="width: 100%; padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--white);">
                            ${roleOptionsHtml}
                        </select>
                    </div>
                    <div id="cu_error" class="error-text hidden" style="color: var(--red); font-size: 13px; text-align: center;"></div>
                    <div class="modal-footer" style="padding-top: 1.5rem; margin-top: 0.5rem; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 1rem;">
                        <button type="button" class="btn cancel-btn" style="background: white; border: 1px solid var(--border); padding: 10px 20px;">Cancel</button>
                        <button type="submit" class="btn primary" style="padding: 10px 20px;">Create User</button>
                    </div>
                </form>
            `,
            onOpen: (modalEl, close) => {
                modalEl.querySelector('.cancel-btn').addEventListener('click', close);
                const form = modalEl.querySelector('#create-user-form');
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const payload = {
                        username: modalEl.querySelector('#cu_username').value.trim(),
                        email: modalEl.querySelector('#cu_email').value.trim(),
                        password: modalEl.querySelector('#cu_password').value,
                        role: modalEl.querySelector('#cu_role').value
                    };
                    
                    const errEl = modalEl.querySelector('#cu_error');
                    const btn = form.querySelector('button[type="submit"]');
                    
                    try {
                        btn.disabled = true;
                        btn.innerHTML = 'Creating...';
                        
                        await Api.post('/users/', payload);
                        Utils.showToast("User created successfully", "success");
                        this.page = 1;
                        this.loadUsers();
                        close();
                    } catch (err) {
                        errEl.textContent = err.message || "Failed to create user";
                        errEl.classList.remove('hidden');
                        btn.disabled = false;
                        btn.innerHTML = 'Create User';
                    }
                });
            }
        });
    }
};
