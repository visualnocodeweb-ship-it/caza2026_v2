"""
Router del Fiscalizador — caza_2026_v2_backend
================================================
Endpoints de consulta de solo lectura pensados para la aplicación
de fiscalización en campo.  No requiere autenticación adicional porque
los datos expuestos forman parte del proceso operativo público de caza.

Endpoints:
  GET /api/fiscalizador/inscripcion?cuit=XXXX
      → Busca en Google Sheets (hoja "inscrip") por CUIT del establecimiento
        y devuelve los datos junto con el estado de pago desde la DB.

  GET /api/fiscalizador/permiso?id=XXXX
      → Busca en Google Sheets (hoja "permisos") por ID de permiso (o DNI)
        y devuelve los datos junto con el estado de pago desde la DB.

  GET /api/fiscalizador/health
      → Verificación rápida de que el router está activo.
"""

import os
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from typing import Dict, Any, Optional

from ..database import database
from ..models import pagos, pagos_permisos
from .. import sheets_services

router = APIRouter(
    prefix="/api/fiscalizador",
    tags=["fiscalizador"],
)


def safe_str_id(val) -> Optional[str]:
    """Convierte IDs (especialmente de Pandas/Sheets) a string limpio sin decimales .0"""
    if val is None:
        return None
    s_val = str(val).strip()
    if s_val == "" or s_val.lower() == "nan":
        return None
    if isinstance(val, (float, int)):
        try:
            if float(val).is_integer():
                return str(int(float(val)))
        except Exception:
            pass
    if "." in s_val:
        try:
            f_val = float(s_val)
            if f_val.is_integer():
                return str(int(f_val))
        except Exception:
            pass
    return s_val


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def fiscalizador_health():
    return {"status": "ok", "router": "fiscalizador"}


# ---------------------------------------------------------------------------
# Endpoint 1 — Consulta inscripción por CUIT
# ---------------------------------------------------------------------------

