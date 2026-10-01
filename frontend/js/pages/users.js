// users.js

App.pages['users'] = {
    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">ADMINISTRATION</span>
                    <h1>User Management</h1>
                    <p>Manage system access and roles.</p>
                </div>
                <div class="header-actions">
                    <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="users-search" placeholder="Search users..." style="background: transparent;">
                    </div>
                    <button class="btn primary" id="btn-create-user">
                        <i class='bx bx-plus'></i> New User
                    </button>
                </div>
            </div>
            
            <div class="card table-responsive" style="margin-top: 20px;">
                <table class="table" id="users-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>USERNAME</th>
                            <th>EMAIL</th>
                            <th>ROLE</th>
                            <th>STATUS</th>
                            <th>ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-secondary);">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    },

    async init() {
        this.loadUsers();
        
        document.getElementById('users-search').addEventListener('input', (e) => {
            // Simple debounce could be added here
            this.loadUsers(e.target.value);
        });

        document.getElementById('btn-create-user').addEventListener('click', () => this.showCreateModal());
    },

    async loadUsers(search = '') {
        const tbody = document.querySelector('#users-table tbody');
        try {
            let url = '/users/';
            if (search) url += `?search=${encodeURIComponent(search)}`;
            
            const data = await Api.get(url);
            
            if (!data.users || data.users.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center;">No users found.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.users.map(u => `
                <tr>
                    <td>#${u.user_id}</td>
                    <td>${Utils.escapeHtml(u.username)}</td>
                    <td>${Utils.escapeHtml(u.email)}</td>
                    <td><span class="badge" style="position: relative; top: 0; background: var(--primary)">${u.role}</span></td>
                    <td>
                        <span class="status-badge ${u.status === 'Active' ? 'status-active' : 'status-inactive'}">
                            ${u.status}
                        </span>
                    </td>
                    <td>
                        <div class="table-actions">
                            <button class="btn-icon text-warning" onclick="App.pages['users'].toggleStatus(${u.user_id}, '${u.status}')" title="Toggle Status">
                                <i class='bx ${u.status === 'Active' ? 'bx-check-circle' : 'bx-block'}'></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-danger" style="text-align: center;">Failed to load users: ${error.message}</td></tr>`;
        }
    },

    async toggleStatus(id, currentStatus) {
        const newStatus = currentStatus === 'Active' ? 'Inactive' : 'Active';
        try {
            await Api.put(`/users/${id}/status`, { status: newStatus });
            Utils.showToast(`User status updated to ${newStatus}`);
            this.loadUsers(document.getElementById('users-search').value);
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    },

    showCreateModal() {
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
                            <option value="Manager">Manager</option>
                            <option value="Employee">Employee</option>
                            <option value="Supplier">Supplier</option>
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
                const currentUser = Auth.getUser();
                if (currentUser && currentUser.role === 'Manager') {
                    // Manager cannot create Manager
                    modalEl.querySelector('#cu_role').querySelector('option[value="Manager"]').remove();
                }

                modalEl.querySelector('.cancel-btn').addEventListener('click', close);
                const form = modalEl.querySelector('#create-user-form');
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const payload = {
                        username: modalEl.querySelector('#cu_username').value,
                        email: modalEl.querySelector('#cu_email').value,
                        password: modalEl.querySelector('#cu_password').value,
                        role: modalEl.querySelector('#cu_role').value
                    };
                    
                    const errEl = modalEl.querySelector('#cu_error');
                    
                    try {
                        const btn = form.querySelector('button[type="submit"]');
                        btn.disabled = true;
                        btn.innerHTML = 'Creating...';
                        
                        await Api.post('/users/', payload);
                        Utils.showToast("User created successfully");
                        this.loadUsers();
                        close();
                    } catch (err) {
                        errEl.textContent = err.message;
                        errEl.classList.remove('hidden');
                        form.querySelector('button[type="submit"]').disabled = false;
                        form.querySelector('button[type="submit"]').innerHTML = 'Create User';
                    }
                });
            }
        });
    }
};
