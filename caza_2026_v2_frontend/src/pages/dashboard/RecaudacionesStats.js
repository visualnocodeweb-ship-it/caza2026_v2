import React, { useState, useEffect } from 'react';
import { fetchRecaudacionesStats } from '../../utils/api';

const RecaudacionesStats = () => {
  const [stats, setStats] = useState({ recaudacion_total: 0, recaudacion_inscripciones: 0 });
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
    <div className="stat-widget-container">
      <div className="stat-widget">
        <div className="stat-widget-count">{loading ? '...' : formatCurrency(stats.recaudacion_total)}</div>
        <div className="stat-widget-label">Recaudación Total (Aprobado)</div>
      </div>
      <div className="stat-widget">
        <div className="stat-widget-count">{loading ? '...' : formatCurrency(stats.recaudacion_inscripciones)}</div>
        <div className="stat-widget-label">Recaudación por Inscripción</div>
      </div>
    </div>
  );
};

export default RecaudacionesStats;
