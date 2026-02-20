import { create } from 'zustand';
import { apiClient } from '../lib/api';

interface AuthUser {
    id: string;
    email: string;
    full_name: string;
    role: string;
    tenant_id: string;
}

interface AuthState {
    token: string | null;
    user: AuthUser | null;
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    setFromToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    token: localStorage.getItem('access_token'),
    user: JSON.parse(localStorage.getItem('auth_user') || 'null'),
    isAuthenticated: !!localStorage.getItem('access_token'),

    login: async (email: string, password: string) => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const res = await apiClient.post('/auth/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        const { access_token } = res.data;
        // Backend returns TokenResponse directly (access_token, token_type, etc) 
        // We might need to fetch user separately if not included, but let's check auth.py
        // auth.py login returns TokenResponse only. MeResponse is on /auth/me.

        localStorage.setItem('access_token', access_token);

        // We need to fetch user details now because /login only returns token
        const meRes = await apiClient.get('/auth/me', {
            headers: { Authorization: `Bearer ${access_token}` }
        });
        const userData = meRes.data;

        localStorage.setItem('auth_user', JSON.stringify(userData));
        set({ token: access_token, user: userData, isAuthenticated: true });
    },

    logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('auth_user');
        set({ token: null, user: null, isAuthenticated: false });
    },

    setFromToken: (token: string) => {
        localStorage.setItem('access_token', token);
        set({ token, isAuthenticated: true });
    },
}));
