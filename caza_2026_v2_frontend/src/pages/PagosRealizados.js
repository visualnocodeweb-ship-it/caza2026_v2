import React, { useState, useEffect } from 'react';
import { fetchPayments, fetchCobrosEnviados, fetchPermisoCobrosEnviados } from '../utils/api';
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
  const [view, setView] = useState('realizados'); // 'realizados', 'enviados_inscripciones', 'enviados_permisos', 'logs'

  // State for "Pagos Realizados"
  const [payments, setPayments] = useState([]);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [errorPayments, setErrorPayments] = useState(null);
  const [paymentsPage, setPaymentsPage] = useState(1);
  const [paymentsTotalPages, setPaymentsTotalPages] = useState(1);

  // State for "Inscripciones Cobros Enviados"
  const [sentCobros, setSentCobros] = useState([]);
  const [loadingCobros, setLoadingCobros] = useState(true);
  const [errorCobros, setErrorCobros] = useState(null);
  const [cobrosPage, setCobrosPage] = useState(1);
  const [cobrosTotalPages, setCobrosTotalPages] = useState(1);

  // State for "Permisos Cobros Enviados"
  const [sentPermisoCobros, setSentPermisoCobros] = useState([]);
  const [loadingPermisoCobros, setLoadingPermisoCobros] = useState(true);
  const [errorPermisoCobros, setErrorPermisoCobros] = useState(null);
  const [permisoCobrosPage, setPermisoCobrosPage] = useState(1);
  const [permisoCobrosTotalPages, setPermisoCobrosTotalPages] = useState(1);

  const [limit] = useState(10); // Common limit for all

  useEffect(() => {
    const getPayments = async () => {
      setLoadingPayments(true);
      try {
        const data = await fetchPayments(paymentsPage, limit);
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
  }, [view, paymentsPage, limit]);

  useEffect(() => {
    const getCobros = async () => {
      setLoadingCobros(true);
      try {
        const data = await fetchCobrosEnviados(cobrosPage, limit);
        setSentCobros(data.data);
        setCobrosTotalPages(data.total_pages);
      } catch (err) {
        setErrorCobros("Error al cargar los cobros enviados: " + err.message);
      } finally {
        setLoadingCobros(false);
      }
    };

    if (view === 'enviados_inscripciones') {
      getCobros();
    }
  }, [view, cobrosPage, limit]);

  useEffect(() => {
    const getPermisoCobros = async () => {
      setLoadingPermisoCobros(true);
      try {
        const data = await fetchPermisoCobrosEnviados(permisoCobrosPage, limit);
        setSentPermisoCobros(data.data);
        setPermisoCobrosTotalPages(data.total_pages);
      } catch (err) {
        setErrorPermisoCobros("Error al cargar los cobros de permisos enviados: " + err.message);
      } finally {
        setLoadingPermisoCobros(false);
      }
    };

    if (view === 'enviados_permisos') {
      getPermisoCobros();
    }
  }, [view, permisoCobrosPage, limit]);

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

  const renderCobrosTable = () => {
    if (loadingCobros) return <div className="container">Cargando cobros enviados...</div>;
    if (errorCobros) return <div className="container error-message">{errorCobros}</div>;
    return (
      <>
        {sentCobros.length === 0 ? (
          <p>No se encontraron cobros enviados.</p>
        ) : (
          <div className="table-responsive">
            <table className="payments-table">
              <thead>
                <tr>
                  <th>ID de Inscripción</th>
                  <th>Email Enviado</th>
                  <th>Monto Enviado</th>
                  <th>Fecha de Envío</th>
                </tr>
              </thead>
              <tbody>
                {sentCobros.map((cobro) => (
                  <tr key={cobro.id}>
                    <td>{cobro.inscription_id}</td>
                    <td>{cobro.email}</td>
                    <td>${cobro.amount ? cobro.amount.toFixed(2) : '0.00'}</td>
                    <td>{formatDate(cobro.date_sent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination-controls">
              <button onClick={() => setCobrosPage(p => Math.max(p - 1, 1))} disabled={cobrosPage === 1}>
                Anterior
              </button>
              <span>Página {cobrosPage} de {cobrosTotalPages}</span>
              <button onClick={() => setCobrosPage(p => Math.min(p + 1, cobrosTotalPages))} disabled={cobrosPage === cobrosTotalPages}>
                Siguiente
              </button>
            </div>
          </div>
        )}
      </>
    );
  };

  const renderPermisoCobrosTable = () => {
    if (loadingPermisoCobros) return <div className="container">Cargando cobros de permisos enviados...</div>;
    if (errorPermisoCobros) return <div className="container error-message">{errorPermisoCobros}</div>;
    return (
      <>
        {sentPermisoCobros.length === 0 ? (
          <p>No se encontraron cobros de permisos enviados.</p>
        ) : (
          <div className="table-responsive">
            <table className="payments-table">
              <thead>
                <tr>
                  <th>ID de Permiso</th>
                  <th>Email Enviado</th>
                  <th>Monto Enviado</th>
                  <th>Fecha de Envío</th>
                </tr>
              </thead>
              <tbody>
                {sentPermisoCobros.map((cobro) => (
                  <tr key={cobro.id}>
                    <td>{cobro.permiso_id}</td>
                    <td>{cobro.email}</td>
                    <td>${cobro.amount ? cobro.amount.toFixed(2) : '0.00'}</td>
                    <td>{formatDate(cobro.date_sent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination-controls">
              <button onClick={() => setPermisoCobrosPage(p => Math.max(p - 1, 1))} disabled={permisoCobrosPage === 1}>
                Anterior
              </button>
              <span>Página {permisoCobrosPage} de {permisoCobrosTotalPages}</span>
              <button onClick={() => setPermisoCobrosPage(p => Math.min(p + 1, permisoCobrosTotalPages))} disabled={permisoCobrosPage === permisoCobrosTotalPages}>
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
            onClick={() => setView('logs')}
            className={`nav-item ${view === 'logs' ? 'active' : ''}`}
          >
            Registro de Actividad (Logs)
          </button>
        </div>
      </div>

      <div className="glass-card" style={{ padding: '2rem' }}>
        <h2 className="app-title" style={{ marginBottom: '2rem', fontSize: '1.5rem', textAlign: 'center' }}>
          {view === 'realizados' ? 'Historial de Pagos' : 'Logs del Sistema'}
        </h2>

        {view === 'realizados' ? renderPaymentsTable() : <Logs />}
      </div>
    </div>
  );
};

export default PagosRealizados;