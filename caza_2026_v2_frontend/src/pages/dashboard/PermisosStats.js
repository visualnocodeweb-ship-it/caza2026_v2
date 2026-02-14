import React, { useEffect, useState } from 'react';
import { fetchTotalPermisos } from '../../utils/api'; // Assuming you will create this API function
import '../styles/App.css';

const PermisosStats = () => {
  const [totalPermisos, setTotalPermisos] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const getStats = async () => {
      try {
        setLoading(true);
        const [permisosResponse] = await Promise.all([
            fetchTotalPermisos(),
        ]);
        setTotalPermisos(permisosResponse.total_permisos || 0);
      } catch (err) {
        setError('No se pudieron cargar las estadísticas de permisos.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    getStats();
  }, []);

  if (loading) {
    return <p>Cargando estadísticas de permisos...</p>;
  }

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  return (
    <div className="stats-container">
      <div className="stat-card">
        <h3>Total de Permisos</h3>
        <p>{totalPermisos}</p>
      </div>
    </div>
  );
};

export default PermisosStats;
