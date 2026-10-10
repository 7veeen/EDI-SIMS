function getToken() {
    return localStorage.getItem("access_token");
}

// This decoded payload is used for display and UX only. Flask verifies the token.
function getTokenPayload() {
    const token = getToken();
    if (!token) return null;
    try {
        const part = token.split(".")[1];
        if (!part) return null;
        const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
        const bytes = Uint8Array.from(atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "=")), char => char.charCodeAt(0));
        return JSON.parse(new TextDecoder().decode(bytes));
    } catch (_error) {
        return null;
    }
}

function getCurrentUserId() {
    return getTokenPayload()?.sub || null;
}

function getCurrentUserRole() {
    return getTokenPayload()?.role || null;
}

function canManageBackups() {
    return ["Owner", "Manager"].includes(getCurrentUserRole());
}

function displayUserRole() {
    const roleElement = document.getElementById("user-role");
    if (roleElement) roleElement.textContent = getCurrentUserRole() || "Not signed in";
}

function logout() {
    localStorage.removeItem("access_token");
    displayUserRole();
    if (typeof showError === "function") {
        showError("You have been signed out. Sign in through the project's login page, then reload this page.");
    }
    if (typeof applyRolePermissions === "function") applyRolePermissions();
}

document.addEventListener("DOMContentLoaded", () => {
    displayUserRole();
    const logoutButton = document.getElementById("logout-btn");
    if (logoutButton) logoutButton.addEventListener("click", logout);
    if (!getToken() && typeof showError === "function") {
        showError("No access token was found. Sign in through the project's login page, then reload this page.");
    }
    if (typeof applyRolePermissions === "function") applyRolePermissions();
});
