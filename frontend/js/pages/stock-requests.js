// stock-requests.js

App.pages['stock-requests'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">WORKSPACE</span>
                    <h1>Stock Requests</h1>
                    <p>Review requests and submit quotation details.</p>
                </div>
                <button class="btn" style="background: white; border: 1px solid var(--border); color: var(--text);" onclick="App.pages['stock-requests'].exportCSV()">
                    <i class='bx bx-export'></i> Export CSV
                </button>
            </div>

            <div class="actions-bar glass-panel" style="padding: 1rem; border-radius: 8px;">
                <div class="search-box input-with-icon" style="flex: 1;">
                    <i class='bx bx-search'></i>
                    <input type="text" id="search-requests" placeholder="Search request, product..." style="width: 100%;" oninput="App.pages['stock-requests'].filterData()">
                </div>
                <div style="display: flex; gap: 1rem;">
                    <select id="filter-status-requests" class="input-with-icon" style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px;" onchange="App.pages['stock-requests'].filterData()">
                        <option value="">All Status</option>
                        <option value="Pending">Pending</option>
                        <option value="Accepted">Accepted</option>
                        <option value="Delivered">Delivered</option>
                        <option value="Rejected">Rejected</option>
                    </select>
                </div>
            </div>

            <div class="card table-responsive" style="margin-top: 1.5rem;">
                <div style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 13px; font-weight: 600;"><span id="requests-count">0</span> Requests</span>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="width: 40px;"><input type="checkbox"></th>
                            <th>REQUEST ID</th>
                            <th>PRODUCT</th>
                            <th>QUANTITY</th>
                            <th>REQUIRED DATE</th>
                            <th>PRIORITY</th>
                            <th>STATUS</th>
                            <th>ACTION</th>
                        </tr>
                    </thead>
                    <tbody id="stock-requests-tbody">
                        <tr><td colspan="8" style="text-align:center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;

        let modalContainer = document.getElementById('quotation-modal-container');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'quotation-modal-container';
            document.body.appendChild(modalContainer);
        }

        this.fetchStockRequests(container.querySelector('#stock-requests-tbody'));

        return container;
    },

    async fetchStockRequests(tbody) {
        try {
            // Using the team2 purchase-orders endpoint for now
            const response = await Api.get('/purchase-orders/');
            tbody.innerHTML = '';
            
            if (response.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No stock requests found.</td></tr>';
                return;
            }

            this.requestsData = response;

            this.requestsData = response;
            this.filterData();
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:red;">Error loading requests</td></tr>';
        }
    },
    
    filterData() {
        const tbody = document.querySelector('#stock-requests-tbody');
        if (!tbody || !this.requestsData) return;
        
        const search = (document.getElementById('search-requests')?.value || '').toLowerCase();
        const status = document.getElementById('filter-status-requests')?.value || '';
        
        const filtered = this.requestsData.filter(req => {
            const matchSearch = (req.product_name || '').toLowerCase().includes(search) || 
                                req.purchase_order_id.toString().includes(search);
            const matchStatus = status ? req.status === status : true;
            return matchSearch && matchStatus;
        });
        
        const countSpan = document.getElementById('requests-count');
        if (countSpan) countSpan.textContent = filtered.length;
        
        tbody.innerHTML = '';
        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No stock requests found matching filters.</td></tr>';
            return;
        }
        
        filtered.forEach(req => {
            const tr = document.createElement('tr');
            let priority = 'Medium';
            let priorityColor = 'var(--yellow)';
            let priorityBg = 'var(--yellow-light)';
            
            const statusColor = req.status === 'Pending' ? 'var(--yellow)' : (req.status === 'Accepted' || req.status === 'Delivered' ? 'var(--green)' : 'var(--red)');
            const statusBg = req.status === 'Pending' ? 'var(--yellow-light)' : (req.status === 'Accepted' || req.status === 'Delivered' ? 'var(--green-light)' : 'var(--red-light)');

            tr.innerHTML = `
                <td><input type="checkbox"></td>
                <td>
                    <div style="font-weight: 600;">SR-${new Date(req.order_date).getFullYear()}-${req.purchase_order_id.toString().padStart(4, '0')}</div>
                    <div style="font-size: 12px; color: var(--text-light);">Received today</div>
                </td>
                <td>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 30px; height: 30px; border-radius: 6px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">
                            ${req.product_name ? req.product_name.substring(0,2).toUpperCase() : 'PR'}
                        </div>
                        <span>${req.product_name || 'Unknown Product'}</span>
                    </div>
                </td>
                <td>${req.quantity || 0} pcs</td>
                <td>
                    <div>${req.expected_delivery || 'N/A'}</div>
                    <div style="font-size: 11px; color: var(--red);">Action required</div>
                </td>
                <td><span class="badge" style="background: ${priorityBg}; color: ${priorityColor}; font-size: 11px !important;">${priority}</span></td>
                <td><span class="badge" style="background: ${statusBg}; color: ${statusColor}; font-size: 11px !important;">${req.status === 'Pending' ? 'Awaiting response' : req.status}</span></td>
                <td>
                    <button class="btn" style="background: var(--primary-light); color: var(--primary); padding: 5px 12px; font-size: 12px;" onclick="App.pages['stock-requests'].respond(${req.purchase_order_id})">Respond</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    },
    
    exportCSV() {
        if (!this.requestsData) return;
        let csv = 'Request ID,Product,Quantity,Required Date,Status\\n';
        this.requestsData.forEach(req => {
            csv += `SR-${new Date(req.order_date).getFullYear()}-${req.purchase_order_id.toString().padStart(4, '0')},${req.product_name},${req.quantity},${req.expected_delivery},${req.status}\n`;
        });
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.setAttribute('href', url);
        a.setAttribute('download', 'Stock_Requests.csv');
        a.click();
    },
    
    respond(id) {
        if (!this.requestsData) return;
        const req = this.requestsData.find(r => r.purchase_order_id === id);
        if (!req) return;

        const modalHtml = `
        <div class="modal glass-panel" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center;">
            <div class="card" style="width: 500px; padding: 2rem; border-radius: 12px; background: white;">
                <h3 style="margin-top: 0;">Submit Quotation</h3>
                <p style="color: var(--text-light); font-size: 13px; margin-bottom: 20px;">For Request ID: SR-${new Date(req.order_date || new Date()).getFullYear()}-${req.purchase_order_id.toString().padStart(4, '0')}</p>
                
                <div style="margin-bottom: 15px;">
                    <label style="display: block; font-size: 13px; margin-bottom: 5px;">Product</label>
                    <input type="text" value="${req.product_name}" disabled style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: #f9f9f9;">
                </div>
                <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <label style="display: block; font-size: 13px; margin-bottom: 5px;">Requested Qty</label>
                        <input type="text" value="${req.quantity}" disabled style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: #f9f9f9;">
                    </div>
                    <div style="flex: 1;">
                        <label style="display: block; font-size: 13px; margin-bottom: 5px;">Available Qty</label>
                        <input type="number" id="quotation-qty" value="${req.quantity}" min="1" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px;" oninput="App.pages['stock-requests'].calculateSubtotal()">
                    </div>
                </div>
                <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <label style="display: block; font-size: 13px; margin-bottom: 5px;">Unit Price (₹)</label>
                        <input type="number" id="quotation-price" min="0" step="0.01" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px;" oninput="App.pages['stock-requests'].calculateSubtotal()">
                    </div>
                    <div style="flex: 1;">
                        <label style="display: block; font-size: 13px; margin-bottom: 5px;">Subtotal (₹)</label>
                        <input type="text" id="quotation-subtotal" disabled style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: #f9f9f9;">
                    </div>
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; font-size: 13px; margin-bottom: 5px;">Valid Until</label>
                    <input type="date" id="quotation-valid" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px;">
                </div>
                
                <div style="display: flex; justify-content: flex-end; gap: 10px;">
                    <button class="btn" style="background: white; border: 1px solid var(--border);" onclick="document.getElementById('quotation-modal-container').innerHTML = ''">Cancel</button>
                    <button class="btn primary" onclick="App.pages['stock-requests'].submitQuotation(${req.product_id})">Submit Quotation</button>
                </div>
            </div>
        </div>
        `;
        document.getElementById('quotation-modal-container').innerHTML = modalHtml;
    },

    calculateSubtotal() {
        const qty = parseFloat(document.getElementById('quotation-qty').value) || 0;
        const price = parseFloat(document.getElementById('quotation-price').value) || 0;
        document.getElementById('quotation-subtotal').value = (qty * price).toFixed(2);
    },
    
    async submitQuotation(productId) {
        const qty = document.getElementById('quotation-qty').value;
        const price = document.getElementById('quotation-price').value;
        const valid = document.getElementById('quotation-valid').value;
        
        if (!qty || qty <= 0) return alert('Quantity must be greater than 0');
        if (!price || price < 0) return alert('Price must be valid');
        if (!valid) return alert('Validity date is required');
        
        try {
            await Api.post('/quotations/', {
                product_id: productId,
                quantity: qty,
                unit_price: price,
                valid_until: valid
            });
            document.getElementById('quotation-modal-container').innerHTML = '';
            if (window.showToast) {
                showToast('Quotation submitted successfully', 'success');
            } else {
                alert('Quotation submitted successfully');
            }
            this.fetchStockRequests(document.querySelector('#stock-requests-tbody'));
        } catch (error) {
            alert(error.message || 'Error submitting quotation');
        }
    }
};
