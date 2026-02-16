// src/utils/api.js
// This file will contain functions to interact with your backend API

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api'; // Example backend URL

export const fetchInscripciones = async (page = 1, limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/inscripciones?page=${page}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching inscripciones:", error);
    return { data: [], total_records: 0, page: 1, limit: 10, total_pages: 0 }; // Return a structured empty response
  }
};

export const fetchPermisos = async (page = 1, limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/permisos?page=${page}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching permisos:", error);
    return { data: [], total_records: 0, page: 1, limit: 10, total_pages: 0 }; // Return a structured empty response
  }
};

export const fetchErrorLog = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/error-log`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching error log:", error);
    return [];
  }
};


export const fetchPrices = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/prices`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching prices:", error);
    return [];
  }
};

export const fetchPayments = async (page = 1, limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/pagos?page=${page}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching payments:", error);
    return { data: [], total_records: 0, page: 1, limit: 10, total_pages: 0 }; // Return a structured empty response
  }
};

// Add more API functions as needed

export const linkData = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/link-data`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      // body: JSON.stringify({ /* any data you might need to send */ }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error linking data:", error);
    throw error; // Re-throw to be handled by the component
  }
};

export const createPaymentPreference = async (paymentDetails) => {
  try {
    const response = await fetch(`${API_BASE_URL}/create-payment-preference`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(paymentDetails),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error creating payment preference:", error);
    throw error;
  }
};

export const simulatePayment = async (paymentDetails) => {
  try {
    const response = await fetch(`${API_BASE_URL}/simulate-payment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(paymentDetails),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error simulating payment:", error);
    throw error;
  }
};

export const sendEmailAPI = async (emailData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/send-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(emailData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error sending email:", error);
    throw error;
  }
};

export const sendPaymentLink = async (paymentLinkData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/send-payment-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(paymentLinkData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error sending payment link:", error);
    throw error;
  }
};

export const sendPermisoPaymentLink = async (paymentLinkData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/send-permiso-payment-link`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(paymentLinkData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error sending permiso payment link:", error);
    throw error;
  }
};

export const sendPermisoEmailAPI = async (permisoData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/send-permiso-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(permisoData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error sending permiso email:", error);
    throw error;
  }
};

export const sendCredentialAPI = async (credentialData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/send-credential`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentialData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error sending credential:", error);
    throw error;
  }
};

export const viewCredentialAPI = async (numero_inscripcion) => {
  try {
    const response = await fetch(`${API_BASE_URL}/view-credential/${numero_inscripcion}`);
    if (!response.ok) {
      const errorData = await response.text();
      throw new Error(errorData || `HTTP error! status: ${response.status}`);
    }
    const html = await response.text();
    return html;
  } catch (error) {
    console.error("Error viewing credential:", error);
    throw error;
  }
};

export const fetchCobrosEnviados = async (page = 1, limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/cobros-enviados?page=${page}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching sent payments:", error);
    return { data: [], total_records: 0, page: 1, limit: 10, total_pages: 0 }; // Return a structured empty response
  }
};

export const fetchPermisoCobrosEnviados = async (page = 1, limit = 10) => {
  try {
    const response = await fetch(`${API_BASE_URL}/permiso-cobros-enviados?page=${page}&limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching sent permiso payments:", error);
    return { data: [], total_records: 0, page: 1, limit: 10, total_pages: 0 }; // Return a structured empty response
  }
};

export const fetchTotalInscripciones = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/stats/total-inscripciones`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching total inscripciones:", error);
    return { total_inscripciones: 0 };
  }
};

export const fetchPermisosStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/permisos/stats`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error fetching permisos stats:", error);
      return { total_permisos: 0, daily_stats: [], monthly_stats: [] };
    }
  };

export const fetchRecaudacionesStats = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/stats/recaudaciones`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching recaudaciones stats:", error);
    return { recaudacion_total: 0, recaudacion_inscripciones: 0, recaudacion_permisos: 0, recaudacion_permisos_por_mes: [] };
  }
};

export const logSentItem = async (itemData) => {
  try {
    const response = await fetch(`${API_BASE_URL}/log-sent-item`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(itemData),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error logging sent item:", error);
    throw error;
  }
};

export const fetchSentItems = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/sent-items`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching sent items:", error);
    return [];
  }
};

export const fetchLogs = async (page = 1, limit = 15) => {
    try {
      const response = await fetch(`${API_BASE_URL}/logs?page=${page}&limit=${limit}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error fetching logs:", error);
      return { data: [], total_records: 0, page: 1, limit: 15, total_pages: 0 };
    }
  };
