import React, { useEffect, useState, useCallback } from 'react';
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

    const [pages, setPages] = useState({
        insc: 1,
        perm: 1,
        res: 1,
        gui: 1
    });

    const [totalPages, setTotalPages] = useState({
        insc: 0,
        perm: 0,
        res: 0,
        gui: 0
    });

    const [loading, setLoading] = useState({
        insc: false,
        perm: false,
        res: false,
        gui: false
    });

    const [expandedStates, setExpandedStates] = useState({
        inscripciones: {},
        permisos: {},
        reses: {},
        guias: {}
    });

    const limit = 40;
    const searchAlgar = "Algar";

    const fetchData = useCallback(async (section, page) => {
        setLoading(prev => ({ ...prev, [section]: true }));
        try {
            let result;
            switch (section) {
                case 'insc':
                    result = await fetchInscripciones(page, limit, searchAlgar);
                    setData(prev => ({ ...prev, inscripciones: result.data || [] }));
                    setTotalPages(prev => ({ ...prev, insc: result.total_pages || 0 }));
                    break;
                case 'perm':
                    result = await fetchPermisos(page, limit, searchAlgar);
                    setData(prev => ({ ...prev, permisos: result.data || [] }));
                    setTotalPages(prev => ({ ...prev, perm: result.total_pages || 0 }));
                    break;
                case 'res':
                    result = await fetchReses(page, limit, searchAlgar);
                    setData(prev => ({ ...prev, reses: result.data || [] }));
                    setTotalPages(prev => ({ ...prev, res: result.total_pages || 0 }));
                    break;
                case 'gui':
                    result = await fetchGuiasTraslados(page, limit, searchAlgar);
                    setData(prev => ({ ...prev, guias: result.data || [] }));
                    setTotalPages(prev => ({ ...prev, gui: result.total_pages || 0 }));
                    break;
                default:
                    break;
            }
        } catch (err) {
            console.error(`Error al cargar datos de ${section}:`, err);
        } finally {
            setLoading(prev => ({ ...prev, [section]: false }));
        }
    }, []);

    useEffect(() => {
        fetchData('insc', pages.insc);
    }, [pages.insc, fetchData]);

    useEffect(() => {
        fetchData('perm', pages.perm);
    }, [pages.perm, fetchData]);

    useEffect(() => {
        fetchData('res', pages.res);
    }, [pages.res, fetchData]);

    useEffect(() => {
        fetchData('gui', pages.gui);
    }, [pages.gui, fetchData]);

    const handlePageChange = (section, newPage) => {
        if (newPage >= 1 && newPage <= totalPages[section]) {
            setPages(prev => ({ ...prev, [section]: newPage }));
            // Reset scroll to top of section or similar if needed
        }
    };

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

    const Pagination = ({ section, currentPage, total }) => {
        if (total <= 1) return null;
        return (
            <div className="pagination-minimal">
                <button
                    disabled={currentPage <= 1 || loading[section]}
                    onClick={() => handlePageChange(section, currentPage - 1)}
                    className="p-btn"
                >
                    Anterior
                </button>
                <span className="p-info">Página {currentPage} de {total}</span>
                <button
                    disabled={currentPage >= total || loading[section]}
                    onClick={() => handlePageChange(section, currentPage + 1)}
                    className="p-btn"
                >
                    Siguiente
                </button>
            </div>
        );
    };

    const isGlobalLoading = loading.insc && loading.perm && loading.res && loading.gui &&
        data.inscripciones.length === 0 && data.permisos.length === 0;

    if (isGlobalLoading) return <div className="loading-container"><p>Iniciando carga de Algar SA...</p></div>;

    return (
        <div className="algar-sa-container" style={{ padding: '20px' }}>
            <h1 style={{ color: '#2E5661', marginBottom: '30px', textAlign: 'center' }}>Registros Consolidados: Algar SA</h1>

            {/* SECCIÓN 1: INSCRIPCIONES */}
            <section className="algar-section">
                <div className="section-header-algar">
                    <h2>Inscripciones (Algar)</h2>
                    {loading.insc && <span className="loading-inline">Cargando...</span>}
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
                    {data.inscripciones.length === 0 && !loading.insc && <p className="no-data">No hay inscripciones de Algar.</p>}
                </div>
                <Pagination section="insc" currentPage={pages.insc} total={totalPages.insc} />
            </section>

            {/* SECCIÓN 2: PERMISOS DE CAZA */}
            <section className="algar-section" style={{ marginTop: '40px' }}>
                <div className="section-header-algar">
                    <h2>Permisos de Caza (Algar)</h2>
                    {loading.perm && <span className="loading-inline">Cargando...</span>}
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
                    {data.permisos.length === 0 && !loading.perm && <p className="no-data">No hay permisos de Algar.</p>}
                </div>
                <Pagination section="perm" currentPage={pages.perm} total={totalPages.perm} />
            </section>

            {/* SECCIÓN 3: GUÍAS DE TRASLADO */}
            <section className="algar-section" style={{ marginTop: '40px' }}>
                <div className="section-header-algar">
                    <h2>Guías de Traslado (Algar)</h2>
                    {loading.gui && <span className="loading-inline">Cargando...</span>}
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
                    {data.guias.length === 0 && !loading.gui && <p className="no-data">No hay guías de traslado de Algar.</p>}
                </div>
                <Pagination section="gui" currentPage={pages.gui} total={totalPages.gui} />
            </section>

            {/* SECCIÓN 4: RESES */}
            <section className="algar-section" style={{ marginTop: '40px' }}>
                <div className="section-header-algar">
                    <h2>Reses (Algar)</h2>
                    {loading.res && <span className="loading-inline">Cargando...</span>}
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
                    {data.reses.length === 0 && !loading.res && <p className="no-data">No hay registros de reses de Algar.</p>}
                </div>
                <Pagination section="res" currentPage={pages.res} total={totalPages.res} />
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
                .loading-inline {
                    font-size: 0.8rem;
                    color: #64748B;
                    font-style: italic;
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
                .pagination-minimal {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 20px;
                    margin-top: 25px;
                    padding-top: 15px;
                    border-top: 1px solid #E2E8F0;
                }
                .p-btn {
                    background: white;
                    border: 1px solid #CBD5E1;
                    padding: 6px 15px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 0.85rem;
                    font-weight: 600;
                    color: #2E5661;
                    transition: all 0.2s;
                }
                .p-btn:hover:not(:disabled) {
                    background: #F1F5F9;
                    border-color: #2E5661;
                }
                .p-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                .p-info {
                    font-size: 0.9rem;
                    font-weight: 600;
                    color: #64748B;
                }
            `}</style>
        </div>
    );
};

export default AlgarSA;
