import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchTotalInscripciones } from '../utils/api';

const Dashboard = () => {
  const [totalInscripciones, setTotalInscripciones] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const getStats = async () => {
      try {
        setLoading(true);
        const data = await fetchTotalInscripciones();
        setTotalInscripciones(data.total_inscripciones);
      } catch (error) {
        console.error("Error al cargar estadísticas:", error);
      } finally {
        setLoading(false);
      }
    };

    getStats();
  }, []);

  return (
    <div>
      <h2>Dashboard</h2>
      <div className="stat-card-container">
        <div className="stat-card">
          <div className="stat-card-number">{loading ? '...' : totalInscripciones}</div>
          <div className="stat-card-label">Inscripciones Totales</div>
          <Link to="/inscripciones" className="stat-card-link">
            Ir a Inscripciones
          </Link>
        </div>
        {/* Aquí se podrían agregar más tarjetas de estadísticas en el futuro */}
      </div>
    </div>
  );
};

export default Dashboard;
