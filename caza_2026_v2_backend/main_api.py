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
from dateutil import parser # Importar el parser de fechas
from sqlalchemy import select, func # <-- NUEVA IMPORTACIÓN

# --- Nuevas importaciones de base de datos ---
from .database import database, engine, metadata
from .models import pagos, cobros_enviados, pagos_permisos, permisos_enviados

# --- Importaciones de servicios existentes ---
from .sheets_services import read_sheet_data, get_sheets_service, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME, get_price_for_establishment, get_price_for_categoria, update_cobro_enviado_status
from .drive_services import list_pdfs_in_folder, GOOGLE_DRIVE_FOLDER_ID, download_file
from .email_services import send_simple_email, send_email_with_attachment

# --- Configuración ---
load_dotenv(encoding='latin-1')

# --- Background Task ---
async def send_payment_links_for_new_permits():
    while True:
        try:
            logging.info("Verificando nuevos permisos para enviar enlaces de pago...")
            permisos_df = read_sheet_data(PERMISOS_SHEET_ID, PERMISOS_SHEET_NAME)
            if 'Estado de Cobro Enviado' not in permisos_df.columns:
                logging.error("La columna 'Estado de Cobro Enviado' no existe en la hoja de permisos.")
                await asyncio.sleep(300) # Wait 5 minutes before retrying
                continue

            for index, row in permisos_df.iterrows():
                if pd.isna(row['Estado de Cobro Enviado']) or row['Estado de Cobro Enviado'] == '':
                    permiso_id = row.get('ID')
                    email = row.get('Dirección de correo electrónico')
                    nombre_apellido = row.get('Nombre y Apellido')
                    categoria = row.get('Categoría')

                    if all([permiso_id, email, nombre_apellido, categoria]):
                        try:
                            await send_permiso_payment_link(SendPermisoPaymentLinkRequest(
                                permiso_id=permiso_id,
                                email=email,
                                nombre_apellido=nombre_apellido,
                                categoria=categoria
                            ))
                            update_cobro_enviado_status(PERMISOS_SHEET_ID, PERMISOS_SHEET_NAME, permiso_id, "Enviado")
                        except Exception as e:
                            logging.error(f"Error al enviar el enlace de pago para el permiso {permiso_id}: {e}")
                    else:
                        logging.warning(f"Faltan datos en la fila {index + 2} de la hoja de permisos. No se puede enviar el enlace de pago.")
            
        except Exception as e:
            logging.error(f"Error en la tarea de fondo para enviar enlaces de pago: {e}", exc_info=True)
        
        await asyncio.sleep(300) # Wait 5 minutes before the next check

# Configurar el logging para main_api
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
metadata.create_all(bind=engine)

app = FastAPI()

# --- Eventos de Startup y Shutdown de la App ---
@app.on_event("startup")
async def startup():
    await database.connect()
    asyncio.create_task(send_payment_links_for_new_permits())

@app.on_event("shutdown")
async def shutdown():
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

@app.get("/api/stats/total-inscripciones")
async def get_total_inscripciones():
    try:
        inscripciones_df = await get_cached_sheet_data(MAIN_SHEET_ID, MAIN_SHEET_NAME)
        total_count = len(inscripciones_df)
        return {"total_inscripciones": total_count}
    except Exception as e:
        logging.error(f"Error al obtener el total de inscripciones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo calcular el total de inscripciones.")

@app.get("/api/stats/recaudaciones")
async def get_recaudaciones_stats():
    try:
        # 1. Recaudación Total
        query_total = select(func.sum(pagos.c.amount)).where(pagos.c.status == 'approved')
        total_revenue = await database.fetch_val(query_total)

        # 2. Recaudación por Inscripciones
        query_inscripciones = select(func.sum(pagos.c.amount)).where(
            pagos.c.status == 'approved',
            pagos.c.inscription_id.like('fau_inscr%')
        )
        inscripciones_revenue = await database.fetch_val(query_inscripciones)

        return {
            "recaudacion_total": total_revenue or 0,
            "recaudacion_inscripciones": inscripciones_revenue or 0,
        }
    except Exception as e:
        logging.error(f"Error al obtener estadísticas de recaudación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo calcular las estadísticas de recaudación.")

