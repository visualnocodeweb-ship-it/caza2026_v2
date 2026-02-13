import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout'; // Import Layout component

// Import your page components
import Inscripciones from './pages/Inscripciones';
import PermisoCaza from './pages/PermisoCaza';
import Dashboard from './pages/Dashboard';
import InscripcionesStats from './pages/dashboard/InscripcionesStats';
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
          <Route path="/dashboard" element={<Dashboard />}>
            <Route index element={<InscripcionesStats />} />
            <Route path="inscripciones" element={<InscripcionesStats />} />
          </Route>
          <Route path="/pagos" element={<PagosRealizados />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;