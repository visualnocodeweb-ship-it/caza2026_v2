import logging
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import datetime
from sqlalchemy import select, func, desc
from .database import database, engine, metadata
from .models import logs, pagos, pagos_permisos, cobros_enviados, permisos_enviados, sent_items
from . import sheets_services, email_services, drive_services # Importar los servicios
import math # Needed for ceil
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# --- Pydantic Models ---
class InscriptionCreate(BaseModel):
    # Ajusta estos campos según la estructura real de tus inscripciones en Google Sheets
    nombre_completo: str
    dni: str
    email: str
    telefono: Optional[str] = None
    tipo_establecimiento: str # 'Area Libre' o 'Criadero'
    monto: float
    # Otros campos que puedan ser relevantes para una inscripción

class PermisoCreate(BaseModel):
    # Ajusta estos campos según la estructura real de tus permisos en Google Sheets
    nombre_completo_solicitante: str
    dni_solicitante: str
    email_solicitante: str
    categoria_permiso: str # Ej. 'Permiso de Caza Mayor', 'Permiso de Caza Menor'
    monto: float
    # Otros campos que puedan ser relevantes para un permiso

class LinkDataRequest(BaseModel):
    # Este modelo es genérico, ajusta los campos según lo que esperes recibir en /api/link-data
    type: str # Ej. 'inscripcion', 'permiso', 'pago'
    id: str # El ID del ítem que se está vinculando
    data: Dict[str, Any] # Datos adicionales a vincular

class PaymentWebhookData(BaseModel):
    # Modelo para datos de webhook de pago (ej. Mercado Pago)
    payment_id: str
    external_reference: str # Podría ser inscription_id o permiso_id
    status: str
    status_detail: str
    amount: float
    payer_email: Optional[str] = None
    # Otros campos relevantes del webhook

class SentItemEntry(BaseModel):
    item_id: str
    item_type: str # 'inscripcion' o 'permiso'
    sent_type: str # 'cobro', 'credencial', 'pdf'
    email: Optional[str] = None
    date_sent: datetime.datetime

class SendPaymentLinkRequest(BaseModel):
    inscription_id: str
    email: str
    nombre_establecimiento: Optional[str] = None
    tipo_establecimiento: Optional[str] = None

class SendCredentialRequest(BaseModel):
    numero_inscripcion: str
    nombre_establecimiento: str
    razon_social: Optional[str] = None
    cuit: Optional[str] = None
    tipo_establecimiento: Optional[str] = None
    email: str

class SendPermisoPaymentLinkRequest(BaseModel):
    permiso_id: str
    email: str
    nombre_apellido: str
    categoria: Optional[str] = None

class SendPermisoEmailRequest(BaseModel):
    permiso_id: str
    email: str
    nombre_apellido: str

