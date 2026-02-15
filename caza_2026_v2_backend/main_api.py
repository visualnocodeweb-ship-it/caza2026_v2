import logging
import time
import random
import asyncio
import base64
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import datetime
import pandas as pd
import mercadopago
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from dateutil import parser
from sqlalchemy import select, func, extract
from collections import defaultdict
import traceback
import math

# --- Nuevas importaciones de base de datos ---
from .database import database, engine, metadata
from .models import pagos, cobros_enviados, pagos_permisos, permisos_enviados, sent_items, logs

# --- Importaciones de servicios existentes ---
from .sheets_services import read_sheet_data, get_sheets_service, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME, get_price_for_establishment, get_price_for_categoria, update_cobro_enviado_status
from .drive_services import list_pdfs_in_folder, GOOGLE_DRIVE_FOLDER_ID, download_file
from .email_services import send_simple_email, send_email_with_attachment

# --- Configuración ---
load_dotenv(encoding='latin-1')

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
        # Si el logging falla, lo imprimimos para no detener la aplicación
        print(f"FATAL: No se pudo guardar el log en la base de datos. Error: {e}")
        print(f"Log original: Level={level}, Event={event}, Details={details}")

# Configurar el logging para main_api
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# (El resto del archivo permanece igual hasta los endpoints que vamos a modificar)

# ... (código existente hasta los endpoints)
MAIN_SHEET_ID = GOOGLE_SHEET_ID
MAIN_SHEET_NAME = GOOGLE_SHEET_NAME
PERMISOS_SHEET_ID = "1Hl99DUx5maPEHkC5JNJqq2SZLa8UgVQBJbeia5jk1VI"
PERMISOS_SHEET_NAME = "permisos"
PERMISOS_DRIVE_FOLDER_ID = "1ZynwbJewIsSodT8ogIm2AXanL2Am0IUt"
PRICES_SHEET_ID = os.getenv("PRICES_SHEET_ID", GOOGLE_SHEET_ID)
PRICES_SHEET_NAME = os.getenv("PRICES_SHEET_NAME", "precios")
SENDER_EMAIL_RESEND = os.getenv("SENDER_EMAIL_RESEND")
if not SENDER_EMAIL_RESEND:
    raise ValueError("SENDER_EMAIL_RESEND environment variable not set.")

# --- Cache simple en memoria ---
sheet_cache = {}
CACHE_TTL = 300  # 5 minutos en segundos

async def get_cached_sheet_data(sheet_id, sheet_name):
    cache_key = f"{sheet_id}_{sheet_name}"
    current_time = time.time()

    if cache_key in sheet_cache:
        data, timestamp = sheet_cache[cache_key]
        if current_time - timestamp < CACHE_TTL:
            logging.info(f"Devolviendo datos desde el caché para: {cache_key}")
            return data

    # Mitigación de "Thundering Herd": espera aleatoria para escalonar las peticiones
    await asyncio.sleep(random.uniform(0, 2))
    
    # Re-verificar el caché después de la espera, por si otro worker ya lo llenó
    if cache_key in sheet_cache:
        data, timestamp = sheet_cache[cache_key]
        if current_time - timestamp < CACHE_TTL:
            logging.info(f"Devolviendo datos desde el caché (post-espera) para: {cache_key}")
            return data

    logging.info(f"No hay caché válido. Leyendo desde Google Sheets para: {cache_key}")
    data = read_sheet_data(sheet_id, sheet_name)
    sheet_cache[cache_key] = (data, current_time)
    return data

# Configuración de Mercado Pago
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
mp_sdk = None
mp_sdk_initialized = False
if MERCADOPAGO_ACCESS_TOKEN:
    try:
        mp_sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)
        mp_sdk_initialized = True
        logging.info("Mercado Pago SDK inicializado exitosamente.")
    except Exception as e:
        logging.error(f"Fallo al inicializar Mercado Pago SDK: {e}", exc_info=True)
else:
    logging.warning("MERCADOPAGO_ACCESS_TOKEN no configurado.")

# --- Creación de la tabla de la base de datos ---
# metadata.create_all(bind=engine) # Mover esta línea al evento startup

app = FastAPI()

# --- Eventos de Startup y Shutdown de la App ---
@app.on_event("startup")
async def startup():
    await database.connect()
    metadata.create_all(bind=engine) # Mover aquí la creación de tablas
    await log_activity('INFO', 'startup', 'La aplicación se ha iniciado.')

@app.on_event("shutdown")
async def shutdown():
    await log_activity('INFO', 'shutdown', 'La aplicación se está cerrando.')
    await database.disconnect()

# --- Pydantic Models ---
class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    html_content: str

class SendPaymentLinkRequest(BaseModel):
    inscription_id: str
    email: str
    nombre_establecimiento: str
    tipo_establecimiento: str # Nuevo campo

