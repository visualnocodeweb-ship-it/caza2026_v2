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
                <div className="stat-widget-container">
                    <div className="stat-widget">
                        <div className="stat-widget-count">{stats.total_reses}</div>
                        <div className="stat-widget-label">Total de Reses</div>
                        <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>registradas en la hoja de cálculo</p>
                    </div>
                    <div className="stat-widget">
                        <div className="stat-widget-count text-success">
                            {new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(stats.total_revenue)}
                        </div>
                        <div className="stat-widget-label">Recaudación</div>
                        <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>Suma de montos con estado "PAGADO: SÍ"</p>
                    </div>
                    <div className="stat-widget">
                        <div className="stat-widget-count">{stats.total_records}</div>
                        <div className="stat-widget-label">Total Registros</div>
                        <p style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>filas procesadas</p>
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
