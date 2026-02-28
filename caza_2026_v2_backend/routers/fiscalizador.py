"""
Router del Fiscalizador — caza_2026_v2_backend
================================================
Endpoints de consulta para el Fiscalizador.
"""

import os
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from typing import Dict, List, Any

from ..database import database
from ..models import pagos, pagos_permisos

router = APIRouter(
    prefix="/api/fiscalizador",
    tags=["Fiscalizador"]
)

@router.get("/pagos")
async def get_pagos_aprobados():
    """
    Lista de IDs con status='approved' de ambas tablas de pagos.
    Adaptado para usar el motor asíncrono 'databases' del proyecto.
    """
    try:
        # Consulta Inscripciones (Establecimientos)
        query_insc = select(pagos.c.inscription_id).where(pagos.c.status == 'approved')
        inscripciones_rows = await database.fetch_all(query_insc)
        
        # Consulta Permisos
        query_perm = select(pagos_permisos.c.permiso_id).where(pagos_permisos.c.status == 'approved')
        permisos_rows = await database.fetch_all(query_perm)
        
        return {
            "inscripciones_pagadas": [str(row[0]) for row in inscripciones_rows],
            "permisos_pagados": [str(row[0]) for row in permisos_rows]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar la base de datos: {str(e)}")

@router.get("/health")
async def health():
    return {"status": "ok", "router": "fiscalizador"}
