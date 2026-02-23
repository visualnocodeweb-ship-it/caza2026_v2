import React, { useEffect, useState } from 'react';
import { fetchReses, sendResesGuia, sendResesPayment, logResesAction } from '../utils/api';
import '../styles/App.css';
import '../styles/Responsive.css';

const RECORDS_PER_PAGE = 10;

const Reses = () => {
    const [reses, setReses] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedStates, setExpandedStates] = useState({});
    const [searchTerm, setSearchTerm] = useState('');
    const [sendingGuia, setSendingGuia] = useState({});
    const [sendingPayment, setSendingPayment] = useState({});
    const [paymentAmounts, setPaymentAmounts] = useState({});

    // Paginación
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [totalRecords, setTotalRecords] = useState(0);

    const getReses = async (page) => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchReses(page, RECORDS_PER_PAGE);
            setReses(data.data);
            setTotalRecords(data.total_records);
            setTotalPages(data.total_pages);

            // Inicializar montos desde la DB
            const initialAmounts = {};
            data.data.forEach(item => {
                if (item.permanent_amount) {
                    initialAmounts[item.ID] = item.permanent_amount;
                }
            });
            setPaymentAmounts(prev => ({ ...prev, ...initialAmounts }));

            const initialExpandedStates = data.data.reduce((acc, _, index) => {
                acc[index] = false;
                return acc;
            }, {});
            setExpandedStates(initialExpandedStates);
        } catch (err) {
            console.error("Error al obtener reses:", err);
            setError('No se pudieron cargar los datos de reses.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        getReses(currentPage);
    }, [currentPage]);

    const toggleExpand = (index) => {
        setExpandedStates(prevStates => ({
            ...prevStates,
            [index]: !prevStates[index]
        }));
    };

    const handleEditDocx = async (res) => {
        try {
            const amount = paymentAmounts[res.ID];

            const payload = {
                res_id: res.ID,
                action: "Se abrió el archivo Docx para edición",
            };
            if (amount) {
                payload.amount = amount.toString();
            }
            await logResesAction(payload);
            // Abrir en nueva pestaña
            window.open(res.docx_link, '_blank');
            // Actualizar historial localmente para feedback inmediato
            updateHistoryLocally(res.ID, "Se abrió el archivo Docx para edición");
        } catch (err) {
            console.error("Error logging edit action:", err);
        }
    };

    const handleSendGuia = async (res) => {
        if (!res.docx_id) {
            alert("No se encontró el archivo Docx asociado a este registro.");
            return;
        }

        if (!res.Email) {
            alert("El registro no tiene un email configurado.");
            return;
        }

        const resId = res.ID;
        const amount = paymentAmounts[resId];
        setSendingGuia(prev => ({ ...prev, [resId]: true }));

        try {
            // Guardar monto antes de enviar guía para cumplir con la petición del usuario
            if (amount) {
                await logResesAction({
                    res_id: resId,
                    action: `Iniciando envío de Guía (PDF) con monto de cobro anotado: $${amount}`,
                    amount: amount.toString()
                });
            }

            await sendResesGuia({
                res_id: resId,
                email: res.Email,
                docx_id: res.docx_id
            });
            alert(`Guía enviada exitosamente a ${res.Email}`);
            updateSentStatusLocally(resId, 'guia');
            updateHistoryLocally(resId, `Se envió Guía (PDF) a ${res.Email}`);
        } catch (err) {
            console.error("Error al enviar guía:", err);
            alert(`Error al enviar guía: ${err.message}`);
        } finally {
            setSendingGuia(prev => ({ ...prev, [resId]: false }));
        }
    };

    const handleSendPayment = async (res) => {
        const resId = res.ID;
        const amount = paymentAmounts[resId];

        if (!amount) {
            alert("Por favor, ingrese un monto para el cobro.");
            return;
        }

        if (!res.Email) {
            alert("El registro no tiene un email configurado.");
            return;
        }

        setSendingPayment(prev => ({ ...prev, [resId]: true }));

        try {
            await sendResesPayment({
                res_id: resId,
                email: res.Email,
                amount: amount.toString()
            });
            alert(`Solicitud de cobro por $${amount} enviada a ${res.Email}`);
            updateSentStatusLocally(resId, 'cobro');
            updateHistoryLocally(resId, `Se envió cobro por $${amount} a ${res.Email}`);
        } catch (err) {
            console.error("Error al enviar cobro:", err);
            alert(`Error al enviar cobro: ${err.message}`);
        } finally {
            setSendingPayment(prev => ({ ...prev, [resId]: false }));
        }
    };

    const handleTogglePaid = async (res, paidStatus) => {
        try {
            const resId = res.ID;
            const amount = paymentAmounts[resId];

            const payload = {
                res_id: resId,
                action: `Estado de pago cambiado a: ${paidStatus ? 'SÍ' : 'NO'}`,
                is_paid: paidStatus,
            };

            if (amount) {
                payload.amount = amount.toString();
            }

            await logResesAction(payload);

            // Actualizar localmente
            setReses(prevReses => prevReses.map(r =>
                r.ID === resId ? { ...r, is_paid: paidStatus } : r
            ));
            updateHistoryLocally(resId, `Estado de pago cambiado a: ${paidStatus ? 'SÍ' : 'NO'}`);
        } catch (err) {
            console.error("Error updating paid status:", err);
            alert("Error al actualizar el estado de pago.");
        }
    };

    const handleSaveAmount = async (res) => {
        try {
            const resId = res.ID;
            const amount = paymentAmounts[resId];
            if (!amount) {
                alert("Por favor, ingrese un monto para guardar.");
                return;
            }
            await logResesAction({
                res_id: resId,
                action: `Monto de cobro guardado: $${amount}`,
                amount: amount.toString()
            });

            // Actualizar localmente el monto permanente para feedback visual
            setReses(prevReses => prevReses.map(r =>
                r.ID === resId ? { ...r, permanent_amount: parseFloat(amount) } : r
            ));

            alert("Monto guardado exitosamente.");
            updateHistoryLocally(resId, `Monto de cobro guardado: $${amount}`);
        } catch (err) {
            console.error("Error saving amount:", err);
            alert("Error al guardar el monto.");
        }
    };

    const updateSentStatusLocally = (resId, type) => {
        setReses(prevReses => prevReses.map(r =>
            r.ID === resId
                ? { ...r, sent_statuses: [...new Set([...(r.sent_statuses || []), type])] }
                : r
        ));
    };

    const updateHistoryLocally = (resId, action) => {
        const newLog = { timestamp: new Date().toISOString(), details: action };
        setReses(prevReses => prevReses.map(r =>
            r.ID === resId
                ? { ...r, history: [newLog, ...(r.history || [])] }
                : r
        ));
    };

    const handleAmountChange = (resId, value) => {
        setPaymentAmounts(prev => ({ ...prev, [resId]: value }));
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        return dateString;
    };

    const filteredReses = reses.filter(item =>
        (item['Nombre y Apellido'] && item['Nombre y Apellido'].toLowerCase().includes(searchTerm.toLowerCase())) ||
        (item['DNI'] && item['DNI'].toLowerCase().includes(searchTerm.toLowerCase())) ||
        (item['Especie'] && item['Especie'].toLowerCase().includes(searchTerm.toLowerCase()))
    );

    if (loading && reses.length === 0) {
        return <p className="loading-text">Cargando datos de reses...</p>;
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

            {loading && reses.length > 0 && <p className="loading-text">Actualizando datos...</p>}

            {filteredReses.length > 0 ? (
                <div className="inscripciones-list">
                    {filteredReses.map((item, index) => (
                        <div key={item.ID || index} className="inscripcion-card" data-expanded={!!expandedStates[index]}>
                            <div className="card-header" onClick={() => toggleExpand(index)}>
                                <div className="header-info">
                                    <h3>{item['Nombre y Apellido'] || 'Nombre no disponible'} - {item['Especie']} ({item['Cantidad de reses']})</h3>
                                    {item.sent_statuses && item.sent_statuses.length > 0 && (
                                        <div className="sent-labels">
                                            {item.sent_statuses.map(status => (
                                                <span key={status} className={`sent-badge ${status}`}>Enviado: {status}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <span className="expand-toggle">▼</span>
                            </div>

                            {expandedStates[index] && (
                                <div className="card-details">
                                    <div className="details-grid">
                                        <p><strong>ID:</strong> {item['ID'] || 'N/A'}</p>
                                        <p><strong>Fecha:</strong> {formatDate(item['Fecha'])}</p>
                                        <p><strong>DNI:</strong> {item['DNI'] || 'N/A'}</p>
                                        <p><strong>Domicilio:</strong> {item['Domicilio. Ciudad. Provincia'] || 'N/A'}</p>
                                        <p><strong>Responsable:</strong> {item['Responable del A.C.M / Criadero'] || 'N/A'}</p>
                                        <p><strong>Cantidad:</strong> {item['Cantidad de reses'] || 'N/A'}</p>
                                        <p><strong>Especie:</strong> {item['Especie'] || 'N/A'}</p>
                                        <p><strong>Sexo:</strong> {item['Sexo'] || 'N/A'}</p>
                                        <p><strong>Precinto ACM:</strong> {item['Número Precinto (A.C.M)'] || 'N/A'}</p>
                                        <p><strong>Remitido a:</strong> {item['Remitido a '] || 'N/A'}</p>
                                        <p><strong>Domicilio Remitente:</strong> {item['Domicilio remitente'] || 'N/A'}</p>
                                        <p><strong>Ciudad Remitente:</strong> {item['Ciudad remitente'] || 'N/A'}</p>
                                        <p><strong>Provincia Remitente:</strong> {item['Provincia remitente'] || 'N/A'}</p>
                                        <p><strong>Destino a:</strong> {item['Destino a...'] || 'N/A'}</p>
                                        <p><strong>Transporte:</strong> {item['Medio de transporte'] || 'N/A'}</p>
                                        <p><strong>Patente:</strong> {item['Patente Número'] || 'N/A'}</p>
                                        <p><strong>Email:</strong> {item['Email'] || 'N/A'}</p>
                                    </div>

                                    <div className="reses-actions-wrapper" style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

                                        {/* Sección de Acciones: Agrupada y Clara */}
                                        <div className="action-buttons-container" style={{ border: '1px solid #e0e0e0', padding: '15px', borderRadius: '8px', backgroundColor: '#fff' }}>
                                            <h5 style={{ margin: '0 0 15px', fontSize: '15px', color: '#333', borderBottom: '1px solid #eee', paddingBottom: '8px' }}>Acciones de Gestión</h5>

                                            {/* Fila 1: Estado de Pago */}
                                            <div className="reses-paid-toggle" style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '20px', padding: '10px', backgroundColor: '#f0f7ff', borderRadius: '6px' }}>
                                                <span style={{ fontSize: '14px', fontWeight: '700', color: '#0056b3' }}>¿Pagado?</span>
                                                <div style={{ display: 'flex', gap: '10px' }}>
                                                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', fontSize: '14px' }}>
                                                        <input
                                                            type="radio"
                                                            name={`paid-${item.ID}`}
                                                            checked={item.is_paid === true}
                                                            onChange={() => handleTogglePaid(item, true)}
                                                        /> Sí
                                                    </label>
                                                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', fontSize: '14px' }}>
                                                        <input
                                                            type="radio"
                                                            name={`paid-${item.ID}`}
                                                            checked={item.is_paid === false}
                                                            onChange={() => handleTogglePaid(item, false)}
                                                        /> No
                                                    </label>
                                                </div>
                                            </div>

                                            {/* Fila 2: Monto y Cobro */}
                                            <div className="reses-payment-section" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
                                                <label htmlFor={`amount-${item.ID}`} style={{ fontSize: '14px', fontWeight: '600' }}>Monto Cobro:</label>
                                                <input
                                                    id={`amount-${item.ID}`}
                                                    type="number"
                                                    placeholder="Ej: 5000"
                                                    value={paymentAmounts[item.ID] || ''}
                                                    onChange={(e) => handleAmountChange(item.ID, e.target.value)}
                                                    className="search-input"
                                                    style={{ width: '100px', padding: '5px 10px', margin: 0 }}
                                                />
                                                <button
                                                    className="action-button btn-secondary"
                                                    onClick={(e) => { e.stopPropagation(); handleSaveAmount(item); }}
                                                    style={{ margin: 0, padding: '5px 15px', fontSize: '13px', backgroundColor: '#6c757d' }}
                                                >
                                                    Guardar
                                                </button>
                                                <button
                                                    className={`action-button btn-primary ${sendingPayment[item.ID] ? 'btn-loading' : ''}`}
                                                    onClick={(e) => { e.stopPropagation(); handleSendPayment(item); }}
                                                    disabled={sendingPayment[item.ID]}
                                                    style={{ margin: 0 }}
                                                >
                                                    {sendingPayment[item.ID] ? 'Enviando...' : 'Enviar Cobro'}
                                                </button>
                                            </div>

                                            {/* Fila 3: Guías */}
                                            <div className="guia-actions" style={{ display: 'flex', gap: '10px' }}>
                                                {item.docx_link ? (
                                                    <button
                                                        className="action-button btn-secondary"
                                                        onClick={(e) => { e.stopPropagation(); handleEditDocx(item); }}
                                                    >
                                                        Editar Guía (Docx)
                                                    </button>
                                                ) : (
                                                    <button className="action-button btn-disabled" disabled title="No se encontró el archivo en la carpeta Docx">Docx no encontrado</button>
                                                )}

                                                <button
                                                    className={`action-button btn-success ${sendingGuia[item.ID] ? 'btn-loading' : ''}`}
                                                    onClick={(e) => { e.stopPropagation(); handleSendGuia(item); }}
                                                    disabled={sendingGuia[item.ID] || !item.docx_id}
                                                >
                                                    {sendingGuia[item.ID] ? 'Enviando...' : 'Enviar Guía (PDF)'}
                                                </button>
                                            </div>
                                        </div>

                                        {/* Sección de Historial: Separada y al final */}
                                        {item.history && item.history.length > 0 && (
                                            <div className="history-section" style={{ backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '8px', border: '1px dashed #ccc' }}>
                                                <h4 style={{ margin: '0 0 10px', fontSize: '13px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Historial de Movimientos</h4>
                                                <div className="history-list" style={{ maxHeight: '120px', overflowY: 'auto', borderLeft: '2px solid #ddd', paddingLeft: '10px' }}>
                                                    {item.history.map((log, lIdx) => (
                                                        <div key={lIdx} className="history-item" style={{ fontSize: '11px', padding: '4px 0', borderBottom: '1px solid #f0f0f0', color: '#555' }}>
                                                            <span style={{ fontWeight: '600', color: '#888', marginRight: '8px' }}>
                                                                {new Date(log.timestamp).toLocaleString()}:
                                                            </span>
                                                            {log.details}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
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

export default Reses;
