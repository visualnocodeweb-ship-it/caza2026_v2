import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout'; // Import Layout component

// Import your page components
import Inscripciones from './pages/Inscripciones';
import PermisoCaza from './pages/PermisoCaza';
import Dashboard from './pages/Dashboard';
import NotFound from './pages/NotFound';
import PagosRealizados from './pages/PagosRealizados'; // New Import

const App = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Inscripciones />} />
          <Route path="/inscripciones" element={<Inscripciones />} />
          <Route path="/permiso-caza" element={<PermisoCaza />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/pagos" element={<PagosRealizados />} /> {/* New Route */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;