@app.get("/api/inscripciones")
async def get_inscripciones(page: int = 1, limit: int = 10):
    try:
        # 1. Leer datos de la hoja de Google (sigue siendo la fuente de verdad para inscripciones)
        inscripciones_df = await get_cached_sheet_data(MAIN_SHEET_ID, MAIN_SHEET_NAME)
        if 'fecha_creacion' in inscripciones_df.columns:
            inscripciones_df['fecha_creacion'] = pd.to_datetime(inscripciones_df['fecha_creacion'], errors='coerce')
            inscripciones_df = inscripciones_df.sort_values(by='fecha_creacion', ascending=False, na_position='last')
        
        inscripciones_data = inscripciones_df.to_dict(orient="records")

        # 2. Obtener todos los IDs de inscripciones pagadas desde la base de datos
        query = "SELECT inscription_id FROM pagos WHERE status = 'approved'"
        paid_records = await database.fetch_all(query)
        paid_ids = {record['inscription_id'] for record in paid_records}

        # 3. Enriquecer los datos de la hoja con el estado de pago de la base de datos
        for inscripcion in inscripciones_data:
            if inscripcion.get('numero_inscripcion') in paid_ids:
                inscripcion['Estado de Pago'] = 'Pagado'
            else:
                inscripcion['Estado de Pago'] = 'Pendiente'
        
        # 4. Paginación y enriquecimiento con PDFs (como antes)
        total_records = len(inscripciones_data)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_data = inscripciones_data[start_index:end_index]
        
        pdf_list = list_pdfs_in_folder(GOOGLE_DRIVE_FOLDER_ID)
        pdf_link_map = {f"{os.path.splitext(pdf['name'])[0].strip()}.pdf": pdf['link'] for pdf in pdf_list} if pdf_list else {}
        for inscripcion in paginated_data:
            expected_pdf_name = f"{str(inscripcion.get('numero_inscripcion', '')).strip()}.pdf"
            inscripcion['pdf_link'] = pdf_link_map.get(expected_pdf_name)

        return {
            "data": paginated_data, "total_records": total_records, "page": page,
            "limit": limit, "total_pages": (total_records + limit - 1) // limit
        }
    except Exception as e:
        logging.error(f"Error al obtener inscripciones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch inscripciones: {e}")

@app.get("/api/permisos")
async def get_permisos(page: int = 1, limit: int = 10):
    try:
        # 1. Leer datos de la hoja de Google
        permisos_df = await get_cached_sheet_data(PERMISOS_SHEET_ID, PERMISOS_SHEET_NAME)
        if 'Fecha' in permisos_df.columns:
            permisos_df['Fecha'] = pd.to_datetime(permisos_df['Fecha'], errors='coerce')
            permisos_df = permisos_df.sort_values(by='Fecha', ascending=False, na_position='last')
        
        permisos_data = permisos_df.to_dict(orient="records")

        # 2. Obtener todos los IDs de permisos pagados desde la base de datos
        query = "SELECT permiso_id FROM pagos_permisos WHERE status = 'approved'"
        paid_records = await database.fetch_all(query)
        paid_ids = {record['permiso_id'] for record in paid_records}

        # 3. Enriquecer los datos de la hoja con el estado de pago de la base de datos
        for permiso in permisos_data:
            if permiso.get('ID') in paid_ids:
                permiso['Estado de Pago'] = 'Pagado'
            else:
                permiso['Estado de Pago'] = 'Pendiente'
        
        # 4. Paginación y enriquecimiento con PDFs
        total_records = len(permisos_data)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_data = permisos_data[start_index:end_index]
        
        pdf_list = list_pdfs_in_folder(PERMISOS_DRIVE_FOLDER_ID)
        pdf_link_map = {f"{os.path.splitext(pdf['name'])[0].strip()}.pdf": pdf['link'] for pdf in pdf_list} if pdf_list else {}
        for permiso in paginated_data:
            expected_pdf_name = f"{str(permiso.get('ID', '')).strip()}.pdf"
            permiso['pdf_link'] = pdf_link_map.get(expected_pdf_name)

        return {
            "data": paginated_data, "total_records": total_records, "page": page,
            "limit": limit, "total_pages": (total_records + limit - 1) // limit
        }
    except Exception as e:
        logging.error(f"Error al obtener permisos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch permisos: {e}")

