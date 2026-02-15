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
        inscripciones_sheet_name = os.getenv("INSCRIPCIONES_SHEET_NAME", "Inscripciones") # Nombre de la hoja para inscripciones
        
        if not sheet_id or not inscripciones_sheet_name:
            raise ValueError("GOOGLE_SHEET_ID o INSCRIPCIONES_SHEET_NAME no configurados.")

        df = sheets_services.read_sheet_data(sheet_id, inscripciones_sheet_name)
        
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
        inscripciones_sheet_name = os.getenv("INSCRIPCIONES_SHEET_NAME", "Inscripciones")
        
        if not sheet_id or not inscripciones_sheet_name:
            raise ValueError("GOOGLE_SHEET_ID o INSCRIPCIONES_SHEET_NAME no configurados.")

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
        permisos_sheet_name = os.getenv("PERMISOS_SHEET_NAME", "Permisos") # Nombre de la hoja para permisos
        
        if not sheet_id or not permisos_sheet_name:
            raise ValueError("GOOGLE_SHEET_ID o PERMISOS_SHEET_NAME no configurados.")

        df = sheets_services.read_sheet_data(sheet_id, permisos_sheet_name)
        
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
        permisos_sheet_name = os.getenv("PERMISOS_SHEET_NAME", "Permisos")
        
        if not sheet_id or not permisos_sheet_name:
            raise ValueError("GOOGLE_SHEET_ID o PERMISOS_SHEET_NAME no configurados.")

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
            inscripciones_sheet_name = os.getenv("INSCRIPCIONES_SHEET_NAME", "Inscripciones")
            if sheet_id and inscripciones_sheet_name:
                sheets_services.update_payment_status(
                    sheet_id, inscripciones_sheet_name, payment_data.external_reference, payment_data.status
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
            permisos_sheet_name = os.getenv("PERMISOS_SHEET_NAME", "Permisos")
            if sheet_id and permisos_sheet_name:
                sheets_services.update_payment_status( # Reutilizamos la función, asumiendo que el ID y la columna son similares
                    sheet_id, permisos_sheet_name, payment_data.external_reference, payment_data.status
                )
            await log_activity('INFO', 'permiso_pago_actualizado', f"Pago {payment_data.payment_id} para permiso {payment_data.external_reference} actualizado a {payment_data.status}")
        else:
            await log_activity('WARNING', 'payment_webhook_unknown_ref', f"Referencia externa desconocida en webhook: {payment_data.external_reference}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Referencia externa desconocida.")

        return {"message": "Webhook de pago procesado exitosamente"}

    except Exception as e:
        await log_activity('ERROR', 'payment_webhook_failed', f"Error al procesar webhook de pago: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al procesar webhook de pago: {e}")

# Rutas adicionales para funcionalidad específica de email o drive pueden ser añadidas aquí.
# Por ejemplo:
# @app.post("/api/send-credencial")
# async def send_credencial(...):
#     # Lógica para generar credencial y enviarla por email
#     pass

# @app.get("/api/download-pdf/{file_id}")
# async def download_permiso_pdf(file_id: str):
#     # Lógica para descargar PDF de Drive
#     pass
