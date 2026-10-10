let selectedDeleteBackupId = null;

const deleteBackupName = document.getElementById("delete-backup-name");
const confirmDeleteButton = document.getElementById("confirm-delete-btn");
const deleteError = document.getElementById("delete-error");

function showDeleteError(message) {
    if (!deleteError) return;
    deleteError.textContent = message;
    deleteError.classList.remove("hidden");
}

function hideDeleteError() {
    if (!deleteError) return;
    deleteError.textContent = "";
    deleteError.classList.add("hidden");
}

async function openDeleteModal(backupId) {
    selectedDeleteBackupId = backupId;
    hideDeleteError();
    showLoading("Loading backup information...");
    try {
        const data = await apiGet(`/api/backups/${backupId}`);
        const backup = data.backup || data;
        deleteBackupName.textContent = backup.backup_name || "-";
        openModal("delete-modal");
    } catch (error) {
        showError(error.message || "Unable to load backup information.");
    } finally {
        hideLoading();
    }
}

async function deleteBackup() {
    if (!selectedDeleteBackupId) {
        showDeleteError("No backup is selected.");
        return;
    }
    confirmDeleteButton.disabled = true;
    showLoading("Deleting backup...");
    hideDeleteError();
    try {
        const result = await apiDelete(`/api/backups/${selectedDeleteBackupId}`);
        showSuccess(result.message || "Backup deleted successfully.");
        closeDeleteModal();
        await loadBackups();
    } catch (error) {
        showDeleteError(error.message || "Unable to delete backup.");
    } finally {
        hideLoading();
        confirmDeleteButton.disabled = false;
    }
}

function closeDeleteModal() {
    selectedDeleteBackupId = null;
    hideDeleteError();
    closeModal("delete-modal");
}

if (confirmDeleteButton) confirmDeleteButton.addEventListener("click", deleteBackup);
document.querySelectorAll('[data-modal="delete-modal"]').forEach(button => {
    button.addEventListener("click", closeDeleteModal);
});