@app.post("/api/link-data")
async def link_data():
    # Este endpoint actualmente solo sirve para confirmar que la acción fue "disparada"
    # desde el frontend. La lógica de vinculación de datos ya está en get_inscripciones,
    # y el frontend refresca los datos después de llamar a este endpoint.
    # A futuro, aquí se podría implementar una lógica más compleja si es necesario.
    return {"status": "success", "message": "Data linking process triggered."}

@app.post("/api/send-email")
async def send_email_endpoint(request: SendEmailRequest):
    try:
        send_simple_email(
            to_email=request.to_email,
            subject=request.subject,
            html_content=request.html_content,
            sender_email=SENDER_EMAIL_RESEND
        )
        logging.info(f"Email de prueba enviado a {request.to_email}.")
        return {"status": "success", "message": "Email enviado con éxito."}
    except Exception as e:
        logging.error(f"Error al enviar email de prueba: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {e}")

@app.get("/api/pagos")
async def get_pagos(page: int = 1, limit: int = 10):
    max_limit = 100
    if limit > max_limit:
        limit = max_limit

    try:
        # Fetch payments from 'pagos' table
        query_inscripciones = pagos.select()
        inscripcion_payments = await database.fetch_all(query_inscripciones)
        inscripcion_payments_data = [dict(p) for p in inscripcion_payments]
        for p in inscripcion_payments_data:
            p['type'] = 'Inscripción'

        # Fetch payments from 'pagos_permisos' table
        query_permisos = pagos_permisos.select()
        permiso_payments = await database.fetch_all(query_permisos)
        permiso_payments_data = [dict(p) for p in permiso_payments]
        for p in permiso_payments_data:
            p['type'] = 'Permiso'

        # Combine and sort all payments
        all_payments = inscripcion_payments_data + permiso_payments_data
        
        # Sort by date_created in descending order
        all_payments.sort(key=lambda x: x.get('date_created', datetime.datetime.min), reverse=True)

        # Apply pagination
        total_records = len(all_payments)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paginated_data = all_payments[start_index:end_index]

        return {
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": (total_records + limit - 1) // limit
        }
    except Exception as e:
        logging.error(f"Error al obtener pagos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch payments: {e}")


@app.get("/api/cobros-enviados")
async def get_cobros_enviados(page: int = 1, limit: int = 10):
    max_limit = 100
    if limit > max_limit:
        limit = max_limit

    try:
        offset = (page - 1) * limit
        query = cobros_enviados.select().order_by(cobros_enviados.c.date_sent.desc()).offset(offset).limit(limit)
        fetched_cobros = await database.fetch_all(query)

        total_records_query = select(func.count()).select_from(cobros_enviados)
        total_records = await database.fetch_val(total_records_query)

        cobros_data = [dict(c) for c in fetched_cobros]

        return {
            "data": cobros_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": (total_records + limit - 1) // limit
        }
    except Exception as e:
        logging.error(f"Error al obtener cobros enviados: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch sent payments: {e}")

