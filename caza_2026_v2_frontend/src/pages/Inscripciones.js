import React, { useEffect, useState } from 'react';
import { fetchInscripciones, linkData, sendPaymentLink, sendCredentialAPI, viewCredentialAPI, logSentItem, fetchSentItems } from '../utils/api';
import '../styles/App.css';
import '../styles/Responsive.css';

const RECORDS_PER_PAGE = 10;

const Inscripciones = () => {
  const [inscripciones, setInscripciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedStates, setExpandedStates] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [linkingData, setLinkingData] = useState(false);
  const [linkingError, setLinkingError] = useState(null);
  const [sendingEmail, setSendingEmail] = useState({});
  const [sendingPayment, setSendingPayment] = useState({});
  const [sendingCredential, setSendingCredential] = useState({});
  const [viewingCredential, setViewingCredential] = useState({});
  // Estados para la paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalRecords, setTotalRecords] = useState(0);

  const getInscripciones = async (page) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInscripciones(page, RECORDS_PER_PAGE);

      setInscripciones(data.data);
      setTotalRecords(data.total_records);
      setTotalPages(data.total_pages);

      const initialExpandedStates = data.data.reduce((acc, _, index) => {
        acc[index] = false;
        return acc;
      }, {});
      setExpandedStates(initialExpandedStates);
    } catch (err) {
      console.error("Error al obtener inscripciones:", err);
      setError('No se pudieron cargar las inscripciones.');
      setInscripciones([]);
      setTotalRecords(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getInscripciones(currentPage);
  }, [currentPage]);

  const toggleExpand = (index) => {
    setExpandedStates(prevStates => ({
      ...prevStates,
      [index]: !prevStates[index]
    }));
  };

  const handleLinkData = async () => {
    setLinkingData(true);
    setLinkingError(null);
    try {
      await linkData();
      await getInscripciones(currentPage);
      alert('Datos vinculados y actualizados correctamente.');
    } catch (err) {
      setLinkingError('Error al vincular los datos: ' + err.message);
    } finally {
      setLinkingData(false);
    }
  };

  const handleSendEmail = (inscripcion) => {
    if (!inscripcion.email) {
      alert('No hay dirección de correo para enviar.');
      return;
    }
    const to = inscripcion.email;
    const subject = `Contacto desde Panel Caza para ${inscripcion.nombre_establecimiento || 'tu establecimiento'}`;
    const body = `Estimado/a ${inscripcion.nombre_establecimiento || 'cliente'},\n\nNos ponemos en contacto desde Caza 2026.\n\nSaludos cordiales,\nEl equipo de Caza 2026`;
    window.location.href = `https://mail.google.com/mail/?view=cm&fs=1&to=${to}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  const updateSentStatusLocally = (inscripcionId, sentType) => {
    setInscripciones(prevInscripciones =>
      prevInscripciones.map(insc =>
        insc.numero_inscripcion === inscripcionId
          ? { ...insc, sent_statuses: [...insc.sent_statuses, sentType] }
          : insc
      )
    );
  };

  const handleSendPayment = async (inscripcion, index) => {
    if (!inscripcion.email || !inscripcion.numero_inscripcion || !inscripcion.nombre_establecimiento) {
      alert('Faltan datos esenciales (email, ID de inscripción o nombre) para enviar el cobro.');
      return;
    }

    setSendingPayment(prev => ({ ...prev, [index]: true }));
    try {
      await sendPaymentLink({
        inscription_id: inscripcion.numero_inscripcion,
        email: inscripcion.email,
        nombre_establecimiento: inscripcion.nombre_establecimiento,
        tipo_establecimiento: inscripcion['su establecimiento es'],
      });
      await logSentItem({ item_id: inscripcion.numero_inscripcion, item_type: 'inscripcion', sent_type: 'cobro' });
      alert(`Email de cobro enviado a ${inscripcion.email} con éxito.`);
      updateSentStatusLocally(inscripcion.numero_inscripcion, 'cobro');
    } catch (err) {
      alert(`Error al enviar el email de cobro: ${err.message}`);
    } finally {
      setSendingPayment(prev => ({ ...prev, [index]: false }));
    }
  };

  const handleSendCredential = async (inscripcion, index) => {
    if (!inscripcion.email) {
      alert('No hay dirección de correo para enviar la credencial.');
      return;
    }

    setSendingCredential(prev => ({ ...prev, [index]: true }));
    try {
      await sendCredentialAPI({
        numero_inscripcion: inscripcion.numero_inscripcion,
        nombre_establecimiento: inscripcion.nombre_establecimiento,
        razon_social: inscripcion.razon_social,
        cuit: inscripcion.cuit,
        tipo_establecimiento: inscripcion['su establecimiento es'],
        email: inscripcion.email,
      });
      await logSentItem({ item_id: inscripcion.numero_inscripcion, item_type: 'inscripcion', sent_type: 'credencial' });
      alert(`Credencial enviada a ${inscripcion.email} con éxito.`);
      updateSentStatusLocally(inscripcion.numero_inscripcion, 'credencial');
    } catch (err) {
      alert(`Error al enviar la credencial: ${err.message}`);
    } finally {
      setSendingCredential(prev => ({ ...prev, [index]: false }));
    }
  };

  const handleViewCredential = async (inscripcion, index) => {
    if (!inscripcion.numero_inscripcion) {
      alert('No hay número de inscripción para ver la credencial.');
      return;
    }

    setViewingCredential(prev => ({ ...prev, [index]: true }));
    try {
      const credentialHtml = await viewCredentialAPI(inscripcion.numero_inscripcion);
      const newWindow = window.open();
      newWindow.document.write(credentialHtml);
      newWindow.document.close();
    } catch (err) {
      alert(`Error al ver la credencial: ${err.message}`);
    } finally {
      setViewingCredential(prev => ({ ...prev, [index]: false }));
    }
  };

  const handleSendPdf = async (inscripcion) => {
    try {
      // Assuming 'Ver PDF' action also needs logging
      await logSentItem({ item_id: inscripcion.numero_inscripcion, item_type: 'inscripcion', sent_type: 'pdf' });
      updateSentStatusLocally(inscripcion.numero_inscripcion, 'pdf');
    } catch (err) {
      alert(`Error al registrar la acción de ver PDF: ${err.message}`);
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return 'Fecha inválida';
    }
    return date.toLocaleString();
  };

  const filteredInscripciones = inscripciones.filter(inscripcion =>
    (inscripcion.nombre_establecimiento && inscripcion.nombre_establecimiento.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (inscripcion.razon_social && inscripcion.razon_social.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading && inscripciones.length === 0) {
    return <p>Cargando inscripciones...</p>;
  }

  if (error) {
    return <p>Error al cargar inscripciones: {error}</p>;
  }

  return (
    <div>
      <div className="toolbar">
        <button onClick={handleLinkData} disabled={linkingData} className="action-button btn-primary">
          {linkingData ? 'Vinculando...' : 'Vincular Datos'}
        </button>
        <input
          type="text"
          placeholder="Buscar por nombre o razón social..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
      </div>
      {linkingError && <p style={{ color: 'red', textAlign: 'center' }}>{linkingError}</p>}

      {loading && inscripciones.length > 0 && <p>Actualizando inscripciones...</p>}

      {filteredInscripciones.length > 0 ? (
        <div className="inscripciones-list">
          {filteredInscripciones.map((inscripcion, index) => (
            <div key={inscripcion.numero_inscripcion || index} className={`inscripcion-card ${inscripcion['Estado de Pago'] === 'Pagado' ? 'pagado-bg' : ''}`} data-expanded={!!expandedStates[index]}>
              <div className="card-header" onClick={() => toggleExpand(index)}>
                <h3>{inscripcion.nombre_establecimiento || 'Nombre no disponible'}</h3>
                <span className="expand-toggle">▼</span>
              </div>

              {expandedStates[index] && (
                <div className="card-details">
                  <p><strong>Email:</strong> {inscripcion.email || 'N/A'}</p>
                  <p><strong>Establecimiento:</strong> {inscripcion['su establecimiento es'] || 'N/A'}</p>
                  <p><strong>Celular:</strong> {inscripcion.celular ? <a href={`https://wa.me/${inscripcion.celular.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer" className="whatsapp-button"><i className="fab fa-whatsapp"></i> {inscripcion.celular}</a> : 'N/A'}</p>
                  <p><strong>Fecha:</strong> {formatDate(inscripcion.fecha_creacion)}</p>
                  <p><strong>Estado del Pago:</strong> <span className={`status-pago status-${(inscripcion['Estado de Pago'] || 'pendiente').toLowerCase()}`}>{inscripcion['Estado de Pago'] || 'Pendiente'}</span></p>

                  <div className="action-buttons">
                    {inscripcion.pdf_link && (
                      <a href={inscripcion.pdf_link} target="_blank" rel="noopener noreferrer" className="action-button btn-secondary" onClick={() => handleSendPdf(inscripcion)}>
                        Ver PDF
                      </a>
                    )}
                    <button
                      onClick={() => handleViewCredential(inscripcion, index)}
                      disabled={viewingCredential[index]}
                      className="action-button btn-info"
                    >
                      {viewingCredential[index] ? 'Cargando...' : 'Ver Credencial'}
                    </button>
                    {inscripcion.email && (
                      <>
                        <button
                          onClick={() => handleSendEmail(inscripcion)}
                          className="action-button btn-secondary"
                        >
                          Enviar Email
                        </button>
                        <button
                          onClick={() => handleSendPayment(inscripcion, index)}
                          disabled={sendingPayment[index] || inscripcion['Estado de Pago'] === 'Pagado'}
                          className="action-button btn-primary"
                        >
                          {sendingPayment[index] ? 'Enviando...' : (inscripcion['Estado de Pago'] === 'Pagado' ? 'Pagado' : 'Enviar Cobro')}
                        </button>
                        <button
                          onClick={() => handleSendCredential(inscripcion, index)}
                          disabled={sendingCredential[index]}
                          className="action-button btn-success"
                        >
                          {sendingCredential[index] ? 'Enviando...' : 'Enviar Credencial'}
                        </button>
                      </>
                    )}
                  </div>
                  <div className="sent-status-container">
                    {inscripcion.sent_statuses && inscripcion.sent_statuses.length > 0 && (
                      <p style={{ fontSize: '10px', color: '#555', margin: '5px 0 0' }}>
                        Enviado: {inscripcion.sent_statuses.join(', ')}
                      </p>
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
        <p>No se encontraron inscripciones que coincidan con la búsqueda.</p>
      )}
    </div>
  );
};

export default Inscripciones;