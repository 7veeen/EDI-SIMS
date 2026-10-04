// dashboard.js

App.pages['dashboard'] = {
    render() {
        const user = Auth.getUser();
        const username = user ? user.username : 'User';
        const role = user ? user.role : 'Role';

        const container = document.createElement('div');
        container.innerHTML = `
            <div class="page-header">
                <div>
                    <span class="eyebrow">${role.toUpperCase()} PORTAL</span>
                    <h1>Good morning, ${username} 👋</h1>
                    <p>Here's an overview of your operations.</p>
                </div>
            </div>

            <div id="dashboard-stats" class="stats-grid">
                <!-- Dynamically populated based on role -->
            </div>
            
            <div id="dashboard-specific-content" style="margin-top: 30px;">
                <!-- Additional dashboard widgets loaded via API -->
            </div>
        `;
        return container;
    },

    async init() {
        const user = Auth.getUser();
        if (!user) return;

        const statsContainer = document.getElementById('dashboard-stats');
        const contentContainer = document.getElementById('dashboard-specific-content');

        const updateUsernameHtml = `
            <div class="section-title" style="margin-top: 40px;">
                <div>
                    <h3>Account Settings</h3>
                    <p>Manage your profile information</p>
                </div>
            </div>
            <div class="card" style="background: var(--white); padding: 24px; border-radius: var(--radius); border: 1px solid var(--border);">
                <div style="display: flex; flex-direction: column; gap: 0.85rem;">
                    <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                        <input type="text" id="new-username-input" class="input" value="${Utils.escapeHtml(user.username || '')}" placeholder="Current Username" disabled style="max-width: 300px; padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); width: 100%; background: #f8fafc; color: var(--text-secondary); cursor: not-allowed;">
                        <button class="btn" id="btn-change-username" disabled style="padding: 12px 24px; opacity: 0.6; cursor: not-allowed;">Change Username</button>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text-secondary);">
                        <i class='bx bx-info-circle' style="color: var(--primary); font-size: 1.1rem; flex-shrink: 0;"></i>
                        <span>Username changes are currently managed by an administrator. Please contact your administrator for assistance.</span>
                    </div>
                </div>
            </div>
        `;

        if (user.role === 'Employee') {
            try {
                const data = await Api.get('/dashboard/employee');
                
                statsContainer.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-top">
                            <span>Total Products</span>
                            <div class="stat-icon blue"><i class='bx bx-package'></i></div>
                        </div>
                        <h2>${data.total_products || 0}</h2>
                    </div>
                    <div class="stat-card">
                        <div class="stat-top">
                            <span>Inventory Alerts</span>
                            <div class="stat-icon yellow"><i class='bx bx-error'></i></div>
                        </div>
                        <h2>${data.low_stock_products ? data.low_stock_products.length : 0}</h2>
                        <div class="stat-bottom warning-text">
                            <i class='bx bx-time'></i> Needs attention
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-top">
                            <span>Stock Ins</span>
                            <div class="stat-icon green"><i class='bx bx-transfer'></i></div>
                        </div>
                        <h2>${data.stock_in || 0}</h2>
                    </div>
                `;

                contentContainer.innerHTML = `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem;">
                        <!-- Low Stock Table -->
                        <div>
                            <div class="section-title">
                                <div>
                                    <h3>Low Stock Products</h3>
                                    <p>Products that require immediate restocking</p>
                                </div>
                            </div>
                            <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">NAME</th>
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">QTY</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.low_stock_products && data.low_stock_products.length > 0 
                                            ? data.low_stock_products.map(p => `
                                                <tr style="border-bottom: 1px solid #edf0ef;">
                                                    <td style="padding: 16px; font-weight: 600;">${Utils.escapeHtml(p.product_name)}</td>
                                                    <td style="padding: 16px; color: var(--red); font-weight: 700;">${p.quantity_available}</td>
                                                </tr>
                                            `).join('')
                                            : '<tr><td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">No low stock alerts.</td></tr>'
                                        }
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- My Tasks -->
                        <div>
                            <div class="section-title">
                                <div>
                                    <h3>My Tasks & Alerts</h3>
                                    <p>Your pending notifications</p>
                                </div>
                            </div>
                            <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">TASK</th>
                                            <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">DATE</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.tasks && data.tasks.length > 0 
                                            ? data.tasks.map(t => `
                                                <tr style="border-bottom: 1px solid #edf0ef;">
                                                    <td style="padding: 16px;">
                                                        <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(t.title)}</div>
                                                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${Utils.escapeHtml(t.message)}</div>
                                                    </td>
                                                    <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${new Date(t.created_at).toLocaleDateString()}</td>
                                                </tr>
                                            `).join('')
                                            : '<tr><td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">You have no pending tasks! 🎉</td></tr>'
                                        }
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    ${updateUsernameHtml}
                `;
            } catch (err) {}
        } else if (user.role === 'Supplier') {
            statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(220px, 1fr))';
            statsContainer.innerHTML = `
                <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--white); min-height: 90px; display: flex; align-items: center; justify-content: center; grid-column: 1 / -1;">
                    <div style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 13.5px;">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 20px; color: var(--primary);"></i> Loading supplier metrics...
                    </div>
                </div>
            `;
            contentContainer.innerHTML = `
                <div style="display: flex; justify-content: center; align-items: center; padding: 40px; color: var(--text-secondary); gap: 10px;">
                    <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; color: var(--primary);"></i>
                    <span>Loading supplier workspace...</span>
                </div>
            `;
            try {
                const data = await Api.get('/dashboard/supplier');

                const openRequestsCount = data.open_requests || 0;
                const pendingQuotationsCount = data.pending_quotations || 0;
                const activePosCount = data.active_pos || 0;
                const pendingPaymentsVal = data.pending_payments !== null && data.pending_payments !== undefined
                    ? `₹${Number(data.pending_payments).toLocaleString('en-IN')}`
                    : '—';
                const paymentsSubtext = data.has_payment_module ? 'Invoices pending' : 'Not tracked';

                const onTimeDeliveryStr = data.on_time_delivery_rate !== null ? `${data.on_time_delivery_rate}%` : 'N/A';
                const onTimeWidth = data.on_time_delivery_rate !== null ? `${Math.min(100, Math.max(0, data.on_time_delivery_rate))}%` : '0%';

                const quoteAcceptanceStr = data.quotation_acceptance_rate !== null ? `${data.quotation_acceptance_rate}%` : 'N/A';
                const quoteWidth = data.quotation_acceptance_rate !== null ? `${Math.min(100, Math.max(0, data.quotation_acceptance_rate))}%` : '0%';

                const orderAcceptanceStr = data.order_acceptance_rate !== null ? `${data.order_acceptance_rate}%` : 'N/A';
                const orderWidth = data.order_acceptance_rate !== null ? `${Math.min(100, Math.max(0, data.order_acceptance_rate))}%` : '0%';

                const profileComp = data.profile_completion || 100;

                // ==========================================
                // ROW 1: PRIMARY 4 KPI CARDS
                // ==========================================
                const pendingDeliveriesCount = data.pending_deliveries || 0;
                const shipmentStats = data.shipment_stats || {};
                const attentionItems = data.attention_items || [];
                const recentActivity = data.recent_activity || [];

                statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(220px, 1fr))';
                statsContainer.innerHTML = `
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('stock-requests')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Open Stock Requests</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(openRequestsCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${openRequestsCount > 0 ? '#d97706' : 'var(--text-light)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx ${openRequestsCount > 0 ? 'bx-time-five' : 'bx-check'}'></i> Awaiting your response
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-git-pull-request'></i>
                            </div>
                        </div>
                    </div>

                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('quotations')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Pending Quotations</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(pendingQuotationsCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-time'></i> Pending review
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-file'></i>
                            </div>
                        </div>
                    </div>

                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('purchase-orders')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Active Purchase Orders</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(activePosCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-briefcase'></i> Currently active
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-receipt'></i>
                            </div>
                        </div>
                    </div>

                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('shipments')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Pending Deliveries</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(pendingDeliveriesCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${pendingDeliveriesCount > 0 ? '#7c3aed' : 'var(--text-light)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-car'></i> Not yet delivered
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-package'></i>
                            </div>
                        </div>
                    </div>
                `;

                // Personalize page header greeting with supplier company name if available
                const pageHeaderTitle = document.querySelector('.page-header h1');
                if (pageHeaderTitle && data.supplier_name) {
                    pageHeaderTitle.innerHTML = `Welcome back, ${Utils.escapeHtml(data.supplier_name)} 👋`;
                }

                contentContainer.innerHTML = `
                    <!-- ========================================== -->
                    <!-- ROW 2: NEEDS YOUR ATTENTION                -->
                    <!-- ========================================== -->
                    <div class="section-title" style="margin-top: 2rem; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text);">Needs Your Attention</h3>
                                ${attentionItems.length > 0 ? `
                                    <span class="badge" style="background: var(--red-light); color: var(--red); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px;">
                                        ${attentionItems.length} ACTION${attentionItems.length > 1 ? 'S' : ''}
                                    </span>
                                ` : ''}
                            </div>
                            <span style="font-size: 12.5px; color: var(--text-secondary);">Direct operational items requiring your review or response</span>
                        </div>
                    </div>

                    ${attentionItems.length > 0 ? `
                        <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 2rem;">
                            ${attentionItems.map(item => {
                                const isUrgent = item.priority === 'Urgent' || item.status === 'Delayed';
                                const iconClass = item.type === 'stock_request' 
                                    ? 'bx-git-pull-request' 
                                    : (item.type === 'purchase_order' ? 'bx-receipt' : 'bx-error-circle');
                                const iconBg = item.type === 'stock_request' 
                                    ? 'rgba(245, 158, 11, 0.12)' 
                                    : (item.type === 'purchase_order' ? 'rgba(59, 130, 246, 0.12)' : 'rgba(217, 83, 79, 0.12)');
                                const iconColor = item.type === 'stock_request' 
                                    ? '#d97706' 
                                    : (item.type === 'purchase_order' ? '#2563eb' : 'var(--red)');
                                const badgeBg = isUrgent ? 'var(--red-light)' : 'var(--yellow-light)';
                                const badgeColor = isUrgent ? 'var(--red)' : 'var(--yellow)';

                                return `
                                    <div class="card" style="padding: 1rem 1.25rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
                                        <div style="display: flex; align-items: center; gap: 14px; min-width: 240px; flex: 1;">
                                            <div style="width: 42px; height: 42px; border-radius: 10px; background: ${iconBg}; color: ${iconColor}; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;">
                                                <i class='bx ${iconClass}'></i>
                                            </div>
                                            <div>
                                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                                    <span style="font-weight: 700; font-size: 14px; color: var(--text);">${Utils.escapeHtml(item.title)}</span>
                                                    <span class="badge" style="font-size: 10.5px !important; padding: 2px 7px; background: ${badgeBg}; color: ${badgeColor}; border-radius: 4px; font-weight: 600;">
                                                        ${item.status}
                                                    </span>
                                                </div>
                                                <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 3px;">
                                                    ${Utils.escapeHtml(item.description)}
                                                    ${item.date ? ` • <span style="color: var(--text-light);"><i class='bx bx-calendar' style="font-size: 11px;"></i> ${item.date}</span>` : ''}
                                                </div>
                                            </div>
                                        </div>
                                        <button class="btn btn-primary" style="padding: 6px 14px; font-size: 12.5px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; border-radius: 6px;" onclick="App.navigate('${item.target_page}')">
                                            ${item.action_label} <i class='bx bx-right-arrow-alt'></i>
                                        </button>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    ` : `
                        <div class="card" style="padding: 1.5rem 1.75rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); display: flex; align-items: center; gap: 16px; margin-bottom: 2rem;">
                            <div style="width: 44px; height: 44px; border-radius: 50%; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0;">
                                <i class='bx bx-check-circle'></i>
                            </div>
                            <div>
                                <h4 style="margin: 0; font-size: 15px; font-weight: 600; color: var(--text);">You're all caught up. 🎉</h4>
                                <p style="margin: 4px 0 0 0; font-size: 13px; color: var(--text-secondary);">No pending stock requests, purchase orders awaiting acceptance, or delayed shipments at this time.</p>
                            </div>
                        </div>
                    `}

                    <!-- ========================================== -->
                    <!-- ROW 3: RECENT POs & SHIPMENT STATUS        -->
                    <!-- ========================================== -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        <!-- Recent Purchase Orders -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Recent Purchase Orders</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Official procurement contracts & orders</p>
                                </div>
                                <button class="btn" style="color: var(--primary); font-weight: 600; font-size: 12.5px; padding: 0; background: none; border: none; cursor: pointer; display: flex; align-items: center; gap: 4px;" onclick="App.navigate('purchase-orders')">
                                    View All Purchase Orders <i class='bx bx-right-arrow-alt'></i>
                                </button>
                            </div>
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">PO ID</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">DATE</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">TOTAL</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">STATUS</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary); text-align: right;">ACTION</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.recent_orders && data.recent_orders.length > 0 
                                            ? data.recent_orders.map(o => `
                                                <tr style="border-bottom: 1px solid #edf0ef;">
                                                    <td style="padding: 12px 14px; font-weight: 700; font-size: 13px; color: var(--primary);">
                                                        PO #${o.purchase_order_id}
                                                    </td>
                                                    <td style="padding: 12px 14px; color: var(--text-secondary); font-size: 12.5px;">
                                                        ${o.order_date ? Utils.formatDate(o.order_date) : 'N/A'}
                                                    </td>
                                                    <td style="padding: 12px 14px; font-weight: 700; font-size: 13px; color: var(--text);">
                                                        ₹${Number(o.total_amount || 0).toLocaleString('en-IN')}
                                                    </td>
                                                    <td style="padding: 12px 14px;">
                                                        <span class="badge" style="font-size: 10.5px !important; background: ${o.status === 'Delivered' ? 'var(--green-light)' : (o.status === 'Accepted' ? 'var(--blue-light)' : (o.status === 'Cancelled' ? 'var(--red-light)' : 'var(--yellow-light)'))}; color: ${o.status === 'Delivered' ? 'var(--green)' : (o.status === 'Accepted' ? 'var(--blue)' : (o.status === 'Cancelled' ? 'var(--red)' : 'var(--yellow)'))};">
                                                            ${o.status}
                                                        </span>
                                                    </td>
                                                    <td style="padding: 12px 14px; text-align: right;">
                                                        <button class="btn" style="background: var(--primary-light); color: var(--primary); padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 4px; border: none; cursor: pointer;" onclick="App.navigate('purchase-orders')">
                                                            View
                                                        </button>
                                                    </td>
                                                </tr>
                                            `).join('')
                                            : '<tr><td colspan="5" style="padding: 28px; text-align: center; color: var(--text-secondary); font-size: 13px;">No active purchase orders.</td></tr>'
                                        }
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Shipment Status -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Shipment Status</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Fulfillment & delivery progress tracking</p>
                                </div>
                                <button class="btn" style="color: var(--primary); font-weight: 600; font-size: 12.5px; padding: 0; background: none; border: none; cursor: pointer; display: flex; align-items: center; gap: 4px;" onclick="App.navigate('shipments')">
                                    Track Shipments <i class='bx bx-right-arrow-alt'></i>
                                </button>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.85rem; margin-bottom: 1rem;">
                                <div style="padding: 0.85rem; border-radius: 10px; background: #f8fafc; border: 1px solid var(--border); cursor: pointer;" onclick="App.navigate('shipments')">
                                    <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Ready</div>
                                    <div style="font-size: 22px; font-weight: 700; color: var(--text); margin-top: 4px;">${shipmentStats.ready_for_shipment || 0}</div>
                                    <div style="font-size: 11px; color: var(--text-light); margin-top: 2px;">Packed & ready</div>
                                </div>
                                <div style="padding: 0.85rem; border-radius: 10px; background: #eff6ff; border: 1px solid #bfdbfe; cursor: pointer;" onclick="App.navigate('shipments')">
                                    <div style="font-size: 11px; font-weight: 600; color: #1e40af; text-transform: uppercase;">Dispatched</div>
                                    <div style="font-size: 22px; font-weight: 700; color: #1d4ed8; margin-top: 4px;">${shipmentStats.dispatched || 0}</div>
                                    <div style="font-size: 11px; color: #3b82f6; margin-top: 2px;">Left warehouse</div>
                                </div>
                                <div style="padding: 0.85rem; border-radius: 10px; background: #fffbeb; border: 1px solid #fde68a; cursor: pointer;" onclick="App.navigate('shipments')">
                                    <div style="font-size: 11px; font-weight: 600; color: #92400e; text-transform: uppercase;">In Transit</div>
                                    <div style="font-size: 22px; font-weight: 700; color: #b45309; margin-top: 4px;">${shipmentStats.in_transit || 0}</div>
                                    <div style="font-size: 11px; color: #d97706; margin-top: 2px;">On the way</div>
                                </div>
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-bottom: 1.25rem;">
                                <div style="padding: 0.85rem; border-radius: 10px; background: ${shipmentStats.delayed > 0 ? '#fef2f2' : '#f8fafc'}; border: 1px solid ${shipmentStats.delayed > 0 ? '#fecaca' : 'var(--border)'}; cursor: pointer;" onclick="App.navigate('shipments')">
                                    <div style="font-size: 11px; font-weight: 600; color: ${shipmentStats.delayed > 0 ? '#991b1b' : 'var(--text-secondary)'}; text-transform: uppercase;">Delayed</div>
                                    <div style="font-size: 22px; font-weight: 700; color: ${shipmentStats.delayed > 0 ? '#dc2626' : 'var(--text)'}; margin-top: 4px;">${shipmentStats.delayed || 0}</div>
                                    <div style="font-size: 11px; color: ${shipmentStats.delayed > 0 ? '#ef4444' : 'var(--text-light)'}; margin-top: 2px;">Passed expected date</div>
                                </div>
                                <div style="padding: 0.85rem; border-radius: 10px; background: #ecfdf5; border: 1px solid #a7f3d0; cursor: pointer;" onclick="App.navigate('shipments')">
                                    <div style="font-size: 11px; font-weight: 600; color: #065f46; text-transform: uppercase;">Delivered</div>
                                    <div style="font-size: 22px; font-weight: 700; color: #059669; margin-top: 4px;">${shipmentStats.delivered || 0}</div>
                                    <div style="font-size: 11px; color: #10b981; margin-top: 2px;">Received at destination</div>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 0.75rem; border-top: 1px solid var(--border); font-size: 12.5px; color: var(--text-secondary);">
                                <span>Total Shipments Logged: <strong style="color: var(--text);">${shipmentStats.total || 0}</strong></span>
                                <span style="color: var(--primary); cursor: pointer;" onclick="App.navigate('shipments')">View Details →</span>
                            </div>
                        </div>
                    </div>

                    <!-- ========================================== -->
                    <!-- ROW 4: RECENT STOCK REQUESTS & PERFORMANCE -->
                    <!-- ========================================== -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        <!-- Recent Stock Requests -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Recent Stock Requests</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Incoming warehouse procurement needs</p>
                                </div>
                                <button class="btn" style="color: var(--primary); font-weight: 600; font-size: 12.5px; padding: 0; background: none; border: none; cursor: pointer; display: flex; align-items: center; gap: 4px;" onclick="App.navigate('stock-requests')">
                                    View All Stock Requests <i class='bx bx-right-arrow-alt'></i>
                                </button>
                            </div>
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">REQUEST ID</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">PRODUCT</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">QTY</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">REQ. DATE</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">PRIORITY</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary); text-align: right;">ACTION</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.recent_stock_requests && data.recent_stock_requests.length > 0 
                                            ? data.recent_stock_requests.map(sr => `
                                                <tr style="border-bottom: 1px solid #edf0ef;">
                                                    <td style="padding: 12px 14px; font-weight: 700; font-size: 12.5px; color: var(--text);">
                                                        ${Utils.escapeHtml(sr.request_number)}
                                                    </td>
                                                    <td style="padding: 12px 14px; font-size: 12.5px; color: var(--text); max-width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                                        ${Utils.escapeHtml(sr.primary_product)}
                                                    </td>
                                                    <td style="padding: 12px 14px; font-weight: 700; font-size: 12.5px;">${sr.total_quantity}</td>
                                                    <td style="padding: 12px 14px; color: var(--text-secondary); font-size: 12px;">
                                                        ${sr.required_date ? Utils.formatDate(sr.required_date) : 'N/A'}
                                                    </td>
                                                    <td style="padding: 12px 14px;">
                                                        <span class="badge" style="font-size: 10px !important; padding: 2px 6px; background: ${sr.priority === 'Urgent' ? 'var(--red-light)' : (sr.priority === 'High' ? 'var(--yellow-light)' : 'var(--blue-light)')}; color: ${sr.priority === 'Urgent' ? 'var(--red)' : (sr.priority === 'High' ? 'var(--yellow)' : 'var(--blue)')};">
                                                            ${sr.priority}
                                                        </span>
                                                    </td>
                                                    <td style="padding: 12px 14px; text-align: right;">
                                                        <button class="btn" style="background: var(--primary-light); color: var(--primary); padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 4px; border: none; cursor: pointer;" onclick="App.navigate('stock-requests')">
                                                            Respond
                                                        </button>
                                                    </td>
                                                </tr>
                                            `).join('')
                                            : '<tr><td colspan="6" style="padding: 28px; text-align: center; color: var(--text-secondary); font-size: 13px;">No stock requests available.</td></tr>'
                                        }
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Supplier Performance -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Supplier Performance</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Operational KPIs & quality score</p>
                                </div>
                                <span class="badge" style="background: var(--green-light); color: var(--green); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px;">
                                    Verified Supplier
                                </span>
                            </div>

                            <div style="display: flex; flex-direction: column; gap: 1.1rem;">
                                <!-- On-time Delivery -->
                                <div>
                                    <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                                        <span style="font-weight: 600; color: var(--text);">On-time Delivery</span>
                                        <span style="font-weight: 700; color: ${data.on_time_delivery_rate !== null ? 'var(--green)' : 'var(--text-secondary)'};">
                                            ${data.on_time_delivery_rate !== null ? `${data.on_time_delivery_rate}%` : 'No sufficient data'}
                                        </span>
                                    </div>
                                    <div style="width: 100%; height: 7px; background: #f1f5f9; border-radius: 999px; overflow: hidden;">
                                        <div style="width: ${data.on_time_delivery_rate !== null ? `${Math.min(100, Math.max(0, data.on_time_delivery_rate))}%` : '0%'}; height: 100%; background: var(--green); border-radius: 999px;"></div>
                                    </div>
                                </div>

                                <!-- Quotation Acceptance Rate -->
                                <div>
                                    <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                                        <span style="font-weight: 600; color: var(--text);">Quotation Acceptance</span>
                                        <span style="font-weight: 700; color: ${data.quotation_acceptance_rate !== null ? 'var(--blue)' : 'var(--text-secondary)'};">
                                            ${data.quotation_acceptance_rate !== null ? `${data.quotation_acceptance_rate}%` : 'No sufficient data'}
                                        </span>
                                    </div>
                                    <div style="width: 100%; height: 7px; background: #f1f5f9; border-radius: 999px; overflow: hidden;">
                                        <div style="width: ${data.quotation_acceptance_rate !== null ? `${Math.min(100, Math.max(0, data.quotation_acceptance_rate))}%` : '0%'}; height: 100%; background: var(--blue); border-radius: 999px;"></div>
                                    </div>
                                </div>

                                <!-- Order Acceptance Rate -->
                                <div>
                                    <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                                        <span style="font-weight: 600; color: var(--text);">Order Acceptance</span>
                                        <span style="font-weight: 700; color: ${data.order_acceptance_rate !== null ? 'var(--primary)' : 'var(--text-secondary)'};">
                                            ${data.order_acceptance_rate !== null ? `${data.order_acceptance_rate}%` : 'No sufficient data'}
                                        </span>
                                    </div>
                                    <div style="width: 100%; height: 7px; background: #f1f5f9; border-radius: 999px; overflow: hidden;">
                                        <div style="width: ${data.order_acceptance_rate !== null ? `${Math.min(100, Math.max(0, data.order_acceptance_rate))}%` : '0%'}; height: 100%; background: var(--primary); border-radius: 999px;"></div>
                                    </div>
                                </div>

                                <!-- Profile Completion -->
                                <div>
                                    <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                                        <span style="font-weight: 600; color: var(--text);">Profile Completion</span>
                                        <span style="font-weight: 700; color: var(--purple);">${profileComp}%</span>
                                    </div>
                                    <div style="width: 100%; height: 7px; background: #f1f5f9; border-radius: 999px; overflow: hidden;">
                                        <div style="width: ${profileComp}%; height: 100%; background: var(--purple); border-radius: 999px;"></div>
                                    </div>
                                </div>
                            </div>

                            <!-- Pending Payments Safe Notice -->
                            <div style="margin-top: 1.25rem; padding: 0.85rem 1rem; border-radius: 8px; background: #f8fafc; border: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <i class='bx bx-credit-card' style="color: var(--text-light); font-size: 18px;"></i>
                                    <div>
                                        <div style="font-size: 12.5px; font-weight: 600; color: var(--text);">Pending Payments</div>
                                        <div style="font-size: 11px; color: var(--text-light);">Financial tracking is managed outside this portal</div>
                                    </div>
                                </div>
                                <div style="text-align: right;">
                                    <span style="font-size: 14px; font-weight: 700; color: var(--text-secondary);">—</span>
                                    <span style="display: block; font-size: 10.5px; color: var(--text-light);">Not tracked</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ========================================== -->
                    <!-- ROW 5: QUICK ACTIONS                       -->
                    <!-- ========================================== -->
                    <div class="section-title" style="margin-top: 1.5rem; margin-bottom: 1rem;">
                        <div>
                            <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text);">Quick Actions</h3>
                            <p style="margin: 2px 0 0 0; font-size: 13px; color: var(--text-secondary);">Direct shortcuts to essential supplier operations</p>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem;">
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('stock-requests')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-git-pull-request'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Review Stock Requests</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${openRequestsCount} pending response</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('quotations')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-file-blank'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">View Quotations</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${pendingQuotationsCount} in review</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('purchase-orders')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-receipt'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">View Purchase Orders</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${activePosCount} active orders</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('shipments')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-car'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Track Shipments</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${shipmentStats.in_transit || 0} in transit</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                    </div>

                    <!-- ========================================== -->
                    <!-- ROW 6: RECENT ACTIVITY                     -->
                    <!-- ========================================== -->
                    <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); margin-bottom: 2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                            <div>
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Recent Activity</h3>
                                <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Timeline of recent status updates and order milestones</p>
                            </div>
                            <span style="font-size: 11.5px; color: var(--text-light);">Audit Trail</span>
                        </div>
                        ${recentActivity && recentActivity.length > 0 ? `
                            <div style="display: flex; flex-direction: column; gap: 0.85rem;">
                                ${recentActivity.map(act => `
                                    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; border-radius: 8px; background: #fbfcfc; border: 1px solid #edf0ef; flex-wrap: wrap; gap: 8px;">
                                        <div style="display: flex; align-items: center; gap: 12px;">
                                            <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; font-size: 15px;">
                                                <i class='bx bx-history'></i>
                                            </div>
                                            <div>
                                                <div style="font-weight: 600; font-size: 13px; color: var(--text);">
                                                    ${act.purchase_order_id ? `PO #${act.purchase_order_id}` : (act.shipment_id ? `Shipment #${act.shipment_id}` : 'Order')}
                                                    ${act.status ? `— <span class="badge" style="font-size: 10px !important; padding: 1px 6px;">${act.status}</span>` : ''}
                                                </div>
                                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                                                    ${Utils.escapeHtml(act.notes || act.action || 'Status updated')}
                                                </div>
                                            </div>
                                        </div>
                                        <div style="font-size: 11.5px; color: var(--text-light); text-align: right;">
                                            <div>${act.created_at ? Utils.formatDate(act.created_at) : ''}</div>
                                            <div style="font-size: 10.5px;">by ${Utils.escapeHtml(act.changed_by)}</div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">No recent activity logged.</div>
                        `}
                    </div>

                    ${updateUsernameHtml}
                `;
            } catch (err) {
                console.error("Failed to load supplier dashboard:", err);
                statsContainer.innerHTML = `
                    <div class="card" style="grid-column: 1 / -1; padding: 24px; color: var(--red); text-align: center; border: 1px solid var(--border); border-radius: 12px;">
                        <i class='bx bx-error-circle' style="font-size: 28px; margin-bottom: 6px; display: block;"></i>
                        <strong>Unable to load dashboard data. Please try again.</strong>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${Utils.escapeHtml(err.message || 'Server error')}</div>
                    </div>
                `;
                contentContainer.innerHTML = `
                    <div class="card" style="padding: 2.5rem; text-align: center; border: 1px solid var(--border); border-radius: 12px; background: var(--white); margin-top: 1rem;">
                        <i class='bx bx-refresh' style="font-size: 40px; color: var(--primary); margin-bottom: 1rem; display: block;"></i>
                        <h4 style="margin-bottom: 0.5rem; color: var(--text);">Unable to load dashboard data</h4>
                        <p style="color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 13.5px;">Please check your connection and click retry below.</p>
                        <button class="btn btn-primary" onclick="App.pages['dashboard'].init()" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; font-size: 13px;">
                            <i class='bx bx-refresh'></i> Retry
                        </button>
                    </div>
                `;
            }
        } else if (user.role === 'Manager') {
            try {
                const data = await Api.get('/dashboard/manager');
                
                statsContainer.style.gridTemplateColumns = 'repeat(4, 1fr)';
                statsContainer.innerHTML = `
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Active POs</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.active_pos || 0}</div>
                                <div style="font-size: 12px; color: var(--blue);"><i class='bx bx-trending-up'></i> In Progress</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--blue-light); color: var(--blue); display: flex; align-items: center; justify-content: center;"><i class='bx bx-briefcase'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Pending PO Value</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">₹${data.pending_po_value ? data.pending_po_value.toLocaleString() : '0'}</div>
                                <div style="font-size: 12px; color: var(--purple);"><i class='bx bx-time'></i> Awaiting fulfillment</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--purple-light); color: var(--purple); display: flex; align-items: center; justify-content: center;"><i class='bx bx-rupee'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Low Stock Alerts</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.low_stock_count || 0}</div>
                                <div style="font-size: 12px; color: var(--red);"><i class='bx bx-error'></i> Requires action</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--red-light); color: var(--red); display: flex; align-items: center; justify-content: center;"><i class='bx bx-box'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">30-Day Movement</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.recent_stock_movement || 0}</div>
                                <div style="font-size: 12px; color: var(--green);"><i class='bx bx-transfer'></i> Total units transacted</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center;"><i class='bx bx-line-chart'></i></div>
                        </div>
                    </div>
                `;

                contentContainer.innerHTML = `
                    <div class="section-title">
                        <div>
                            <h3>Recent Stock Transactions</h3>
                            <p>Latest movements across the warehouse</p>
                        </div>
                    </div>
                    <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden; margin-bottom: 2rem;">
                        <table style="width: 100%; text-align: left; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">PRODUCT</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">TYPE</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">QUANTITY</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">DATE</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.recent_transactions && data.recent_transactions.length > 0 
                                    ? data.recent_transactions.map(t => `
                                        <tr style="border-bottom: 1px solid #edf0ef;">
                                            <td style="padding: 16px; font-weight: 600;">${Utils.escapeHtml(t.product_name)}</td>
                                            <td style="padding: 16px;">
                                                <span class="badge" style="background: var(${t.transaction_type === 'STOCK_IN' ? '--green-light' : '--red-light'}); color: var(${t.transaction_type === 'STOCK_IN' ? '--green' : '--red'}); font-weight: 600;">
                                                    ${t.transaction_type}
                                                </span>
                                            </td>
                                            <td style="padding: 16px; font-weight: 700;">${t.quantity}</td>
                                            <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${new Date(t.transaction_date).toLocaleDateString()}</td>
                                        </tr>
                                    `).join('')
                                    : '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">No recent transactions.</td></tr>'
                                }
                            </tbody>
                        </table>
                    </div>
                    ${updateUsernameHtml}
                `;
            } catch (err) {}
        } else if (user.role === 'Owner') {
            try {
                const data = await Api.get('/dashboard/owner');
                
                statsContainer.style.gridTemplateColumns = 'repeat(4, 1fr)';
                statsContainer.innerHTML = `
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Total Users</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.total_users || 0}</div>
                                <div style="font-size: 12px; color: var(--blue);"><i class='bx bx-group'></i> Active Accounts</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--blue-light); color: var(--blue); display: flex; align-items: center; justify-content: center;"><i class='bx bx-user-pin'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Registered Suppliers</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.total_suppliers || 0}</div>
                                <div style="font-size: 12px; color: var(--green);"><i class='bx bx-buildings'></i> Network Partners</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center;"><i class='bx bx-network-chart'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Total Products</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">${data.total_products || 0}</div>
                                <div style="font-size: 12px; color: var(--purple);"><i class='bx bx-category'></i> Catalog Size</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--purple-light); color: var(--purple); display: flex; align-items: center; justify-content: center;"><i class='bx bx-category-alt'></i></div>
                        </div>
                    </div>
                    <div class="card" style="padding: 1.5rem;">
                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 5px;">Inventory Value</div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                            <div>
                                <div style="font-size: 28px; font-weight: 700;">₹${data.total_inventory_value ? data.total_inventory_value.toLocaleString() : '0'}</div>
                                <div style="font-size: 12px; color: var(--yellow);"><i class='bx bx-line-chart'></i> Current Asset Worth</div>
                            </div>
                            <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--yellow-light); color: var(--yellow); display: flex; align-items: center; justify-content: center;"><i class='bx bx-rupee'></i></div>
                        </div>
                    </div>
                `;

                contentContainer.innerHTML = `
                    <div class="section-title">
                        <div>
                            <h3>Recent System Audit Logs</h3>
                            <p>Global security and activity monitoring</p>
                        </div>
                    </div>
                    <div style="background: var(--white); border-radius: var(--radius); border: 1px solid var(--border); overflow: hidden; margin-bottom: 2rem;">
                        <table style="width: 100%; text-align: left; border-collapse: collapse;">
                            <thead>
                                <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">USER</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">ACTION</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">DETAILS</th>
                                    <th style="padding: 16px; font-weight: 600; font-size: 13px; color: var(--text-secondary);">TIME</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.recent_audits && data.recent_audits.length > 0 
                                    ? data.recent_audits.map(a => `
                                        <tr style="border-bottom: 1px solid #edf0ef;">
                                            <td style="padding: 16px; font-weight: 600;">
                                                <div style="display: flex; align-items: center; gap: 8px;">
                                                    <div style="width: 24px; height: 24px; border-radius: 50%; background: var(--bg); display: flex; align-items: center; justify-content: center; font-size: 12px; color: var(--text-secondary);"><i class='bx bx-user'></i></div>
                                                    ${Utils.escapeHtml(a.username)}
                                                </div>
                                            </td>
                                            <td style="padding: 16px; font-weight: 600;">${Utils.escapeHtml(a.action)}</td>
                                            <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${Utils.escapeHtml(a.details)}</td>
                                            <td style="padding: 16px; color: var(--text-secondary); font-size: 13px;">${new Date(a.timestamp).toLocaleString()}</td>
                                        </tr>
                                    `).join('')
                                    : '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">No recent audit logs.</td></tr>'
                                }
                            </tbody>
                        </table>
                    </div>
                    ${updateUsernameHtml}
                `;
            } catch (err) {}
        }

        // Attach event listener for change username (informational advisory; API managed by admin)
        const btnChangeUsername = document.getElementById('btn-change-username');
        if (btnChangeUsername) {
            btnChangeUsername.addEventListener('click', (e) => {
                e.preventDefault();
                Utils.showToast("Username changes are currently managed by an administrator. Please contact your administrator for assistance.", "info");
            });
        }
    }
};
