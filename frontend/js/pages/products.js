// products.js

App.pages['products'] = {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    search: '',
    categoryId: '',
    status: '',
    sortBy: 'product_id',
    sortOrder: 'asc',
    debounceTimer: null,

    render() {
        const container = document.createElement('div');
        const user = Auth.getUser();
        const canAdd = user && ['Owner', 'Manager'].includes(user.role);
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">INVENTORY</span>
                    <h1>Products 📦</h1>
                    <p>Manage your product catalog and reorder levels.</p>
                </div>
                <div class="header-actions">
                    <div class="header-filters">
                        <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border);">
                            <i class='bx bx-search'></i>
                            <input type="text" id="product-search" placeholder="Search by name or SKU..." style="background: transparent;">
                        </div>
                        <select id="product-category-filter" class="filter-select">
                            <option value="">All Categories</option>
                        </select>
                        <select id="product-status-filter" class="filter-select">
                            <option value="">All Statuses</option>
                            <option value="Active">Active</option>
                            <option value="Inactive">Inactive</option>
                        </select>
                    </div>
                    ${canAdd ? `
                        <button class="btn primary" id="btn-add-product">
                            <i class='bx bx-plus'></i> Add Product
                        </button>
                    ` : ''}
                </div>
            </div>
            
            <div class="card table-responsive" style="margin-top: 20px; overflow: hidden;">
                <table class="table" id="products-table">
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="product_id">ID <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="product_name">NAME <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="sku">SKU <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="category">CATEGORY <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="price">PRICE <i class='bx bx-sort'></i></th>
                            <th class="sortable" data-sort="status">STATUS <i class='bx bx-sort'></i></th>
                            <th style="text-align: right;">ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="7" style="text-align: center; padding: 28px; color: var(--text-secondary);">Loading products...</td></tr>
                    </tbody>
                </table>
                <div class="table-pagination" id="products-pagination">
                    <div class="pagination-info" id="products-pagination-info">Showing 0 of 0 products</div>
                    <div class="pagination-controls" id="products-pagination-controls"></div>
                </div>
            </div>
        `;
        return container;
    },

    async init() {
        this.page = 1;
        this.search = '';
        this.categoryId = '';
        this.status = '';
        this.sortBy = 'product_id';
        this.sortOrder = 'asc';

        this.setupSortingHeaders();
        this.loadCategoryFilter();
        this.loadProducts();

        const searchInput = document.getElementById('product-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.search = e.target.value.trim();
                    this.page = 1;
                    this.loadProducts();
                }, 300);
            });
        }

        const catFilter = document.getElementById('product-category-filter');
        if (catFilter) {
            catFilter.addEventListener('change', (e) => {
                this.categoryId = e.target.value;
                this.page = 1;
                this.loadProducts();
            });
        }

        const statusFilter = document.getElementById('product-status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.status = e.target.value;
                this.page = 1;
                this.loadProducts();
            });
        }

        const addBtn = document.getElementById('btn-add-product');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                this.showProductModal();
            });
        }
    },

    setupSortingHeaders() {
        const ths = document.querySelectorAll('#products-table th.sortable');
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
                this.loadProducts();
            });
        });
        this.updateSortHeaderIcons();
    },

    updateSortHeaderIcons() {
        const ths = document.querySelectorAll('#products-table th.sortable');
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

    async loadCategoryFilter() {
        const select = document.getElementById('product-category-filter');
        if (!select) return;
        try {
            const data = await Api.get('/categories/');
            const categories = data.categories || [];
            let optionsHtml = '<option value="">All Categories</option>';
            categories.forEach(c => {
                optionsHtml += `<option value="${c.category_id}">${Utils.escapeHtml(c.category_name)}</option>`;
            });
            select.innerHTML = optionsHtml;
        } catch (e) {
            // Keep default
        }
    },

    async loadProducts() {
        const tbody = document.querySelector('#products-table tbody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-secondary);"><i class='bx bx-loader-alt bx-spin' style='margin-right: 6px; font-size: 16px;'></i> Loading products...</td></tr>`;

        try {
            let url = `/products/?page=${this.page}&page_size=${this.pageSize}&sort_by=${encodeURIComponent(this.sortBy)}&sort_order=${this.sortOrder}`;
            if (this.search) {
                url += `&search=${encodeURIComponent(this.search)}`;
            }
            if (this.categoryId) {
                url += `&category_id=${encodeURIComponent(this.categoryId)}`;
            }
            if (this.status) {
                url += `&status=${encodeURIComponent(this.status)}`;
            }

            const data = await Api.get(url);
            const products = data.products || [];
            this.total = data.total !== undefined ? data.total : products.length;
            this.totalPages = data.total_pages || Math.max(1, Math.ceil(this.total / this.pageSize));
            
            if (products.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 28px; color: var(--text-secondary);">No products found matching your criteria.</td></tr>`;
                this.renderPagination();
                return;
            }

            const user = Auth.getUser();
            const canManage = user && ['Owner', 'Manager'].includes(user.role);

            tbody.innerHTML = products.map(p => {
                const formattedPrice = typeof p.price === 'number' ? `₹${p.price.toFixed(2)}` : `₹${parseFloat(p.price || 0).toFixed(2)}`;
                return `
                    <tr>
                        <td><strong>#${p.product_id}</strong></td>
                        <td><strong>${Utils.escapeHtml(p.product_name)}</strong></td>
                        <td><code>${Utils.escapeHtml(p.sku)}</code></td>
                        <td><span class="badge" style="background: #e2e8f0; color: #334155; font-weight: 500;">${Utils.escapeHtml(p.category_name || 'N/A')}</span></td>
                        <td><strong>${formattedPrice}</strong></td>
                        <td>
                            <span class="status-badge ${p.status === 'Active' ? 'status-active' : 'status-inactive'}">
                                ${p.status}
                            </span>
                        </td>
                        <td style="text-align: right;">
                            ${canManage ? `
                                <div class="action-buttons" style="justify-content: flex-end;">
                                    <button class="btn-icon text-primary" onclick="App.pages['products'].showProductModal(${p.product_id})" title="Edit Product">
                                        <i class='bx bx-edit'></i>
                                    </button>
                                    <button class="btn-icon text-danger" onclick="App.pages['products'].deleteProduct(${p.product_id}, '${Utils.escapeHtml(p.product_name)}')" title="Delete or Deactivate Product">
                                        <i class='bx bx-trash'></i>
                                    </button>
                                </div>
                            ` : `
                                <span class="protected-badge">Read-Only</span>
                            `}
                        </td>
                    </tr>
                `;
            }).join('');

            this.renderPagination();
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-danger" style="text-align: center; padding: 24px;">Failed to load products: ${Utils.escapeHtml(error.message || 'Error')}</td></tr>`;
            this.renderPagination();
        }
    },

    renderPagination() {
        const infoEl = document.getElementById('products-pagination-info');
        const controlsEl = document.getElementById('products-pagination-controls');
        if (!infoEl || !controlsEl) return;

        if (this.total === 0) {
            infoEl.textContent = 'Showing 0 products';
            controlsEl.innerHTML = '';
            return;
        }

        const start = (this.page - 1) * this.pageSize + 1;
        const end = Math.min(this.page * this.pageSize, this.total);
        infoEl.textContent = `Showing ${start}–${end} of ${this.total} products`;

        let html = `
            <button class="pagination-btn" ${this.page <= 1 ? 'disabled' : ''} onclick="App.pages['products'].goToPage(${this.page - 1})">
                <i class='bx bx-chevron-left'></i> Previous
            </button>
        `;

        for (let p = 1; p <= this.totalPages; p++) {
            if (p === 1 || p === this.totalPages || (p >= this.page - 1 && p <= this.page + 1)) {
                html += `
                    <button class="pagination-btn ${p === this.page ? 'active' : ''}" onclick="App.pages['products'].goToPage(${p})">
                        ${p}
                    </button>
                `;
            } else if (p === this.page - 2 || p === this.page + 2) {
                html += `<span style="padding: 0 4px; color: var(--text-light);">...</span>`;
            }
        }

        html += `
            <button class="pagination-btn" ${this.page >= this.totalPages ? 'disabled' : ''} onclick="App.pages['products'].goToPage(${this.page + 1})">
                Next <i class='bx bx-chevron-right'></i>
            </button>
        `;

        controlsEl.innerHTML = html;
    },

    goToPage(pageNum) {
        if (pageNum < 1 || pageNum > this.totalPages || pageNum === this.page) return;
        this.page = pageNum;
        this.loadProducts();
    },
    
    async loadCategoriesForSelect(selectElement, selectedId = null) {
        try {
            const data = await Api.get('/categories/');
            const categories = data.categories || [];
            selectElement.innerHTML = '<option value="">Select Category</option>' + 
                categories.map(c => `<option value="${c.category_id}" ${c.category_id === selectedId ? 'selected' : ''}>${Utils.escapeHtml(c.category_name)}</option>`).join('');
        } catch (e) {
            selectElement.innerHTML = '<option value="">Failed to load categories</option>';
        }
    },

    async showProductModal(productId = null) {
        let product = null;
        if (productId) {
            try {
                const data = await Api.get(`/products/${productId}`);
                product = data.product;
            } catch (err) {
                Utils.showToast("Failed to load product details", "error");
                return;
            }
        }

        const isEdit = !!product;

        const modalHtml = `
            <div style="display: flex; flex-direction: column; gap: 1rem;">
                <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                    <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Product Name</label>
                    <input type="text" id="modal-product-name" class="input" value="${product ? Utils.escapeHtml(product.product_name) : ''}" placeholder="e.g. Ergonomic Office Chair" required style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);">
                </div>
                <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                    <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">SKU Code</label>
                    <input type="text" id="modal-product-sku" class="input" value="${product ? Utils.escapeHtml(product.sku) : ''}" placeholder="e.g. FUR-CHR-001" required style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);">
                </div>
                <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                    <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Category</label>
                    <select id="modal-product-category" class="input" required style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--white);">
                        <option value="">Loading categories...</option>
                    </select>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Selling Price (₹)</label>
                        <input type="number" step="0.01" min="0" id="modal-product-price" class="input" value="${product ? product.price : '0.00'}" required style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Reorder Level</label>
                        <input type="number" min="0" step="1" id="modal-product-reorder" class="input" value="${product ? product.reorder_level : '10'}" required style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);">
                    </div>
                </div>
                ${!isEdit ? `
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Initial Stock Quantity</label>
                        <input type="number" min="0" step="1" id="modal-product-initial-stock" class="input" value="0" required style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);">
                        <span style="font-size: 11.5px; color: var(--text-light);">Starting stock count to initialize in Inventory.</span>
                    </div>
                ` : `
                    <div class="form-group" style="display: flex; flex-direction: column; gap: 0.35rem;">
                        <label style="font-size: 13px; font-weight: 600; color: var(--text-secondary);">Status</label>
                        <select id="modal-product-status" class="input" style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--white);">
                            <option value="Active" ${product.status === 'Active' ? 'selected' : ''}>Active</option>
                            <option value="Inactive" ${product.status === 'Inactive' ? 'selected' : ''}>Inactive</option>
                        </select>
                    </div>
                `}
            </div>
        `;

        Modal.show({
            title: isEdit ? 'Edit Product' : 'Add New Product',
            content: modalHtml,
            saveText: isEdit ? 'Save Changes' : 'Create Product',
            onSave: async (container) => {
                const name = container.querySelector('#modal-product-name').value.trim();
                const sku = container.querySelector('#modal-product-sku').value.trim();
                const catId = container.querySelector('#modal-product-category').value;
                const price = parseFloat(container.querySelector('#modal-product-price').value);
                const reorder = parseInt(container.querySelector('#modal-product-reorder').value);
                
                if (!name || !sku || !catId) {
                    throw new Error("Name, SKU, and Category are required");
                }
                if (isNaN(price) || price < 0) {
                    throw new Error("Price must be a valid number >= 0");
                }
                if (isNaN(reorder) || reorder < 0) {
                    throw new Error("Reorder level must be an integer >= 0");
                }

                const payload = {
                    product_name: name,
                    sku: sku,
                    category_id: parseInt(catId),
                    price: price,
                    reorder_level: reorder
                };

                if (isEdit) {
                    payload.status = container.querySelector('#modal-product-status').value;
                    await Api.put(`/products/${productId}`, payload);
                    Utils.showToast("Product updated successfully", "success");
                } else {
                    const initialStockVal = parseInt(container.querySelector('#modal-product-initial-stock')?.value || 0);
                    payload.initial_stock = isNaN(initialStockVal) ? 0 : Math.max(0, initialStockVal);
                    await Api.post('/products/', payload);
                    Utils.showToast("Product created successfully", "success");
                    this.page = 1;
                }
                
                this.loadProducts();
            }
        });
        
        this.loadCategoriesForSelect(document.getElementById('modal-product-category'), product ? product.category_id : null);
    },

    async deleteProduct(productId, productName) {
        const confirmMsg = productName ? `Are you sure you want to delete product "${productName}"?` : 'Are you sure you want to delete this product?';
        if (!confirm(confirmMsg)) return;

        try {
            const res = await Api.delete(`/products/${productId}`);
            if (res && res.status === 'Inactive') {
                Utils.showToast(res.message || "Product has existing records and was deactivated to preserve data integrity.", "warning");
            } else {
                Utils.showToast(res && res.message ? res.message : "Product deleted successfully.", "success");
            }
            this.loadProducts();
        } catch (error) {
            Utils.showToast(error.message || "Failed to delete product", "error");
        }
    }
};
