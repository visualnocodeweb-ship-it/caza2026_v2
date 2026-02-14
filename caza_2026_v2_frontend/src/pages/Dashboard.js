import React, { useState, useEffect } from 'react';
import { Link, Outlet, NavLink } from 'react-router-dom';
// import '../../styles/App.css'; // Esto ya se carga globalmente en App.js

const Dashboard = () => {
  return (
    <div>
      <h2>Dashboard</h2>
      <nav className="dashboard-subnav">
        <NavLink 
          to="/dashboard/inscripciones" 
          className={({ isActive }) => "subnav-item" + (isActive ? " active" : "")}
        >
          Inscripciones
        </NavLink>
        <NavLink 
            to="/dashboard/permisos" 
            className={({ isActive }) => "subnav-item" + (isActive ? " active" : "")}
        >
            Permisos
        </NavLink>
        <NavLink 
          to="/dashboard/recaudaciones" 
          className={({ isActive }) => "subnav-item" + (isActive ? " active" : "")}
        >
          Recaudaciones
        </NavLink>
        {/* Futuras pestañas del dashboard irán aquí */}
        {/* 
        <NavLink 
          to="/dashboard/pagos" 
          className={({ isActive }) => "subnav-item" + (isActive ? " active" : "")}
        >
          Pagos
        </NavLink> 
        */}
      </nav>
      <div className="dashboard-content">
        <Outlet />
      </div>
    </div>
  );
};

export default Dashboard;