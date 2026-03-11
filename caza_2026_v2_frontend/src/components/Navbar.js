import { NavLink } from 'react-router-dom';
import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import '../styles/App.css'; // Import global styles

const Navbar = () => {
  const { logout } = useContext(AuthContext);
  return (
    <nav className="navbar">
      <NavLink to="/inscripciones" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Inscripciones
      </NavLink>
      <NavLink to="/permiso-caza" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Permiso de Caza
      </NavLink>
      <NavLink to="/reses" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Reses
      </NavLink>
      <NavLink to="/guias-traslados" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Guías de Traslados
      </NavLink>
      <NavLink to="/dashboard" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Dashboard
      </NavLink>
      <NavLink to="/pagos" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Pagos Realizados
      </NavLink>
      <a
        href="https://mapas-caza-frontend.onrender.com/"
        target="_blank"
        rel="noopener noreferrer"
        className="nav-item maps-nav-link"
        style={{ textDecoration: 'none' }}
      >
        Maps
      </a>

      <div className="nav-item dropdown">
        <button className="dropbtn">Varios ▼</button>
        <div className="dropdown-content">
          <NavLink to="/algar-sa" className={({ isActive }) => (isActive ? "active" : "")}>
            Algar SA
          </NavLink>
        </div>
      </div>

      <button
        onClick={logout}
        className="nav-item logout-btn"
        style={{ marginLeft: 'auto' }}
      >
        Cerrar Sesión
      </button>
    </nav>
  );
};

export default Navbar;