// Local development API. Change this constant when the Flask host changes.
const API_BASE_URL = "http://127.0.0.1:5000";

class ApiError extends Error {
    constructor(message, status = 0) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

function getAuthToken() {
    return localStorage.getItem("access_token");
}

function messageForStatus(status, serverMessage) {
    const defaults = {
        401: "Authentication required or your session has expired. Sign in through the project's login page and reload.",
        403: "You do not have permission to perform this action.",
        404: "The requested backup was not found.",
        500: "The server could not complete the request. Please try again later."
    };
    return defaults[status] || serverMessage || `Request failed (${status}).`;
}

async function apiFetch(endpoint, options = {}) {
    const token = getAuthToken();
    if (!token) {
        throw new ApiError("No access token was found. Sign in through the project's login page, then reload this page.", 401);
    }

    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token}`);
    if (options.body !== undefined && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }

    let response;
    try {
        response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });
    } catch (_error) {
        throw new ApiError("Unable to reach the backend. Check that Flask is running at http://127.0.0.1:5000.");
    }

    if (response.status === 401) {
        localStorage.removeItem("access_token");
        if (typeof displayUserRole === "function") displayUserRole();
        if (typeof applyRolePermissions === "function") applyRolePermissions();
    }
    return response;
}

async function apiRequest(endpoint, options = {}) {
    const response = await apiFetch(endpoint, options);
    let data = {};
    try {
        data = await response.json();
    } catch (_error) {
        // Non-JSON success/error responses are handled below.
    }
    if (!response.ok) {
        throw new ApiError(messageForStatus(response.status, data.error || data.message), response.status);
    }
    return data;
}

function apiGet(endpoint) {
    return apiRequest(endpoint, { method: "GET" });
}

function apiPost(endpoint, body = {}) {
    return apiRequest(endpoint, { method: "POST", body: JSON.stringify(body) });
}

function apiDelete(endpoint) {
    return apiRequest(endpoint, { method: "DELETE" });
}
