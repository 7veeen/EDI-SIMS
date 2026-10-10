// auth.js

const Auth = {
    isAuthenticated() {
        return !!(localStorage.getItem('sims_token') || localStorage.getItem('sims_access_token'));
    },

    getUser() {
        const userStr = localStorage.getItem('sims_user');
        if (!userStr) return null;
        try {
            return JSON.parse(userStr);
        } catch (e) {
            return null;
        }
    },

    getRole() {
        const user = this.getUser();
        return user ? user.role : null;
    },

    async login(username, password) {
        try {
            const data = await Api.post('/auth/login', { username, password });
            if (data.access_token) {
                localStorage.setItem('sims_token', data.access_token);
                localStorage.setItem('sims_access_token', data.access_token);
                
                const userData = data.user || {};
                const resolvedId = userData.user_id || userData.id || data.user_id || data.id;
                
                localStorage.setItem('sims_user', JSON.stringify({
                    id: resolvedId,
                    user_id: resolvedId,
                    username: userData.username || data.username || username,
                    role: userData.role || userData.role_name || data.role || data.role_name
                }));
                return true;
            }
            return false;
        } catch (error) {
            throw error;
        }
    },

    logout() {
        localStorage.removeItem('sims_token');
        localStorage.removeItem('sims_access_token');
        localStorage.removeItem('sims_user');
        window.location.reload();
    },
    
    async changePassword(currentPassword, newPassword) {
        try {
            await Api.put('/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            });
            return true;
        } catch (error) {
            throw error;
        }
    }
};
