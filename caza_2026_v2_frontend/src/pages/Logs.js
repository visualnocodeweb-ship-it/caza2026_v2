import React, { useEffect, useState } from 'react';
import { fetchLogs } from '../utils/api';
import '../styles/App.css';

const RECORDS_PER_PAGE = 15; // Constante para la paginación

const Logs = () => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [totalRecords, setTotalRecords] = useState(0);

    useEffect(() => {
        const getLogs = async () => {
            try {
                setLoading(true);
                const data = await fetchLogs(currentPage, RECORDS_PER_PAGE);
                setLogs(data.data);
                setTotalRecords(data.total_records);
                setTotalPages(data.total_pages);
            } catch (err) {
                setError('No se pudieron cargar los logs.');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        getLogs();
    }, [currentPage]); // Dependencia: currentPage

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return isNaN(date.getTime()) ? 'Fecha inválida' : date.toLocaleString();
    };

    if (loading) {
        return <p>Cargando logs...</p>;
    }

    if (error) {
        return <p style={{ color: 'red' }}>{error}</p>;
    }

    return (
        <div className="logs-container">
            <h3>Registro de Actividad</h3>
            <div className="table-responsive">
                <table className="logs-table">
                    <thead>
                        <tr>
                            <th>Fecha y Hora</th>
                            <th>Nivel</th>
                            <th>Evento</th>
                            <th>Detalles</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.length > 0 ? (
                            logs.map(log => (
                                <tr key={log.id} className={log.level === 'ERROR' ? 'log-error' : ''}>
                                    <td>{formatDate(log.timestamp)}</td>
                                    <td>
                                        <span className={`log-level log-level-${log.level.toLowerCase()}`}>
                                            {log.level}
                                        </span>
                                    </td>
                                    <td>{log.event}</td>
                                    <td>{log.details}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="4">No hay registros de actividad.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
                <div className="pagination-controls">
                    <button
                        onClick={() => setCurrentPage(prev => prev - 1)}
                        disabled={currentPage === 1 || loading}
                    >
                        Anterior
                    </button>
                    <span>Página {currentPage} de {totalPages} ({totalRecords} registros)</span>
                    <button
                        onClick={() => setCurrentPage(prev => prev + 1)}
                        disabled={currentPage === totalPages || loading}
                    >
                        Siguiente
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Logs;