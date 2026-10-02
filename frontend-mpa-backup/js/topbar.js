// SIMS Shared Topbar Component Logic
document.addEventListener("DOMContentLoaded", () => {
  const logoutBtn = document.getElementById("topbar-logout-btn");
  if (logoutBtn && typeof Auth !== "undefined") {
    logoutBtn.addEventListener("click", () => {
      Auth.logout();
    });
  }
});

