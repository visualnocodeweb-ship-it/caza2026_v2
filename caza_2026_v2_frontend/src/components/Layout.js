import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import GuardafaunaLogo from '../assets/Guardafauna - 1.png';
import '../styles/App.css';

const Layout = () => { // Remove children prop
  return (
    <div className="app-container">
      <header className="app-header glass-header">
        <div className="logo-container">
          <img src={GuardafaunaLogo} className="app-logo" alt="Guardafauna Logo" />
        </div>
        <h1 className="app-title">Tablero de Control Caza 2026</h1>
        <Navbar />
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
      </footer>
    </div>
  );
};

export default Layout;