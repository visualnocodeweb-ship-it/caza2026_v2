import React from 'react';
import Navbar from './Navbar';
import GuardafaunaLogo from '../assets/Guardafauna - 1.png'; // Corrected path to the image
import '../styles/App.css'; // Import global styles

const Layout = ({ children }) => {
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo-container">
          <img src={GuardafaunaLogo} className="app-logo" alt="Guardafauna Logo" />
        </div>
        <h1 className="app-title">Tablero de Control Caza 2026</h1>
        <Navbar />
      </header>
      <main className="app-main">
        {children}
      </main>
      <footer className="app-footer">
      </footer>
    </div>
  );
};

export default Layout;