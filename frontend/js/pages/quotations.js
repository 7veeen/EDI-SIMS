// quotations.js

App.pages['quotations'] = {
    render() {
        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">WORKSPACE</span>
                    <h1>Quotations</h1>
                    <p>Manage pricing, GST and quotation responses.</p>
                </div>
                <button class="btn primary" onclick="window.location.hash = 'stock-requests'">
                    <i class='bx bx-plus'></i> New Quotation
                </button>
            </div>

            <div class="actions-bar glass-panel" style="margin-top: 1.5rem; padding: 1rem; border-radius: 8px; display: flex; gap: 1rem;">
                <div class="search-box input-with-icon" style="flex: 1;">
                    <i class='bx bx-search'></i>
                    <input type="text" id="search-quotations" placeholder="Search product..." style="width: 100%;" oninput="App.pages['quotations'].filterData()">
                </div>
                <select id="filter-status-quotations" class="input-with-icon" style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 6px;" onchange="App.pages['quotations'].filterData()">
                    <option value="">All Status</option>
                    <option value="Pending">Pending</option>
                    <option value="Under Review">Under Review</option>
                    <option value="Accepted">Accepted</option>
                    <option value="Expired">Expired</option>
                </select>
            </div>

            <div class="stats-grid" style="margin-top: 1.5rem; display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem;">
                <!-- Drafts -->
                <div class="card" style="padding: 1.5rem;">
                    <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Drafts</div>
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">01</div>
                    <div style="font-size: 12px; color: var(--text-light);">Needs completion</div>
                </div>
                <!-- Submitted -->
                <div class="card" style="padding: 1.5rem;">
                    <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Submitted</div>
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">06</div>
                    <div style="font-size: 12px; color: var(--text-light);">Under review</div>
                </div>
                <!-- Approved -->
                <div class="card" style="padding: 1.5rem;">
                    <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Approved</div>
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">14</div>
                    <div style="font-size: 12px; color: var(--text-light);">This quarter</div>
                </div>
                <!-- Revision Required -->
                <div class="card" style="padding: 1.5rem;">
                    <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Revision Required</div>
                    <div style="font-size: 28px; font-weight: 700; margin-bottom: 5px;">02</div>
                    <div style="font-size: 12px; color: var(--text-light);">Action needed</div>
                </div>
            </div>

            <div class="card table-responsive" style="margin-top: 1.5rem;">
                <div style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 13px; font-weight: 600;">Quotation History <span style="color: var(--text-light); font-weight: normal; margin-left: 8px;">3 quotations</span></span>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px 10px;" onclick="App.pages['quotations'].exportCSV()">Export</button>
                    </div>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>QUOTATION</th>
                            <th>REQUEST</th>
                            <th>PRODUCT</th>
                            <th>UNIT PRICE</th>
                            <th>TOTAL</th>
                            <th>VALID UNTIL</th>
                            <th>STATUS</th>
                            <th>ACTION</th>
                        </tr>
                    </thead>
                    <tbody id="quotations-tbody">
                        <tr><td colspan="8" style="text-align:center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        `;

        this.fetchQuotations(container.querySelector('#quotations-tbody'));

        return container;
    },

    async fetchQuotations(tbody) {
        try {
            const response = await Api.get('/quotations/');
            tbody.innerHTML = '';
            
            if (response.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No quotations found.</td></tr>';
                return;
            }

            this.quotationsData = response;
            this.filterData();
        } catch (error) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:red;">Error loading quotations</td></tr>';
        }
    },
    
    filterData() {
        const tbody = document.querySelector('#quotations-tbody');
        if (!tbody || !this.quotationsData) return;
        
        const search = (document.getElementById('search-quotations')?.value || '').toLowerCase();
        const status = document.getElementById('filter-status-quotations')?.value || '';
        
        const filtered = this.quotationsData.filter(qt => {
            const matchSearch = (qt.product_name || '').toLowerCase().includes(search);
            const matchStatus = status ? qt.status === status : true;
            return matchSearch && matchStatus;
        });
        
        tbody.innerHTML = '';
        if (filtered.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;">No quotations found matching filters.</td></tr>';
            return;
        }
        
        filtered.forEach(qt => {
            const tr = document.createElement('tr');
            const statusColor = qt.status === 'Pending' ? 'var(--yellow)' : 
                                (qt.status === 'Accepted' ? 'var(--green)' : 
                                (qt.status === 'Under Review' ? 'var(--blue)' : 'var(--red)'));
            const statusBg = qt.status === 'Pending' ? 'var(--yellow-light)' : 
                             (qt.status === 'Accepted' ? 'var(--green-light)' : 
                             (qt.status === 'Under Review' ? 'var(--blue-light)' : 'var(--red-light)'));

            tr.innerHTML = `
                <td>
                    <div style="font-weight: 600;">QT-${new Date(qt.quotation_date).getFullYear()}-${qt.quotation_id.toString().padStart(4, '0')}</div>
                    <div style="font-size: 12px; color: var(--text-light);">${qt.quotation_date}</div>
                </td>
                <td style="color: var(--text-light);">-</td>
                <td>${qt.product_name || 'Unknown'}</td>
                <td>₹${qt.unit_price}</td>
                <td style="font-weight: 600;">₹${qt.subtotal}</td>
                <td style="color: var(--text-light);">${qt.valid_until}</td>
                <td><span class="badge" style="background: ${statusBg}; color: ${statusColor}; font-size: 11px !important;">${qt.status}</span></td>
                <td>
                    <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px; margin-right: 5px;" onclick='App.pages["quotations"].viewQuotation(${JSON.stringify(qt).replace(/'/g, "&#39;")})'><i class='bx bx-show'></i></button>
                    ${(qt.status === 'Pending' || qt.status === 'Under Review') ? `<button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px; margin-right: 5px;" onclick='App.pages["quotations"].editQuotation(${JSON.stringify(qt).replace(/'/g, "&#39;")})'><i class='bx bx-edit'></i></button>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
    },
    
    exportCSV() {
        if (!this.quotationsData) return;
        let csv = 'Quotation ID,Product,Quantity,Unit Price,Subtotal,Valid Until,Status\n';
        this.quotationsData.forEach(qt => {
            csv += `QT-${new Date(qt.quotation_date).getFullYear()}-${qt.quotation_id.toString().padStart(4, '0')},${qt.product_name},${qt.quantity},${qt.unit_price},${qt.subtotal},${qt.valid_until},${qt.status}\n`;
        });
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.setAttribute('href', url);
        a.setAttribute('download', 'Quotations.csv');
        a.click();
    },
    
    viewQuotation(qt) {
        let modalContainer = document.getElementById('quotation-view-modal-container');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'quotation-view-modal-container';
            document.body.appendChild(modalContainer);
        }
        
        const modalHtml = `
        <div class="modal glass-panel" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center;">
            <div class="card" style="width: 500px; padding: 2rem; border-radius: 12px; background: white;">
                <h3 style="margin-top: 0;">Quotation Details</h3>
                <p style="color: var(--text-light); font-size: 13px; margin-bottom: 20px;">Quotation ID: QT-${new Date(qt.quotation_date).getFullYear()}-${qt.quotation_id.toString().padStart(4, '0')}</p>
                
                <table style="width:100%; margin-bottom: 20px;">
                    <tr><td style="padding: 5px; color: var(--text-light);">Product:</td><td style="padding: 5px; font-weight: 600;">${qt.product_name}</td></tr>
                    <tr><td style="padding: 5px; color: var(--text-light);">Quantity:</td><td style="padding: 5px; font-weight: 600;">${qt.quantity}</td></tr>
                    <tr><td style="padding: 5px; color: var(--text-light);">Unit Price:</td><td style="padding: 5px; font-weight: 600;">₹${qt.unit_price}</td></tr>
                    <tr><td style="padding: 5px; color: var(--text-light);">Subtotal:</td><td style="padding: 5px; font-weight: 600;">₹${qt.subtotal}</td></tr>
                    <tr><td style="padding: 5px; color: var(--text-light);">Status:</td><td style="padding: 5px; font-weight: 600;">${qt.status}</td></tr>
                    <tr><td style="padding: 5px; color: var(--text-light);">Valid Until:</td><td style="padding: 5px; font-weight: 600;">${qt.valid_until}</td></tr>
                </table>
                
                <div style="display: flex; justify-content: flex-end;">
                    <button class="btn" style="background: white; border: 1px solid var(--border);" onclick="document.getElementById('quotation-view-modal-container').innerHTML = ''">Close</button>
                </div>
            </div>
        </div>
        `;
        document.getElementById('quotation-view-modal-container').innerHTML = modalHtml;
    },
    
    editQuotation(qt) {
        let modalContainer = document.getElementById('quotation-edit-modal-container');
        if (!modalContainer) {
            modalContainer = document.createElement('div');
            modalContainer.id = 'quotation-edit-modal-container';
            document.body.appendChild(modalContainer);
        }

        const validDate = qt.valid_until ? qt.valid_until.split('T')[0] : '';

        const modalHtml = `
        <div class="modal glass-panel" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000; align-items: center; justify-content: center;">
            <div class="card" style="width: 500px; padding: 2rem; border-radius: 12px; background: white;">
                <h3 style="margin-top: 0;">Edit Quotation</h3>
                <p style="color: var(--text-light); font-size: 13px; margin-bottom: 20px;">Quotation ID: QT-${new Date(qt.quotation_date).getFullYear()}-${qt.quotation_id.toString().padStart(4, '0')}</p>
                
                <div style="margin-bottom: 15px;">
                    <label style="display: block; font-size: 13px; margin-bottom: 5px;">Product</label>
                    <input type="text" value="${qt.product_name}" disabled style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: #f9f9f9;">
                </div>
                <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <label style="display: block; font-size: 13px; margin-bottom: 5px;">Quantity</label>
                        <input type="number" id="edit-quotation-qty" value="${qt.quantity}" min="1" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px;" oninput="App.pages['quotations'].calculateEditSubtotal()">
                    </div>
                </div>
                <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <label style="display: block; font-size: 13px; margin-bottom: 5px;">Unit Price (₹)</label>
                        <input type="number" id="edit-quotation-price" value="${qt.unit_price}" min="0" step="0.01" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px;" oninput="App.pages['quotations'].calculateEditSubtotal()">
                    </div>
                    <div style="flex: 1;">
                        <label style="display: block; font-size: 13px; margin-bottom: 5px;">Subtotal (₹)</label>
                        <input type="text" id="edit-quotation-subtotal" value="${qt.subtotal}" disabled style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: #f9f9f9;">
                    </div>
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; font-size: 13px; margin-bottom: 5px;">Valid Until</label>
                    <input type="date" id="edit-quotation-valid" value="${validDate}" style="width: 100%; padding: 8px; border: 1px solid var(--border); border-radius: 4px;">
                </div>
                
                <div style="display: flex; justify-content: flex-end; gap: 10px;">
                    <button class="btn" style="background: white; border: 1px solid var(--border);" onclick="document.getElementById('quotation-edit-modal-container').innerHTML = ''">Cancel</button>
                    <button class="btn primary" onclick="App.pages['quotations'].submitEditQuotation(${qt.quotation_id})">Save Changes</button>
                </div>
            </div>
        </div>
        `;
        document.getElementById('quotation-edit-modal-container').innerHTML = modalHtml;
    },

    calculateEditSubtotal() {
        const qty = parseFloat(document.getElementById('edit-quotation-qty').value) || 0;
        const price = parseFloat(document.getElementById('edit-quotation-price').value) || 0;
        document.getElementById('edit-quotation-subtotal').value = (qty * price).toFixed(2);
    },
    
    async submitEditQuotation(id) {
        const qty = document.getElementById('edit-quotation-qty').value;
        const price = document.getElementById('edit-quotation-price').value;
        const valid = document.getElementById('edit-quotation-valid').value;
        
        if (!qty || qty <= 0) return alert('Quantity must be greater than 0');
        if (!price || price < 0) return alert('Price must be valid');
        if (!valid) return alert('Validity date is required');
        
        try {
            await Api.put('/quotations/' + id, {
                quantity: qty,
                unit_price: price,
                valid_until: valid
            });
            document.getElementById('quotation-edit-modal-container').innerHTML = '';
            if (window.showToast) {
                showToast('Quotation updated successfully', 'success');
            } else {
                alert('Quotation updated successfully');
            }
            this.fetchQuotations(document.querySelector('#quotations-tbody'));
        } catch (error) {
            alert(error.message || 'Error updating quotation');
        }
    }
};
