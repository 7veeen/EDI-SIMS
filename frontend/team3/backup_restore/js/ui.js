// ==========================================
// UI HELPERS
// ==========================================


// ==========================================
// GET ELEMENT
// ==========================================

function getElement(id) {
    return document.getElementById(id);
}


// ==========================================
// SHOW LOADING
// ==========================================

function showLoading(message = "Loading...") {

    const loadingElement = getElement("loading-message");

    if (!loadingElement) {
        return;
    }

    loadingElement.textContent = message;
    loadingElement.classList.remove("hidden");
}


// ==========================================
// HIDE LOADING
// ==========================================

function hideLoading() {

    const loadingElement = getElement("loading-message");

    if (!loadingElement) {
        return;
    }

    loadingElement.classList.add("hidden");
}


// ==========================================
// SHOW SUCCESS MESSAGE
// ==========================================

function showSuccess(message) {

    const successElement = getElement("success-message");

    if (!successElement) {
        return;
    }

    successElement.textContent = message;
    successElement.classList.remove("hidden");

    // Automatically hide after 5 seconds
    setTimeout(() => {
        successElement.classList.add("hidden");
    }, 5000);
}


// ==========================================
// SHOW ERROR MESSAGE
// ==========================================

function showError(message) {

    const errorElement = getElement("error-message");

    if (!errorElement) {
        return;
    }

    errorElement.textContent = message;
    errorElement.classList.remove("hidden");
}


// ==========================================
// HIDE ERROR MESSAGE
// ==========================================

function hideError() {

    const errorElement = getElement("error-message");

    if (!errorElement) {
        return;
    }

    errorElement.classList.add("hidden");
}


// ==========================================
// SHOW MESSAGE
// ==========================================

function showMessage(type, message) {

    hideError();
    hideSuccess();

    if (type === "success") {
        showSuccess(message);
    }

    if (type === "error") {
        showError(message);
    }
}


// ==========================================
// HIDE SUCCESS
// ==========================================

function hideSuccess() {

    const successElement = getElement("success-message");

    if (!successElement) {
        return;
    }

    successElement.classList.add("hidden");
}


// ==========================================
// OPEN MODAL
// ==========================================

function openModal(modalId) {

    const modal = getElement(modalId);

    if (!modal) {
        return;
    }

    modal.classList.remove("hidden");
}


// ==========================================
// CLOSE MODAL
// ==========================================

function closeModal(modalId) {

    const modal = getElement(modalId);

    if (!modal) {
        return;
    }

    modal.classList.add("hidden");
}


// ==========================================
// CLOSE MODAL WHEN CLICKING OUTSIDE
// ==========================================

function setupModalOutsideClick(modalId) {

    const modal = getElement(modalId);

    if (!modal) {
        return;
    }

    modal.addEventListener("click", (event) => {

        if (event.target === modal) {
            closeModal(modalId);
        }

    });
}


// ==========================================
// FORMAT DATE
// ==========================================

function formatDate(dateString) {

    if (!dateString) {
        return "-";
    }

    const date = new Date(dateString);

    if (isNaN(date.getTime())) {
        return dateString;
    }

    return date.toLocaleString();
}


// ==========================================
// FORMAT FILE SIZE
// ==========================================

function formatFileSize(bytes) {

    if (bytes === null || bytes === undefined) {
        return "-";
    }

    const size = Number(bytes);

    if (isNaN(size)) {
        return "-";
    }

    if (size < 1024) {
        return `${size} B`;
    }

    if (size < 1024 * 1024) {
        return `${(size / 1024).toFixed(2)} KB`;
    }

    if (size < 1024 * 1024 * 1024) {
        return `${(size / (1024 * 1024)).toFixed(2)} MB`;
    }

    return `${(size / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}


// ==========================================
// CONFIRM ACTION
// ==========================================

function confirmAction(message) {
    return window.confirm(message);
}