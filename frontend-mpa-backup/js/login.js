// ==========================================================================
// SIMS — Executive Login Page Controller (UI ONLY)
// Note: Backend connection will be established in subsequent tasks.
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  const usernameInput = document.getElementById("username");
  const passwordInput = document.getElementById("password");
  const togglePasswordBtn = document.getElementById("btn-toggle-password");
  const eyeIcon = document.getElementById("eye-icon");
  const submitBtn = document.getElementById("btn-submit-login");
  const btnText = document.getElementById("btn-text");
  const btnSpinner = document.getElementById("btn-spinner");
  const alertBox = document.getElementById("login-alert");
  const alertText = document.getElementById("alert-text");
  const forgotPasswordBtn = document.getElementById("btn-forgot-password");
  const infoNotice = document.getElementById("info-card-notice");
  const closeNoticeBtn = document.getElementById("btn-close-notice");

  // 1. Show / Hide Password Toggle
  if (togglePasswordBtn && passwordInput) {
    togglePasswordBtn.addEventListener("click", () => {
      const isPassword = passwordInput.type === "password";
      passwordInput.type = isPassword ? "text" : "password";

      if (eyeIcon) {
        eyeIcon.textContent = isPassword ? "🙈" : "👁️";
      }
      togglePasswordBtn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
      togglePasswordBtn.setAttribute("title", isPassword ? "Hide password" : "Show password");
    });
  }

  // 2. Clear Alert on Input
  [usernameInput, passwordInput].forEach(input => {
    if (input) {
      input.addEventListener("input", () => {
        hideAlert();
      });
    }
  });

  // 3. Forgot Password Interaction (UI Only)
  if (forgotPasswordBtn && infoNotice) {
    forgotPasswordBtn.addEventListener("click", () => {
      infoNotice.classList.remove("hidden");
    });
  }

  if (closeNoticeBtn && infoNotice) {
    closeNoticeBtn.addEventListener("click", () => {
      infoNotice.classList.add("hidden");
    });
  }

  // 4. Form Submit Handler (UI Simulation Only)
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      hideAlert();

      const username = usernameInput ? usernameInput.value.trim() : "";
      const password = passwordInput ? passwordInput.value : "";

      // Client-side validation
      if (!username) {
        showAlert("Please enter your corporate username or email.");
        if (usernameInput) usernameInput.focus();
        return;
      }

      if (!password) {
        showAlert("Please enter your password.");
        if (passwordInput) passwordInput.focus();
        return;
      }

      // Trigger UI Loading State
      setLoading(true);

      // Demonstrate UI loading state without calling backend (UI ONLY as requested)
      setTimeout(() => {
        setLoading(false);
        showAlert(
          "UI Verification Mode: Form inputs captured successfully. Backend authentication endpoint will be linked in the next phase.",
          "info"
        );
      }, 1000);
    });
  }

  // Helper: Display Alert Banner
  function showAlert(message, type = "error") {
    if (!alertBox || !alertText) return;
    alertText.textContent = message;

    if (type === "info") {
      alertBox.style.backgroundColor = "var(--navy-subtle)";
      alertBox.style.borderColor = "rgba(0, 51, 102, 0.25)";
      alertBox.style.color = "var(--navy-primary)";
      const icon = document.getElementById("alert-icon");
      if (icon) icon.textContent = "ℹ️";
    } else {
      alertBox.style.backgroundColor = "var(--error-bg)";
      alertBox.style.borderColor = "var(--error-border)";
      alertBox.style.color = "var(--error-text)";
      const icon = document.getElementById("alert-icon");
      if (icon) icon.textContent = "⚠️";
    }

    alertBox.classList.remove("hidden");
  }

  // Helper: Hide Alert Banner
  function hideAlert() {
    if (alertBox) {
      alertBox.classList.add("hidden");
    }
  }

  // Helper: Toggle Loading State
  function setLoading(isLoading) {
    if (!submitBtn) return;

    if (isLoading) {
      submitBtn.disabled = true;
      if (btnText) btnText.textContent = "Authenticating...";
      if (btnSpinner) btnSpinner.classList.remove("hidden");
    } else {
      submitBtn.disabled = false;
      if (btnText) btnText.textContent = "Sign In to SIMS";
      if (btnSpinner) btnSpinner.classList.add("hidden");
    }
  }
});

