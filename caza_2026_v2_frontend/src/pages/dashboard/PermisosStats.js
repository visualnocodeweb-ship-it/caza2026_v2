import React, { useEffect, useState } from 'react';
import { fetchPermisosStats } from '../../utils/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import '../../styles/App.css';

const PermisosStats = () => {
  const [stats, setStats] = useState({ total_permisos: 0, daily_stats: [], monthly_stats: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const getStats = async () => {
    try {
      const data = await fetchPermisosStats();
      setStats(data);
    } catch (err) {
      setError('No se pudieron cargar las estadísticas de permisos.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getStats(); // Initial fetch

    const intervalId = setInterval(() => {
      getStats(); // Auto-refresh every 60 seconds
    }, 60000);

    return () => clearInterval(intervalId); // Cleanup on unmount
  }, []);

  if (loading && stats.total_permisos === 0) {
    return <p>Cargando estadísticas de permisos...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  return (
    <div className="stats-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Estadísticas de Permisos</h2>
        <button
          onClick={getStats}
          disabled={loading}
          style={{
            padding: '10px 20px',
            backgroundColor: '#2E5661',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          {loading ? 'Actualizando...' : 'Actualizar Datos'}
        </button>
      </div>

      <div className="stat-widget-container">
        <div className="stat-widget">
          <div className="stat-widget-count">{stats.total_permisos}</div>
          <div className="stat-widget-label">Total de Permisos</div>
        </div>
      </div>

      <div style={{ marginTop: '2rem', display: 'flex', flexWrap: 'wrap', gap: '2rem' }}>
        <div style={{ flex: 1, minWidth: '300px', height: '300px', backgroundColor: '#fff', padding: '1rem', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <h4 style={{ marginBottom: '1rem', textAlign: 'center', color: '#374151' }}>Permisos por Día</h4>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats.daily_stats}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#2E5661" name="Permisos" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ flex: 1, minWidth: '300px', height: '300px', backgroundColor: '#fff', padding: '1rem', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <h4 style={{ marginBottom: '1rem', textAlign: 'center', color: '#374151' }}>Permisos por Mes</h4>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stats.monthly_stats}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#A8C289" name="Permisos" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default PermisosStats;
