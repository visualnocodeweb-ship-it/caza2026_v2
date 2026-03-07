import React, { useEffect, useState } from 'react';
import { fetchGuiasTraslados, getGuiaPdfUrl, sendGuiaEmail, saveGuiaPago, sendGuiaCobro } from '../utils/api';
import '../styles/App.css';
import '../styles/Responsive.css';

const RECORDS_PER_PAGE = 10;

const GuiasTraslados = () => {
    const [guias, setGuias] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sendingEmail, setSendingEmail] = useState({});
    const [sendingCobro, setSendingCobro] = useState({});
    const [savingAmount, setSavingAmount] = useState({});
    const [error, setError] = useState(null);
    const [expandedStates, setExpandedStates] = useState({});
    const [searchTerm, setSearchTerm] = useState('');

    const [amounts, setAmounts] = useState({}); // {guia_id: amount}
    const [paidStatus, setPaidStatus] = useState({}); // {guia_id: boolean}

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

            // Cargar montos y estados de pago iniciales
            const initialAmounts = {};
            const initialPaidStatus = {};
            data.data.forEach(item => {
                initialAmounts[item.ID] = item.amount || 0;
                initialPaidStatus[item.ID] = item.is_paid || false;
            });
            setAmounts(initialAmounts);
            setPaidStatus(initialPaidStatus);

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
        if (!window.confirm("¿Seguro que quieres enviar el PDF de la guía por email al solicitante?")) return;
        setSendingEmail(prev => ({ ...prev, [guiaId]: true }));
        try {
            await sendGuiaEmail(guiaId);
            alert("Email enviado correctamente con el PDF adjunto.");
            // Recargar para ver el log en el historial
            getGuias(currentPage, searchTerm);
        } catch (err) {
            console.error("Error al enviar email:", err);
            alert("No se pudo enviar el email: " + err.message);
        } finally {
            setSendingEmail(prev => ({ ...prev, [guiaId]: false }));
        }
    };

    const handleAmountChange = (guiaId, value) => {
        setAmounts(prev => ({ ...prev, [guiaId]: value }));
    };

    const handleSaveAmount = async (guiaId) => {
        setSavingAmount(prev => ({ ...prev, [guiaId]: true }));
        try {
            const amount = parseFloat(amounts[guiaId] || 0);
            const isPaid = paidStatus[guiaId] || false;
            await saveGuiaPago({ guia_id: guiaId, amount, is_paid: isPaid });
            alert("Monto guardado correctamente.");
            getGuias(currentPage, searchTerm);
        } catch (err) {
            console.error("Error al guardar monto:", err);
            alert("Error: " + err.message);
        } finally {
            setSavingAmount(prev => ({ ...prev, [guiaId]: false }));
        }
    };

    const handleTogglePaid = async (guiaId) => {
        const newStatus = !paidStatus[guiaId];
        setPaidStatus(prev => ({ ...prev, [guiaId]: newStatus }));
        try {
            const amount = parseFloat(amounts[guiaId] || 0);
            await saveGuiaPago({ guia_id: guiaId, amount, is_paid: newStatus });
            getGuias(currentPage, searchTerm);
        } catch (err) {
            console.error("Error al actualizar estado de pago:", err);
            alert("Error: " + err.message);
            setPaidStatus(prev => ({ ...prev, [guiaId]: !newStatus }));
        }
    };

    const handleSendCobro = async (guiaId, email) => {
        const amount = amounts[guiaId] || 0;
        if (amount <= 0) {
            alert("Por favor, ingresa un precio de guía mayor a 0 antes de enviar el cobro.");
            return;
        }
        if (!email) {
            alert("El registro no tiene un correo electrónico válido.");
            return;
        }

        if (!window.confirm(`¿Enviar solicitud de cobro por $${amount} a ${email}?`)) return;

        setSendingCobro(prev => ({ ...prev, [guiaId]: true }));
        try {
            await sendGuiaCobro({ guia_id: guiaId, email, amount });
            alert("Enlace de cobro enviado correctamente.");
            getGuias(currentPage, searchTerm);
        } catch (err) {
            console.error("Error al enviar cobro:", err);
            alert("Error: " + err.message);
        } finally {
            setSendingCobro(prev => ({ ...prev, [guiaId]: false }));
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
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <h3>{item['Nombre'] || 'Nombre no disponible'} - {item['Especies'] || item['Especie'] || 'N/A'}</h3>
                                        {paidStatus[item.ID] && <span className="status-badge approved" style={{ padding: '2px 8px', fontSize: '10px' }}>PAGADO</span>}
                                    </div>
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

                                    {/* Gestión de Pago */}
                                    <div className="payment-management" style={{ marginTop: '20px', padding: '15px', background: '#f0f9ff', borderRadius: '8px', border: '1px solid #bae6fd' }}>
                                        <h4 style={{ margin: '0 0 10px 0', color: '#0369a1' }}>Gestión de Pago</h4>
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '15px', alignItems: 'center' }}>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                                <label style={{ fontSize: '12px', fontWeight: 'bold' }}>Precio de Guía ($)</label>
                                                <div style={{ display: 'flex', gap: '5px' }}>
                                                    <input
                                                        type="number"
                                                        value={amounts[item.ID] || ''}
                                                        onChange={(e) => handleAmountChange(item.ID, e.target.value)}
                                                        placeholder="0.00"
                                                        style={{ width: '100px', padding: '8px', borderRadius: '4px', border: '1px solid #cbd5e1' }}
                                                    />
                                                    <button
                                                        onClick={() => handleSaveAmount(item.ID)}
                                                        disabled={savingAmount[item.ID]}
                                                        className="action-button btn-primary"
                                                        style={{ padding: '8px 15px', minWidth: '80px' }}
                                                    >
                                                        {savingAmount[item.ID] ? '...' : 'Guardar'}
                                                    </button>
                                                </div>
                                            </div>

                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                                <label style={{ fontSize: '12px', fontWeight: 'bold' }}>¿Pagado?</label>
                                                <button
                                                    onClick={() => handleTogglePaid(item.ID)}
                                                    className={`action-button ${paidStatus[item.ID] ? 'btn-success' : 'btn-secondary'}`}
                                                    style={{ padding: '8px 15px', minWidth: '100px' }}
                                                >
                                                    {paidStatus[item.ID] ? 'SÍ (Pagado)' : 'NO'}
                                                </button>
                                            </div>

                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                                <label style={{ fontSize: '12px', fontWeight: 'bold' }}>Acción</label>
                                                <button
                                                    onClick={() => handleSendCobro(item.ID, item['Correo'])}
                                                    disabled={sendingCobro[item.ID]}
                                                    className="action-button"
                                                    style={{ padding: '8px 15px', background: '#0ea5e9', color: 'white', border: 'none' }}
                                                >
                                                    {sendingCobro[item.ID] ? 'Enviando...' : 'Enviar Cobro Email'}
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {item['Imagen'] && (
                                        <div style={{ marginTop: '15px' }}>
                                            <strong>Imagen:</strong><br />
                                            <img src={item['Imagen']} alt="Registro" style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px', marginTop: '10px' }} />
                                        </div>
                                    )}

                                    <div className="reses-actions-wrapper" style={{ marginTop: '20px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                                        <button
                                            className="action-button btn-primary"
                                            onClick={() => handleCopyId(item['ID'])}
                                            style={{ minWidth: '100px' }}
                                        >
                                            Copiar ID
                                        </button>
                                        <a
                                            href="https://cazaypesca.neuquen.gob.ar/?ff_landing=22"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="action-button btn-success"
                                            style={{ textDecoration: 'none', minWidth: '100px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                                        >
                                            Parte 2 Kobo
                                        </a>
                                        <a
                                            href={getGuiaPdfUrl(item['ID'])}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="action-button btn-secondary"
                                            style={{ textDecoration: 'none', background: '#64748b', color: 'white', minWidth: '100px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                                        >
                                            Ver PDF Final
                                        </a>
                                        <button
                                            className="action-button"
                                            onClick={() => handleSendEmail(item['ID'])}
                                            disabled={sendingEmail[item['ID']]}
                                            style={{ background: '#2E5661', color: 'white', minWidth: '130px' }}
                                        >
                                            {sendingEmail[item['ID']] ? 'Enviando...' : 'Enviar PDF Email'}
                                        </button>
                                    </div>

                                    {/* Historial de Movimientos */}
                                    <div className="history-section" style={{ marginTop: '25px', borderTop: '1px solid #e2e8f0', paddingTop: '15px' }}>
                                        <h4 style={{ margin: '0 0 10px 0', color: '#475569', fontSize: '0.9rem' }}>Historial de Movimientos</h4>
                                        <div className="history-list" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                            {item.history && item.history.length > 0 ? (
                                                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                                                    {item.history.map((log, lIdx) => (
                                                        <li key={lIdx} style={{ fontSize: '11px', padding: '6px 0', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between' }}>
                                                            <span style={{ color: '#64748b' }}>{new Date(log.timestamp).toLocaleString()}</span>
                                                            <span style={{ fontWeight: '500', color: '#334155' }}>{log.event}</span>
                                                            <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>{log.details}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>No hay movimientos registrados.</p>
                                            )}
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
