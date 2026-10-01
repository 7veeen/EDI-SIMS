// modal.js

const Modal = {
    create(options) {
        const { id, title, content, footer, onOpen, onClose } = options;
        
        const modalsContainer = document.getElementById('modals-container');
        
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.id = id;
        
        overlay.innerHTML = `
            <div class="glass-panel modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="btn-icon close-modal"><i class='bx bx-x'></i></button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
            </div>
        `;
        
        modalsContainer.appendChild(overlay);
        
        const closeBtn = overlay.querySelector('.close-modal');
        const closeModal = () => {
            overlay.classList.remove('active');
            setTimeout(() => {
                overlay.remove();
                if (onClose) onClose();
            }, 300);
        };
        
        closeBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', closeModal); // Click outside to close
        
        // Trigger show
        setTimeout(() => overlay.classList.add('active'), 10);
        
        if (onOpen) onOpen(overlay, closeModal);
        
        return closeModal;
    }
};

// Global Change Password Modal
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('change-password-btn');
    if(btn) {
        btn.addEventListener('click', () => {
            Modal.create({
                id: 'changePasswordModal',
                title: 'Change Password',
                content: `
                    <form id="change-password-form">
                        <div class="form-group">
                            <label>Current Password</label>
                            <input type="password" id="cp_current" required>
                        </div>
                        <div class="form-group">
                            <label>New Password (min 8 chars)</label>
                            <input type="password" id="cp_new" minlength="8" required>
                        </div>
                        <div class="form-group">
                            <label>Confirm New Password</label>
                            <input type="password" id="cp_confirm" required>
                        </div>
                        <div id="cp_error" class="error-text hidden"></div>
                        <div class="modal-footer" style="padding-top: 1rem; border-top: 1px solid var(--border)">
                            <button type="button" class="btn btn-outline cancel-btn">Cancel</button>
                            <button type="submit" class="btn btn-primary">Change Password</button>
                        </div>
                    </form>
                `,
                onOpen: (modalEl, close) => {
                    modalEl.querySelector('.cancel-btn').addEventListener('click', close);
                    const form = modalEl.querySelector('#change-password-form');
                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const current = modalEl.querySelector('#cp_current').value;
                        const newPass = modalEl.querySelector('#cp_new').value;
                        const confirm = modalEl.querySelector('#cp_confirm').value;
                        const errEl = modalEl.querySelector('#cp_error');
                        
                        if (newPass !== confirm) {
                            errEl.textContent = "New passwords do not match.";
                            errEl.classList.remove('hidden');
                            return;
                        }
                        
                        try {
                            const btn = form.querySelector('button[type="submit"]');
                            btn.disabled = true;
                            btn.innerHTML = 'Updating...';
                            await Auth.changePassword(current, newPass);
                            Utils.showToast("Password changed successfully", "success");
                            close();
                        } catch (err) {
                            errEl.textContent = err.message;
                            errEl.classList.remove('hidden');
                        } finally {
                            const btn = form.querySelector('button[type="submit"]');
                            btn.disabled = false;
                            btn.innerHTML = 'Change Password';
                        }
                    });
                }
            });
        });
    }
});
