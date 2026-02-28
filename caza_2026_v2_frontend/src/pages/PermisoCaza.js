import React, { useEffect, useState } from 'react';
import { fetchPermisos, sendPermisoPaymentLink, sendPermisoEmailAPI, logSentItem, fetchSentItems } from '../utils/api'; // Updated API imports
import '../styles/App.css';
import '../styles/Responsive.css';

const RECORDS_PER_PAGE = 10;

const PermisoCaza = () => {
  const [permisos, setPermisos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedStates, setExpandedStates] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [sendingPayment, setSendingPayment] = useState({});
  const [sendingPermiso, setSendingPermiso] = useState({});
  // Estados para la paginación
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalRecords, setTotalRecords] = useState(0);

  const getPermisos = async (page) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPermisos(page, RECORDS_PER_PAGE);

      setPermisos(data.data);
      setTotalRecords(data.total_records);
      setTotalPages(data.total_pages);

      const initialExpandedStates = data.data.reduce((acc, _, index) => {
        acc[index] = false;
        return acc;
      }, {});
      setExpandedStates(initialExpandedStates);
    } catch (err) {
      console.error("Error al obtener permisos:", err);
      setError('No se pudieron cargar los permisos.');
      setPermisos([]);
      setTotalRecords(0);
      setTotalPages(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getPermisos(currentPage);
  }, [currentPage]);

  const toggleExpand = (index) => {
    setExpandedStates(prevStates => ({
      ...prevStates,
      [index]: !prevStates[index]
    }));
  };

  const handleSendEmail = (permiso) => {
    if (!permiso['Dirección de correo electrónico']) {
      alert('No hay dirección de correo para enviar.');
      return;
    }
    const to = permiso['Dirección de correo electrónico'];
    const subject = `Contacto desde Panel Caza para ${permiso['Nombre y Apellido']}`;
    const body = `Estimado/a ${permiso['Nombre y Apellido']},\n\nNos ponemos en contacto desde Caza 2026.\n\nSaludos cordiales,\nEl equipo de Caza 2026`;
    window.location.href = `https://mail.google.com/mail/?view=cm&fs=1&to=${to}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  const updateSentStatusLocally = (permisoId, sentType) => {
    setPermisos(prevPermisos =>
      prevPermisos.map(perm =>
        perm.ID === permisoId
          ? { ...perm, sent_statuses: [...perm.sent_statuses, sentType] }
          : perm
      )
    );
  };

  const handleSendPermisoPayment = async (permiso, index) => {
    if (!permiso['Dirección de correo electrónico'] || !permiso.ID || !permiso['Nombre y Apellido'] || !permiso['Categoría']) {
      alert('Faltan datos esenciales (email, ID, nombre o categoría) para enviar el cobro.');
      return;
    }

    setSendingPayment(prev => ({ ...prev, [index]: true }));
    try {
      await sendPermisoPaymentLink({
        permiso_id: permiso.ID,
        email: permiso['Dirección de correo electrónico'],
        nombre_apellido: permiso['Nombre y Apellido'],
        categoria: permiso['Categoría'],
      });
      await logSentItem({ item_id: permiso.ID, item_type: 'permiso', sent_type: 'cobro' });
      alert(`Email de cobro enviado a ${permiso['Dirección de correo electrónico']} con éxito.`);
      updateSentStatusLocally(permiso.ID, 'cobro');
    } catch (err) {
      alert(`Error al enviar el email de cobro: ${err.message}`);
    } finally {
      setSendingPayment(prev => ({ ...prev, [index]: false }));
    }
  };

  const handleSendPermiso = async (permiso, index) => {
    if (!permiso['Dirección de correo electrónico'] || !permiso.ID) {
      alert('Faltan datos esenciales (email o ID) para enviar el permiso.');
      return;
    }

    setSendingPermiso(prev => ({ ...prev, [index]: true }));
    try {
      await sendPermisoEmailAPI({
        permiso_id: permiso.ID,
        email: permiso['Dirección de correo electrónico'],
        nombre_apellido: permiso['Nombre y Apellido'],
      });
      await logSentItem({ item_id: permiso.ID, item_type: 'permiso', sent_type: 'permiso' });
      alert(`Permiso enviado a ${permiso['Dirección de correo electrónico']} con éxito.`);
      updateSentStatusLocally(permiso.ID, 'permiso');
    } catch (err) {
      alert(`Error al enviar el permiso: ${err.message}`);
    } finally {
      setSendingPermiso(prev => ({ ...prev, [index]: false }));
    }
  };

  const handleSendPdf = async (permiso) => {
    try {
      await logSentItem({ item_id: permiso.ID, item_type: 'permiso', sent_type: 'pdf' });
      updateSentStatusLocally(permiso.ID, 'pdf');
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

  const filteredPermisos = permisos.filter(permiso =>
    (permiso['Nombre y Apellido'] && permiso['Nombre y Apellido'].toLowerCase().includes(searchTerm.toLowerCase())) ||
    (permiso['DNI o Pasaporte'] && permiso['DNI o Pasaporte'].toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (loading && permisos.length === 0) {
    return <p>Cargando permisos...</p>;
  }

  if (error) {
    return <p>Error al cargar permisos: {error}</p>;
  }

  return (
    <div>
      <div className="toolbar">
        <input
          type="text"
          placeholder="Buscar por nombre o DNI..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
      </div>

      {loading && permisos.length > 0 && <p>Actualizando permisos...</p>}

      {filteredPermisos.length > 0 ? (
        <div className="inscripciones-list">
          {filteredPermisos.map((permiso, index) => (
            <div key={permiso.ID || index} className={`inscripcion-card ${permiso['Estado de Pago'] === 'Pagado' ? 'pagado-bg' : ''}`} data-expanded={!!expandedStates[index]}>
              <div className="card-header" onClick={() => toggleExpand(index)}>
                <h3>{permiso['Nombre y Apellido'] || 'Nombre no disponible'}</h3>
                <span className="expand-toggle">▼</span>
              </div>

              {expandedStates[index] && (
                <div className="card-details">
                  <p><strong>Email:</strong> {permiso['Dirección de correo electrónico'] || 'N/A'}</p>
                  <p><strong>Categoría:</strong> {permiso['Categoría'] || 'N/A'}</p>
                  <p><strong>ACM:</strong> {permiso['ACM'] || 'N/A'}</p>
                  <p><strong>Celular:</strong> {permiso.WhatsApp ? <a href={`https://wa.me/${permiso.WhatsApp.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer" className="whatsapp-button"><i className="fab fa-whatsapp"></i> {permiso.WhatsApp}</a> : 'N/A'}</p>
                  <p><strong>Fecha:</strong> {formatDate(permiso.Fecha)}</p>
                  <p><strong>Estado de Cobro:</strong> {permiso['Estado de Cobro Enviado'] || 'No Enviado'}</p>
                  <p><strong>Estado del Pago:</strong> <span className={`status-pago status-${(permiso['Estado de Pago'] || 'pendiente').toLowerCase()}`}>{permiso['Estado de Pago'] || 'Pendiente'}</span></p>

                  <div className="action-buttons">
                    {permiso.pdf_link && (
                      <a href={permiso.pdf_link} target="_blank" rel="noopener noreferrer" className="action-button btn-secondary" onClick={() => handleSendPdf(permiso)}>
                        Ver PDF
                      </a>
                    )}
                    {permiso['Dirección de correo electrónico'] && (
                      <>
                        <button
                          onClick={() => handleSendEmail(permiso)}
                          className="action-button btn-secondary"
                        >
                          Enviar Email
                        </button>
                        <button
                          onClick={() => handleSendPermisoPayment(permiso, index)}
                          disabled={sendingPayment[index] || permiso['Estado de Cobro Enviado'] === 'Enviado' || permiso['Estado de Pago'] === 'Pagado'}
                          className="action-button btn-primary"
                        >
                          {sendingPayment[index] ? 'Enviando...' : (permiso['Estado de Cobro Enviado'] === 'Enviado' ? 'Cobro Enviado' : (permiso['Estado de Pago'] === 'Pagado' ? 'Pagado' : 'Enviar Cobro'))}
                        </button>
                        <button
                          onClick={() => handleSendPermiso(permiso, index)}
                          disabled={sendingPermiso[index]}
                          className="action-button btn-success"
                        >
                          {sendingPermiso[index] ? 'Enviando...' : 'Enviar Permiso'}
                        </button>
                      </>
                    )}
                  </div>
                  <div className="sent-status-container">
                    {permiso.sent_statuses && permiso.sent_statuses.length > 0 && (
                      <p style={{ fontSize: '10px', color: '#555', margin: '5px 0 0' }}>
                        Enviado: {permiso.sent_statuses.join(', ')}
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
        <p>No se encontraron permisos que coincidan con la búsqueda.</p>
      )}
    </div>
  );
};

export default PermisoCaza;