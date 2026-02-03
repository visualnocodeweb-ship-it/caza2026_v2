import React, { useState, useEffect } from 'react';
import { fetchPayments } from '../utils/api';
import './PagosRealizados.css'; // Assuming a CSS file for styling

const PagosRealizados = () => {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [limit] = useState(10); // Fixed limit for now
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const getPayments = async () => {
      setLoading(true);
      try {
        const data = await fetchPayments(page, limit);
        setPayments(data.data);
        setTotalPages(data.total_pages);
      } catch (err) {
        setError("Error al cargar los pagos: " + err.message);
      } finally {
        setLoading(false);
      }
    };

    getPayments();
  }, [page, limit]);

  const handlePreviousPage = () => {
    setPage(prevPage => Math.max(prevPage - 1, 1));
  };

  const handleNextPage = () => {
    setPage(prevPage => Math.min(prevPage + 1, totalPages));
  };

  const formatStatus = (status) => {
    if (status === 'approved') {
      return <span className="status-approved">Éxito</span>;
    } else if (status === 'pending') {
      return <span className="status-pending">Pendiente</span>;
    }
    return <span className="status-failed">Fallido</span>;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString(); // Formats date and time based on locale
  };

  if (loading) return <div className="container">Cargando pagos...</div>;
  if (error) return <div className="container error-message">{error}</div>;

  return (
    <div className="container">
      <h1 className="title">Pagos Realizados</h1>
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
            <button onClick={handlePreviousPage} disabled={page === 1}>
              Anterior
            </button>
            <span>Página {page} de {totalPages}</span>
            <button onClick={handleNextPage} disabled={page === totalPages}>
              Siguiente
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default PagosRealizados;
