import React, { useEffect, useState } from 'react';
import { fetchInscripciones, fetchPermisos, fetchReses, fetchGuiasTraslados, getResesPdfUrl, getGuiaPdfUrl } from '../utils/api';
import '../styles/App.css';
import '../styles/Responsive.css';

const AlgarSA = () => {
    const [data, setData] = useState({
        inscripciones: [],
        permisos: [],
        reses: [],
        guias: []
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedStates, setExpandedStates] = useState({
        inscripciones: {},
        permisos: {},
        reses: {},
        guias: {}
    });

    const searchAlgar = "Algar";

    const fetchAllData = async () => {
        setLoading(true);
        try {
            // Buscamos con un límite alto para traer "todas" como pidió el usuario
            const limit = 1000;
            const [insc, perm, res, gui] = await Promise.all([
                fetchInscripciones(1, limit, searchAlgar),
                fetchPermisos(1, limit, searchAlgar),
                fetchReses(1, limit, searchAlgar),
                fetchGuiasTraslados(1, limit, searchAlgar)
            ]);

            setData({
                inscripciones: insc.data || [],
                permisos: perm.data || [],
                reses: res.data || [],
                guias: gui.data || []
            });
        } catch (err) {
            console.error("Error al cargar datos de Algar SA:", err);
            setError("Hubo un error al cargar algunos datos.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAllData();
    }, []);

    const toggleExpand = (section, index) => {
        setExpandedStates(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                [index]: !prev[section][index]
            }
        }));
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return isNaN(date.getTime()) ? dateString : date.toLocaleString();
    };

    if (loading) return <div className="loading-container"><p>Cargando datos de Algar SA...</p></div>;
    if (error) return <div className="error-container"><p>{error}</p></div>;

    return (
        <div className="algar-sa-container" style={{ padding: '20px' }}>
            <h1 style={{ color: '#2E5661', marginBottom: '30px', textAlign: 'center' }}>Registros Consolidados: Algar SA</h1>

            {/* SECCIÓN 1: INSCRIPCIONES */}
            <section className="algar-section">
                <div className="section-header-algar">
                    <h2>Inscripciones (Algar)</h2>
                    <span className="count-badge">{data.inscripciones.length}</span>
                </div>
                <div className="inscripciones-list">
                    {data.inscripciones.map((item, index) => (
                        <div key={item.numero_inscripcion || index} className={`inscripcion-card ${item['Estado de Pago'] === 'Pagado' ? 'pagado-bg' : 'pendiente-bg'}`} data-expanded={!!expandedStates.inscripciones[index]}>
                            <div className="card-header" onClick={() => toggleExpand('inscripciones', index)}>
                                <h3>{item.nombre_establecimiento || 'Sin Nombre'}</h3>
                                <span className="expand-toggle">▼</span>
                            </div>
                            {expandedStates.inscripciones[index] && (
                                <div className="card-details">
                                    <p><strong>ID:</strong> {item.numero_inscripcion}</p>
                                    <p><strong>Email:</strong> {item.email || 'N/A'}</p>
                                    <p><strong>Tipo:</strong> {item['su establecimiento es'] || 'N/A'}</p>
                                    <p><strong>Fecha:</strong> {formatDate(item.fecha_creacion)}</p>
                                    <p><strong>Estado:</strong> {item['Estado de Pago']}</p>
                                    <div className="action-buttons">
                                        {item.pdf_link && <a href={item.pdf_link} target="_blank" rel="noopener noreferrer" className="action-button btn-secondary">Ver PDF</a>}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                    {data.inscripciones.length === 0 && <p className="no-data">No hay inscripciones de Algar.</p>}
                </div>
            </section>

            {/* SECCIÓN 2: PERMISOS DE CAZA */}
            <section className="algar-section" style={{ marginTop: '40px' }}>
                <div className="section-header-algar">
                    <h2>Permisos de Caza (Algar)</h2>
                    <span className="count-badge">{data.permisos.length}</span>
                </div>
                <div className="inscripciones-list">
                    {data.permisos.map((item, index) => (
                        <div key={item.ID || index} className={`inscripcion-card ${item['Estado de Pago'] === 'Pagado' ? 'pagado-bg' : 'pendiente-bg'}`} data-expanded={!!expandedStates.permisos[index]}>
                            <div className="card-header" onClick={() => toggleExpand('permisos', index)}>
                                <h3>{item['Nombre y Apellido'] || 'Sin Nombre'}</h3>
                                <span className="expand-toggle">▼</span>
                            </div>
                            {expandedStates.permisos[index] && (
                                <div className="card-details">
                                    <p><strong>ID:</strong> {item.ID}</p>
                                    <p><strong>DNI:</strong> {item['DNI o Pasaporte'] || 'N/A'}</p>
                                    <p><strong>Categoría:</strong> {item['Categoría'] || 'N/A'}</p>
                                    <p><strong>Fecha:</strong> {formatDate(item.Fecha)}</p>
                                    <p><strong>Estado:</strong> {item['Estado de Pago']}</p>
                                    <div className="action-buttons">
                                        {item.pdf_link && <a href={item.pdf_link} target="_blank" rel="noopener noreferrer" className="action-button btn-secondary">Ver PDF</a>}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                    {data.permisos.length === 0 && <p className="no-data">No hay permisos de Algar.</p>}
                </div>
            </section>

            {/* SECCIÓN 3: GUÍAS DE TRASLADO */}
            <section className="algar-section" style={{ marginTop: '40px' }}>
                <div className="section-header-algar">
                    <h2>Guías de Traslado (Algar)</h2>
                    <span className="count-badge">{data.guias.length}</span>
                </div>
                <div className="inscripciones-list">
                    {data.guias.map((item, index) => (
                        <div key={item.ID || index} className={`inscripcion-card ${item.is_paid ? 'pagado-bg' : 'pendiente-bg'}`} data-expanded={!!expandedStates.guias[index]}>
                            <div className="card-header" onClick={() => toggleExpand('guias', index)}>
                                <h3>{item.Nombre || 'Sin Nombre'} - {item.Especies || 'N/A'}</h3>
                                <span className="expand-toggle">▼</span>
                            </div>
                            {expandedStates.guias[index] && (
                                <div className="card-details">
                                    <p><strong>ID:</strong> {item.ID}</p>
                                    <p><strong>NI:</strong> {item.NI || 'N/A'}</p>
                                    <p><strong>Fecha:</strong> {item.Fecha || 'N/A'}</p>
                                    <p><strong>Estado:</strong> {item.is_paid ? 'Pagado' : 'Pendiente'}</p>
                                    <div className="action-buttons">
                                        <a href={getGuiaPdfUrl(item.ID)} target="_blank" rel="noopener noreferrer" className="action-button btn-secondary">Ver PDF</a>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                    {data.guias.length === 0 && <p className="no-data">No hay guías de traslado de Algar.</p>}
                </div>
            </section>

            {/* SECCIÓN 4: RESES */}
            <section className="algar-section" style={{ marginTop: '40px' }}>
                <div className="section-header-algar">
                    <h2>Reses (Algar)</h2>
                    <span className="count-badge">{data.reses.length}</span>
                </div>
                <div className="inscripciones-list">
                    {data.reses.map((item, index) => (
                        <div key={item.ID || index} className={`inscripcion-card ${item.is_paid ? 'pagado-bg' : 'pendiente-bg'}`} data-expanded={!!expandedStates.reses[index]}>
                            <div className="card-header" onClick={() => toggleExpand('reses', index)}>
                                <h3>{item['Nombre y Apellido'] || 'Sin Nombre'} - {item.Especie} ({item['Cantidad de reses']})</h3>
                                <span className="expand-toggle">▼</span>
                            </div>
                            {expandedStates.reses[index] && (
                                <div className="card-details">
                                    <p><strong>ID:</strong> {item.ID}</p>
                                    <p><strong>Fecha:</strong> {item.Fecha || 'N/A'}</p>
                                    <p><strong>Estado:</strong> {item.is_paid ? 'Pagado' : 'Pendiente'}</p>
                                    <div className="action-buttons">
                                        {item.docx_id && (
                                            <a href={getResesPdfUrl(item.docx_id)} target="_blank" rel="noopener noreferrer" className="action-button btn-success">Ver PDF</a>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                    {data.reses.length === 0 && <p className="no-data">No hay registros de reses de Algar.</p>}
                </div>
            </section>

            <style>{`
                .section-header-algar {
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    border-bottom: 2px solid #2E5661;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }
                .section-header-algar h2 {
                    margin: 0;
                    color: #2E5661;
                    font-size: 1.5rem;
                }
                .count-badge {
                    background: #2E5661;
                    color: white;
                    padding: 2px 10px;
                    border-radius: 20px;
                    font-size: 0.9rem;
                    font-weight: bold;
                }
                .no-data {
                    text-align: center;
                    color: #64748B;
                    font-style: italic;
                    padding: 20px;
                }
                .algar-section {
                    background: #f8fafc;
                    padding: 20px;
                    border-radius: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }
            `}</style>
        </div>
    );
};

export default AlgarSA;
