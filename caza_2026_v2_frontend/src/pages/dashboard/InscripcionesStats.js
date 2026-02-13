import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchTotalInscripciones } from '../../utils/api';
// import '../../styles/App.css'; // Esto ya se carga globalmente en App.js

const InscripcionesStats = () => {
  const [totalInscripciones, setTotalInscripciones] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getStats = async () => {
      try {
        setLoading(true);
        const data = await fetchTotalInscripciones();
        setTotalInscripciones(data.total_inscripciones);
      } catch (error) {
        console.error("Error al cargar estadísticas de inscripciones:", error);
      } finally {
        setLoading(false);
      }
    };

    getStats();
  }, []);

  return (
    <div className="stat-widget-container">
      <Link to="/inscripciones" className="stat-widget-link">
        <div className="stat-widget">
          <div className="stat-widget-count">{loading ? '...' : totalInscripciones}</div>
          <div className="stat-widget-label">Inscripciones Totales</div>
        </div>
      </Link>
      {/* Aquí se pueden añadir otros contadores relacionados a inscripciones */}
    </div>
  );
};

export default InscripcionesStats;
