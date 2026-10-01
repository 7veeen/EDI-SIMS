// products.js

App.pages['products'] = {
    render() {
        const container = document.createElement('div');
        
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">INVENTORY</span>
                    <h1>Products 📦</h1>
                    <p>Manage your product catalog.</p>
                </div>
                <div class="header-actions">
                    <div class="global-search" style="margin: 0; background: var(--white); border: 1px solid var(--border);">
                        <i class='bx bx-search'></i>
                        <input type="text" id="product-search" placeholder="Search products..." style="background: transparent;">
                    </div>
                    <button class="btn primary" id="btn-add-product">
                        <i class='bx bx-plus'></i> Add Product
                    </button>
                </div>
            </div>
            
            <div class="card table-responsive" style="margin-top: 20px;">
                <table class="table" id="products-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>NAME</th>
                            <th>SKU</th>
                            <th>CATEGORY</th>
                            <th>PRICE</th>
                            <th>STATUS</th>
                            <th>ACTIONS</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--text-secondary);">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;
        return container;
    },

    async init() {
        this.loadProducts();

        const searchInput = document.getElementById('product-search');
        if (searchInput) {
            let timeout = null;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.loadProducts(e.target.value);
                }, 300);
            });
        }

        const addBtn = document.getElementById('btn-add-product');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                this.showProductModal();
            });
            
            // Hide add button if supplier
            const user = Auth.getUser();
            if (user && user.role === 'Supplier') {
                addBtn.style.display = 'none';
            }
        }
    },

    async loadProducts(search = '') {
        const tbody = document.querySelector('#products-table tbody');
        try {
            let url = '/products/';
            if (search) {
                url += `?search=${encodeURIComponent(search)}`;
            }
            const data = await Api.get(url);
            
            if (!data.products || data.products.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center;">No products found.</td></tr>`;
                return;
            }

            const user = Auth.getUser();
            const canEdit = user && ['Owner', 'Manager', 'Employee'].includes(user.role);
            const canDelete = user && ['Owner', 'Manager'].includes(user.role);

            tbody.innerHTML = data.products.map(p => `
                <tr>
                    <td>#${p.product_id}</td>
                    <td><strong>${Utils.escapeHtml(p.product_name)}</strong></td>
                    <td>${Utils.escapeHtml(p.sku)}</td>
                    <td><span class="badge" style="background: #e0e0e0; color: #333;">${Utils.escapeHtml(p.category_name || 'N/A')}</span></td>
                    <td>₹${p.price.toFixed(2)}</td>
                    <td>
                        <span class="status-badge ${p.status === 'Active' ? 'status-active' : 'status-inactive'}">
                            ${p.status}
                        </span>
                    </td>
                    <td>
                        <div class="action-buttons">
                            ${canEdit ? `<button class="btn-icon text-primary" onclick="App.pages['products'].showProductModal(${p.product_id})" title="Edit"><i class='bx bx-edit'></i></button>` : ''}
                            ${canDelete ? `<button class="btn-icon text-danger" onclick="App.pages['products'].deleteProduct(${p.product_id})" title="Delete"><i class='bx bx-trash'></i></button>` : ''}
                        </div>
                    </td>
                </tr>
            `).join('');
            
        } catch (error) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-danger" style="text-align: center;">Failed to load products: ${error.message}</td></tr>`;
        }
    },
    
    async loadCategoriesForSelect(selectElement, selectedId = null) {
        try {
            const data = await Api.get('/categories/');
            selectElement.innerHTML = '<option value="">Select Category</option>' + 
                data.map(c => `<option value="${c.category_id}" ${c.category_id === selectedId ? 'selected' : ''}>${Utils.escapeHtml(c.category_name)}</option>`).join('');
        } catch (e) {
            selectElement.innerHTML = '<option value="">Failed to load categories</option>';
        }
    },

    async showProductModal(productId = null) {
        let product = null;
        if (productId) {
            // we can fetch or just get from DOM, but let's fetch to be safe, wait there's no GET /products/:id 
            // I'll quickly fetch all and find it
            const data = await Api.get('/products/');
            product = data.products.find(p => p.product_id === productId);
            if (!product) return;
        }

        const modalHtml = `
            <div class="form-group">
                <label>Product Name</label>
                <input type="text" id="modal-product-name" class="input" value="${product ? Utils.escapeHtml(product.product_name) : ''}" required>
            </div>
            <div class="form-group">
                <label>SKU</label>
                <input type="text" id="modal-product-sku" class="input" value="${product ? Utils.escapeHtml(product.sku) : ''}" required>
            </div>
            <div class="form-group">
                <label>Category</label>
                <select id="modal-product-category" class="input" required>
                    <option value="">Loading...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Price (₹)</label>
                <input type="number" step="0.01" id="modal-product-price" class="input" value="${product ? product.price : '0.00'}" required>
            </div>
            <div class="form-group">
                <label>Reorder Level</label>
                <input type="number" id="modal-product-reorder" class="input" value="${product ? product.reorder_level : '10'}" required>
            </div>
            ${product ? `
            <div class="form-group">
                <label>Status</label>
                <select id="modal-product-status" class="input">
                    <option value="Active" ${product.status === 'Active' ? 'selected' : ''}>Active</option>
                    <option value="Inactive" ${product.status === 'Inactive' ? 'selected' : ''}>Inactive</option>
                </select>
            </div>
            ` : ''}
        `;

        Modal.show({
            title: product ? 'Edit Product' : 'Add Product',
            content: modalHtml,
            onSave: async (container) => {
                const name = container.querySelector('#modal-product-name').value;
                const sku = container.querySelector('#modal-product-sku').value;
                const catId = container.querySelector('#modal-product-category').value;
                const price = parseFloat(container.querySelector('#modal-product-price').value);
                const reorder = parseInt(container.querySelector('#modal-product-reorder').value);
                
                if (!name || !sku || !catId) {
                    throw new Error("Name, SKU, and Category are required");
                }

                const payload = {
                    product_name: name,
                    sku: sku,
                    category_id: parseInt(catId),
                    price: price,
                    reorder_level: reorder
                };

                if (product) {
                    payload.status = container.querySelector('#modal-product-status').value;
                    await Api.put(`/products/${productId}`, payload);
                } else {
                    await Api.post('/products/', payload);
                }
                
                this.loadProducts(document.getElementById('product-search').value);
            }
        });
        
        this.loadCategoriesForSelect(document.getElementById('modal-product-category'), product ? product.category_id : null);
    },

    async deleteProduct(productId) {
        if (!confirm('Are you sure you want to delete this product?')) return;

        try {
            await Api.delete(`/products/${productId}`);
            Utils.showToast("Product deleted successfully", "success");
            this.loadProducts(document.getElementById('product-search')?.value);
        } catch (error) {
            Utils.showToast(error.message, "error");
        }
    }
};
