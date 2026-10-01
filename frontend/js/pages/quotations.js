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
                <button class="btn primary">
                    <i class='bx bx-plus'></i> New Quotation
                </button>
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
                        <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px 10px;"><i class='bx bx-filter'></i> Filter</button>
                        <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px 10px;">Export</button>
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
                        <!-- Mock data matching screenshot -->
                        <tr>
                            <td>
                                <div style="font-weight: 600;">QT-2026-0041</div>
                                <div style="font-size: 12px; color: var(--text-light);">18 Sep 2026</div>
                            </td>
                            <td style="color: var(--text-light);">SR-2026-0142</td>
                            <td>Steel Couplings</td>
                            <td>₹420</td>
                            <td style="font-weight: 600;">₹50,400</td>
                            <td style="color: var(--text-light);">25 Sep 2026</td>
                            <td><span class="badge" style="background: var(--blue-light); color: var(--blue); font-size: 11px !important;">Submitted</span></td>
                            <td>
                                <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px; margin-right: 5px;"><i class='bx bx-show'></i></button>
                                <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px;"><i class='bx bx-dots-horizontal-rounded'></i></button>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div style="font-weight: 600;">QT-2026-0038</div>
                                <div style="font-size: 12px; color: var(--text-light);">16 Sep 2026</div>
                            </td>
                            <td style="color: var(--text-light);">SR-2026-0139</td>
                            <td>Drive Belts</td>
                            <td>₹780</td>
                            <td style="font-weight: 600;">₹46,800</td>
                            <td style="color: var(--text-light);">23 Sep 2026</td>
                            <td><span class="badge" style="background: var(--green-light); color: var(--green); font-size: 11px !important;">Approved</span></td>
                            <td>
                                <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px; margin-right: 5px;"><i class='bx bx-show'></i></button>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div style="font-weight: 600;">QT-2026-0035</div>
                                <div style="font-size: 12px; color: var(--text-light);">12 Sep 2026</div>
                            </td>
                            <td style="color: var(--text-light);">SR-2026-0131</td>
                            <td>Hydraulic Pumps</td>
                            <td>₹8,400</td>
                            <td style="font-weight: 600;">₹1,68,000</td>
                            <td style="color: var(--text-light);">20 Sep 2026</td>
                            <td><span class="badge" style="background: var(--red-light); color: var(--red); font-size: 11px !important;">Revision</span></td>
                            <td>
                                <button class="btn" style="background: white; border: 1px solid var(--border); padding: 5px 10px; font-size: 12px;">Edit</button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;

        return container;
    }
};
