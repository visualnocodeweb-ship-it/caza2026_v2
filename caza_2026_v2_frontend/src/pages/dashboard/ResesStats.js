import React, { useState, useEffect } from 'react';
import { fetchResesStats } from '../../utils/api';

const ResesStats = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const getStats = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchResesStats();
            setStats(data);
        } catch (err) {
            console.error("Error fetching reses stats:", err);
            setError("No se pudieron obtener las estadísticas de reses.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        getStats();
    }, []);

    return (
        <div className="stats-container">
            <h3>Estadísticas de Reses</h3>

            <div className="stats-controls" style={{ marginBottom: '20px', display: 'flex', gap: '15px' }}>
                <button
                    className={`action-button btn-primary ${loading ? 'btn-loading' : ''}`}
                    onClick={getStats}
                    disabled={loading}
                >
                    {loading ? 'Calculando...' : 'Contar y Calcular Recaudación'}
                </button>
            </div>

            {error && <p className="error-text">{error}</p>}

            {stats && (
                <div className="stats-grid">
                    <div className="stat-card">
                        <h4>Total de Reses</h4>
                        <p className="stat-value">{stats.total_reses}</p>
                        <p className="stat-label">registradas en la hoja de cálculo</p>
                    </div>
                    <div className="stat-card revenue">
                        <h4>Recaudación</h4>
                        <p className="stat-value text-success">${stats.total_revenue.toLocaleString()}</p>
                        <p className="stat-label">Suma de montos con estado "PAGADO: SÍ"</p>
                    </div>
                    <div className="stat-card">
                        <h4>Total Registros</h4>
                        <p className="stat-value">{stats.total_records}</p>
                        <p className="stat-label">filas procesadas</p>
                    </div>
                </div>
            )}

            {!stats && !loading && !error && (
                <p>Haz clic en el botón para obtener las estadísticas.</p>
            )}
        </div>
    );
};

export default ResesStats;
