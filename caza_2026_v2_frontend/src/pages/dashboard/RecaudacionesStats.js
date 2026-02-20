import React, { useState, useEffect } from 'react';
import { fetchRecaudacionesStats } from '../../utils/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const RecaudacionesStats = () => {
  const [stats, setStats] = useState({
    recaudacion_total: 0,
    recaudacion_inscripciones: 0,
    recaudacion_permisos: 0,
    recaudacion_reses: 0,
    recaudacion_permisos_por_mes: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getStats = async () => {
      try {
        setLoading(true);
        const data = await fetchRecaudacionesStats();
        setStats(data);
      } catch (error) {
        console.error("Error al cargar estadísticas de recaudaciones:", error);
      } finally {
        setLoading(false);
      }
    };

    getStats();
  }, []);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency: 'ARS',
    }).format(amount);
  };

  return (
    <div>
      <div className="stat-widget-container">
        <div className="stat-widget">
          <div className="stat-widget-count">{loading ? '...' : formatCurrency(stats.recaudacion_total)}</div>
          <div className="stat-widget-label">Recaudación Total (Aprobado)</div>
        </div>
        <div className="stat-widget">
          <div className="stat-widget-count">{loading ? '...' : formatCurrency(stats.recaudacion_inscripciones)}</div>
          <div className="stat-widget-label">Recaudación por Inscripción</div>
        </div>
        <div className="stat-widget">
          <div className="stat-widget-count">{loading ? '...' : formatCurrency(stats.recaudacion_permisos)}</div>
          <div className="stat-widget-label">Recaudación por Permisos</div>
        </div>
        <div className="stat-widget">
          <div className="stat-widget-count">{loading ? '...' : formatCurrency(stats.recaudacion_reses)}</div>
          <div className="stat-widget-label">Recaudación por Reses</div>
        </div>
      </div>

      <div style={{ marginTop: '40px' }}>
        <h4>Recaudación de Permisos por Mes</h4>
        {loading ? (
          <p>Cargando gráfico...</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={stats.recaudacion_permisos_por_mes}
              margin={{
                top: 5, right: 30, left: 20, bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip formatter={(value) => formatCurrency(value)} />
              <Legend />
              <Bar dataKey="total" fill="#8884d8" name="Total Recaudado" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default RecaudacionesStats;