# --- Logging Centralizado ---
async def log_activity(level: str, event: str, details: str = ""):
    """Guarda un registro de actividad en la base de datos."""
    try:
        query = logs.insert().values(
            level=level.upper(),
            event=event,
            details=details,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        await database.execute(query)
    except Exception as e:
        print(f"FATAL: No se pudo guardar el log en la base de datos. Error: {e}")
        print(f"Log original: Level={level}, Event={event}, Details={details}")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()
    metadata.create_all(bind=engine) # Ensure tables are created
    await log_activity('INFO', 'startup', 'Aplicación iniciada.')

@app.on_event("shutdown")
async def shutdown():
    await log_activity('INFO', 'shutdown', 'Aplicación cerrándose.')
    await database.disconnect()

# --- CORS Configuration ---
origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "https://caza2026-frontend.onrender.com",
    # Agrega aquí cualquier otro dominio donde se despliegue tu frontend
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.get("/")
async def read_root():
    await log_activity('INFO', 'root_access', 'Acceso al endpoint raíz.')
    return {"message": "Hello from FastAPI app!"}

@app.get("/api/logs", response_model=Dict[str, Any])
async def get_logs(page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100)):
    try:
        total_records_query = select(func.count()).select_from(logs)
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        
        query = logs.select().order_by(desc(logs.c.timestamp)).offset(offset).limit(limit)
        log_records = await database.fetch_all(query)
        
        return {
            "data": [dict(record) for record in log_records],
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_logs_failed', f"Error al obtener logs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch logs.")

@app.get("/api/inscripciones", response_model=Dict[str, Any])
async def get_inscripciones(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    await log_activity('INFO', 'get_inscripciones_request', f'Solicitud de inscripciones - Página: {page}, Límite: {limit}')
    try:
        # Aquí deberías leer las inscripciones desde Google Sheets o tu DB.
        # Por simplicidad, leeremos de sheets_services.py, ajusta esto si usas una DB principal.
        # Asume que GOOGLE_SHEET_ID y un nombre de hoja específico para inscripciones están en .env
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        main_sheet_name_env = os.getenv("GOOGLE_SHEET_NAME") # Obtener el nombre de la hoja principal del .env
        inscripciones_tab_name = "inscrip" # Nombre de la pestaña, confirmado por el usuario
        
        if not sheet_id or not main_sheet_name_env:
            raise ValueError("GOOGLE_SHEET_ID o GOOGLE_SHEET_NAME no configurados.")

        df = sheets_services.read_sheet_data(sheet_id, inscripciones_tab_name)
        
        if df.empty:
            return {"data": [], "total_records": 0, "page": page, "limit": limit, "total_pages": 0}

        total_records = len(df)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        
        # Aplicar paginación al DataFrame
        paginated_data = df.iloc[offset : offset + limit].to_dict(orient="records")

        return {
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_inscripciones_failed', f"Error al obtener inscripciones: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener inscripciones: {e}")

@app.post("/api/inscripciones", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_inscripcion(inscripcion: InscriptionCreate):
    await log_activity('INFO', 'create_inscripcion_request', f'Solicitud para crear inscripción: {inscripcion.email}')
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        main_sheet_name_env = os.getenv("GOOGLE_SHEET_NAME")
        inscripciones_tab_name = "inscrip" # Nombre de la pestaña, confirmado por el usuario
        
        if not sheet_id or not main_sheet_name_env:
            raise ValueError("GOOGLE_SHEET_ID o GOOGLE_SHEET_NAME no configurados.")


        # Generar un numero_inscripcion único (ej. timestamp + hash o UUID)
        numero_inscripcion = f"INS-{int(datetime.datetime.now().timestamp())}"

        # Datos a agregar a la hoja de Google
        # Asegúrate de que el orden de las columnas aquí coincida con tu hoja de Google
        values_to_append = [
            [
                numero_inscripcion,
                inscripcion.nombre_completo,
                inscripcion.dni,
                inscripcion.email,
                inscripcion.telefono,
                inscripcion.tipo_establecimiento,
                inscripcion.monto,
                "Pendiente", # Estado inicial del pago
                str(datetime.datetime.now(datetime.timezone.utc)) # Fecha de creación
                # ... añade aquí más campos según tu hoja
            ]
        ]
        
        sheets_services.append_sheet_data(sheet_id, inscripciones_sheet_name, values_to_append)
        
        # Opcional: registrar en la base de datos si tienes un modelo para inscripciones
        # await database.execute(inscripciones.insert().values(...))

        await log_activity('INFO', 'inscripcion_creada', f'Inscripción {numero_inscripcion} creada.')
        return {"message": "Inscripción creada exitosamente", "numero_inscripcion": numero_inscripcion}
    except Exception as e:
        await log_activity('ERROR', 'create_inscripcion_failed', f"Error al crear inscripción: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear inscripción: {e}")

@app.get("/api/permisos", response_model=Dict[str, Any])
async def get_permisos(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    await log_activity('INFO', 'get_permisos_request', f'Solicitud de permisos - Página: {page}, Límite: {limit}')
    try:
        # Leer permisos desde Google Sheets o DB
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        main_sheet_name_env = os.getenv("GOOGLE_SHEET_NAME") # Obtener el nombre de la hoja principal del .env
        permisos_tab_name = "permisos" # Nombre de la pestaña, confirmado por el usuario
        
        if not sheet_id or not main_sheet_name_env:
            raise ValueError("GOOGLE_SHEET_ID o GOOGLE_SHEET_NAME no configurados.")

        df = sheets_services.read_sheet_data(sheet_id, permisos_tab_name)
        
        if df.empty:
            return {"data": [], "total_records": 0, "page": page, "limit": limit, "total_pages": 0}

        total_records = len(df)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        
        paginated_data = df.iloc[offset : offset + limit].to_dict(orient="records")

        return {
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_permisos_failed', f"Error al obtener permisos: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener permisos: {e}")

@app.post("/api/permisos", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def create_permiso(permiso: PermisoCreate):
    await log_activity('INFO', 'create_permiso_request', f'Solicitud para crear permiso para: {permiso.email_solicitante}')
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        main_sheet_name_env = os.getenv("GOOGLE_SHEET_NAME")
        permisos_tab_name = "permisos" # Nombre de la pestaña, confirmado por el usuario
        
        if not sheet_id or not main_sheet_name_env:
            raise ValueError("GOOGLE_SHEET_ID o GOOGLE_SHEET_NAME no configurados.")


        # Generar un ID de permiso único
        permiso_id = f"PER-{int(datetime.datetime.now().timestamp())}"

        # Datos a agregar a la hoja de Google
        values_to_append = [
            [
                permiso_id,
                permiso.nombre_completo_solicitante,
                permiso.dni_solicitante,
                permiso.email_solicitante,
                permiso.categoria_permiso,
                permiso.monto,
                "Pendiente", # Estado inicial del pago
                str(datetime.datetime.now(datetime.timezone.utc)) # Fecha de creación
                # ... añade aquí más campos según tu hoja
            ]
        ]
        
        sheets_services.append_sheet_data(sheet_id, permisos_sheet_name, values_to_append)
        
        # Opcional: registrar en la base de datos si tienes un modelo para permisos
        # await database.execute(permisos.insert().values(...))

        await log_activity('INFO', 'permiso_creado', f'Permiso {permiso_id} creado.')
        return {"message": "Permiso creado exitosamente", "permiso_id": permiso_id}
    except Exception as e:
        await log_activity('ERROR', 'create_permiso_failed', f"Error al crear permiso: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear permiso: {e}")

@app.get("/api/sent-items", response_model=Dict[str, Any])
async def get_sent_items(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    await log_activity('INFO', 'get_sent_items_request', f'Solicitud de sent items - Página: {page}, Límite: {limit}')
    try:
        total_records_query = select(func.count()).select_from(sent_items)
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        
        query = sent_items.select().order_by(desc(sent_items.c.date_sent)).offset(offset).limit(limit)
        records = await database.fetch_all(query)
        
        return {
            "data": [dict(record) for record in records],
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_sent_items_failed', f"Error al obtener sent items: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener sent items: {e}")

@app.post("/api/link-data", response_model=Dict[str, str])
async def link_data(request_data: LinkDataRequest):
    await log_activity('INFO', 'link_data_request', f'Solicitud de link-data para tipo: {request_data.type}, ID: {request_data.id}')
    try:
        # Esta función es un placeholder. La lógica real dependerá de lo que
        # signifique "link-data" en tu aplicación.
        # Podría ser para:
        # 1. Actualizar el estado de un registro en la DB o Sheets.
        # 2. Iniciar un flujo de trabajo (ej. enviar email, generar PDF).
        # 3. Sincronizar datos entre diferentes sistemas.
        
        # Ejemplo muy básico: registrar en los logs
        await log_activity(
            'INFO', 
            f'link_data_{request_data.type}', 
            f"Datos vinculados para {request_data.type} con ID {request_data.id}: {request_data.data}"
        )
        
        return {"message": f"Datos para {request_data.type} con ID {request_data.id} procesados."}
    except Exception as e:
        await log_activity('ERROR', 'link_data_failed', f"Error al procesar link-data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al procesar link-data: {e}")


@app.post("/api/pagos/webhook", status_code=status.HTTP_200_OK)
async def handle_payment_webhook(payment_data: PaymentWebhookData):
    await log_activity('INFO', 'payment_webhook_received', f"Webhook de pago recibido para {payment_data.external_reference}")
    try:
        # Registrar el pago en la base de datos `pagos` o `pagos_permisos`
        if payment_data.external_reference.startswith("INS-"): # Es una inscripción
            query = pagos.insert().values(
                payment_id=payment_data.payment_id,
                inscription_id=payment_data.external_reference,
                status=payment_data.status,
                status_detail=payment_data.status_detail,
                amount=payment_data.amount,
                email=payment_data.payer_email,
                date_created=datetime.datetime.now(datetime.timezone.utc)
            )
            await database.execute(query)

            # Actualizar el estado en Google Sheets (hoja de inscripciones)
            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            main_sheet_name_env = os.getenv("GOOGLE_SHEET_NAME")
            inscripciones_tab_name = "inscrip" # Nombre de la pestaña, confirmado por el usuario
            if sheet_id and main_sheet_name_env:
                sheets_services.update_payment_status(
                    sheet_id, inscripciones_tab_name, payment_data.external_reference, payment_data.status
                )
            await log_activity('INFO', 'inscripcion_pago_actualizado', f"Pago {payment_data.payment_id} para inscripción {payment_data.external_reference} actualizado a {payment_data.status}")

        elif payment_data.external_reference.startswith("PER-"): # Es un permiso
            query = pagos_permisos.insert().values(
                payment_id=payment_data.payment_id,
                permiso_id=payment_data.external_reference,
                status=payment_data.status,
                status_detail=payment_data.status_detail,
                amount=payment_data.amount,
                email=payment_data.payer_email,
                date_created=datetime.datetime.now(datetime.timezone.utc)
            )
            await database.execute(query)

            # Actualizar el estado en Google Sheets (hoja de permisos)
            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            main_sheet_name_env = os.getenv("GOOGLE_SHEET_NAME")
            permisos_tab_name = "permisos" # Nombre de la pestaña, confirmado por el usuario
            if sheet_id and main_sheet_name_env:
                sheets_services.update_payment_status( # Reutilizamos la función, asumiendo que el ID y la columna son similares
                    sheet_id, permisos_tab_name, payment_data.external_reference, payment_data.status
                )
            await log_activity('INFO', 'permiso_pago_actualizado', f"Pago {payment_data.payment_id} para permiso {payment_data.external_reference} actualizado a {payment_data.status}")
        else:
            await log_activity('WARNING', 'payment_webhook_unknown_ref', f"Referencia externa desconocida en webhook: {payment_data.external_reference}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Referencia externa desconocida.")

        return {"message": "Webhook de pago procesado exitosamente"}

    except Exception as e:
        await log_activity('ERROR', 'payment_webhook_failed', f"Error al procesar webhook de pago: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al procesar webhook de pago: {e}")

@app.get("/api/pagos", response_model=Dict[str, Any])
async def get_pagos(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    await log_activity('INFO', 'get_pagos_request', f'Solicitud de pagos - Página: {page}, Límite: {limit}')
    try:
        total_records_query = select(func.count()).select_from(pagos)
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        
        query = pagos.select().order_by(desc(pagos.c.date_created)).offset(offset).limit(limit)
        payment_records = await database.fetch_all(query)
        
        return {
            "data": [dict(record) for record in payment_records],
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_pagos_failed', f"Error al obtener pagos: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener pagos: {e}")

@app.get("/api/stats/total-inscripciones", response_model=Dict[str, int])
async def get_total_inscripciones():
    await log_activity('INFO', 'get_total_inscripciones_request', 'Solicitud del total de inscripciones.')
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        inscripciones_tab_name = "inscrip" # Nombre de la pestaña, confirmado por el usuario
        
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID no configurado.")

        df = sheets_services.read_sheet_data(sheet_id, inscripciones_tab_name)
        
        total_inscripciones = len(df) if not df.empty else 0

        return {"total_inscripciones": total_inscripciones}
    except Exception as e:
        await log_activity('ERROR', 'get_total_inscripciones_failed', f"Error al obtener total de inscripciones: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener total de inscripciones: {e}")

@app.get("/api/stats/total-permisos", response_model=Dict[str, int])
async def get_total_permisos():
    await log_activity('INFO', 'get_total_permisos_request', 'Solicitud del total de permisos.')
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        permisos_tab_name = "permisos" # Nombre de la pestaña, confirmado por el usuario
        
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID no configurado.")

        df = sheets_services.read_sheet_data(sheet_id, permisos_tab_name)
        
        total_permisos = len(df) if not df.empty else 0
        
        return {"total_permisos": total_permisos}
    except Exception as e:
        await log_activity('ERROR', 'get_total_permisos_failed', f"Error al obtener total de permisos: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener total de permisos: {e}")

@app.get("/api/cobros-enviados", response_model=Dict[str, Any])
async def get_cobros_enviados(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    await log_activity('INFO', 'get_cobros_enviados_request', f'Solicitud de cobros enviados - Página: {page}, Límite: {limit}')
    try:
        total_records_query = select(func.count()).select_from(cobros_enviados)
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        
        query = cobros_enviados.select().order_by(desc(cobros_enviados.c.date_sent)).offset(offset).limit(limit)
        cobros_records = await database.fetch_all(query)
        
        return {
            "data": [dict(record) for record in cobros_records],
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_cobros_enviados_failed', f"Error al obtener cobros enviados: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener cobros enviados: {e}")

@app.get("/api/permiso-cobros-enviados", response_model=Dict[str, Any])
async def get_permiso_cobros_enviados(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    await log_activity('INFO', 'get_permiso_cobros_enviados_request', f'Solicitud de cobros de permisos enviados - Página: {page}, Límite: {limit}')
    try:
        total_records_query = select(func.count()).select_from(permisos_enviados)
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        
        query = permisos_enviados.select().order_by(desc(permisos_enviados.c.date_sent)).offset(offset).limit(limit)
        permiso_cobros_records = await database.fetch_all(query)
        
        return {
            "data": [dict(record) for record in permiso_cobros_records],
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_permiso_cobros_enviados_failed', f"Error al obtener cobros de permisos enviados: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener cobros de permisos enviados: {e}")

@app.get("/api/stats/recaudaciones", response_model=Dict[str, Any])
async def get_recaudaciones_stats():
    await log_activity('INFO', 'get_recaudaciones_stats_request', 'Solicitud de estadísticas de recaudaciones.')
    try:
        # Recaudación total de inscripciones (estado 'approved')
        total_inscripciones_aprobadas_query = select(func.sum(pagos.c.amount)).where(pagos.c.status == 'approved')
        recaudacion_inscripciones = await database.fetch_val(total_inscripciones_aprobadas_query) or 0.0

        # Recaudación total de permisos (estado 'approved')
        total_permisos_aprobados_query = select(func.sum(pagos_permisos.c.amount)).where(pagos_permisos.c.status == 'approved')
        recaudacion_permisos = await database.fetch_val(total_permisos_aprobados_query) or 0.0

        recaudacion_total = recaudacion_inscripciones + recaudacion_permisos

        # Recaudación de permisos por mes
        recaudacion_permisos_por_mes_query = select(
            func.to_char(pagos_permisos.c.date_created, 'YYYY-MM').label('mes'),
            func.sum(pagos_permisos.c.amount).label('total')
        ).where(
            pagos_permisos.c.status == 'approved'
        ).group_by(
            'mes'
        ).order_by(
            'mes'
        )

        recaudacion_permisos_por_mes_raw = await database.fetch_all(recaudacion_permisos_por_mes_query)
        recaudacion_permisos_por_mes = [{"name": r["mes"], "total": float(r["total"])} for r in recaudacion_permisos_por_mes_raw]


        return {
            "recaudacion_total": recaudacion_total,
            "recaudacion_inscripciones": recaudacion_inscripciones,
            "recaudacion_permisos": recaudacion_permisos,
            "recaudacion_permisos_por_mes": recaudacion_permisos_por_mes
        }
    except Exception as e:
        await log_activity('ERROR', 'get_recaudaciones_stats_failed', f"Error al obtener estadísticas de recaudaciones: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener estadísticas de recaudaciones: {e}")

@app.post("/api/log-sent-item", response_model=Dict[str, str], status_code=status.HTTP_201_CREATED)
async def log_sent_item_endpoint(item_data: SentItemEntry):
    await log_activity('INFO', 'log_sent_item_request', f'Registrando ítem enviado: {item_data.item_type} - {item_data.item_id} - {item_data.sent_type}')
    try:
        query = sent_items.insert().values(
            item_id=item_data.item_id,
            item_type=item_data.item_type,
            sent_type=item_data.sent_type,
            email=item_data.email,
            date_sent=datetime.datetime.now(datetime.timezone.utc)
        )
        await database.execute(query)
        return {"message": "Ítem enviado registrado exitosamente."}
    except Exception as e:
        await log_activity('ERROR', 'log_sent_item_failed', f"Error al registrar ítem enviado: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al registrar ítem enviado: {e}")

@app.post("/api/send-payment-link", response_model=Dict[str, str]) # NUEVO
async def send_payment_link_endpoint(request_data: SendPaymentLinkRequest):
    await log_activity('INFO', 'send_payment_link_request', f'Solicitud para enviar link de pago a: {request_data.email} para inscripción: {request_data.inscription_id}')
    try:
        # TODO: Generar link de pago real (integración con MercadoPago o similar)
        # Por ahora, un placeholder
        payment_link = "https://example.com/mock_payment_link/inscripciones/" + request_data.inscription_id 

        subject = f"Enlace de pago para su inscripción {request_data.inscription_id}"
        html_content = f"""
        <html>
            <body>
                <p>Estimado/a {request_data.nombre_establecimiento},</p>
                <p>Adjunto encontrará el enlace para realizar el pago de su inscripción <b>{request_data.inscription_id}</b> ({request_data.tipo_establecimiento}).</p>
                <p>Puede realizar el pago haciendo click en el siguiente enlace: <a href="{payment_link}">{payment_link}</a></p>
                <p>Gracias.</p>
                <p>El equipo de Caza 2026</p>
            </body>
        </html>
        """
        sender_email = os.getenv("SENDER_EMAIL_RESEND", "onboarding@resend.dev")

        email_sent = email_services.send_simple_email(
            to_email=request_data.email,
            subject=subject,
            html_content=html_content,
            sender_email=sender_email
        )

        if not email_sent:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo al enviar el email de cobro.")
        
        return {"message": "Email de cobro enviado exitosamente."}
    except Exception as e:
        await log_activity('ERROR', 'send_payment_link_failed', f"Error al enviar link de pago: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al enviar link de pago: {e}")

@app.post("/api/send-credential", response_model=Dict[str, str])
async def send_credential_endpoint(request_data: SendCredentialRequest):
    await log_activity('INFO', 'send_credential_request', f'Solicitud para enviar credencial a: {request_data.email} para inscripción: {request_data.numero_inscripcion}')
    try:
        subject = f"Credencial de Inscripción {request_data.numero_inscripcion}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Credencial de Inscripción</h2>
                <p>Estimado/a <strong>{request_data.nombre_establecimiento}</strong>,</p>
                <p>Adjunto encontrará su credencial de inscripción:</p>
                <div style="border: 2px solid #333; padding: 15px; margin: 20px 0; background-color: #f9f9f9;">
                    <p><strong>Número de Inscripción:</strong> {request_data.numero_inscripcion}</p>
                    <p><strong>Establecimiento:</strong> {request_data.nombre_establecimiento}</p>
                    <p><strong>Razón Social:</strong> {request_data.razon_social or 'N/A'}</p>
                    <p><strong>CUIT:</strong> {request_data.cuit or 'N/A'}</p>
                    <p><strong>Tipo:</strong> {request_data.tipo_establecimiento or 'N/A'}</p>
                </div>
                <p>Gracias por su inscripción.</p>
                <p>El equipo de Caza 2026</p>
            </body>
        </html>
        """
        sender_email = os.getenv("SENDER_EMAIL_RESEND", "onboarding@resend.dev")

        email_sent = email_services.send_simple_email(
            to_email=request_data.email,
            subject=subject,
            html_content=html_content,
            sender_email=sender_email
        )

        if not email_sent:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo al enviar la credencial por email.")

        return {"message": "Credencial enviada exitosamente."}
    except Exception as e:
        await log_activity('ERROR', 'send_credential_failed', f"Error al enviar credencial: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al enviar credencial: {e}")

@app.get("/api/view-credential/{numero_inscripcion}", response_class=HTMLResponse)
async def view_credential_endpoint(numero_inscripcion: str):
    await log_activity('INFO', 'view_credential_request', f'Solicitud para ver credencial de inscripción: {numero_inscripcion}')
    try:
        # Obtener datos de la inscripción desde Google Sheets
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        inscripciones_tab_name = "inscrip"

        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID no configurado.")

        df = sheets_services.read_sheet_data(sheet_id, inscripciones_tab_name)

        # Buscar la inscripción específica
        inscripcion = df[df['numero_inscripcion'] == numero_inscripcion]

        if inscripcion.empty:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Inscripción {numero_inscripcion} no encontrada.")

        inscripcion_data = inscripcion.iloc[0]

        html_content = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <title>Credencial - {numero_inscripcion}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 40px; background-color: #f5f5f5; }}
                    .credential {{
                        max-width: 600px;
                        margin: 0 auto;
                        background: white;
                        padding: 30px;
                        border: 3px solid #333;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }}
                    h1 {{ color: #333; text-align: center; }}
                    .field {{ margin: 15px 0; }}
                    .field strong {{ display: inline-block; width: 180px; }}
                    .print-btn {{
                        display: block;
                        width: 200px;
                        margin: 20px auto;
                        padding: 10px;
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        cursor: pointer;
                        font-size: 16px;
                    }}
                    .print-btn:hover {{ background-color: #45a049; }}
                    @media print {{ .print-btn {{ display: none; }} }}
                </style>
            </head>
            <body>
                <div class="credential">
                    <h1>Credencial de Inscripción</h1>
                    <div class="field"><strong>Número:</strong> {inscripcion_data.get('numero_inscripcion', 'N/A')}</div>
                    <div class="field"><strong>Establecimiento:</strong> {inscripcion_data.get('nombre_establecimiento', 'N/A')}</div>
                    <div class="field"><strong>Razón Social:</strong> {inscripcion_data.get('razon_social', 'N/A')}</div>
                    <div class="field"><strong>CUIT:</strong> {inscripcion_data.get('cuit', 'N/A')}</div>
                    <div class="field"><strong>Tipo:</strong> {inscripcion_data.get('su establecimiento es', 'N/A')}</div>
                    <div class="field"><strong>Email:</strong> {inscripcion_data.get('email', 'N/A')}</div>
                    <div class="field"><strong>Celular:</strong> {inscripcion_data.get('celular', 'N/A')}</div>
                    <button class="print-btn" onclick="window.print()">Imprimir Credencial</button>
                </div>
            </body>
        </html>
        """

        return HTMLResponse(content=html_content)
    except Exception as e:
        await log_activity('ERROR', 'view_credential_failed', f"Error al ver credencial: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al ver credencial: {e}")

@app.post("/api/send-permiso-payment-link", response_model=Dict[str, str])
async def send_permiso_payment_link_endpoint(request_data: SendPermisoPaymentLinkRequest):
    await log_activity('INFO', 'send_permiso_payment_link_request', f'Solicitud para enviar link de pago de permiso a: {request_data.email} para permiso: {request_data.permiso_id}')
    try:
        # TODO: Generar link de pago real (integración con MercadoPago o similar)
        payment_link = "https://example.com/mock_payment_link/permisos/" + request_data.permiso_id

        subject = f"Enlace de pago para su permiso de caza {request_data.permiso_id}"
        html_content = f"""
        <html>
            <body>
                <p>Estimado/a {request_data.nombre_apellido},</p>
                <p>Adjunto encontrará el enlace para realizar el pago de su permiso de caza <b>{request_data.permiso_id}</b> ({request_data.categoria}).</p>
                <p>Puede realizar el pago haciendo click en el siguiente enlace: <a href="{payment_link}">{payment_link}</a></p>
                <p>Gracias.</p>
                <p>El equipo de Caza 2026</p>
            </body>
        </html>
        """
        sender_email = os.getenv("SENDER_EMAIL_RESEND", "onboarding@resend.dev")

        email_sent = email_services.send_simple_email(
            to_email=request_data.email,
            subject=subject,
            html_content=html_content,
            sender_email=sender_email
        )

        if not email_sent:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo al enviar el email de cobro del permiso.")

        return {"message": "Email de cobro de permiso enviado exitosamente."}
    except Exception as e:
        await log_activity('ERROR', 'send_permiso_payment_link_failed', f"Error al enviar link de pago de permiso: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al enviar link de pago de permiso: {e}")

@app.post("/api/send-permiso-email", response_model=Dict[str, str])
async def send_permiso_email_endpoint(request_data: SendPermisoEmailRequest):
    await log_activity('INFO', 'send_permiso_email_request', f'Solicitud para enviar permiso a: {request_data.email} para permiso: {request_data.permiso_id}')
    try:
        subject = f"Su permiso de caza {request_data.permiso_id}"
        html_content = f"""
        <html>
            <body>
                <p>Estimado/a {request_data.nombre_apellido},</p>
                <p>Adjunto encontrará su permiso de caza <b>{request_data.permiso_id}</b>.</p>
                <p>Por favor, conserve este permiso para su presentación cuando sea requerido.</p>
                <p>Gracias.</p>
                <p>El equipo de Caza 2026</p>
            </body>
        </html>
        """
        sender_email = os.getenv("SENDER_EMAIL_RESEND", "onboarding@resend.dev")

        email_sent = email_services.send_simple_email(
            to_email=request_data.email,
            subject=subject,
            html_content=html_content,
            sender_email=sender_email
        )

        if not email_sent:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo al enviar el email del permiso.")

        return {"message": "Permiso enviado exitosamente por email."}
    except Exception as e:
        await log_activity('ERROR', 'send_permiso_email_failed', f"Error al enviar permiso por email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al enviar permiso por email: {e}")

