import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import '../styles/App.css'; // Make sure to import styles

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const { login } = useContext(AuthContext);

    const handleSubmit = (e) => {
        e.preventDefault();
        setError(null);
        const result = login(username, password);
        if (!result.success) {
            setError(result.message);
        }
    };

    return (
        <div className="login-page-wrapper" style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '80vh',
        }}>
            <div className="glass-card" style={{
                padding: '2.5rem',
                width: '100%',
                maxWidth: '420px',
                textAlign: 'center'
            }}>
                <h2 className="app-title" style={{ marginBottom: '2rem', fontSize: '1.5rem' }}>Acceso al Sistema</h2>

                {error && (
                    <div style={{
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        color: '#B91C1C',
                        padding: '0.8rem',
                        borderRadius: 'var(--radius-sm)',
                        marginBottom: '1.5rem',
                        fontSize: '0.85rem',
                        fontWeight: '600',
                        border: '1px solid rgba(239, 68, 68, 0.2)'
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} style={{ textAlign: 'left' }}>
                    <div style={{ marginBottom: '1.25rem' }}>
                        <label className="detail-label" style={{ display: 'block', marginBottom: '0.5rem' }}>Usuario</label>
                        <input
                            type="text"
                            className="search-input"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Usuario"
                            style={{ maxWidth: '100%' }}
                            required
                        />
                    </div>

                    <div style={{ marginBottom: '2rem' }}>
                        <label className="detail-label" style={{ display: 'block', marginBottom: '0.5rem' }}>Contraseña</label>
                        <input
                            type="password"
                            className="search-input"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            style={{ maxWidth: '100%' }}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="action-button btn-primary"
                        style={{ width: '100%', justifyContent: 'center', padding: '1rem' }}
                    >
                        Ingresar al Tablero
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Login;
