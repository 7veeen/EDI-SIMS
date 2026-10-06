// categories.js

App.pages['categories'] = {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    search: '',
    sortBy: 'category_id',
    sortOrder: 'asc',
    debounceTimer: null,

    render() {
        const container = document.createElement('div');
        const user = Auth.getUser();
        const canManage = user && ['Owner', 'Manager'].includes(user.role);
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">INVENTORY</span>
                    <h1>Categories 🏷️</h1>
                    <p>Organize your products into catalog departments.</p>
                </div>
                <div class="header-actions">
                    <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="categories-search" placeholder="Search categories..." style="background: transparent;">
                    </div>
                    ${canManage ? `
                        <button class="btn primary" id="btn-create-category">
                            <i class='bx bx-plus'></i> New Category
                        </button>
                    ` : ''}
                </div>
            </div>
            
            <div class="card table-responsive" style="margin-top: 20px; overflow: hidden;">
                <table class="table" id="categories-table">
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="category_id">ID <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="category_name">NAME <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="description">DESCRIPTION <i class='bx bx-sort'></i></th>
                            <th style="text-align: right;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="4" style="text-align: center; padding: 28px; color: var(--text-secondary);">Loading categories...</td></tr>
                    </tbody>
                </table>
                <div class="table-pagination" id="categories-pagination">
                    <div class="pagination-info" id="categories-pagination-info">Showing 0 of 0 categories</div>
                    <div class="pagination-controls" id="categories-pagination-controls"></div>
                </div>
            </div>
        `;
        return container;
    },

    async init() {
        this.page = 1;
        this.search = '';
        this.sortBy = 'category_id';
        this.sortOrder = 'asc';

        this.setupSortingHeaders();
        this.loadCategories();
        
        const searchInput = document.getElementById('categories-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.search = e.target.value.trim();
                    this.page = 1;
                    this.loadCategories();
                }, 300);
            });
        }

        const createBtn = document.getElementById('btn-create-category');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.showCategoryModal());
        }
    },

    setupSortingHeaders() {
        const ths = document.querySelectorAll('#categories-table th.sortable');
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
                this.loadCategories();
            });
        });
        this.updateSortHeaderIcons();
    },

    updateSortHeaderIcons() {
        const ths = document.querySelectorAll('#categories-table th.sortable');
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

    async loadCategories() {
        const tbody = document.querySelector('#categories-table tbody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 24px; color: var(--text-secondary);"><i class='bx bx-loader-alt bx-spin' style='margin-right: 6px; font-size: 16px;'></i> Loading categories...</td></tr>`;

        try {
            let url = `/categories/?page=${this.page}&page_size=${this.pageSize}&sort_by=${encodeURIComponent(this.sortBy)}&sort_order=${this.sortOrder}`;
            if (this.search) {
                url += `&search=${encodeURIComponent(this.search)}`;
            }
            
            const data = await Api.get(url);
            const categories = data.categories || [];
            this.total = data.total !== undefined ? data.total : categories.length;
            this.totalPages = data.total_pages || Math.max(1, Math.ceil(this.total / this.pageSize));
            
            if (categories.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 28px; color: var(--text-secondary);">No categories found.</td></tr>`;
                this.renderPagination();
                return;
            }

            const user = Auth.getUser();
            const canManage = user && ['Owner', 'Manager'].includes(user.role);

            tbody.innerHTML = categories.map(c => `
                <tr>
                    <td><strong>#${c.category_id}</strong></td>
                    <td><strong>${Utils.escapeHtml(c.category_name)}</strong></td>
                    <td style="color: var(--text-secondary);">${Utils.escapeHtml(c.description || '-')}</td>
                    <td style="text-align: right;">
                        ${canManage ? `
                            <div class="table-actions" style="justify-content: flex-end;">
                                <button class="btn-icon text-primary" onclick="App.pages['categories'].showCategoryModal(${c.category_id}, '${Utils.escapeHtml(c.category_name)}', '${Utils.escapeHtml(c.description || '')}')" title="Edit Category">
                                    <i class='bx bx-edit'></i>
                                </button>
                                <button class="btn-icon text-danger" onclick="App.pages['categories'].deleteCategory(${c.category_id}, '${Utils.escapeHtml(c.category_name)}')" title="Delete Category">
                                    <i class='bx bx-trash'></i>
                                </button>
                            </div>
                        ` : `
                            <span class="protected-badge">Read-Only</span>
                        `}
                    </td>
                </tr>
            `).join('');

            this.renderPagination();
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-danger" style="text-align: center; padding: 24px;">Failed to load categories: ${Utils.escapeHtml(error.message || 'Error')}</td></tr>`;
            this.renderPagination();
        }
    },

    renderPagination() {
        const infoEl = document.getElementById('categories-pagination-info');
        const controlsEl = document.getElementById('categories-pagination-controls');
        if (!infoEl || !controlsEl) return;

        if (this.total === 0) {
            infoEl.textContent = 'Showing 0 categories';
            controlsEl.innerHTML = '';
            return;
        }

        const start = (this.page - 1) * this.pageSize + 1;
        const end = Math.min(this.page * this.pageSize, this.total);
        infoEl.textContent = `Showing ${start}–${end} of ${this.total} categories`;

        let html = `
            <button class="pagination-btn" ${this.page <= 1 ? 'disabled' : ''} onclick="App.pages['categories'].goToPage(${this.page - 1})">
                <i class='bx bx-chevron-left'></i> Previous
            </button>
        `;

        for (let p = 1; p <= this.totalPages; p++) {
            if (p === 1 || p === this.totalPages || (p >= this.page - 1 && p <= this.page + 1)) {
                html += `
                    <button class="pagination-btn ${p === this.page ? 'active' : ''}" onclick="App.pages['categories'].goToPage(${p})">
                        ${p}
                    </button>
                `;
            } else if (p === this.page - 2 || p === this.page + 2) {
                html += `<span style="padding: 0 4px; color: var(--text-light);">...</span>`;
            }
        }

        html += `
            <button class="pagination-btn" ${this.page >= this.totalPages ? 'disabled' : ''} onclick="App.pages['categories'].goToPage(${this.page + 1})">
                Next <i class='bx bx-chevron-right'></i>
            </button>
        `;

        controlsEl.innerHTML = html;
    },

    goToPage(pageNum) {
        if (pageNum < 1 || pageNum > this.totalPages || pageNum === this.page) return;
        this.page = pageNum;
        this.loadCategories();
    },

    async deleteCategory(id, categoryName) {
        const confirmMsg = categoryName ? `Are you sure you want to delete category "${categoryName}"?` : 'Are you sure you want to delete this category?';
        if (!confirm(confirmMsg)) return;

        try {
            await Api.delete(`/categories/${id}`);
            Utils.showToast("Category deleted successfully", "success");
            this.loadCategories();
        } catch (error) {
            Utils.showToast(error.message || "Failed to delete category", "error");
        }
    },

    showCategoryModal(id = null, name = '', description = '') {
        const isEdit = !!id;
        
        const modalHtml = `
            <div style="display: flex; flex-direction: column; gap: 1rem;">
                <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                    <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Category Name</label>
                    <input type="text" id="modal-cat-name" class="input" value="${Utils.escapeHtml(name)}" placeholder="e.g. Office Supplies" required style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);">
                </div>
                <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                    <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Description</label>
                    <textarea id="modal-cat-desc" class="input" rows="3" placeholder="Optional category description..." style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); font-family: inherit;">${Utils.escapeHtml(description)}</textarea>
                </div>
            </div>
        `;

        Modal.show({
            title: isEdit ? 'Edit Category' : 'Create Category',
            content: modalHtml,
            saveText: isEdit ? 'Save Changes' : 'Create Category',
            onSave: async (container) => {
                const catName = container.querySelector('#modal-cat-name').value.trim();
                const catDesc = container.querySelector('#modal-cat-desc').value.trim();

                if (!catName) {
                    throw new Error("Category name is required");
                }

                const payload = {
                    category_name: catName,
                    description: catDesc
                };

                if (isEdit) {
                    await Api.put(`/categories/${id}`, payload);
                    Utils.showToast("Category updated successfully", "success");
                } else {
                    await Api.post('/categories/', payload);
                    Utils.showToast("Category created successfully", "success");
                    this.page = 1;
                }

                this.loadCategories();
            }
        });
    }
};
