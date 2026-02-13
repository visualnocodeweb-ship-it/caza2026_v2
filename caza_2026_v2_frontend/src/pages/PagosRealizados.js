import React, { useState, useEffect } from 'react';
import { fetchPayments, fetchCobrosEnviados } from '../utils/api';
import './PagosRealizados.css';

const PagosRealizados = () => {
  // State for the view mode
  const [view, setView] = useState('realizados'); // 'realizados' or 'enviados'

  // State for "Pagos Realizados"
  const [payments, setPayments] = useState([]);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [errorPayments, setErrorPayments] = useState(null);
  const [paymentsPage, setPaymentsPage] = useState(1);
  const [paymentsTotalPages, setPaymentsTotalPages] = useState(1);

  // State for "Cobros Enviados"
  const [sentCobros, setSentCobros] = useState([]);
  const [loadingCobros, setLoadingCobros] = useState(true);
  const [errorCobros, setErrorCobros] = useState(null);
  const [cobrosPage, setCobrosPage] = useState(1);
  const [cobrosTotalPages, setCobrosTotalPages] = useState(1);
  
  const [limit] = useState(10); // Common limit for both

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

    if (view === 'enviados') {
      getCobros();
    }
  }, [view, cobrosPage, limit]);


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

  const renderPaymentsTable = () => {
    if (loadingPayments) return <div className="container">Cargando pagos...</div>;
    if (errorPayments) return <div className="container error-message">{errorPayments}</div>;
    return (
      <>
        {payments.length === 0 ? (
          <p>No se encontraron pagos.</p>
        ) : (
          <>
            <table className="payments-table">
              <thead>
                <tr>
                  <th>ID de Pago</th>
                  <th>ID de Inscripción</th>
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
                    <td>{payment.inscription_id}</td>
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
          </>
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
          <>
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
          </>
        )}
      </>
    );
  };


  return (
    <div className="container">
      <div className="view-toggle">
        <button onClick={() => setView('realizados')} className={view === 'realizados' ? 'active' : ''}>
          Pagos Realizados
        </button>
        <button onClick={() => setView('enviados')} className={view === 'enviados' ? 'active' : ''}>
          Cobros Enviados
        </button>
      </div>
      <h1 className="title">{view === 'realizados' ? 'Pagos Realizados' : 'Cobros Enviados'}</h1>
      {view === 'realizados' ? renderPaymentsTable() : renderCobrosTable()}
    </div>
  );
};

export default PagosRealizados;
