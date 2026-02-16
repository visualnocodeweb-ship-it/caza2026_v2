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
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100vh',
            backgroundColor: '#f0f2f5'
        }}>
            <div style={{
                padding: '2rem',
                backgroundColor: 'white',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                width: '100%',
                maxWidth: '400px'
            }}>
                <h2 style={{
                    color: '#2E5661',
                    textAlign: 'center',
                    marginBottom: '1.5rem'
                }}>Ingreso al Sistema</h2>

                {error && (
                    <div style={{
                        backgroundColor: '#FEE2E2',
                        color: '#B91C1C',
                        padding: '0.75rem',
                        borderRadius: '4px',
                        marginBottom: '1rem',
                        fontSize: '0.9rem'
                    }}>
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#4B5563', fontSize: '0.9rem', fontWeight: '500' }}>Usuario</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '1px solid #D1D5DB',
                                borderRadius: '6px',
                                fontSize: '1rem',
                                outline: 'none',
                                boxSizing: 'border-box'
                            }}
                            placeholder="Ej. Karen"
                            required
                        />
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#4B5563', fontSize: '0.9rem', fontWeight: '500' }}>Contraseña</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '1px solid #D1D5DB',
                                borderRadius: '6px',
                                fontSize: '1rem',
                                outline: 'none',
                                boxSizing: 'border-box'
                            }}
                            placeholder="••••••••"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        style={{
                            width: '100%',
                            padding: '0.75rem',
                            backgroundColor: '#2E5661',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            fontSize: '1rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'background-color 0.2s'
                        }}
                    >
                        Ingresar
                    </button>
                </form>
            </div>
        </div>
    );
};

export default Login;
