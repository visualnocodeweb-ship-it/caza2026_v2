import React, { useEffect, useState } from 'react';
import { fetchReses, sendResesGuia, sendResesPayment } from '../utils/api';
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
        setSendingGuia(prev => ({ ...prev, [resId]: true }));

        try {
            await sendResesGuia({
                res_id: resId,
                email: res.Email,
                docx_id: res.docx_id
            });
            alert(`Guía enviada exitosamente a ${res.Email}`);
            updateSentStatusLocally(resId, 'guia');
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
                amount: amount
            });
            alert(`Solicitud de cobro por $${amount} enviada a ${res.Email}`);
            updateSentStatusLocally(resId, 'cobro');
        } catch (err) {
            console.error("Error al enviar cobro:", err);
            alert(`Error al enviar cobro: ${err.message}`);
        } finally {
            setSendingPayment(prev => ({ ...prev, [resId]: false }));
        }
    };

    const updateSentStatusLocally = (resId, type) => {
        setReses(prevReses => prevReses.map(r =>
            r.ID === resId
                ? { ...r, sent_statuses: [...new Set([...(r.sent_statuses || []), type])] }
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

                                    <div className="action-buttons" style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '15px' }}>
                                        <div className="reses-payment-section" style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
                                            <label htmlFor={`amount-${item.ID}`} style={{ fontSize: '14px', fontWeight: '600' }}>Monto Cobro:</label>
                                            <input
                                                id={`amount-${item.ID}`}
                                                type="number"
                                                placeholder="Ej: 5000"
                                                value={paymentAmounts[item.ID] || ''}
                                                onChange={(e) => handleAmountChange(item.ID, e.target.value)}
                                                className="search-input"
                                                style={{ width: '120px', padding: '5px 10px', margin: 0 }}
                                            />
                                            <button
                                                className={`action-button btn-primary ${sendingPayment[item.ID] ? 'btn-loading' : ''}`}
                                                onClick={(e) => { e.stopPropagation(); handleSendPayment(item); }}
                                                disabled={sendingPayment[item.ID]}
                                                style={{ margin: 0 }}
                                            >
                                                {sendingPayment[item.ID] ? 'Enviando...' : 'Enviar Cobro'}
                                            </button>
                                        </div>

                                        <div className="guia-actions" style={{ display: 'flex', gap: '10px' }}>
                                            {item.docx_link ? (
                                                <a href={item.docx_link} target="_blank" rel="noopener noreferrer" className="action-button btn-secondary">
                                                    Editar Guía (Docx)
                                                </a>
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