@router.get("/inscripcion", response_model=Dict[str, Any])
async def consultar_inscripcion_por_cuit(
    cuit: str = Query(..., description="CUIT del establecimiento a buscar"),
):
    """
    Busca en la hoja 'inscrip' de Google Sheets todos los registros cuyo campo CUIT
    coincida (exacto o substring) con el valor ingresado y enriquece cada resultado
    con el estado de pago proveniente de la tabla 'pagos' de PostgreSQL.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise HTTPException(status_code=500, detail="GOOGLE_SHEET_ID no configurado en el servidor.")

    try:
        df = sheets_services.read_sheet_data(sheet_id, "inscrip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer Google Sheets: {e}")

    if df.empty:
        return {"found": False, "results": []}

    # Normalizar columnas para la búsqueda — convertir a string y buscar CUIT
    cuit_normalizado = cuit.strip().replace("-", "").replace(" ", "")

    # Intentar encontrar la columna CUIT (puede llamarse 'cuit', 'CUIT', 'Cuit', etc.)
    cuit_col = None
    for col in df.columns:
        if col.strip().lower() == "cuit":
            cuit_col = col
            break

    if cuit_col is None:
        # Si no hay columna CUIT, devolver error descriptivo
        raise HTTPException(
            status_code=422,
            detail=f"No se encontró la columna 'cuit' en la hoja 'inscrip'. Columnas disponibles: {list(df.columns)}",
        )

    # Filtrar filas cuyo CUIT normalizado contenga el valor buscado
    mask = df[cuit_col].astype(str).str.replace("-", "").str.replace(" ", "").str.contains(
        cuit_normalizado, case=False, na=False
    )
    matches = df[mask].to_dict(orient="records")

    if not matches:
        return {"found": False, "results": []}

    # Enriquecer con estado de pago
    for registro in matches:
        numero_inscripcion = safe_str_id(registro.get("numero_inscripcion"))
        if numero_inscripcion:
            registro["numero_inscripcion"] = numero_inscripcion
            pago_query = select(pagos).where(
                pagos.c.inscription_id == numero_inscripcion,
                pagos.c.status == "approved",
            )
            pago_result = await database.fetch_one(pago_query)

            if pago_result:
                registro["estado_pago"] = "Pagado"
                registro["payment_id"] = pago_result["payment_id"]
                registro["fecha_pago"] = (
                    pago_result["date_created"].isoformat()
                    if pago_result["date_created"]
                    else None
                )
            else:
                any_pago_query = select(pagos).where(pagos.c.inscription_id == numero_inscripcion)
                any_pago = await database.fetch_one(any_pago_query)
                if any_pago:
                    registro["estado_pago"] = any_pago["status"].capitalize()
                else:
                    registro["estado_pago"] = "Pendiente"
        else:
            registro["estado_pago"] = "Sin ID"

    return {"found": True, "total": len(matches), "results": matches}


# ---------------------------------------------------------------------------
# Endpoint 2 — Consulta permiso por ID (o DNI)
# ---------------------------------------------------------------------------

@router.get("/permiso", response_model=Dict[str, Any])
async def consultar_permiso(
    id: Optional[str] = Query(None, description="ID del permiso"),
    dni: Optional[str] = Query(None, description="DNI del titular del permiso"),
):
    """
    Busca en la hoja 'permisos' de Google Sheets por ID de permiso o por DNI
    del titular y enriquece el resultado con el estado de pago de la tabla
    'pagos_permisos' de PostgreSQL.
    """
    if not id and not dni:
        raise HTTPException(status_code=400, detail="Debés proporcionar al menos 'id' o 'dni' como parámetro.")

    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise HTTPException(status_code=500, detail="GOOGLE_SHEET_ID no configurado en el servidor.")

    try:
        df = sheets_services.read_sheet_data(sheet_id, "permisos")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer Google Sheets: {e}")

    if df.empty:
        return {"found": False, "results": []}

    mask = None

    # Filtro por ID de permiso
    if id:
        id_normalizado = id.strip()
        # Intentar encontrar columna ID
        id_col = None
        for col in df.columns:
            if col.strip().upper() == "ID":
                id_col = col
                break
        if id_col:
            mask_id = df[id_col].astype(str).str.strip().str.contains(
                id_normalizado, case=False, na=False
            )
            mask = mask_id if mask is None else (mask | mask_id)

    # Filtro por DNI
    if dni:
        dni_normalizado = dni.strip().replace(".", "").replace(" ", "")
        # Intentar encontrar columna DNI (puede llamarse 'dni', 'DNI', 'Dni', 'dni_solicitante', etc.)
        dni_col = None
        for col in df.columns:
            if "dni" in col.strip().lower():
                dni_col = col
                break
        if dni_col:
            mask_dni = df[dni_col].astype(str).str.replace(".", "").str.replace(" ", "").str.contains(
                dni_normalizado, case=False, na=False
            )
            mask = mask_dni if mask is None else (mask | mask_dni)

    if mask is None:
        raise HTTPException(
            status_code=422,
            detail=f"No se encontraron columnas 'ID' o 'dni' en la hoja 'permisos'. Columnas disponibles: {list(df.columns)}",
        )

    matches = df[mask].to_dict(orient="records")

    if not matches:
        return {"found": False, "results": []}

    # Enriquecer con estado de pago
    for registro in matches:
        permiso_id = safe_str_id(registro.get("ID"))
        if permiso_id:
            registro["ID"] = permiso_id
            pago_query = select(pagos_permisos).where(
                pagos_permisos.c.permiso_id == permiso_id,
                pagos_permisos.c.status == "approved",
            )
            pago_result = await database.fetch_one(pago_query)

            if pago_result:
                registro["estado_pago"] = "Pagado"
                registro["payment_id"] = pago_result["payment_id"]
                registro["fecha_pago"] = (
                    pago_result["date_created"].isoformat()
                    if pago_result["date_created"]
                    else None
                )
            else:
                any_pago_query = select(pagos_permisos).where(
                    pagos_permisos.c.permiso_id == permiso_id
                )
                any_pago = await database.fetch_one(any_pago_query)
                if any_pago:
                    registro["estado_pago"] = any_pago["status"].capitalize()
                else:
                    registro["estado_pago"] = "Pendiente"
        else:
            registro["estado_pago"] = "Sin ID"

    return {"found": True, "total": len(matches), "results": matches}
