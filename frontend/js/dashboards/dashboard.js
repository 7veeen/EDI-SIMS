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
            // Personalize page header greeting
            const pageHeaderTitle = document.querySelector('.page-header h1');
            const pageHeaderSub = document.querySelector('.page-header p');
            if (pageHeaderTitle) {
                pageHeaderTitle.innerHTML = `Welcome back, ${Utils.escapeHtml(user.username)} 👋`;
            }
            if (pageHeaderSub) {
                pageHeaderSub.textContent = "Here's an overview of your assigned warehouse tasks.";
            }

            // Loading state
            statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(210px, 1fr))';
            statsContainer.innerHTML = `
                <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--white); min-height: 90px; display: flex; align-items: center; justify-content: center; grid-column: 1 / -1;">
                    <div style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 13.5px;">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 20px; color: var(--primary);"></i> Loading employee workspace...
                    </div>
                </div>
            `;
            contentContainer.innerHTML = `
                <div style="display: flex; justify-content: center; align-items: center; padding: 40px; color: var(--text-secondary); gap: 10px;">
                    <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; color: var(--primary);"></i>
                    <span>Loading assigned warehouse tasks...</span>
                </div>
            `;

            try {
                const data = await Api.get('/dashboard/employee');

                if (pageHeaderTitle && data.employee_name) {
                    pageHeaderTitle.innerHTML = `Welcome back, ${Utils.escapeHtml(data.employee_name)} 👋`;
                }

                const assignedShipmentsCount = data.assigned_shipments_count || 0;
                const awaitingStockInCount = data.awaiting_stock_in || 0;
                const inTransitCount = data.in_transit_shipments || 0;
                const completedStockInsCount = data.completed_stock_ins_count || 0;
                const completedStockInsQty = data.completed_stock_ins_quantity || 0;
                const lowStockCount = data.low_stock_count !== undefined ? data.low_stock_count : (data.low_stock_products ? data.low_stock_products.length : 0);

                const attentionItems = data.attention_items || [];
                const assignedShipments = data.assigned_shipments || [];
                const recentTransactions = data.recent_transactions || [];
                const lowStockProducts = data.low_stock_products || [];
                const tasks = data.tasks || [];

                // ==========================================
                // ROW 1: 5 PRIMARY ACTIONABLE KPI CARDS
                // ==========================================
                statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(210px, 1fr))';
                statsContainer.innerHTML = `
                    <!-- 1. Assigned Shipments -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('shipments')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Assigned Shipments</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(assignedShipmentsCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--blue); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-car'></i> ${inTransitCount > 0 ? `${inTransitCount} in transit` : 'Total assignments'}
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-car'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 2. Awaiting Stock-In -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('shipments')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Awaiting Stock-In</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(awaitingStockInCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${awaitingStockInCount > 0 ? '#d97706' : 'var(--green)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx ${awaitingStockInCount > 0 ? 'bx-time-five' : 'bx-check'}'></i> ${awaitingStockInCount > 0 ? 'Delivered at dock' : 'All caught up'}
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-download'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 3. In Transit -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('shipments')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">In Transit</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(inTransitCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--purple); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-navigation'></i> En route to warehouse
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-package'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 4. Completed Stock-Ins -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('inventory')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Completed Stock-Ins</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(completedStockInsCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--green); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-check-double'></i> ${completedStockInsQty} units received
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-check-shield'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 5. Inventory Alerts -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('inventory')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Inventory Alerts</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(lowStockCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${lowStockCount > 0 ? 'var(--red)' : 'var(--text-light)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx ${lowStockCount > 0 ? 'bx-error-circle' : 'bx-check'}'></i> ${lowStockCount > 0 ? 'Low stock items' : 'Healthy inventory'}
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(239, 68, 68, 0.12); color: #dc2626; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-error'></i>
                            </div>
                        </div>
                    </div>
                `;

                // ==========================================
                // ROW 2 to ROW 6: CONTENT CONTAINER
                // ==========================================
                contentContainer.innerHTML = `
                    <!-- ========================================== -->
                    <!-- SECTION 1: NEEDS YOUR ATTENTION            -->
                    <!-- ========================================== -->
                    <div class="section-title" style="margin-top: 2rem; margin-bottom: 1rem;">
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text);">Needs Your Attention</h3>
                                ${attentionItems.length > 0 ? `
                                    <span class="badge" style="background: var(--red-light); color: var(--red); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px;">
                                        ${attentionItems.length} ACTION${attentionItems.length > 1 ? 'S' : ''} REQUIRED
                                    </span>
                                ` : ''}
                            </div>
                            <span style="font-size: 12.5px; color: var(--text-secondary);">Delivered shipments awaiting goods receipt &amp; stock verification</span>
                        </div>
                    </div>

                    ${attentionItems.length > 0 ? `
                        <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 2rem;">
                            ${attentionItems.map(item => `
                                <div class="card" style="padding: 1rem 1.25rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
                                    <div style="display: flex; align-items: center; gap: 14px; min-width: 240px; flex: 1;">
                                        <div style="width: 42px; height: 42px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;">
                                            <i class='bx bx-download'></i>
                                        </div>
                                        <div>
                                            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                                <span style="font-weight: 700; font-size: 14px; color: var(--text);">${Utils.escapeHtml(item.title)}</span>
                                                <span class="badge" style="font-size: 10.5px !important; padding: 2px 7px; background: ${item.receiving_status === 'Partially Received' ? 'rgba(245, 158, 11, 0.12)' : 'var(--red-light)'}; color: ${item.receiving_status === 'Partially Received' ? '#d97706' : 'var(--red)'}; border-radius: 4px; font-weight: 600;">
                                                    ${item.receiving_status}
                                                </span>
                                            </div>
                                            <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 3px;">
                                                ${Utils.escapeHtml(item.description)}
                                                ${item.total_expected > 0 ? ` • <span style="font-weight: 600; color: #059669;">Received ${item.total_received} / ${item.total_expected} units (${item.total_remaining} remaining)</span>` : ''}
                                            </div>
                                        </div>
                                    </div>
                                    <button class="btn btn-primary" style="padding: 7px 16px; font-size: 12.5px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; border-radius: 6px; background: #059669; border-color: #059669;" onclick="App.navigate('shipments')">
                                        ${item.action_label} <i class='bx bx-right-arrow-alt'></i>
                                    </button>
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div class="card" style="padding: 1.5rem 1.75rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); display: flex; align-items: center; gap: 16px; margin-bottom: 2rem;">
                            <div style="width: 44px; height: 44px; border-radius: 50%; background: var(--green-light); color: var(--green); display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0;">
                                <i class='bx bx-check-circle'></i>
                            </div>
                            <div>
                                <h4 style="margin: 0; font-size: 15px; font-weight: 600; color: var(--text);">You're all caught up. 🎉</h4>
                                <p style="margin: 4px 0 0 0; font-size: 13px; color: var(--text-secondary);">No pending receiving tasks assigned to you. All delivered shipments have been processed.</p>
                            </div>
                        </div>
                    `}

                    <!-- ========================================== -->
                    <!-- SECTION 2: ASSIGNED SHIPMENTS TABLE        -->
                    <!-- ========================================== -->
                    <div class="section-title" style="margin-top: 1.5rem; margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text);">Assigned Shipments</h3>
                                <p style="margin: 2px 0 0 0; font-size: 13px; color: var(--text-secondary);">Deliveries assigned to you for warehouse verification &amp; receiving</p>
                            </div>
                            <button class="btn btn-sm" style="background: transparent; border: 1px solid var(--border); color: var(--primary); font-size: 12.5px; font-weight: 600; padding: 4px 10px; border-radius: 6px; cursor: pointer;" onclick="App.navigate('shipments')">
                                View In Shipments <i class='bx bx-right-arrow-alt'></i>
                            </button>
                        </div>
                    </div>

                    <div class="card table-responsive" style="border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); overflow: hidden; margin-bottom: 2rem;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left;">
                            <thead>
                                <tr style="background: var(--bg-surface, #f9fafb); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
                                    <th style="padding: 12px 16px;">SHIPMENT #</th>
                                    <th style="padding: 12px 16px;">PURCHASE ORDER</th>
                                    <th style="padding: 12px 16px;">SUPPLIER</th>
                                    <th style="padding: 12px 16px;">STATUS</th>
                                    <th style="padding: 12px 16px;">RECEIVING STATUS</th>
                                    <th style="padding: 12px 16px;">PROGRESS</th>
                                    <th style="padding: 12px 16px; text-align: center;">ACTION</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${assignedShipments.length > 0 ? assignedShipments.slice(0, 8).map(s => {
                                    const expQty = s.total_expected_quantity || 0;
                                    const recQty = s.total_received_quantity || 0;
                                    const pct = expQty > 0 ? Math.min(100, Math.round((recQty / expQty) * 100)) : (s.receiving_status === 'Fully Received' ? 100 : 0);
                                    
                                    let statusColor = '#2563eb';
                                    let statusBg = 'rgba(59, 130, 246, 0.1)';
                                    if (s.status === 'Delivered') { statusColor = '#059669'; statusBg = 'rgba(16, 185, 129, 0.1)'; }
                                    else if (s.status === 'In Transit' || s.status === 'Dispatched') { statusColor = '#7c3aed'; statusBg = 'rgba(139, 92, 246, 0.1)'; }

                                    let recBadge = '';
                                    if (s.receiving_status === 'Fully Received') {
                                        recBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.12); color: #059669; font-size: 11px; padding: 2px 7px; border-radius: 4px; font-weight: 600;"><i class='bx bx-check-double'></i> Fully Received</span>`;
                                    } else if (s.receiving_status === 'Partially Received') {
                                        recBadge = `<span class="badge" style="background: rgba(245, 158, 11, 0.12); color: #d97706; font-size: 11px; padding: 2px 7px; border-radius: 4px; font-weight: 600;"><i class='bx bx-pie-chart-alt'></i> Partially Received</span>`;
                                    } else {
                                        recBadge = `<span class="badge" style="background: rgba(107, 114, 128, 0.1); color: #64748b; font-size: 11px; padding: 2px 7px; border-radius: 4px; font-weight: 500;"><i class='bx bx-time'></i> Pending Receipt</span>`;
                                    }

                                    return `
                                        <tr style="border-bottom: 1px solid #edf0ef; font-size: 13px;">
                                            <td style="padding: 12px 16px;">
                                                <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(s.shipment_number)}</div>
                                                <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${Utils.escapeHtml(s.carrier || '')} ${s.tracking_number ? `• ${Utils.escapeHtml(s.tracking_number)}` : ''}</div>
                                            </td>
                                            <td style="padding: 12px 16px;">
                                                <span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; border-radius: 4px; background: rgba(59, 130, 246, 0.08); color: #2563eb; font-size: 11.5px; font-weight: 600;">
                                                    PO #${s.purchase_order_id}
                                                </span>
                                            </td>
                                            <td style="padding: 12px 16px; font-weight: 500; color: var(--text);">
                                                ${Utils.escapeHtml(s.supplier_name || 'Supplier')}
                                            </td>
                                            <td style="padding: 12px 16px;">
                                                <span class="badge" style="background: ${statusBg}; color: ${statusColor}; font-size: 11px; padding: 2px 7px; border-radius: 4px; font-weight: 600;">
                                                    ${s.status}
                                                </span>
                                            </td>
                                            <td style="padding: 12px 16px;">
                                                ${recBadge}
                                            </td>
                                            <td style="padding: 12px 16px; min-width: 140px;">
                                                <div style="display: flex; justify-content: space-between; font-size: 11.5px; margin-bottom: 4px; font-weight: 600; color: var(--text);">
                                                    <span>${recQty}/${expQty} units</span>
                                                    <span>${pct}%</span>
                                                </div>
                                                <div style="width: 100%; height: 6px; background: #f1f5f9; border-radius: 999px; overflow: hidden;">
                                                    <div style="width: ${pct}%; height: 100%; background: ${pct === 100 ? '#059669' : (pct > 0 ? '#d97706' : '#94a3b8')}; border-radius: 999px;"></div>
                                                </div>
                                            </td>
                                            <td style="padding: 12px 16px; text-align: center;">
                                                ${s.can_stock_in ? `
                                                    <button class="btn btn-sm" style="background: #059669; color: white; border: none; padding: 5px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" onclick="App.navigate('shipments')">
                                                        <i class='bx bx-download'></i> Receive
                                                    </button>
                                                ` : `
                                                    <button class="btn btn-icon-small" title="View Shipment" style="background: white; border: 1px solid var(--border); border-radius: 6px; padding: 4px 6px; cursor: pointer; color: var(--text-secondary);" onclick="App.navigate('shipments')">
                                                        <i class='bx bx-show' style="font-size: 15px;"></i>
                                                    </button>
                                                `}
                                            </td>
                                        </tr>
                                    `;
                                }).join('') : `
                                    <tr>
                                        <td colspan="7" style="padding: 32px 16px; text-align: center; color: var(--text-secondary);">
                                            <i class='bx bx-car' style="font-size: 32px; color: var(--text-light); display: block; margin-bottom: 6px;"></i>
                                            No shipments are currently assigned to you.
                                        </td>
                                    </tr>
                                `}
                            </tbody>
                        </table>
                    </div>

                    <!-- ========================================== -->
                    <!-- SECTION 3: QUICK ACTIONS                   -->
                    <!-- ========================================== -->
                    <div class="section-title" style="margin-top: 1.5rem; margin-bottom: 1rem;">
                        <div>
                            <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text);">Quick Actions</h3>
                            <p style="margin: 2px 0 0 0; font-size: 13px; color: var(--text-secondary);">Direct shortcuts to warehouse operations</p>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1.25rem; margin-bottom: 2rem;">
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('shipments')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-download'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Receive Stock</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${awaitingStockInCount} shipments awaiting</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>

                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('inventory')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #ea580c; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-upload'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Issue Stock</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">Perform Stock-Out</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>

                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('inventory')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-box'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">View Inventory</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${data.total_stock || 0} units in stock</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>

                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('stock-transactions')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-history'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Transactions</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">View stock history</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                    </div>

                    <!-- ========================================== -->
                    <!-- SECTION 4: RECENT STOCK ACTIVITY           -->
                    <!-- ========================================== -->
                    <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); margin-bottom: 2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">My Recent Stock Activity</h3>
                                <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Recent goods receipts and stock reductions performed by you</p>
                            </div>
                            <button class="btn btn-sm" style="background: transparent; border: 1px solid var(--border); color: var(--primary); font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 6px; cursor: pointer;" onclick="App.navigate('stock-transactions')">
                                View All Transactions →
                            </button>
                        </div>

                        ${recentTransactions.length > 0 ? `
                            <div style="display: flex; flex-direction: column; gap: 0.85rem;">
                                ${recentTransactions.map(tx => {
                                    const isStockIn = tx.transaction_type === 'STOCK_IN';
                                    const iconBg = isStockIn ? 'rgba(16, 185, 129, 0.12)' : 'rgba(234, 88, 12, 0.12)';
                                    const iconColor = isStockIn ? '#059669' : '#ea580c';
                                    const icon = isStockIn ? 'bx-download' : 'bx-upload';
                                    const typeLabel = isStockIn ? 'STOCK_IN' : 'STOCK_OUT';
                                    const qtyPrefix = isStockIn ? '+' : '-';
                                    const qtyColor = isStockIn ? '#059669' : '#ea580c';

                                    return `
                                        <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; border-radius: 8px; background: #fbfcfc; border: 1px solid #edf0ef; flex-wrap: wrap; gap: 8px;">
                                            <div style="display: flex; align-items: center; gap: 12px;">
                                                <div style="width: 34px; height: 34px; border-radius: 8px; background: ${iconBg}; color: ${iconColor}; display: flex; align-items: center; justify-content: center; font-size: 17px; flex-shrink: 0;">
                                                    <i class='bx ${icon}'></i>
                                                </div>
                                                <div>
                                                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                                        <span style="font-weight: 600; font-size: 13px; color: var(--text);">${Utils.escapeHtml(tx.product_name)}</span>
                                                        <span class="badge" style="font-size: 10px !important; padding: 1px 6px; background: ${iconBg}; color: ${iconColor}; font-weight: 700;">
                                                            ${typeLabel}
                                                        </span>
                                                        ${tx.sku ? `<span style="font-size: 11px; color: var(--text-light); font-family: monospace;">(${Utils.escapeHtml(tx.sku)})</span>` : ''}
                                                    </div>
                                                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                                                        ${tx.shipment_number ? `<span style="font-weight: 500; color: #2563eb;">Shipment ${Utils.escapeHtml(tx.shipment_number)}</span> • ` : ''}
                                                        ${Utils.escapeHtml(tx.notes || 'Recorded stock movement')}
                                                    </div>
                                                </div>
                                            </div>
                                            <div style="text-align: right;">
                                                <div style="font-weight: 700; font-size: 14px; color: ${qtyColor};">${qtyPrefix}${tx.quantity} units</div>
                                                <div style="font-size: 11px; color: var(--text-light); margin-top: 2px;">${tx.transaction_date ? Utils.formatDate(tx.transaction_date) : ''}</div>
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        ` : `
                            <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                                No recent stock activity.
                            </div>
                        `}
                    </div>

                    <!-- ========================================== -->
                    <!-- SECTION 5: RESPONSIVE TWO-COLUMN GRID      -->
                    <!-- Left: Low Stock | Right: My Tasks & Alerts -->
                    <!-- ========================================== -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        <!-- Low Stock Products (Read-Only) -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Low Stock Products</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Warehouse items below reorder threshold</p>
                                </div>
                                <span class="badge" style="background: var(--red-light); color: var(--red); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px;">
                                    ${lowStockProducts.length} Alert${lowStockProducts.length === 1 ? '' : 's'}
                                </span>
                            </div>

                            <div style="overflow-x: auto;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 12.5px;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 10px 12px; font-weight: 600; color: var(--text-secondary);">PRODUCT</th>
                                            <th style="padding: 10px 12px; font-weight: 600; color: var(--text-secondary); text-align: right;">CURRENT</th>
                                            <th style="padding: 10px 12px; font-weight: 600; color: var(--text-secondary); text-align: right;">REORDER</th>
                                            <th style="padding: 10px 12px; font-weight: 600; color: var(--text-secondary); text-align: center;">STATUS</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${lowStockProducts.length > 0 ? lowStockProducts.slice(0, 6).map(p => `
                                            <tr style="border-bottom: 1px solid #edf0ef;">
                                                <td style="padding: 10px 12px;">
                                                    <div style="font-weight: 600; color: var(--text);">${Utils.escapeHtml(p.product_name)}</div>
                                                    ${p.sku ? `<div style="font-size: 11px; color: var(--text-light); font-family: monospace;">${Utils.escapeHtml(p.sku)}</div>` : ''}
                                                </td>
                                                <td style="padding: 10px 12px; text-align: right; color: var(--red); font-weight: 700;">
                                                    ${p.quantity_available}
                                                </td>
                                                <td style="padding: 10px 12px; text-align: right; color: var(--text-secondary);">
                                                    ${p.reorder_level}
                                                </td>
                                                <td style="padding: 10px 12px; text-align: center;">
                                                    <span class="badge" style="font-size: 10.5px !important; padding: 2px 6px; background: ${p.quantity_available <= 0 ? 'var(--red-light)' : 'var(--yellow-light)'}; color: ${p.quantity_available <= 0 ? 'var(--red)' : 'var(--yellow)'}; font-weight: 600;">
                                                        ${p.stock_status || (p.quantity_available <= 0 ? 'Out of Stock' : 'Low Stock')}
                                                    </span>
                                                </td>
                                            </tr>
                                        `).join('') : `
                                            <tr>
                                                <td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">
                                                    <i class='bx bx-check-shield' style="font-size: 24px; color: var(--green); display: block; margin-bottom: 4px;"></i>
                                                    Inventory levels are healthy.
                                                </td>
                                            </tr>
                                        `}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- My Tasks & Notifications -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">My Tasks &amp; Notices</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Notifications and assignment updates</p>
                                </div>
                                <span class="badge" style="background: var(--blue-light); color: var(--blue); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px;">
                                    ${tasks.length} Active
                                </span>
                            </div>

                            <div style="overflow-x: auto;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 12.5px;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 10px 12px; font-weight: 600; color: var(--text-secondary);">NOTICE</th>
                                            <th style="padding: 10px 12px; font-weight: 600; color: var(--text-secondary); text-align: right;">DATE</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${tasks.length > 0 ? tasks.slice(0, 6).map(t => {
                                            const isShipmentNotice = (t.title && t.title.toLowerCase().includes('shipment')) || (t.message && t.message.toLowerCase().includes('shipment'));
                                            return `
                                                <tr style="border-bottom: 1px solid #edf0ef; cursor: ${isShipmentNotice ? 'pointer' : 'default'};" ${isShipmentNotice ? 'onclick="App.navigate(\'shipments\')"' : ''}>
                                                    <td style="padding: 10px 12px;">
                                                        <div style="font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 6px;">
                                                            <i class='bx ${isShipmentNotice ? 'bx-car text-primary' : 'bx-bell'}' style="font-size: 14px;"></i>
                                                            ${Utils.escapeHtml(t.title)}
                                                        </div>
                                                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 3px;">
                                                            ${Utils.escapeHtml(t.message)}
                                                        </div>
                                                    </td>
                                                    <td style="padding: 10px 12px; color: var(--text-light); font-size: 11px; text-align: right; white-space: nowrap; vertical-align: top;">
                                                        ${t.created_at ? new Date(t.created_at).toLocaleDateString() : ''}
                                                    </td>
                                                </tr>
                                            `;
                                        }).join('') : `
                                            <tr>
                                                <td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">
                                                    <i class='bx bx-party' style="font-size: 24px; color: var(--primary); display: block; margin-bottom: 4px;"></i>
                                                    You have no pending tasks! 🎉
                                                </td>
                                            </tr>
                                        `}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    ${updateUsernameHtml}
                `;
            } catch (err) {
                console.error("Failed to load employee dashboard:", err);
                statsContainer.innerHTML = `
                    <div class="card" style="grid-column: 1 / -1; padding: 24px; color: var(--red); text-align: center; border: 1px solid var(--border); border-radius: 12px;">
                        <i class='bx bx-error-circle' style="font-size: 28px; margin-bottom: 6px; display: block;"></i>
                        <strong>Unable to load dashboard data.</strong>
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
            // Personalize greeting
            const pageHeaderTitle = document.querySelector('.page-header h1');
            const pageHeaderSub = document.querySelector('.page-header p');
            if (pageHeaderTitle) {
                pageHeaderTitle.innerHTML = `Welcome back, ${Utils.escapeHtml(user.username)} 👋`;
            }
            if (pageHeaderSub) {
                pageHeaderSub.textContent = "Here's an overview of your warehouse operations.";
            }

            // Loading state
            statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(220px, 1fr))';
            statsContainer.innerHTML = `
                <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--white); min-height: 90px; display: flex; align-items: center; justify-content: center; grid-column: 1 / -1;">
                    <div style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 13.5px;">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 20px; color: var(--primary);"></i> Loading warehouse metrics...
                    </div>
                </div>
            `;
            contentContainer.innerHTML = `
                <div style="display: flex; justify-content: center; align-items: center; padding: 40px; color: var(--text-secondary); gap: 10px;">
                    <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; color: var(--primary);"></i>
                    <span>Loading manager workspace...</span>
                </div>
            `;

            try {
                const data = await Api.get('/dashboard/manager');

                const activePos = data.active_pos || 0;
                const pendingPoVal = data.pending_po_value || 0;
                const lowStockCount = data.low_stock_count || 0;
                const pendingQuotations = data.pending_quotations || 0;
                const pendingDeliveries = data.pending_deliveries || 0;

                const shipmentStats = data.shipment_stats || {};
                const attentionItems = data.attention_items || [];
                const recentOrders = data.recent_orders || [];
                const criticalLowStock = data.critical_low_stock || [];
                const stockRequestsOverview = data.stock_requests_overview || {};
                const recentStockRequests = data.recent_stock_requests || [];
                const recentTransactions = data.recent_transactions || [];
                const recentActivity = data.recent_activity || [];

                // ==========================================
                // ROW 1: TOP 5 PRIMARY KPI CARDS
                // ==========================================
                statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(210px, 1fr))';
                statsContainer.innerHTML = `
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('purchase-orders')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Active Purchase Orders</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(activePos).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--blue); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-briefcase'></i> Currently active
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-briefcase'></i>
                            </div>
                        </div>
                    </div>

                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('purchase-orders')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Pending PO Value</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">₹${Number(pendingPoVal).toLocaleString('en-IN')}</div>
                                <div style="font-size: 12px; color: var(--purple); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-time'></i> Awaiting fulfillment
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-rupee'></i>
                            </div>
                        </div>
                    </div>

                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('inventory')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Low Stock Alerts</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(lowStockCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${lowStockCount > 0 ? 'var(--red)' : 'var(--text-light)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx ${lowStockCount > 0 ? 'bx-error-circle' : 'bx-check'}'></i> Requires action
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(239, 68, 68, 0.12); color: #dc2626; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-box'></i>
                            </div>
                        </div>
                    </div>

                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('quotations')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Pending Quotations</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(pendingQuotations).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${pendingQuotations > 0 ? '#d97706' : 'var(--text-light)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx ${pendingQuotations > 0 ? 'bx-time-five' : 'bx-check'}'></i> Awaiting review
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-file'></i>
                            </div>
                        </div>
                    </div>

                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('shipments')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Pending Deliveries</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(pendingDeliveries).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${pendingDeliveries > 0 ? 'var(--green)' : 'var(--text-light)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-car'></i> Awaiting stock-in
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-package'></i>
                            </div>
                        </div>
                    </div>
                `;

                // ==========================================
                // ROW 2 to ROW 7: CONTENT CONTAINER
                // ==========================================
                contentContainer.innerHTML = `
                    <!-- ROW 2: NEEDS YOUR ATTENTION -->
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
                            <span style="font-size: 12.5px; color: var(--text-secondary);">Direct operational items requiring manager review or approval</span>
                        </div>
                    </div>

                    ${attentionItems.length > 0 ? `
                        <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 2rem;">
                            ${attentionItems.map(item => {
                                const isUrgent = item.priority === 'Urgent';
                                const iconClass = item.type === 'quotation' 
                                    ? 'bx-file' 
                                    : (item.type === 'low_stock' ? 'bx-error-circle' : 'bx-package');
                                const iconBg = item.type === 'quotation' 
                                    ? 'rgba(245, 158, 11, 0.12)' 
                                    : (item.type === 'low_stock' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.12)');
                                const iconColor = item.type === 'quotation' 
                                    ? '#d97706' 
                                    : (item.type === 'low_stock' ? '#dc2626' : '#059669');
                                const badgeBg = isUrgent || item.type === 'low_stock' ? 'var(--red-light)' : (item.type === 'delivery' ? 'var(--green-light)' : 'var(--yellow-light)');
                                const badgeColor = isUrgent || item.type === 'low_stock' ? 'var(--red)' : (item.type === 'delivery' ? 'var(--green)' : 'var(--yellow)');

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
                                <p style="margin: 4px 0 0 0; font-size: 13px; color: var(--text-secondary);">No pending quotations, low-stock breaches, or shipments waiting for receiving at this time.</p>
                            </div>
                        </div>
                    `}

                    <!-- ROW 3: RECENT POs & SHIPMENT STATUS -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        <!-- Recent Purchase Orders -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Recent Purchase Orders</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Latest official procurement contracts</p>
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
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">SUPPLIER</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">DATE</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">TOTAL</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">STATUS</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary); text-align: right;">ACTION</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${recentOrders.length > 0 ? recentOrders.map(o => `
                                            <tr style="border-bottom: 1px solid #edf0ef;">
                                                <td style="padding: 12px 14px; font-weight: 700; font-size: 13px; color: var(--primary);">PO #${o.purchase_order_id}</td>
                                                <td style="padding: 12px 14px; font-size: 12.5px; color: var(--text);">${Utils.escapeHtml(o.supplier_name)}</td>
                                                <td style="padding: 12px 14px; color: var(--text-secondary); font-size: 12px;">${o.order_date ? Utils.formatDate(o.order_date) : 'N/A'}</td>
                                                <td style="padding: 12px 14px; font-weight: 700; font-size: 13px; color: var(--text);">₹${Number(o.total_amount || 0).toLocaleString('en-IN')}</td>
                                                <td style="padding: 12px 14px;">
                                                    <span class="badge" style="font-size: 10.5px !important; background: ${o.status === 'Delivered' ? 'var(--green-light)' : (o.status === 'Accepted' ? 'var(--blue-light)' : (o.status === 'Cancelled' || o.status === 'Rejected' ? 'var(--red-light)' : 'var(--yellow-light)'))}; color: ${o.status === 'Delivered' ? 'var(--green)' : (o.status === 'Accepted' ? 'var(--blue)' : (o.status === 'Cancelled' || o.status === 'Rejected' ? 'var(--red)' : 'var(--yellow)'))};">
                                                        ${o.status}
                                                    </span>
                                                </td>
                                                <td style="padding: 12px 14px; text-align: right;">
                                                    <button class="btn" style="background: var(--primary-light); color: var(--primary); padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 4px; border: none; cursor: pointer;" onclick="App.navigate('purchase-orders')">
                                                        View
                                                    </button>
                                                </td>
                                            </tr>
                                        `).join('') : '<tr><td colspan="6" style="padding: 28px; text-align: center; color: var(--text-secondary); font-size: 13px;">No active purchase orders.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Shipment Status Widget -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Shipment Status</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Fulfillment & incoming goods tracking</p>
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
                                    <div style="font-size: 11px; color: #3b82f6; margin-top: 2px;">Left supplier</div>
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
                                    <div style="font-size: 11px; color: #10b981; margin-top: 2px;">At warehouse bay</div>
                                </div>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 0.75rem; border-top: 1px solid var(--border); font-size: 12.5px; color: var(--text-secondary);">
                                <span>Total Shipments Logged: <strong style="color: var(--text);">${shipmentStats.total || 0}</strong></span>
                                <span style="color: var(--primary); cursor: pointer;" onclick="App.navigate('shipments')">Manage Receiving →</span>
                            </div>
                        </div>
                    </div>

                    <!-- ROW 4: CRITICAL LOW STOCK & STOCK REQUESTS OVERVIEW -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        <!-- Low Stock Critical Inventory -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Low Stock Inventory</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Products requiring urgent warehouse replenishment</p>
                                </div>
                                <button class="btn" style="color: var(--primary); font-weight: 600; font-size: 12.5px; padding: 0; background: none; border: none; cursor: pointer; display: flex; align-items: center; gap: 4px;" onclick="App.navigate('inventory')">
                                    View All Inventory <i class='bx bx-right-arrow-alt'></i>
                                </button>
                            </div>
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">PRODUCT</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">SKU</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">STOCK</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">MIN LEVEL</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary);">STATUS</th>
                                            <th style="padding: 12px 14px; font-weight: 600; font-size: 11.5px; color: var(--text-secondary); text-align: right;">ACTION</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${criticalLowStock.length > 0 ? criticalLowStock.map(p => `
                                            <tr style="border-bottom: 1px solid #edf0ef;">
                                                <td style="padding: 12px 14px; font-weight: 700; font-size: 12.5px; color: var(--text);">${Utils.escapeHtml(p.product_name)}</td>
                                                <td style="padding: 12px 14px; font-size: 12px; color: var(--text-secondary);">${Utils.escapeHtml(p.sku)}</td>
                                                <td style="padding: 12px 14px; font-weight: 700; font-size: 13px; color: var(--red);">${p.quantity_available}</td>
                                                <td style="padding: 12px 14px; font-size: 12.5px; color: var(--text-secondary);">${p.reorder_level}</td>
                                                <td style="padding: 12px 14px;">
                                                    <span class="badge" style="font-size: 10px !important; padding: 2px 6px; background: var(--red-light); color: var(--red);">
                                                        ${p.status}
                                                    </span>
                                                </td>
                                                <td style="padding: 12px 14px; text-align: right;">
                                                    <button class="btn" style="background: var(--primary-light); color: var(--primary); padding: 4px 10px; font-size: 11px; font-weight: 600; border-radius: 4px; border: none; cursor: pointer;" onclick="App.navigate('stock-requests')">
                                                        Restock
                                                    </button>
                                                </td>
                                            </tr>
                                        `).join('') : '<tr><td colspan="6" style="padding: 28px; text-align: center; color: var(--green); font-size: 13px;"><i class="bx bx-check-circle" style="font-size: 16px; vertical-align: middle;"></i> Inventory levels are healthy.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Stock Requests Overview -->
                        <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white);">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Stock Requests Overview</h3>
                                    <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Supplier restock request lifecycle</p>
                                </div>
                                <button class="btn" style="color: var(--primary); font-weight: 600; font-size: 12.5px; padding: 0; background: none; border: none; cursor: pointer; display: flex; align-items: center; gap: 4px;" onclick="App.navigate('stock-requests')">
                                    View All Stock Requests <i class='bx bx-right-arrow-alt'></i>
                                </button>
                            </div>
                            <!-- Mini Counters -->
                            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.65rem; margin-bottom: 1rem;">
                                <div style="padding: 0.65rem; border-radius: 8px; background: #f8fafc; border: 1px solid var(--border); text-align: center;">
                                    <div style="font-size: 10.5px; font-weight: 600; color: var(--text-secondary);">PENDING</div>
                                    <div style="font-size: 18px; font-weight: 700; color: var(--text);">${stockRequestsOverview.pending || 0}</div>
                                </div>
                                <div style="padding: 0.65rem; border-radius: 8px; background: #eff6ff; border: 1px solid #bfdbfe; text-align: center;">
                                    <div style="font-size: 10.5px; font-weight: 600; color: #1e40af;">QUOTED</div>
                                    <div style="font-size: 18px; font-weight: 700; color: #1d4ed8;">${stockRequestsOverview.quoted || 0}</div>
                                </div>
                                <div style="padding: 0.65rem; border-radius: 8px; background: #fef2f2; border: 1px solid #fecaca; text-align: center;">
                                    <div style="font-size: 10.5px; font-weight: 600; color: #991b1b;">REJECTED</div>
                                    <div style="font-size: 18px; font-weight: 700; color: #dc2626;">${stockRequestsOverview.rejected || 0}</div>
                                </div>
                                <div style="padding: 0.65rem; border-radius: 8px; background: var(--primary-light); border: 1px solid rgba(7, 143, 114, 0.2); text-align: center;">
                                    <div style="font-size: 10.5px; font-weight: 600; color: var(--primary);">TOTAL</div>
                                    <div style="font-size: 18px; font-weight: 700; color: var(--primary);">${stockRequestsOverview.total || 0}</div>
                                </div>
                            </div>
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                    <thead>
                                        <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                            <th style="padding: 10px 12px; font-weight: 600; font-size: 11px; color: var(--text-secondary);">REQ ID</th>
                                            <th style="padding: 10px 12px; font-weight: 600; font-size: 11px; color: var(--text-secondary);">PRODUCT</th>
                                            <th style="padding: 10px 12px; font-weight: 600; font-size: 11px; color: var(--text-secondary);">QTY</th>
                                            <th style="padding: 10px 12px; font-weight: 600; font-size: 11px; color: var(--text-secondary);">PRIORITY</th>
                                            <th style="padding: 10px 12px; font-weight: 600; font-size: 11px; color: var(--text-secondary); text-align: right;">STATUS</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${recentStockRequests.length > 0 ? recentStockRequests.map(sr => `
                                            <tr style="border-bottom: 1px solid #edf0ef;">
                                                <td style="padding: 10px 12px; font-weight: 700; font-size: 12px; color: var(--text);">${Utils.escapeHtml(sr.request_number)}</td>
                                                <td style="padding: 10px 12px; font-size: 12px; color: var(--text); max-width: 120px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${Utils.escapeHtml(sr.primary_product)}</td>
                                                <td style="padding: 10px 12px; font-weight: 700; font-size: 12px;">${sr.total_quantity}</td>
                                                <td style="padding: 10px 12px;">
                                                    <span class="badge" style="font-size: 9.5px !important; padding: 2px 5px; background: ${sr.priority === 'Urgent' ? 'var(--red-light)' : (sr.priority === 'High' ? 'var(--yellow-light)' : 'var(--blue-light)')}; color: ${sr.priority === 'Urgent' ? 'var(--red)' : (sr.priority === 'High' ? 'var(--yellow)' : 'var(--blue)')};">
                                                        ${sr.priority}
                                                    </span>
                                                </td>
                                                <td style="padding: 10px 12px; text-align: right;">
                                                    <span class="badge" style="font-size: 9.5px !important; padding: 2px 5px; background: ${sr.status === 'Quoted' ? 'var(--green-light)' : (sr.status === 'Rejected' ? 'var(--red-light)' : 'var(--yellow-light)')}; color: ${sr.status === 'Quoted' ? 'var(--green)' : (sr.status === 'Rejected' ? 'var(--red)' : 'var(--yellow)')};">
                                                        ${sr.status}
                                                    </span>
                                                </td>
                                            </tr>
                                        `).join('') : '<tr><td colspan="5" style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 12px;">No stock requests found.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- ROW 5: RECENT STOCK MOVEMENTS -->
                    <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); margin-bottom: 2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                            <div>
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Recent Stock Movements</h3>
                                <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Latest warehouse Stock-In and Stock-Out operations</p>
                            </div>
                            <button class="btn" style="color: var(--primary); font-weight: 600; font-size: 12.5px; padding: 0; background: none; border: none; cursor: pointer; display: flex; align-items: center; gap: 4px;" onclick="App.navigate('stock-transactions')">
                                View All Transactions <i class='bx bx-right-arrow-alt'></i>
                            </button>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; text-align: left; border-collapse: collapse;">
                                <thead>
                                    <tr style="background: #f7faf9; border-bottom: 1px solid var(--border);">
                                        <th style="padding: 14px 16px; font-weight: 600; font-size: 12px; color: var(--text-secondary);">PRODUCT</th>
                                        <th style="padding: 14px 16px; font-weight: 600; font-size: 12px; color: var(--text-secondary);">TYPE</th>
                                        <th style="padding: 14px 16px; font-weight: 600; font-size: 12px; color: var(--text-secondary);">QUANTITY</th>
                                        <th style="padding: 14px 16px; font-weight: 600; font-size: 12px; color: var(--text-secondary);">DATE</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${recentTransactions.length > 0 ? recentTransactions.map(t => `
                                        <tr style="border-bottom: 1px solid #edf0ef;">
                                            <td style="padding: 14px 16px; font-weight: 600; font-size: 13px;">${Utils.escapeHtml(t.product_name)}</td>
                                            <td style="padding: 14px 16px;">
                                                <span class="badge" style="background: var(${t.transaction_type === 'STOCK_IN' ? '--green-light' : '--red-light'}); color: var(${t.transaction_type === 'STOCK_IN' ? '--green' : '--red'}); font-weight: 600; font-size: 11px !important;">
                                                    ${t.transaction_type}
                                                </span>
                                            </td>
                                            <td style="padding: 14px 16px; font-weight: 700; font-size: 13px;">${t.quantity}</td>
                                            <td style="padding: 14px 16px; color: var(--text-secondary); font-size: 12.5px;">${t.transaction_date ? Utils.formatDate(t.transaction_date) : 'N/A'}</td>
                                        </tr>
                                    `).join('') : '<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">No recent stock movements.</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- ROW 6: QUICK ACTIONS -->
                    <div class="section-title" style="margin-top: 1.5rem; margin-bottom: 1rem;">
                        <div>
                            <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text);">Quick Actions</h3>
                            <p style="margin: 2px 0 0 0; font-size: 13px; color: var(--text-secondary);">Direct shortcuts to high-frequency manager operations</p>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.25rem; margin-bottom: 2rem;">
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('purchase-orders')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-plus-circle'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Create Purchase Order</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${activePos} active orders</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('quotations')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-file-blank'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Review Quotations</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${pendingQuotations} awaiting approval</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('stock-requests')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-git-pull-request'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Create Stock Request</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">Restock warehouse</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                        <div class="card stat-card" style="padding: 1.25rem; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid var(--border); border-radius: var(--radius); background: var(--white);" onclick="App.navigate('shipments')">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <div style="width: 40px; height: 40px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); color: #059669; display: flex; align-items: center; justify-content: center; font-size: 20px;"><i class='bx bx-package'></i></div>
                                <div>
                                    <div style="font-weight: 700; font-size: 13.5px; color: var(--text);">Receive Shipments</div>
                                    <div style="font-size: 11.5px; color: var(--text-light);">${pendingDeliveries} ready for stock-in</div>
                                </div>
                            </div>
                            <i class='bx bx-right-arrow-alt' style="color: var(--text-light); font-size: 18px;"></i>
                        </div>
                    </div>

                    <!-- ROW 7: RECENT OPERATIONAL ACTIVITY -->
                    <div class="card" style="padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--white); margin-bottom: 2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                            <div>
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text);">Recent Activity</h3>
                                <p style="font-size: 12.5px; color: var(--text-secondary); margin: 3px 0 0 0;">Timeline of recent status updates and order milestones</p>
                            </div>
                            <span style="font-size: 11.5px; color: var(--text-light);">Audit Trail</span>
                        </div>
                        ${recentActivity.length > 0 ? `
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
                console.error("Failed to load manager dashboard:", err);
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
        } else if (user.role === 'Owner') {
            // Personalize executive page header
            const pageHeaderTitle = document.querySelector('.page-header h1');
            const pageHeaderSub = document.querySelector('.page-header p');
            const pageHeaderEyebrow = document.querySelector('.page-header .eyebrow');
            if (pageHeaderEyebrow) {
                pageHeaderEyebrow.textContent = 'EXECUTIVE COMMAND CENTER';
            }
            if (pageHeaderTitle) {
                pageHeaderTitle.innerHTML = `Welcome back, ${Utils.escapeHtml(user.username)} 👑`;
            }
            if (pageHeaderSub) {
                pageHeaderSub.textContent = "Organization-wide overview of inventory, procurement, financials & system health.";
            }

            // Loading state
            statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(220px, 1fr))';
            statsContainer.innerHTML = `
                <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--white); min-height: 90px; display: flex; align-items: center; justify-content: center; grid-column: 1 / -1;">
                    <div style="display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: 13.5px;">
                        <i class='bx bx-loader-alt bx-spin' style="font-size: 20px; color: var(--primary);"></i> Loading executive command center...
                    </div>
                </div>
            `;
            contentContainer.innerHTML = `
                <div style="display: flex; justify-content: center; align-items: center; padding: 40px; color: var(--text-secondary); gap: 10px;">
                    <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; color: var(--primary);"></i>
                    <span>Loading enterprise workspace...</span>
                </div>
            `;

            try {
                const data = await Api.get('/dashboard/owner');

                const totalInventoryVal = Number(data.total_inventory_value || 0);
                const activePos = data.active_pos_count || 0;
                const activePosVal = Number(data.active_pos_value || 0);
                const pendingQuotes = data.pending_quotations_count || 0;
                const lowStockCount = data.low_stock_count || 0;
                const activeUsers = data.active_users_count || 0;
                const totalUsers = data.total_users || 0;
                const totalSuppliers = data.total_suppliers || 0;
                const attentionItems = data.attention_items || [];
                const recentOrders = data.recent_orders || [];
                const shipmentStats = data.shipment_stats || {};
                const invHealth = data.inventory_health || {};
                const usersByRole = data.users_by_role || {};
                const poBreakdown = data.po_status_breakdown || {};
                const latestBackup = data.latest_backup || null;
                const recentAudits = data.recent_audits || [];

                // ==========================================
                // 1. TOP 5 PRIMARY EXECUTIVE KPI CARDS
                // ==========================================
                statsContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(220px, 1fr))';
                statsContainer.innerHTML = `
                    <!-- 1. Total Inventory Value -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('inventory')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Total Inventory Value</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">₹${totalInventoryVal.toLocaleString('en-IN')}</div>
                                <div style="font-size: 12px; color: var(--green); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-check-shield'></i> ${invHealth.total_products || data.total_products || 0} products (${invHealth.total_units || 0} units)
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(16, 185, 129, 0.12); color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-rupee'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 2. Active Purchase Orders -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('purchase-orders')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Active Purchase Orders</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(activePos).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--blue); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-time'></i> ₹${activePosVal.toLocaleString('en-IN')} committed
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(59, 130, 246, 0.12); color: #2563eb; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-briefcase'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 3. Pending Quotations -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('quotations')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Pending Quotations</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(pendingQuotes).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${pendingQuotes > 0 ? '#d97706' : 'var(--green)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx ${pendingQuotes > 0 ? 'bx-bell' : 'bx-check'}'></i> ${pendingQuotes > 0 ? 'Requires Owner review' : 'All resolved'}
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(245, 158, 11, 0.12); color: #d97706; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-file'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 4. Low Stock Alerts -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('inventory')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Inventory Alerts</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(lowStockCount).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: ${lowStockCount > 0 ? 'var(--red)' : 'var(--green)'}; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx ${lowStockCount > 0 ? 'bx-error-circle' : 'bx-check-circle'}'></i> ${lowStockCount > 0 ? 'Items below reorder point' : 'Inventory healthy'}
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(239, 68, 68, 0.12); color: #dc2626; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-package'></i>
                            </div>
                        </div>
                    </div>

                    <!-- 5. Organization Users -->
                    <div class="card stat-card" style="padding: 1.5rem; cursor: pointer; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); transition: transform 0.15s, box-shadow 0.15s;" onclick="App.navigate('users')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div>
                                <span style="font-size: 13px; font-weight: 500; color: var(--text-secondary); display: block; margin-bottom: 6px;">Organization Users</span>
                                <div style="font-size: 28px; font-weight: 700; color: var(--text);">${String(activeUsers).padStart(2, '0')}</div>
                                <div style="font-size: 12px; color: var(--purple); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                                    <i class='bx bx-user-check'></i> ${totalUsers} accounts (${totalSuppliers} suppliers)
                                </div>
                            </div>
                            <div style="width: 44px; height: 44px; border-radius: 10px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                                <i class='bx bx-group'></i>
                            </div>
                        </div>
                    </div>
                `;

                // ==========================================
                // 2. MAIN EXECUTIVE CONTENT
                // ==========================================
                contentContainer.innerHTML = `
                    <!-- Needs Your Attention Section -->
                    <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); margin-bottom: 2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                            <div>
                                <h3 style="font-size: 17px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                                    <i class='bx bx-error-circle' style="color: #ea580c; font-size: 20px;"></i> Needs Your Attention
                                </h3>
                                <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">Urgent items requiring Owner review, authorization, or restocking decisions.</p>
                            </div>
                            ${attentionItems.length > 0 ? `<span class="badge" style="background: #fff7ed; color: #c2410c; border: 1px solid #ffedd5; font-size: 12px; padding: 4px 10px; border-radius: 6px; font-weight: 600;">${attentionItems.length} action item${attentionItems.length > 1 ? 's' : ''}</span>` : ''}
                        </div>

                        ${attentionItems.length > 0 ? `
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                ${attentionItems.map(item => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-radius: 8px; background: var(--surface, #f8fafc); border: 1px solid var(--border); flex-wrap: wrap; gap: 10px;">
                                        <div style="display: flex; align-items: center; gap: 12px;">
                                            <div style="width: 38px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; ${item.type === 'quotation' ? 'background: #fef3c7; color: #b45309;' : item.type === 'low_stock' ? 'background: #fee2e2; color: #dc2626;' : 'background: #e0f2fe; color: #0284c7;'}">
                                                <i class='bx ${item.type === 'quotation' ? 'bx-file' : item.type === 'low_stock' ? 'bx-box' : 'bx-briefcase'}'></i>
                                            </div>
                                            <div>
                                                <div style="font-weight: 600; font-size: 13.5px; color: var(--text-primary);">${Utils.escapeHtml(item.title)}</div>
                                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${Utils.escapeHtml(item.subtitle)}</div>
                                            </div>
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 12px;">
                                            <span style="font-size: 11.5px; font-weight: 600; padding: 3px 8px; border-radius: 4px; ${item.badge_color === 'danger' ? 'background: #fee2e2; color: #dc2626;' : item.badge_color === 'warning' ? 'background: #fef3c7; color: #b45309;' : 'background: #e0f2fe; color: #0369a1;'}">${item.badge}</span>
                                            <button class="btn btn-sm btn-primary" onclick="App.navigate('${item.action_route}')" style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; font-size: 12px; font-weight: 600; border-radius: 6px;">
                                                ${item.action_label}
                                            </button>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div style="text-align: center; padding: 28px; color: var(--text-secondary);">
                                <i class='bx bx-check-double' style="font-size: 34px; color: var(--green); display: block; margin-bottom: 6px;"></i>
                                <strong style="font-size: 14px; color: var(--text-primary);">You're all caught up. 🎉</strong>
                                <div style="font-size: 12.5px; margin-top: 2px;">All quotations, orders, and inventory are in good standing.</div>
                            </div>
                        `}
                    </div>

                    <!-- Executive Quick Actions -->
                    <div class="card" style="padding: 1.25rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); margin-bottom: 2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <span style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary);">Executive Quick Actions</span>
                            <span style="font-size: 12px; color: var(--text-secondary);"><i class='bx bx-shield-quarter'></i> Authorized Admin Tools</span>
                        </div>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <button class="btn btn-secondary" onclick="App.navigate('users')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-user-plus'></i> Manage Users
                            </button>
                            <button class="btn btn-secondary" onclick="App.navigate('products')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-package'></i> Catalog
                            </button>
                            <button class="btn btn-secondary" onclick="App.navigate('quotations')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-file'></i> Quotations
                            </button>
                            <button class="btn btn-secondary" onclick="App.navigate('purchase-orders')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-receipt'></i> Purchase Orders
                            </button>
                            <button class="btn btn-secondary" onclick="App.navigate('inventory')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-box'></i> Inventory
                            </button>
                            <button class="btn btn-secondary" onclick="App.navigate('reports')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-bar-chart-alt-2'></i> Reports
                            </button>
                            <button class="btn btn-secondary" onclick="App.navigate('system-status')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-pulse'></i> System Health
                            </button>
                            <button class="btn btn-secondary" onclick="App.navigate('backups')" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 8px;">
                                <i class='bx bx-data'></i> Backups
                            </button>
                        </div>
                    </div>

                    <!-- Executive Overview Grid: Procurement & Inventory Health -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        
                        <!-- 1. Procurement & PO Status -->
                        <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <div>
                                    <h4 style="margin: 0; font-size: 15px; font-weight: 700; color: var(--text-primary);"><i class='bx bx-shopping-bag' style="color: var(--primary);"></i> Procurement Overview</h4>
                                    <span style="font-size: 12px; color: var(--text-secondary);">${data.total_pos_count || 0} Total Purchase Orders in System</span>
                                </div>
                                <button class="btn-link" onclick="App.navigate('purchase-orders')" style="font-size: 12px; color: var(--primary); font-weight: 600; background: none; border: none; cursor: pointer;">View All Orders →</button>
                            </div>

                            <!-- PO Status Pills -->
                            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 1.25rem;">
                                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 8px 10px; border-radius: 8px; text-align: center;">
                                    <span style="font-size: 11px; color: #15803d; font-weight: 600; display: block;">Accepted</span>
                                    <span style="font-size: 16px; font-weight: 700; color: #15803d;">${poBreakdown.Accepted?.count || 0}</span>
                                </div>
                                <div style="background: #eff6ff; border: 1px solid #bfdbfe; padding: 8px 10px; border-radius: 8px; text-align: center;">
                                    <span style="font-size: 11px; color: #1d4ed8; font-weight: 600; display: block;">Delivered</span>
                                    <span style="font-size: 16px; font-weight: 700; color: #1d4ed8;">${poBreakdown.Delivered?.count || 0}</span>
                                </div>
                                <div style="background: #fffbeb; border: 1px solid #fde68a; padding: 8px 10px; border-radius: 8px; text-align: center;">
                                    <span style="font-size: 11px; color: #b45309; font-weight: 600; display: block;">Pending</span>
                                    <span style="font-size: 16px; font-weight: 700; color: #b45309;">${poBreakdown.Pending?.count || 0}</span>
                                </div>
                                <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 8px 10px; border-radius: 8px; text-align: center;">
                                    <span style="font-size: 11px; color: #b91c1c; font-weight: 600; display: block;">Rejected</span>
                                    <span style="font-size: 16px; font-weight: 700; color: #b91c1c;">${poBreakdown.Rejected?.count || 0}</span>
                                </div>
                            </div>

                            <!-- Recent PO Mini Table -->
                            <div class="table-responsive" style="border: 1px solid var(--border); border-radius: 8px; overflow: hidden;">
                                <table class="table" style="width: 100%; border-collapse: collapse; font-size: 12.5px;">
                                    <thead>
                                        <tr style="background: var(--surface, #f8fafc); border-bottom: 1px solid var(--border); text-align: left; color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                            <th style="padding: 8px 12px;">PO ID</th>
                                            <th style="padding: 8px 12px;">Supplier</th>
                                            <th style="padding: 8px 12px; text-align: right;">Amount</th>
                                            <th style="padding: 8px 12px; text-align: center;">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${recentOrders.length > 0 ? recentOrders.map(po => `
                                            <tr style="border-bottom: 1px solid var(--border); cursor: pointer;" onclick="App.navigate('purchase-orders')">
                                                <td style="padding: 8px 12px; font-family: monospace; font-weight: 600;">#${po.purchase_order_id}</td>
                                                <td style="padding: 8px 12px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${Utils.escapeHtml(po.supplier_name)}</td>
                                                <td style="padding: 8px 12px; text-align: right; font-weight: 600;">₹${Number(po.total_amount).toLocaleString('en-IN')}</td>
                                                <td style="padding: 8px 12px; text-align: center;">
                                                    <span style="display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600; ${po.status === 'Accepted' || po.status === 'Delivered' ? 'background: #dcfce7; color: #15803d;' : po.status === 'Pending' ? 'background: #fef3c7; color: #b45309;' : 'background: #fee2e2; color: #b91c1c;'}">${po.status}</span>
                                                </td>
                                            </tr>
                                        `).join('') : `<tr><td colspan="4" style="text-align: center; padding: 20px; color: var(--text-secondary);">No recent purchase orders.</td></tr>`}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- 2. Inventory Health & Throughput -->
                        <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <div>
                                    <h4 style="margin: 0; font-size: 15px; font-weight: 700; color: var(--text-primary);"><i class='bx bx-layer' style="color: #8b5cf6;"></i> Inventory Health & Throughput</h4>
                                    <span style="font-size: 12px; color: var(--text-secondary);">Catalog valuation & warehouse movements</span>
                                </div>
                                <button class="btn-link" onclick="App.navigate('inventory')" style="font-size: 12px; color: var(--primary); font-weight: 600; background: none; border: none; cursor: pointer;">View Inventory →</button>
                            </div>

                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 1.25rem;">
                                <div style="background: var(--surface, #f8fafc); border: 1px solid var(--border); border-radius: 8px; padding: 12px;">
                                    <div style="font-size: 11px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Stock Units on Hand</div>
                                    <div style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${invHealth.total_units || 0}</div>
                                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">across ${invHealth.total_products || 0} active products</div>
                                </div>
                                <div style="background: var(--surface, #f8fafc); border: 1px solid var(--border); border-radius: 8px; padding: 12px;">
                                    <div style="font-size: 11px; text-transform: uppercase; color: var(--text-secondary); font-weight: 600;">Ledger Transactions</div>
                                    <div style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${invHealth.total_transactions || 0}</div>
                                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">historical movements</div>
                                </div>
                            </div>

                            <!-- Movement Flow Breakdown -->
                            <div style="border: 1px solid var(--border); border-radius: 8px; padding: 14px; background: var(--surface, #f8fafc);">
                                <div style="font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 10px;">Stock Movement Balance</div>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <span style="font-size: 12px; color: var(--text-secondary);"><i class='bx bx-down-arrow-alt' style="color: #16a34a;"></i> Total Received (Stock-In)</span>
                                    <strong style="color: #16a34a; font-size: 13px;">+${invHealth.received_units || 0} units</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span style="font-size: 12px; color: var(--text-secondary);"><i class='bx bx-up-arrow-alt' style="color: #dc2626;"></i> Total Issued (Stock-Out)</span>
                                    <strong style="color: #dc2626; font-size: 13px;">-${invHealth.issued_units || 0} units</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; padding-top: 8px; border-top: 1px dashed var(--border);">
                                    <span style="font-size: 12px; font-weight: 600; color: var(--text-primary);">Stock Alert Status</span>
                                    <span style="font-size: 12px; font-weight: 600; color: ${invHealth.low_stock_count > 0 ? '#ea580c' : '#16a34a'};">${invHealth.low_stock_count > 0 ? `${invHealth.low_stock_count} item(s) low` : 'All healthy'}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Row 3: Logistics, Users, & Infrastructure Telemetry -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        
                        <!-- 1. Shipments & Logistics -->
                        <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <h4 style="margin: 0; font-size: 14.5px; font-weight: 700; color: var(--text-primary);"><i class='bx bx-car' style="color: #0284c7;"></i> Logistics & Shipments</h4>
                                <button class="btn-link" onclick="App.navigate('shipments')" style="font-size: 12px; color: var(--primary); font-weight: 600; background: none; border: none; cursor: pointer;">Track →</button>
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; text-align: center; margin-bottom: 12px;">
                                <div style="padding: 10px 6px; border-radius: 8px; background: #e0f2fe; border: 1px solid #bae6fd;">
                                    <div style="font-size: 18px; font-weight: 800; color: #0369a1;">${shipmentStats.ready_for_shipment || 0}</div>
                                    <div style="font-size: 10.5px; color: #0369a1; font-weight: 600; margin-top: 2px;">Ready at Dock</div>
                                </div>
                                <div style="padding: 10px 6px; border-radius: 8px; background: #f3e8ff; border: 1px solid #e9d5ff;">
                                    <div style="font-size: 18px; font-weight: 800; color: #7e22ce;">${shipmentStats.in_transit || 0}</div>
                                    <div style="font-size: 10.5px; color: #7e22ce; font-weight: 600; margin-top: 2px;">In Transit</div>
                                </div>
                                <div style="padding: 10px 6px; border-radius: 8px; background: #dcfce7; border: 1px solid #bbf7d0;">
                                    <div style="font-size: 18px; font-weight: 800; color: #15803d;">${shipmentStats.delivered || 0}</div>
                                    <div style="font-size: 10.5px; color: #15803d; font-weight: 600; margin-top: 2px;">Delivered</div>
                                </div>
                            </div>
                            <div style="font-size: 12px; color: var(--text-secondary); text-align: center;">
                                Total tracked shipments: <strong>${shipmentStats.total_shipments || 0}</strong>
                            </div>
                        </div>

                        <!-- 2. Organization Users -->
                        <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <h4 style="margin: 0; font-size: 14.5px; font-weight: 700; color: var(--text-primary);"><i class='bx bx-group' style="color: #7c3aed;"></i> Organization Roles</h4>
                                <button class="btn-link" onclick="App.navigate('users')" style="font-size: 12px; color: var(--primary); font-weight: 600; background: none; border: none; cursor: pointer;">Manage Users →</button>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding-bottom: 6px; border-bottom: 1px solid var(--border);">
                                    <span style="color: var(--text-secondary);"><i class='bx bx-shield-quarter'></i> Owners</span>
                                    <strong>${usersByRole.Owner?.active || 0} active</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding-bottom: 6px; border-bottom: 1px solid var(--border);">
                                    <span style="color: var(--text-secondary);"><i class='bx bx-briefcase'></i> Managers</span>
                                    <strong>${usersByRole.Manager?.active || 0} active</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 12.5px; padding-bottom: 6px; border-bottom: 1px solid var(--border);">
                                    <span style="color: var(--text-secondary);"><i class='bx bx-user-pin'></i> Employees</span>
                                    <strong>${usersByRole.Employee?.active || 0} active <span style="font-size: 11px; color: var(--text-secondary);">(${usersByRole.Employee?.total || 0} total)</span></strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; font-size: 12.5px;">
                                    <span style="color: var(--text-secondary);"><i class='bx bx-buildings'></i> Suppliers</span>
                                    <strong>${usersByRole.Supplier?.active || 0} active</strong>
                                </div>
                            </div>
                        </div>

                        <!-- 3. Infrastructure & Backup Status -->
                        <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <h4 style="margin: 0; font-size: 14.5px; font-weight: 700; color: var(--text-primary);"><i class='bx bx-server' style="color: #10b981;"></i> System & Backups</h4>
                                <button class="btn-link" onclick="App.navigate('backups')" style="font-size: 12px; color: var(--primary); font-weight: 600; background: none; border: none; cursor: pointer;">Manage Backups →</button>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; padding-bottom: 6px; border-bottom: 1px solid var(--border);">
                                    <span style="color: var(--text-secondary);">Backend & DB</span>
                                    <span class="badge" style="background: #dcfce7; color: #15803d; font-size: 11px; padding: 2px 7px; border-radius: 4px; font-weight: 600;"><i class='bx bx-check'></i> Online</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; padding-bottom: 6px; border-bottom: 1px solid var(--border);">
                                    <span style="color: var(--text-secondary);">Latest Backup</span>
                                    <strong style="font-size: 12px; font-family: monospace;">${latestBackup ? latestBackup.backup_name.slice(0, 18) + '...' : 'None'}</strong>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; padding-bottom: 6px; border-bottom: 1px solid var(--border);">
                                    <span style="color: var(--text-secondary);">Backup Date</span>
                                    <span style="font-size: 12px; color: var(--text-secondary);">${latestBackup && latestBackup.backup_date ? new Date(latestBackup.backup_date).toLocaleDateString() : 'N/A'}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12.5px;">
                                    <span style="color: var(--text-secondary);">Backup Status</span>
                                    <span class="badge" style="background: #dcfce7; color: #15803d; font-size: 11px; padding: 2px 7px; border-radius: 4px; font-weight: 600;">${latestBackup ? latestBackup.status : 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Row 4: Recent System Activity (Audit Logs) -->
                    <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff); margin-bottom: 2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem;">
                            <div>
                                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 4px 0; color: var(--text-primary);"><i class='bx bx-history' style="color: var(--primary);"></i> Recent System Activity</h3>
                                <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">Global security, user management, and catalog audit trail.</p>
                            </div>
                            <button class="btn btn-secondary" onclick="App.navigate('audit-logs')" style="display: inline-flex; align-items: center; gap: 4px; padding: 6px 14px; font-size: 12.5px; font-weight: 600; border-radius: 8px;">
                                View All Audit Logs →
                            </button>
                        </div>
                        <div class="table-responsive" style="border: 1px solid var(--border); border-radius: 8px; overflow: hidden;">
                            <table style="width: 100%; text-align: left; border-collapse: collapse; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--surface, #f8fafc); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 16px;">User</th>
                                        <th style="padding: 12px 16px;">Action</th>
                                        <th style="padding: 12px 16px;">Details</th>
                                        <th style="padding: 12px 16px;">Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${recentAudits.length > 0 ? recentAudits.map(a => `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 12px 16px; font-weight: 600;">
                                                <div style="display: flex; align-items: center; gap: 8px;">
                                                    <div style="width: 26px; height: 26px; border-radius: 50%; background: #e0f2fe; color: #0284c7; display: flex; align-items: center; justify-content: center; font-size: 13px;">
                                                        <i class='bx bx-user'></i>
                                                    </div>
                                                    ${Utils.escapeHtml(a.username)}
                                                </div>
                                            </td>
                                            <td style="padding: 12px 16px; font-weight: 600;">
                                                <span class="badge" style="background: #f1f5f9; color: #475569; font-size: 11px; padding: 3px 8px; border-radius: 4px;">${Utils.escapeHtml(a.action)}</span>
                                            </td>
                                            <td style="padding: 12px 16px; color: var(--text-secondary); font-size: 12.5px;">${Utils.escapeHtml(a.details)}</td>
                                            <td style="padding: 12px 16px; color: var(--text-secondary); font-size: 12px; white-space: nowrap;">${a.timestamp ? new Date(a.timestamp).toLocaleString() : 'N/A'}</td>
                                        </tr>
                                    `).join('') : `<tr><td colspan="4" style="padding: 24px; text-align: center; color: var(--text-secondary);">No recent audit logs recorded.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Row 5: Executive Administrative Profile Status -->
                    <div class="card" style="padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); background: var(--card-bg, #ffffff);">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                            <div style="display: flex; align-items: center; gap: 14px;">
                                <div style="width: 44px; height: 44px; border-radius: 12px; background: rgba(139, 92, 246, 0.12); color: #7c3aed; display: flex; align-items: center; justify-content: center; font-size: 24px;">
                                    <i class='bx bx-crown'></i>
                                </div>
                                <div>
                                    <h4 style="margin: 0 0 3px 0; font-size: 15px; font-weight: 700; color: var(--text-primary);">Owner Administration Profile</h4>
                                    <div style="font-size: 12.5px; color: var(--text-secondary);">Logged in as <strong>${Utils.escapeHtml(user.username)}</strong> • Role: <strong>System Owner</strong> (Full Authority)</div>
                                </div>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button class="btn btn-secondary" onclick="App.navigate('system-status')" style="font-size: 12px; padding: 7px 14px; border-radius: 8px;">
                                    <i class='bx bx-pulse'></i> System Health
                                </button>
                                <button class="btn btn-secondary" onclick="App.navigate('backups')" style="font-size: 12px; padding: 7px 14px; border-radius: 8px;">
                                    <i class='bx bx-data'></i> Backup Vault
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            } catch (err) {
                console.error("Failed to load Owner dashboard:", err);
                statsContainer.innerHTML = `
                    <div class="card" style="grid-column: 1 / -1; padding: 24px; color: var(--red); text-align: center; border: 1px solid var(--border); border-radius: 12px; background: var(--card-bg, #fff);">
                        <i class='bx bx-error-circle' style="font-size: 28px; margin-bottom: 6px; display: block;"></i>
                        <strong>Unable to load Owner Dashboard data.</strong>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${Utils.escapeHtml(err.message || 'Server error')}</div>
                    </div>
                `;
                contentContainer.innerHTML = `
                    <div class="card" style="padding: 2.5rem; text-align: center; border: 1px solid var(--border); border-radius: 12px; background: var(--card-bg, #fff); margin-top: 1rem;">
                        <i class='bx bx-refresh' style="font-size: 40px; color: var(--primary); margin-bottom: 1rem; display: block;"></i>
                        <h4 style="margin-bottom: 0.5rem; color: var(--text);">Unable to load Owner Dashboard data</h4>
                        <p style="color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 13.5px;">Please check your connection and click retry below.</p>
                        <button class="btn btn-primary" onclick="App.pages['dashboard'].init()" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; font-size: 13px;">
                            <i class='bx bx-refresh'></i> Retry
                        </button>
                    </div>
                `;
            }
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