@app.get("/api/permiso-cobros-enviados")
async def get_permiso_cobros_enviados(page: int = 1, limit: int = 10):
    max_limit = 100
    if limit > max_limit:
        limit = max_limit

    try:
        offset = (page - 1) * limit
        query = permisos_enviados.select().order_by(permisos_enviados.c.date_sent.desc()).offset(offset).limit(limit)
        fetched_cobros = await database.fetch_all(query)

        total_records_query = select(func.count()).select_from(permisos_enviados)
        total_records = await database.fetch_val(total_records_query)

        cobros_data = [dict(c) for c in fetched_cobros]

        return {
            "data": cobros_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": (total_records + limit - 1) // limit
        }
    except Exception as e:
        logging.error(f"Error al obtener cobros de permisos enviados: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch sent permit payments: {e}")


@app.post("/api/send-payment-link")
async def send_payment_link(request: SendPaymentLinkRequest):
    try:
        if not mp_sdk_initialized:
            raise HTTPException(status_code=503, detail="Mercado Pago no está configurado.")
        
        # Obtener el precio dinámicamente según el tipo de establecimiento
        try:
            dynamic_price = get_price_for_establishment(PRICES_SHEET_ID, PRICES_SHEET_NAME, request.tipo_establecimiento)
        except ValueError as ve:
            logging.error(f"Error de validación al obtener precio: {ve}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(ve))

        if dynamic_price <= 0:
            raise ValueError("Precio de pago no válido.")

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
        if not payment_link:
            raise ValueError("No se pudo generar el link de pago desde Mercado Pago.")

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
        
        # Registrar el cobro enviado en la nueva tabla
        log_query = cobros_enviados.insert().values(
            inscription_id=request.inscription_id,
            email=request.email,
            amount=dynamic_price,
            date_sent=datetime.datetime.now(datetime.timezone.utc)
        )
        await database.execute(log_query)
        
        logging.info("Email con enlace de pago enviado.")
        return {"status": "success", "message": "Email con enlace de pago enviado."}
    
    except Exception as e:
        logging.error(f"Error al procesar envío de pago: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar el envío de pago: {e}")

@app.post("/api/send-permiso-payment-link")
async def send_permiso_payment_link(request: SendPermisoPaymentLinkRequest):
    try:
        if not mp_sdk_initialized:
            raise HTTPException(status_code=503, detail="Mercado Pago no está configurado.")
        
        # Obtener el precio dinámicamente según la categoría
        try:
            dynamic_price = get_price_for_categoria(PRICES_SHEET_ID, PRICES_SHEET_NAME, request.categoria)
        except ValueError as ve:
            logging.error(f"Error de validación al obtener precio: {ve}", exc_info=True)
            raise HTTPException(status_code=400, detail=str(ve))

        if dynamic_price <= 0:
            raise ValueError("Precio de pago no válido.")

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
        preference = preference_response["response"]
        payment_link = preference.get("init_point") or preference.get("sandbox_init_point")
        if not payment_link:
            raise ValueError("No se pudo generar el link de pago desde Mercado Pago.")

        email_subject = f"Enlace de pago para Permiso de Caza - {request.nombre_apellido}"
        email_html = f"""
            <h1>Hola {request.nombre_apellido},</h1>
            <p>Aquí tienes tu enlace para abonar el permiso de caza.</p>
            <p><strong>Monto:</strong> ${dynamic_price}</p>
            <a href="{payment_link}" target="_blank" style="padding: 15px; background-color: #009ee3; color: white; text-decoration: none; border-radius: 5px;">Pagar Ahora</a>
        """
        
        send_simple_email(
            to_email=request.email, subject=email_subject,
            html_content=email_html, sender_email=SENDER_EMAIL_RESEND
        )
        
        # Registrar el cobro enviado en la nueva tabla
        log_query = cobros_enviados.insert().values(
            inscription_id=request.permiso_id,
            email=request.email,
            amount=dynamic_price,
            date_sent=datetime.datetime.now(datetime.timezone.utc)
        )
        await database.execute(log_query)
        
        logging.info("Email con enlace de pago de permiso enviado.")
        return {"status": "success", "message": "Email con enlace de pago de permiso enviado."}
    
    except Exception as e:
        logging.error(f"Error al procesar envío de pago de permiso: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al procesar el envío de pago de permiso: {e}")

@app.post("/api/send-permiso-email")
async def send_permiso_email(request: SendPermisoEmailRequest):
    try:
        pdf_list = list_pdfs_in_folder(PERMISOS_DRIVE_FOLDER_ID)
        pdf_file = next((pdf for pdf in pdf_list if pdf['name'].startswith(request.permiso_id)), None)

        if not pdf_file:
            raise HTTPException(status_code=404, detail="PDF no encontrado para el permiso ID.")

        pdf_content = download_file(pdf_file['id'])
        if not pdf_content:
            raise HTTPException(status_code=500, detail="Error al descargar el PDF de Google Drive.")

        email_subject = f"Tu Permiso de Caza 2026 - {request.nombre_apellido}"
        email_html = f"""
            <h1>Hola {request.nombre_apellido},</h1>
            <p>Adjunto encontrarás tu permiso de caza para la temporada 2026.</p>
            <p>¡Buena caza!</p>
        """
        
        send_email_with_attachment(
            to_email=request.email,
            subject=email_subject,
            html_content=email_html,
            sender_email=SENDER_EMAIL_RESEND,
            attachment_content=base64.b64encode(pdf_content).decode('utf-8'),
            attachment_filename=pdf_file['name']
        )
        
        # Registrar el envío en la base de datos
        log_query = permisos_enviados.insert().values(
            permiso_id=request.permiso_id,
            email=request.email,
            date_sent=datetime.datetime.now(datetime.timezone.utc)
        )
        await database.execute(log_query)
        
        logging.info(f"Permiso enviado a {request.email}.")
        return {"status": "success", "message": "Permiso enviado con éxito."}
    
    except Exception as e:
        logging.error(f"Error al enviar el permiso: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al enviar el permiso: {e}")


@app.post("/api/send-credential")
async def send_credential(request: SendCredentialRequest):
    try:
        email_subject = f"Credencial de Caza 2026 para {request.nombre_establecimiento}"
        
        # Obtener la fecha actual y formatearla
        current_date = datetime.datetime.now().strftime("%d/%m/%Y")

        email_html = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>CREDENCIAL DE CAZA 2026 - Inscripción de Establecimientos</h2>
                <p><strong>Número de inscripción:</strong> {request.numero_inscripcion}</p>
                <p>Se otorga la presente credencial a:</p>
                <p><strong>Establecimiento:</strong> {request.nombre_establecimiento}</p>
                <p><strong>Razón Social:</strong> {request.razon_social}</p>
                <p><strong>CUIT:</strong> {request.cuit}</p>
                <p>Esta credencial autoriza la actividad de caza en <strong>{request.tipo_establecimiento}</strong> para la temporada 2026.</p>
                <p><strong>Fecha de Emisión:</strong> {current_date}</p>
                <br>
                <p>Atentamente,</p>
                <p><strong>Dirección de Fauna de la Provincia de Neuquén.</strong></p>
            </div>
        """
        
        send_simple_email(
            to_email=request.email,
            subject=email_subject,
            html_content=email_html,
            sender_email=SENDER_EMAIL_RESEND
        )
        
        logging.info(f"Credencial enviada a {request.email} para el establecimiento {request.nombre_establecimiento}.")
        return {"status": "success", "message": "Credencial enviada con éxito."}

    except Exception as e:
        logging.error(f"Error al enviar la credencial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al enviar la credencial: {e}")

@app.get("/api/view-credential/{numero_inscripcion}", response_class=HTMLResponse)
async def view_credential(numero_inscripcion: str):
    try:
        inscripciones_df = await get_cached_sheet_data(MAIN_SHEET_ID, MAIN_SHEET_NAME)
        
        # Asegurarse de que la columna 'numero_inscripcion' sea de tipo string para la comparación
        inscripciones_df['numero_inscripcion'] = inscripciones_df['numero_inscripcion'].astype(str)
        
        # Buscar la inscripción por su número
        inscripcion_row = inscripciones_df[inscripciones_df['numero_inscripcion'] == numero_inscripcion]
        
        if inscripcion_row.empty:
            raise HTTPException(status_code=404, detail="Inscripción no encontrada.")
            
        inscripcion = inscripcion_row.iloc[0]
        
        current_date = datetime.datetime.now().strftime("%d/%m/%Y")

        html_content = f"""
            <html>
                <head>
                    <title>Credencial de Caza 2026 - {inscripcion.get('nombre_establecimiento', '')}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
                        h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
                        strong {{ color: #333; }}
                    </style>
                </head>
                <body>
                    <h2>CREDENCIAL DE CAZA 2026 - Inscripción de Establecimientos</h2>
                    <p><strong>Número de inscripción:</strong> {inscripcion.get('numero_inscripcion', 'N/A')}</p>
                    <p>Se otorga la presente credencial a:</p>
                    <p><strong>Establecimiento:</strong> {inscripcion.get('nombre_establecimiento', 'N/A')}</p>
                    <p><strong>Razón Social:</strong> {inscripcion.get('razon_social', 'N/A')}</p>
                    <p><strong>CUIT:</strong> {inscripcion.get('cuit', 'N/A')}</p>
                    <p>Esta credencial autoriza la actividad de caza en <strong>{inscripcion.get('su establecimiento es', 'N/A')}</strong> para la temporada 2026.</p>
                    <p><strong>Fecha de Emisión:</strong> {current_date}</p>
                    <br>
                    <p>Atentamente,</p>
                    <p><strong>Dirección de Fauna de la Provincia de Neuquén.</strong></p>
                </body>
            </html>
        """
        return HTMLResponse(content=html_content)

    except Exception as e:
        logging.error(f"Error al generar la vista de la credencial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar la vista de la credencial: {e}")


@app.post("/api/mercadopago-webhook")
async def mercadopago_webhook(request: Request):
    # Lógica de parseo robusta
    query_params = request.query_params
    topic = query_params.get("topic") or query_params.get("type")
    payment_id = query_params.get("data.id") or query_params.get("id")
    if not topic or not payment_id:
        try:
            body = await request.json()
            topic = body.get("topic") or body.get("type")
            payment_id = body.get("data", {}).get("id")
        except Exception:
            pass

    if topic == "payment" and payment_id:
        logging.info(f"Notificación de pago recibida para ID: {payment_id}")
        try:
            if not mp_sdk_initialized:
                raise Exception("Webhook recibido pero Mercado Pago SDK no está inicializado.")

            payment_info = mp_sdk.payment().get(payment_id)
            payment = payment_info.get("response")

            if payment:
                # --- NUEVA LÓGICA: Guardar en PostgreSQL ---
                date_str = payment.get('date_created')
                if date_str:
                    parsed_date = parser.isoparse(date_str)
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                else:
                    parsed_date = datetime.datetime.now(datetime.timezone.utc)

                external_reference = payment.get('external_reference')
                
                if external_reference and external_reference.startswith('fau_inscr'):
                    values = {
                        "payment_id": payment.get('id'),
                        "inscription_id": external_reference,
                        "status": payment.get('status'),
                        "status_detail": payment.get('status_detail'),
                        "amount": payment.get('transaction_amount'),
                        "email": payment.get('payer', {}).get('email'),
                        "date_created": parsed_date
                    }
                    insert_stmt = insert(pagos).values(values)
                    update_stmt = insert_stmt.on_conflict_do_update(
                        index_elements=['payment_id'],
                        set_=dict(status=values['status'], status_detail=values['status_detail'])
                    )
                    await database.execute(update_stmt)
                    logging.info(f"Pago de inscripción ID {payment_id} guardado/actualizado en la base de datos.")
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
                    logging.info(f"Pago de permiso ID {payment_id} guardado/actualizado en la base de datos.")

        except Exception as e:
            logging.error(f"Error al procesar el webhook de Mercado Pago: {e}", exc_info=True)
            return {"status": "error", "message": "Internal server error"}
            
    return {"status": "notification received"}
