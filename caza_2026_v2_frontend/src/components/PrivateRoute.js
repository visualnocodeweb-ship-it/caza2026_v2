import React, { useContext } from 'react';
import { Navigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

const PrivateRoute = ({ children }) => {
    const { user, loading } = useContext(AuthContext); // Added loading
    console.log("PrivateRoute checking user:", user, "loading:", loading); // DEBUG

    if (loading) {
        return <div>Cargando...</div>; // O un spinner
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    // Restriction for algar user
    const currentPath = window.location.pathname;
    if (user === 'algar' && currentPath !== '/algar-sa') {
        return <Navigate to="/algar-sa" replace />;
    }

    return children;
};

export default PrivateRoute;
