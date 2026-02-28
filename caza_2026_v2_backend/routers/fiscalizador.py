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
from ..models import pagos, pagos_permisos, reses_details

router = APIRouter(
    prefix="/api/fiscalizador",
    tags=["Fiscalizador"]
)

@router.get("/pagos")
async def get_pagos_aprobados():
    """
    Lista de IDs con status='approved' o is_paid=True de todas las tablas.
    """
    try:
        # Consulta Inscripciones (Establecimientos)
        query_insc = select(pagos.c.inscription_id).where(pagos.c.status == 'approved')
        inscripciones_rows = await database.fetch_all(query_insc)
        
        # Consulta Permisos
        query_perm = select(pagos_permisos.c.permiso_id).where(pagos_permisos.c.status == 'approved')
        permisos_rows = await database.fetch_all(query_perm)

        # Consulta Reses
        query_res = select(reses_details.c.res_id).where(reses_details.c.is_paid == True)
        reses_rows = await database.fetch_all(query_res)
        
        return {
            "inscripciones_pagadas": [str(row[0]) for row in inscripciones_rows],
            "permisos_pagados": [str(row[0]) for row in permisos_rows],
            "reses_pagadas": [str(row[0]) for row in reses_rows]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar la base de datos: {str(e)}")

@router.get("/check/{item_id}")
async def check_pago_status(item_id: str):
    """
    Busca un ID específico en todas las tablas de pago para ver su estado.
    """
    try:
        # 1. Buscar en Inscripciones
        query_insc = select(pagos.c.status).where(pagos.c.inscription_id == item_id).order_by(pagos.c.date_created.desc())
        res_insc = await database.fetch_one(query_insc)
        if res_insc:
            return {"id": item_id, "tipo": "inscripcion", "pagado": res_insc['status'] == 'approved', "status": res_insc['status']}

        # 2. Buscar en Permisos
        query_perm = select(pagos_permisos.c.status).where(pagos_permisos.c.permiso_id == item_id).order_by(pagos_permisos.c.date_created.desc())
        res_perm = await database.fetch_one(query_perm)
        if res_perm:
            return {"id": item_id, "tipo": "permiso", "pagado": res_perm['status'] == 'approved', "status": res_perm['status']}

        # 3. Buscar en Reses
        query_res = select(reses_details.c.is_paid).where(reses_details.c.res_id == item_id)
        res_res = await database.fetch_one(query_res)
        if res_res:
            return {"id": item_id, "tipo": "reses", "pagado": res_res['is_paid'], "status": "approved" if res_res['is_paid'] else "pending"}

        return {"id": item_id, "tipo": "not_found", "pagado": False, "status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al verificar ID: {str(e)}")

@router.get("/health")
async def health():
    return {"status": "ok", "router": "fiscalizador"}
