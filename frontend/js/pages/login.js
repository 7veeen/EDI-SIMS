// login.js

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    const togglePassword = document.getElementById('toggle-password');
    const passwordInput = document.getElementById('password');

    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', () => {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            togglePassword.classList.toggle('bx-show');
            togglePassword.classList.toggle('bx-hide');
        });
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const usernameInput = document.getElementById('username');
        const errorDiv = document.getElementById('login-error');
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        
        errorDiv.classList.add('hidden');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span>Logging in...</span>';

        try {
            const success = await Auth.login(usernameInput.value, passwordInput.value);
            if (success) {
                window.location.reload();
            }
        } catch (error) {
            errorDiv.textContent = error.message || "Username or password incorrect";
            errorDiv.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<span>Sign in </span><i class='bx bx-right-arrow-alt'></i>`;
        }
    });
});
