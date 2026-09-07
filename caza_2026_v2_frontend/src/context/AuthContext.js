import React, { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const AuthContext = createContext();

const API_BASE_URL = process.env.NODE_ENV === 'production'
  ? 'https://caza2026-1.onrender.com/api'
  : (process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api');

const SESSION_DURATION = 2 * 60 * 60 * 1000; // 2 hours in milliseconds

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const clearSession = () => {
        setUser(null);
        localStorage.removeItem('caza_user');
        localStorage.removeItem('caza_token');
        localStorage.removeItem('caza_login_time');
    };

    useEffect(() => {
        const storedUser = localStorage.getItem('caza_user');
        const storedToken = localStorage.getItem('caza_token');
        const storedLoginTime = localStorage.getItem('caza_login_time');

        if (storedUser && storedToken && storedLoginTime) {
            const now = Date.now();
            if (now - parseInt(storedLoginTime, 10) > SESSION_DURATION) {
                clearSession();
            } else {
                setUser(storedUser);
            }
        }
        setLoading(false);
    }, []);

    const login = async (username, password) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                return {
                    success: false,
                    message: errorData.detail || 'Usuario o contraseña incorrectos',
                };
            }

            const data = await response.json();
            const userKey = data.user;

            setUser(userKey);
            localStorage.setItem('caza_user', userKey);
            localStorage.setItem('caza_token', data.token);
            localStorage.setItem('caza_login_time', Date.now().toString());

            if (userKey === 'algar') {
                navigate('/algar-sa');
            } else if (userKey === 'fauna1') {
                navigate('/guias-traslados-varios');
            } else if (userKey === 'cazamenor') {
                navigate('/permiso-caza-menor');
            } else {
                navigate('/dashboard');
            }

            return { success: true };
        } catch (error) {
            console.error('Error en login:', error);
            return { success: false, message: 'No se pudo conectar con el servidor' };
        }
    };

    const logout = () => {
        clearSession();
        navigate('/login');
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};
