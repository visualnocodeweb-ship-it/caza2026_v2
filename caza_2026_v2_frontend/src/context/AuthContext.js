import React, { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    // Hardcoded credentials as per user request
    const CREDENTIALS = {
        'Karen': 'Karen321',
        'Emanuel': 'Emanuel321',
        'Nico': 'Nico321',
        'algar': 'algarmariano',
        'fauna1': 'fauna1nqn'
    };

    const SESSION_DURATION = 2 * 60 * 60 * 1000; // 2 hours in milliseconds

    useEffect(() => {
        // Check for active session on mount
        const storedUser = localStorage.getItem('caza_user');
        const storedLoginTime = localStorage.getItem('caza_login_time');

        if (storedUser && storedLoginTime) {
            const now = Date.now();
            if (now - parseInt(storedLoginTime) > SESSION_DURATION) {
                logout(); // Session expired
            } else {
                setUser(storedUser);
            }
        }
        setLoading(false);
    }, []);

    const login = (username, password) => {
        if (CREDENTIALS[username] === password) {
            setUser(username);
            localStorage.setItem('caza_user', username);
            localStorage.setItem('caza_login_time', Date.now().toString());

            // Redirect based on user
            if (username === 'algar') {
                navigate('/algar-sa');
            } else if (username === 'fauna1') {
                navigate('/guias-traslados-varios');
            } else {
                navigate('/dashboard');
            }
            return { success: true };
        } else {
            return { success: false, message: 'Usuario o contraseña incorrectos' };
        }
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem('caza_user');
        localStorage.removeItem('caza_login_time');
        navigate('/login');
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};
