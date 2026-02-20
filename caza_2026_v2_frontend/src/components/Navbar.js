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
      <NavLink to="/dashboard" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Dashboard
      </NavLink>
      <NavLink to="/pagos" className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}>
        Pagos Realizados
      </NavLink>
      <button
        onClick={logout}
        className="nav-item"
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: 'inherit',
          font: 'inherit',
          marginLeft: 'auto'
        }}
      >
        Cerrar Sesión
      </button>
    </nav>
  );
};

export default Navbar;