class SendPermisoPaymentLinkRequest(BaseModel):
    permiso_id: str
    email: str
    nombre_apellido: str
    categoria: str

class SendPermisoEmailRequest(BaseModel):
    permiso_id: str
    email: str
    nombre_apellido: str

class SendCredentialRequest(BaseModel):
    numero_inscripcion: str
    nombre_establecimiento: str
    razon_social: str
    cuit: str
    tipo_establecimiento: str
    email: str

class LogSentItemRequest(BaseModel):
    item_id: str
    item_type: str
    sent_type: str

# --- CORS ---
origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "https://caza2026-frontend.onrender.com",
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# --- Endpoints ---
@app.get("/api/logs")
async def get_logs(page: int = 1, limit: int = 15): # Default limit to 15
    try:
        # Get total records
        total_records_query = select(func.count()).select_from(logs)
        total_records = await database.fetch_val(total_records_query)

        # Calculate offset and total pages
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit)

        # Fetch paginated logs
        query = logs.select().order_by(logs.c.timestamp.desc()).offset(offset).limit(limit)
        log_records = await database.fetch_all(query)
        
        return {
            "data": [dict(record) for record in log_records],
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_logs_failed', f"Error al obtener logs: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to fetch logs.")

@app.post("/api/log-sent-item")
async def log_sent_item(request: LogSentItemRequest):
    try:
        await log_activity(
            'INFO', 
            'button_click', 
            f"Botón '{request.sent_type}' presionado para {request.item_type} ID: {request.item_id}"
        )
        query = sent_items.insert().values(
            item_id=request.item_id,
            item_type=request.item_type,
            sent_type=request.sent_type,
            date_sent=datetime.datetime.now(datetime.timezone.utc)
        )
        await database.execute(query)
        return {"status": "success", "message": "Item logged successfully."}
    except Exception as e:
        await log_activity('ERROR', 'log_sent_item_failed', f"Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to log sent item.")


@app.post("/api/send-payment-link")
async def send_payment_link(request: SendPaymentLinkRequest):
    details=f"ID Inscripción: {request.inscription_id}, Email: {request.email}"
    try:
        await log_activity('INFO', 'send_payment_link_started', details)
        # ... (código existente)
        if not mp_sdk_initialized:
            raise HTTPException(status_code=503, detail="Mercado Pago no está configurado.")
        
        # ... (código existente)
        dynamic_price = get_price_for_establishment(PRICES_SHEET_ID, PRICES_SHEET_NAME, request.tipo_establecimiento)
        
        # ... (código existente)
        preference_data = {
            "items": [{"title": f"Cuota Anual Caza 2026 - {request.nombre_establecimiento}", "quantity": 1, "unit_price": dynamic_price}],
            "payer": {"email": request.email},
            "external_reference": request.inscription_id,
            "back_urls": {
                "success": "https://caza2026-frontend.onrender.com/inscripciones",
                "failure": "https://caza2026-frontend.onrender.com/inscripciones",
                "pending": "https://caza2026-frontend.onrender.com/inscripciones"
            },
            "notification_url": "https://caza2026-1.onrender.com/api/mercadopago-webhook",
        }
        
        preference_response = mp_sdk.preference().create(preference_data)
        preference = preference_response["response"]
        payment_link = preference.get("init_point") or preference.get("sandbox_init_point")

        # ... (código existente)
        email_subject = f"Enlace de pago para {request.nombre_establecimiento}"
        email_html = f"""
            <h1>Hola {request.nombre_establecimiento},</h1>
            <p>Aquí tienes tu enlace para abonar la cuota anual.</p>
            <p><strong>Monto:</strong> ${dynamic_price}</p>
            <a href="{payment_link}" target="_blank" style="padding: 15px; background-color: #009ee3; color: white; text-decoration: none; border-radius: 5px;">Pagar Ahora</a>
        """
        
        send_simple_email(
            to_email=request.email, subject=email_subject,
            html_content=email_html, sender_email=SENDER_EMAIL_RESEND
        )
        
        # ... (código existente)
        
        await log_activity('INFO', 'send_payment_link_success', details)
        return {"status": "success", "message": "Email con enlace de pago enviado."}
    
    except Exception as e:
        await log_activity('ERROR', 'send_payment_link_failed', f"{details} | Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el envío de pago: {e}")


@app.post("/api/send-permiso-payment-link")
async def send_permiso_payment_link(request: SendPermisoPaymentLinkRequest):
    details=f"ID Permiso: {request.permiso_id}, Email: {request.email}"
    try:
        await log_activity('INFO', 'send_permiso_payment_link_started', details)
        # ... (código existente)
        dynamic_price = get_price_for_categoria(PRICES_SHEET_ID, PRICES_SHEET_NAME, request.categoria)
        preference_data = {
            "items": [{"title": f"Permiso de Caza 2026 - {request.nombre_apellido}", "quantity": 1, "unit_price": dynamic_price}],
            "payer": {"email": request.email},
            "external_reference": request.permiso_id,
            "back_urls": {
                "success": "https://caza2026-frontend.onrender.com/permiso-caza",
                "failure": "https://caza2026-frontend.onrender.com/permiso-caza",
                "pending": "https://caza2026-frontend.onrender.com/permiso-caza"
            },
            "notification_url": "https://caza2026-1.onrender.com/api/mercadopago-webhook",
        }
        preference_response = mp_sdk.preference().create(preference_data)
        payment_link = (preference_response["response"]).get("init_point")
        
        email_html = f"""
            <h1>Hola {request.nombre_apellido},</h1>
            <p>Aquí tienes tu enlace para abonar el permiso de caza.</p>
            <p><strong>Monto:</strong> ${dynamic_price}</p>
            <a href="{payment_link}" target="_blank">Pagar Ahora</a>
        """
        send_simple_email(to_email=request.email, subject="Enlace de pago para Permiso de Caza", html_content=email_html, sender_email=SENDER_EMAIL_RESEND)
        await log_activity('INFO', 'send_permiso_payment_link_success', details)
        return {"status": "success", "message": "Email con enlace de pago de permiso enviado."}
    except Exception as e:
        await log_activity('ERROR', 'send_permiso_payment_link_failed', f"{details} | Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el envío de pago de permiso: {e}")

@app.post("/api/send-permiso-email")
async def send_permiso_email(request: SendPermisoEmailRequest):
    details = f"ID Permiso: {request.permiso_id}, Email: {request.email}"
    try:
        await log_activity('INFO', 'send_permiso_email_started', details)
        # ... (código existente)
        pdf_list = list_pdfs_in_folder(PERMISOS_DRIVE_FOLDER_ID)
        pdf_file = next((pdf for pdf in pdf_list if pdf['name'].startswith(request.permiso_id)), None)
        pdf_content = download_file(pdf_file['id'])
        
        email_html = "..." # (como estaba antes)
        
        send_email_with_attachment(
            to_email=request.email,
            subject=f"Tu Permiso de Caza 2026 - {request.nombre_apellido}",
            html_content=email_html,
            sender_email=SENDER_EMAIL_RESEND,
            attachment_content=base64.b64encode(pdf_content).decode('utf-8'),
            attachment_filename=pdf_file['name']
        )
        await log_activity('INFO', 'send_permiso_email_success', details)
        return {"status": "success", "message": "Permiso enviado con éxito."}
    except Exception as e:
        await log_activity('ERROR', 'send_permiso_email_failed', f"{details} | Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error al enviar el permiso: {e}")


@app.post("/api/send-credential")
async def send_credential(request: SendCredentialRequest):
    details = f"Inscripción: {request.numero_inscripcion}, Email: {request.email}"
    try:
        await log_activity('INFO', 'send_credential_started', details)
        # ... (código existente)
        email_html = "..." # (como estaba antes)

        send_simple_email(
            to_email=request.email,
            subject=f"Credencial de Caza 2026 para {request.nombre_establecimiento}",
            html_content=email_html,
            sender_email=SENDER_EMAIL_RESEND
        )
        await log_activity('INFO', 'send_credential_success', details)
        return {"status": "success", "message": "Credencial enviada con éxito."}
    except Exception as e:
        await log_activity('ERROR', 'send_credential_failed', f"{details} | Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error al enviar la credencial: {e}")


@app.post("/api/mercadopago-webhook")
async def mercadopago_webhook(request: Request):
    # ... (código existente)
    if topic == "payment" and payment_id:
        details = f"Payment ID: {payment_id}"
        await log_activity('INFO', 'webhook_received', details)
        try:
            # ... (código existente)
            if payment:
                # ... (código existente)
                if external_reference and external_reference.startswith('fau_inscr'):
                    # ...
                    await database.execute(update_stmt)
                    await log_activity('INFO', 'webhook_payment_success', f"{details} para inscripción {external_reference}")
                else:
                    values = {
                        "payment_id": payment.get('id'),
                        "permiso_id": external_reference,
                        "status": payment.get('status'),
                        "status_detail": payment.get('status_detail'),
                        "amount": payment.get('transaction_amount'),
                        "email": payment.get('payer', {}).get('email'),
                        "date_created": parsed_date
                    }
                    insert_stmt = insert(pagos_permisos).values(values)
                    update_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=['payment_id'],
                        set_=dict(status=values['status'], status_detail=values['status_detail'])
                    )
                    await database.execute(update_stmt)
                    await log_activity('INFO', 'webhook_payment_success', f"{details} para permiso {external_reference}")
        except Exception as e:
            await log_activity('ERROR', 'webhook_processing_failed', f"{details} | Error: {traceback.format_exc()}")
            return {"status": "error", "message": "Internal server error"}
            
    return {"status": "notification received"}

# El resto del archivo como estaba...
# (get_inscripciones, get_permisos, etc. no necesitan cambios para el logging)
