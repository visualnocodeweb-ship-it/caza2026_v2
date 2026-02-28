import React, { useState, useEffect } from 'react';
import { Link, Outlet, NavLink } from 'react-router-dom';
// import '../../styles/App.css'; // Esto ya se carga globalmente en App.js

const Dashboard = () => {
  console.log("Dashboard component mounted"); // DEBUG
  return (
    <div>
      <h2>Dashboard</h2>
      <div className="toolbar" style={{ justifyContent: 'center', marginBottom: '2rem' }}>
        <nav className="navbar" style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.5)' }}>
          <NavLink
            to="/dashboard/inscripciones"
            className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
          >
            Inscripciones
          </NavLink>
          <NavLink
            to="/dashboard/permisos"
            className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
          >
            Permisos
          </NavLink>
          <NavLink
            to="/dashboard/recaudaciones"
            className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
          >
            Recaudaciones
          </NavLink>
          <NavLink
            to="/dashboard/reses"
            className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
          >
            Reses
          </NavLink>
        </nav>
      </div>
      <div className="dashboard-content">
        <Outlet />
      </div>
    </div>
  );
};

export default Dashboard;