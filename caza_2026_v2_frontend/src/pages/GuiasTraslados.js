import React, { useEffect, useState } from 'react';
import { fetchGuiasTraslados, getGuiaPdfUrl, sendGuiaEmail } from '../utils/api';
import '../styles/App.css';
import '../styles/Responsive.css';

const RECORDS_PER_PAGE = 10;

const GuiasTraslados = () => {
    const [guias, setGuias] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sendingEmail, setSendingEmail] = useState({});
    const [error, setError] = useState(null);
    const [expandedStates, setExpandedStates] = useState({});
    const [searchTerm, setSearchTerm] = useState('');

    // Paginación
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [totalRecords, setTotalRecords] = useState(0);

    const getGuias = async (page, search = '') => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchGuiasTraslados(page, RECORDS_PER_PAGE, search);
            setGuias(data.data);
            setTotalRecords(data.total_records);
            setTotalPages(data.total_pages);

            const initialExpandedStates = data.data.reduce((acc, _, index) => {
                acc[index] = false;
                return acc;
            }, {});
            setExpandedStates(initialExpandedStates);
        } catch (err) {
            console.error("Error al obtener guías de traslados:", err);
            setError('No se pudieron cargar los datos de las guías.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        getGuias(currentPage, searchTerm);
    }, [currentPage, searchTerm]);

    const toggleExpand = (index) => {
        setExpandedStates(prevStates => ({
            ...prevStates,
            [index]: !prevStates[index]
        }));
    };

    const handleCopyId = (id) => {
        navigator.clipboard.writeText(id);
        alert(`ID ${id} copiado al portapapeles`);
    };

    const handleSendEmail = async (guiaId) => {
        setSendingEmail(prev => ({ ...prev, [guiaId]: true }));
        try {
            await sendGuiaEmail(guiaId);
            alert("Email enviado correctamente con el PDF adjunto.");
        } catch (err) {
            console.error("Error al enviar email:", err);
            alert("No se pudo enviar el email: " + err.message);
        } finally {
            setSendingEmail(prev => ({ ...prev, [guiaId]: false }));
        }
    };

    if (loading && guias.length === 0) {
        return <p className="loading-text">Cargando guías de traslados...</p>;
    }

    if (error) {
        return <p className="error-text">Error: {error}</p>;
    }

    return (
        <div className="reses-container">
            <div className="toolbar">
                <input
                    type="text"
                    placeholder="Buscar por nombre, DNI o especie..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="search-input"
                />
            </div>

            {loading && guias.length > 0 && <p className="loading-text">Actualizando datos...</p>}

            {guias.length > 0 ? (
                <div className="inscripciones-list">
                    {guias.map((item, index) => (
                        <div key={item.ID || index} className="inscripcion-card" data-expanded={!!expandedStates[index]}>
                            <div className="card-header" onClick={() => toggleExpand(index)}>
                                <div className="header-info">
                                    <h3>{item['Nombre'] || 'Nombre no disponible'} - {item['Especies'] || item['Especie'] || 'N/A'}</h3>
                                    <span style={{ fontSize: '12px', color: '#64748b' }}>NI: {item['NI'] || 'N/A'} | ID: {item['ID'] || 'N/A'}</span>
                                </div>
                                <span className="expand-toggle">▼</span>
                            </div>

                            {expandedStates[index] && (
                                <div className="card-details">
                                    <div className="details-grid">
                                        <p><strong>NI</strong> {item['NI'] || 'N/A'}</p>
                                        <p><strong>ID</strong> {item['ID'] || 'N/A'}</p>
                                        <p><strong>ACM</strong> {item['ACM'] || 'N/A'}</p>
                                        <p><strong>Tipo ACM</strong> {item['Tipo ACM'] || 'N/A'}</p>
                                        <p><strong>Especies</strong> {item['Especies'] || item['Especie'] || 'N/A'}</p>
                                        <p><strong>Fecha</strong> {item['Fecha'] || 'N/A'}</p>
                                        <p><strong>Nombre</strong> {item['Nombre'] || 'N/A'}</p>
                                        <p><strong>DNI</strong> {item['DNI'] || 'N/A'}</p>
                                        <p><strong>Correo</strong> {item['Correo'] || 'N/A'}</p>
                                        <p><strong>Teléfono</strong> {item['Telefono'] || 'N/A'}</p>
                                        <p><strong>Número Permiso Caza</strong> {item['Numero permiso caza'] || 'N/A'}</p>
                                    </div>
                                    {item['Imagen'] && (
                                        <div style={{ marginTop: '15px' }}>
                                            <strong>Imagen:</strong><br />
                                            <img src={item['Imagen']} alt="Registro" style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px', marginTop: '10px' }} />
                                        </div>
                                    )}
                                    <div className="reses-actions-wrapper" style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
                                        <button
                                            className="action-button btn-primary"
                                            onClick={() => handleCopyId(item['ID'])}
                                        >
                                            Copiar ID
                                        </button>
                                        <a
                                            href="https://cazaypesca.neuquen.gob.ar/?ff_landing=22"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="action-button btn-success"
                                            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                                        >
                                            Parte 2
                                        </a>
                                    </div>

                                    <div className="reses-actions-wrapper" style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px', background: '#f8fafc', padding: '15px', borderRadius: '8px' }}>
                                        <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: '700', color: '#1e293b' }}>Parte 2 Completa</p>
                                        <div style={{ display: 'flex', gap: '10px' }}>
                                            <a
                                                href={getGuiaPdfUrl(item['ID'])}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="action-button btn-secondary"
                                                style={{ textDecoration: 'none', background: '#64748b', color: 'white' }}
                                            >
                                                Ver PDF
                                            </a>
                                            <button
                                                className="action-button btn-primary"
                                                onClick={() => handleSendEmail(item['ID'])}
                                                disabled={sendingEmail[item['ID']]}
                                                style={{ background: '#2E5661' }}
                                            >
                                                {sendingEmail[item['ID']] ? 'Enviando...' : 'Enviar Email'}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
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
            ) : (
                <p className="no-results">No se encontraron registros que coincidan con la búsqueda.</p>
            )}
        </div>
    );
};

export default GuiasTraslados;
