import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { AuthProvider } from './context/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import Login from './pages/Login';

import Inscripciones from './pages/Inscripciones';
import PermisoCaza from './pages/PermisoCaza';
import Dashboard from './pages/Dashboard';
import InscripcionesStats from './pages/dashboard/InscripcionesStats';
import RecaudacionesStats from './pages/dashboard/RecaudacionesStats';
import PermisosStats from './pages/dashboard/PermisosStats';
import NotFound from './pages/NotFound';
import PagosRealizados from './pages/PagosRealizados';

const App = () => {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* Public Route: Login */}
          <Route path="/login" element={<Login />} />

          {/* Protected Routes nested under Layout */}
          <Route element={<Layout />}>
            <Route path="/" element={
              <PrivateRoute>
                <Inscripciones />
              </PrivateRoute>
            } />
            <Route path="/inscripciones" element={
              <PrivateRoute>
                <Inscripciones />
              </PrivateRoute>
            } />
            <Route path="/permiso-caza" element={
              <PrivateRoute>
                <PermisoCaza />
              </PrivateRoute>
            } />
            <Route path="/pagos" element={
              <PrivateRoute>
                <PagosRealizados />
              </PrivateRoute>
            } />

            <Route path="/dashboard" element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }>
              <Route index element={<InscripcionesStats />} />
              <Route path="inscripciones" element={<InscripcionesStats />} />
              <Route path="permisos" element={<PermisosStats />} />
              <Route path="recaudaciones" element={<RecaudacionesStats />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
};

export default App;