// SIMS Shared Sidebar Component Logic
document.addEventListener("DOMContentLoaded", () => {
  // Highlight active link based on current filename
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll(".nav-link");

  navLinks.forEach(link => {
    const href = link.getAttribute("href");
    if (href && currentPath.endsWith(href)) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Populate user profile info in sidebar footer if available
  const user = typeof Auth !== "undefined" ? Auth.getUser() : null;
  const nameEl = document.getElementById("sidebar-user-name");
  const roleEl = document.getElementById("sidebar-user-role");
  const avatarEl = document.getElementById("sidebar-user-avatar");

  if (nameEl && user) nameEl.textContent = user.username || "User";
  if (roleEl && user) roleEl.textContent = user.role || "Administrator";
  if (avatarEl && user && user.username) avatarEl.textContent = user.username.charAt(0).toUpperCase();
});

