import React, { useState, useEffect } from 'react';
import { fetchPayments, fetchCobrosEnviados, fetchPermisoCobrosEnviados, fetchResesPagos, fetchGuiasPagos } from '../utils/api';
import Logs from './Logs'; // Import the new Logs component
import './PagosRealizados.css';
import '../styles/Responsive.css';
import '../styles/App.css'; // Import App.css for log styles

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString();
};

const formatStatus = (status) => {
  if (status === 'approved') return <span className="status-approved">Aprobado</span>;
  if (status === 'pending') return <span className="status-pending">Pendiente</span>;
  return <span className="status-failed">Fallido</span>;
};

const PagosRealizados = () => {
  // State for the view mode
  const [view, setView] = useState('realizados'); // 'realizados', 'reses', 'guias', 'logs'

  // State for "Pagos Realizados"
  const [payments, setPayments] = useState([]);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [errorPayments, setErrorPayments] = useState(null);
  const [paymentsPage, setPaymentsPage] = useState(1);
  const [paymentsTotalPages, setPaymentsTotalPages] = useState(1);

  // State for "Pagos de Reses"
  const [resesPayments, setResesPayments] = useState([]);
  const [loadingReses, setLoadingReses] = useState(true);
  const [errorReses, setErrorReses] = useState(null);
  const [resesPage, setResesPage] = useState(1);
  const [resesTotalPages, setResesTotalPages] = useState(1);

  // State for "Pagos de Guías"
  const [guiasPayments, setGuiasPayments] = useState([]);
  const [loadingGuias, setLoadingGuias] = useState(true);
  const [errorGuias, setErrorGuias] = useState(null);
  const [guiasPage, setGuiasPage] = useState(1);
  const [guiasTotalPages, setGuiasTotalPages] = useState(1);

  const [searchTerm, setSearchTerm] = useState('');
  const [limit] = useState(10); // Common limit for all

  useEffect(() => {
    const getPayments = async () => {
      setLoadingPayments(true);
      try {
        const data = await fetchPayments(paymentsPage, limit, searchTerm);
        setPayments(data.data);
        setPaymentsTotalPages(data.total_pages);
      } catch (err) {
        setErrorPayments("Error al cargar los pagos: " + err.message);
      } finally {
        setLoadingPayments(false);
      }
    };

    if (view === 'realizados') {
      getPayments();
    }
  }, [view, paymentsPage, limit, searchTerm]);

  useEffect(() => {
    const getResesPayments = async () => {
      setLoadingReses(true);
      try {
        const data = await fetchResesPagos(resesPage, limit);
        setResesPayments(data.data);
        setResesTotalPages(data.total_pages);
      } catch (err) {
        setErrorReses("Error al cargar los pagos de reses: " + err.message);
      } finally {
        setLoadingReses(false);
      }
    };

    if (view === 'reses') {
      getResesPayments();
    }
  }, [view, resesPage, limit]);

  useEffect(() => {
    const getGuiasPayments = async () => {
      setLoadingGuias(true);
      try {
        const data = await fetchGuiasPagos(guiasPage, limit);
        setGuiasPayments(data.data);
        setGuiasTotalPages(data.total_pages);
      } catch (err) {
        setErrorGuias("Error al cargar los pagos de guías: " + err.message);
      } finally {
        setLoadingGuias(false);
      }
    };

    if (view === 'guias') {
      getGuiasPayments();
    }
  }, [view, guiasPage, limit]);

  const renderPaymentsTable = () => {
    if (loadingPayments) return <div className="container">Cargando pagos...</div>;
    if (errorPayments) return <div className="container error-message">{errorPayments}</div>;
    return (
      <>
        {payments.length === 0 ? (
          <p>No se encontraron pagos.</p>
        ) : (
          <div className="table-responsive">
            <table className="payments-table">
              <thead>
                <tr>
                  <th>ID de Pago</th>
                  <th>ID de Referencia</th>
                  <th>Tipo</th>
                  <th>Estado</th>
                  <th>Monto</th>
                  <th>Email</th>
                  <th>Fecha de Creación</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((payment) => (
                  <tr key={payment.payment_id}>
                    <td>{payment.payment_id}</td>
                    <td>{payment.inscription_id || payment.permiso_id}</td>
                    <td>{payment.inscription_id ? 'Inscripción' : 'Permiso'}</td>
                    <td>{formatStatus(payment.status)}</td>
                    <td>${payment.amount ? payment.amount.toFixed(2) : '0.00'}</td>
                    <td>{payment.email}</td>
                    <td>{formatDate(payment.date_created)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination-controls">
              <button onClick={() => setPaymentsPage(p => Math.max(p - 1, 1))} disabled={paymentsPage === 1}>
                Anterior
              </button>
              <span>Página {paymentsPage} de {paymentsTotalPages}</span>
              <button onClick={() => setPaymentsPage(p => Math.min(p + 1, paymentsTotalPages))} disabled={paymentsPage === paymentsTotalPages}>
                Siguiente
              </button>
            </div>
          </div>
        )}
      </>
    );
  };

  const renderResesPaymentsTable = () => {
    if (loadingReses) return <div className="container">Cargando pagos de reses...</div>;
    if (errorReses) return <div className="container error-message">{errorReses}</div>;
    return (
      <>
        {resesPayments.length === 0 ? (
          <p>No se encontraron pagos de reses marcados como "Pagado".</p>
        ) : (
          <div className="table-responsive">
            <table className="payments-table">
              <thead>
                <tr>
                  <th>ID Res</th>
                  <th>Cazador / Empresa</th>
                  <th>Especie</th>
                  <th>Monto Pagado</th>
                  <th>Fecha</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {resesPayments.map((p) => (
                  <tr key={p.res_id}>
                    <td style={{ fontWeight: 'bold' }}>{p.res_id}</td>
                    <td>{p.nombre}</td>
                    <td>{p.especie}</td>
                    <td style={{ color: '#166534', fontWeight: 'bold' }}>
                      ${p.amount ? p.amount.toLocaleString('es-AR', { minimumFractionDigits: 2 }) : '0.00'}
                    </td>
                    <td>{p.date}</td>
                    <td>{formatStatus('approved')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination-controls">
              <button onClick={() => setResesPage(p => Math.max(p - 1, 1))} disabled={resesPage === 1}>
                Anterior
              </button>
              <span>Página {resesPage} de {resesTotalPages}</span>
              <button onClick={() => setResesPage(p => Math.min(p + 1, resesTotalPages))} disabled={resesPage === resesTotalPages}>
                Siguiente
              </button>
            </div>
          </div>
        )}
      </>
    );
  };

  const renderGuiasPaymentsTable = () => {
    if (loadingGuias) return <div className="container">Cargando pagos de guías...</div>;
    if (errorGuias) return <div className="container error-message">{errorGuias}</div>;
    return (
      <>
        {guiasPayments.length === 0 ? (
          <p>No se encontraron pagos de guías marcados como "Pagado".</p>
        ) : (
          <div className="table-responsive">
            <table className="payments-table">
              <thead>
                <tr>
                  <th>ID Guía</th>
                  <th>Cazador / Solicitante</th>
                  <th>Especie</th>
                  <th>Monto Pagado</th>
                  <th>Fecha</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {guiasPayments.map((p) => (
                  <tr key={p.guia_id}>
                    <td style={{ fontWeight: 'bold' }}>{p.guia_id}</td>
                    <td>{p.nombre}</td>
                    <td>{p.especie}</td>
                    <td style={{ color: '#166534', fontWeight: 'bold' }}>
                      ${p.amount ? p.amount.toLocaleString('es-AR', { minimumFractionDigits: 2 }) : '0.00'}
                    </td>
                    <td>{p.fecha}</td>
                    <td>{formatStatus('approved')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination-controls">
              <button onClick={() => setGuiasPage(p => Math.max(p - 1, 1))} disabled={guiasPage === 1}>
                Anterior
              </button>
              <span>Página {guiasPage} de {guiasTotalPages}</span>
              <button onClick={() => setGuiasPage(p => Math.min(p + 1, guiasTotalPages))} disabled={guiasPage === guiasTotalPages}>
                Siguiente
              </button>
            </div>
          </div>
        )}
      </>
    );
  };

  return (
    <div className="pagos-container">
      <div className="toolbar" style={{ justifyContent: 'center', marginBottom: '3rem' }}>
        <div className="navbar" style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.5)' }}>
          <button
            onClick={() => setView('realizados')}
            className={`nav-item ${view === 'realizados' ? 'active' : ''}`}
          >
            Pagos Realizados
          </button>
          <button
            onClick={() => setView('reses')}
            className={`nav-item ${view === 'reses' ? 'active' : ''}`}
          >
            Pagos de Reses
          </button>
          <button
            onClick={() => setView('guias')}
            className={`nav-item ${view === 'guias' ? 'active' : ''}`}
          >
            Pagos de Guías
          </button>
          <button
            onClick={() => setView('logs')}
            className={`nav-item ${view === 'logs' ? 'active' : ''}`}
          >
            Registro de Actividad (Logs)
          </button>
        </div>
      </div>

      <div className="toolbar" style={{ justifyContent: 'center', marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder="Buscar en todos los registros..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
          style={{ width: '100%', maxWidth: '500px' }}
        />
      </div>

      <div className="glass-card" style={{ padding: '2rem' }}>
        <h2 className="app-title" style={{ marginBottom: '2rem', fontSize: '1.5rem', textAlign: 'center' }}>
          {view === 'realizados' ? 'Historial de Pagos' :
            view === 'reses' ? 'Pagos de Reses' :
              view === 'guias' ? 'Pagos de Guías de Traslado' : 'Logs del Sistema'}
        </h2>

        {view === 'realizados' ? renderPaymentsTable() :
          view === 'reses' ? renderResesPaymentsTable() :
            view === 'guias' ? renderGuiasPaymentsTable() : <Logs />}
      </div>
    </div>
  );
};

export default PagosRealizados;