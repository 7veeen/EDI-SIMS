// categories.js

App.pages['categories'] = {
    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">INVENTORY</span>
                    <h1>Categories 🏷️</h1>
                    <p>Organize your products.</p>
                </div>
                <div class="header-actions">
                    <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="categories-search" placeholder="Search categories..." style="background: transparent;">
                    </div>
                    <button class="btn primary" id="btn-create-category">
                        <i class='bx bx-plus'></i> New Category
                    </button>
                </div>
            </div>
            
            <div class="card table-responsive" style="margin-top: 20px;">
                <table class="table" id="categories-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>NAME</th>
                            <th>DESCRIPTION</th>
                            <th>ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="4" style="text-align: center; padding: 24px; color: var(--text-secondary);">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    },

    async init() {
        const user = Auth.getUser();
        if (user && (user.role === 'Employee' || user.role === 'Supplier')) {
            document.getElementById('btn-create-category').style.display = 'none';
        }

        this.loadCategories();
        
        document.getElementById('categories-search').addEventListener('input', (e) => {
            this.loadCategories(e.target.value);
        });

        document.getElementById('btn-create-category').addEventListener('click', () => this.showCategoryModal());
    },

    async loadCategories(search = '') {
        const tbody = document.querySelector('#categories-table tbody');
        try {
            let url = '/categories/';
            if (search) url += `?search=${encodeURIComponent(search)}`;
            
            const data = await Api.get(url);
            const categories = data.categories || [];
            
            if (categories.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align: center;">No categories found.</td></tr>`;
                return;
            }

            const user = Auth.getUser();
            const canEdit = user && (user.role === 'Owner' || user.role === 'Manager');

            tbody.innerHTML = categories.map(c => `
                <tr>
                    <td>#${c.category_id}</td>
                    <td><strong>${Utils.escapeHtml(c.category_name)}</strong></td>
                    <td>${Utils.escapeHtml(c.description || '-')}</td>
                    <td>
                        ${canEdit ? `
                        <div class="table-actions">
                            <button class="btn-icon text-primary" onclick="App.pages['categories'].showCategoryModal(${c.category_id}, '${Utils.escapeHtml(c.category_name)}', '${Utils.escapeHtml(c.description || '')}')" title="Edit">
                                <i class='bx bx-edit'></i>
                            </button>
                            <button class="btn-icon text-danger" onclick="App.pages['categories'].deleteCategory(${c.category_id})" title="Delete">
                                <i class='bx bx-trash'></i>
                            </button>
                        </div>
                        ` : '-'}
                    </td>
                </tr>
            `).join('');
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-danger" style="text-align: center;">Failed to load categories: ${error.message}</td></tr>`;
        }
    },

    async deleteCategory(id) {
        if (confirm('Are you sure you want to delete this category?')) {
            try {
                await Api.delete(`/categories/${id}`);
                Utils.showToast("Category deleted successfully");
                this.loadCategories(document.getElementById('categories-search').value);
            } catch (error) {
                Utils.showToast(error.message, "error");
            }
        }
    },

    showCategoryModal(id = null, name = '', description = '') {
        const isEdit = !!id;
        
        Modal.create({
            id: 'categoryModal',
            title: isEdit ? 'Edit Category' : 'Create Category',
            content: `
                <form id="category-form">
                    <div class="form-group">
                        <label>Category Name</label>
                        <input type="text" id="cat_name" value="${name}" required>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="cat_desc" rows="3">${description}</textarea>
                    </div>
                    <div id="cat_error" class="error-text hidden"></div>
                    <div class="modal-footer" style="padding-top: 1rem; border-top: 1px solid var(--border)">
                        <button type="button" class="btn btn-outline cancel-btn">Cancel</button>
                        <button type="submit" class="btn btn-primary">${isEdit ? 'Save Changes' : 'Create'}</button>
                    </div>
                </form>
            `,
            onOpen: (modalEl, close) => {
                modalEl.querySelector('.cancel-btn').addEventListener('click', close);
                const form = modalEl.querySelector('#category-form');
                
                form.addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const payload = {
                        category_name: modalEl.querySelector('#cat_name').value,
                        description: modalEl.querySelector('#cat_desc').value
                    };
                    
                    const errEl = modalEl.querySelector('#cat_error');
                    const btn = form.querySelector('button[type="submit"]');
                    
                    try {
                        btn.disabled = true;
                        btn.innerHTML = 'Saving...';
                        
                        if (isEdit) {
                            await Api.put(`/categories/${id}`, payload);
                        } else {
                            await Api.post('/categories/', payload);
                        }
                        
                        Utils.showToast(`Category ${isEdit ? 'updated' : 'created'} successfully`);
                        this.loadCategories();
                        close();
                    } catch (err) {
                        errEl.textContent = err.message;
                        errEl.classList.remove('hidden');
                        btn.disabled = false;
                        btn.innerHTML = isEdit ? 'Save Changes' : 'Create';
                    }
                });
            }
        });
    }
};
