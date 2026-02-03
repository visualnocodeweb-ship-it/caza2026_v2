from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import datetime
import pandas as pd # Import pandas for DataFrame handling if needed
import json # Import json for json.dumps
import mercadopago # Import Mercado Pago SDK
from pydantic import BaseModel # Import BaseModel for Pydantic models

# Import your existing service files
from .sheets_services import read_sheet_data, append_sheet_data, update_payment_status, get_sheets_service, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME
from .drive_services import list_pdfs_in_folder, GOOGLE_DRIVE_FOLDER_ID
from .email_services import send_simple_email # Importa la función de envío de correos


# Load environment variables (important for GOOGLE_SHEET_ID, etc.)
load_dotenv(encoding='latin-1') # Ensure encoding is set as before

# Define API specific Sheet IDs and Names
# Assuming GOOGLE_SHEET_ID is the main sheet
MAIN_SHEET_ID = GOOGLE_SHEET_ID
MAIN_SHEET_NAME = GOOGLE_SHEET_NAME
PRICES_SHEET_ID = os.getenv("PRICES_SHEET_ID", GOOGLE_SHEET_ID) # Use main ID or specific
PRICES_SHEET_NAME = os.getenv("PRICES_SHEET_NAME", "precios") # Default to "precios"

# Mercado Pago configuration
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
mp_sdk = None
mp_sdk_initialized = False

if MERCADOPAGO_ACCESS_TOKEN:
    try:
        mp_sdk = mercadopago.SDK(MERCADOPAGO_ACCESS_TOKEN)
        mp_sdk_initialized = True
        print("INFO: Mercado Pago SDK inicializado exitosamente.")
    except Exception as e:
        print(f"ERROR: Fallo al inicializar Mercado Pago SDK: {e}")
else:
    print("WARNING: MERCADOPAGO_ACCESS_TOKEN no configurado. La funcionalidad de Mercado Pago estará deshabilitada.")

# Payments Log Sheet Configuration
PAGOS_SHEET_ID = os.getenv("PAGOS_SHEET_ID")
PAGOS_SHEET_NAME = os.getenv("PAGOS_SHEET_NAME", "pagos")


SENDER_EMAIL_RESEND = os.getenv("SENDER_EMAIL_RESEND")
if not SENDER_EMAIL_RESEND:
    raise ValueError("SENDER_EMAIL_RESEND environment variable not set.")

app = FastAPI()

# --- Pydantic Models ---
class EmailRequest(BaseModel):
    to_email: str
    subject: str
    html_content: str

class PaymentRequest(BaseModel):
    inscription_id: str
    email: str
    item_title: str
    nombre_establecimiento: str

class SendPaymentLinkRequest(BaseModel):
    inscription_id: str
    email: str
    nombre_establecimiento: str

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://caza2026-frontend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Caching Mechanisms ---
_cached_sheet_data = None
_cache_timestamp = None
CACHE_DURATION_SECONDS = 300

def _get_sheet_data_cached():
    global _cached_sheet_data, _cache_timestamp
    current_time = datetime.datetime.now()
    if _cached_sheet_data and _cache_timestamp and (current_time - _cache_timestamp).total_seconds() < CACHE_DURATION_SECONDS:
        return _cached_sheet_data
    df = read_sheet_data(MAIN_SHEET_ID, MAIN_SHEET_NAME)
    if not df.empty and 'fecha_creacion' in df.columns:
        df['fecha_creacion'] = pd.to_datetime(df['fecha_creacion'], errors='coerce')
        df = df.sort_values(by='fecha_creacion', ascending=False, na_position='last')
    _cached_sheet_data = df.to_dict(orient="records")
    _cache_timestamp = current_time
    return _cached_sheet_data

_cached_price = None
_price_cache_timestamp = None
PRICE_CACHE_DURATION_SECONDS = 3600

def _get_fixed_price_cached():
    global _cached_price, _price_cache_timestamp
    current_time = datetime.datetime.now()
    if _cached_price and _price_cache_timestamp and (current_time - _price_cache_timestamp).total_seconds() < PRICE_CACHE_DURATION_SECONDS:
        return _cached_price
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(spreadsheetId=PRICES_SHEET_ID, range=f"'{PRICES_SHEET_NAME}'!B2").execute()
        price = float(result.get('values', [['0']])[0][0])
        _cached_price = price
        _price_cache_timestamp = current_time
        return price
    except Exception as e:
        print(f"Error al leer el precio de la hoja '{PRICES_SHEET_NAME}' celda B2: {e}")
        return 0.0

# --- API Endpoints ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Caza 2026 API"}

@app.post("/api/send-email")
async def send_email_endpoint(email_request: EmailRequest):
    try:
        success = send_simple_email(
            to_email=email_request.to_email,
            subject=email_request.subject,
            html_content=email_request.html_content,
            sender_email=SENDER_EMAIL_RESEND
        )
        if success:
            return {"status": "success", "message": "Email enviado exitosamente."}
        else:
            raise HTTPException(status_code=500, detail="Fallo al enviar el email.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar email: {str(e)}")

@app.get("/api/inscripciones")
async def get_inscripciones(page: int = 1, limit: int = 10):
    try:
        inscripciones_data = _get_sheet_data_cached()
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
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": (total_records + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch inscripciones: {str(e)}")

@app.post("/api/link-data")
async def link_data():
    global _cached_sheet_data, _cache_timestamp
    _cached_sheet_data = None
    _cache_timestamp = None
    return {"status": "success", "message": "Cache invalidado."}

async def internal_create_payment_preference(payment_request: PaymentRequest):
    if not mp_sdk_initialized:
        raise HTTPException(status_code=503, detail="Mercado Pago no está configurado.")
    
    fixed_price = _get_fixed_price_cached()
    if fixed_price <= 0:
        raise ValueError("Precio de pago no válido.")

    preference_data = {
        "items": [{"title": payment_request.item_title, "quantity": 1, "unit_price": fixed_price}],
        "payer": {"email": payment_request.email},
        "external_reference": payment_request.inscription_id,
        "back_urls": {
            "success": "https://caza2026-frontend.onrender.com/inscripciones",
            "failure": "https://caza2026-frontend.onrender.com/inscripciones",
            "pending": "https://caza2026-frontend.onrender.com/inscripciones"
        },
        "notification_url": "https://caza2026-1.onrender.com/api/mercadopago-webhook",
    }
    
    print(f"DEBUG: Enviando datos de preferencia a Mercado Pago: {preference_data}")
    preference_response = mp_sdk.preference().create(preference_data)
    print(f"DEBUG: Respuesta de la preferencia de Mercado Pago: {preference_response}")

    if not preference_response or "response" not in preference_response:
        raise ValueError("Respuesta inválida de Mercado Pago al crear la preferencia.")

    preference = preference_response["response"]
    payment_link = preference.get("init_point") or preference.get("sandbox_init_point")

    if not payment_link:
        print(f"ERROR: No se pudo obtener 'init_point' o 'sandbox_init_point' de la respuesta: {preference}")
        raise ValueError("No se pudo generar el link de pago desde Mercado Pago.")

    return payment_link

@app.post("/api/send-payment-link")
async def send_payment_link(request: SendPaymentLinkRequest):
    try:
        item_title = f"Cuota Anual Caza 2026 - {request.nombre_establecimiento}"
        payment_request = PaymentRequest(
            inscription_id=request.inscription_id,
            email=request.email,
            item_title=item_title,
            nombre_establecimiento=request.nombre_establecimiento
        )
        payment_link = await internal_create_payment_preference(payment_request)
        
        email_subject = f"Enlace de pago para {request.nombre_establecimiento}"
        email_html = f"""
            <h1>Hola {request.nombre_establecimiento},</h1>
            <p>Gracias por ser parte de Caza 2026. Aquí tienes tu enlace para abonar la cuota anual.</p>
            <p><strong>Monto:</strong> ${_get_fixed_price_cached()}</p>
            <a href="{payment_link}" target="_blank" style="padding: 15px; background-color: #009ee3; color: white; text-decoration: none; border-radius: 5px;">
                Pagar Ahora
            </a>
            <p>Si tienes alguna consulta, no dudes en contactarnos.</p>
        """
        
        success = send_simple_email(
            to_email=request.email,
            subject=email_subject,
            html_content=email_html,
            sender_email=SENDER_EMAIL_RESEND
        )
        
        if success:
            return {"status": "success", "message": "Email con enlace de pago enviado exitosamente."}
        else:
            raise HTTPException(status_code=500, detail="Fallo al enviar el email de pago.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el envío de pago: {str(e)}")

@app.post("/api/mercadopago-webhook")
async def mercadopago_webhook(request: Request):
    # --- Diagnóstico Agresivo ---
    print("--- INICIO DE NOTIFICACIÓN WEBHOOK ---")
    print(f"URL de la solicitud: {request.url}")
    print(f"Parámetros de la URL (Query Params): {request.query_params}")
    try:
        body = await request.json()
        print(f"Cuerpo de la solicitud (JSON Body): {body}")
    except Exception:
        body_raw = await request.body()
        print(f"Cuerpo de la solicitud (Raw, no es JSON): {body_raw}")
        body = {} # Evitar errores si el cuerpo no es JSON
    print("--- FIN DE DIAGNÓSTICO ---")
    # --- Fin Diagnóstico ---

    query_params = request.query_params
    
    # Intenta obtener datos de los parámetros de la URL primero (formato más común)
    topic = query_params.get("topic") or query_params.get("type")
    payment_id = query_params.get("data.id") or query_params.get("id")

    # Si no están en la URL, intenta obtenerlos del cuerpo JSON que ya leímos
    if not topic or not payment_id:
        topic = body.get("topic") or body.get("type")
        payment_id = body.get("data", {}).get("id")

    if topic == "payment" and payment_id:
        print(f"INFO: Notificación de pago recibida para ID: {payment_id} (Tópico: {topic})")
        try:
            if not mp_sdk_initialized:
                print("ERROR: Webhook recibido pero Mercado Pago SDK no está inicializado.")
                return {"status": "error", "message": "MP SDK not initialized"}

            payment_info = mp_sdk.payment().get(payment_id)
            payment = payment_info.get("response")

            if payment:
                # Log every payment attempt to the 'pagos' sheet
                try:
                    log_entry = [
                        payment.get('date_created', datetime.datetime.now().isoformat()),
                        payment.get('id'),
                        payment.get('external_reference'),
                        payment.get('payer', {}).get('email'),
                        payment.get('transaction_amount'),
                        payment.get('status'),
                        payment.get('status_detail')
                    ]
                    append_sheet_data(PAGOS_SHEET_ID, PAGOS_SHEET_NAME, [log_entry])
                    print(f"INFO: Intento de pago ID {payment_id} registrado en la hoja 'pagos'.")
                except Exception as log_e:
                    print(f"ERROR: No se pudo registrar el intento de pago en la hoja 'pagos': {log_e}")

                # If approved, also update the main sheet status
                if payment.get("status") == "approved":
                    inscription_id = payment.get("external_reference")
                    if inscription_id:
                        print(f"INFO: Pago aprobado para inscripción ID: {inscription_id}. Actualizando hoja de cálculo.")
                        update_payment_status(
                            sheet_id=MAIN_SHEET_ID,
                            sheet_name=MAIN_SHEET_NAME,
                            inscription_id=inscription_id,
                            new_status="Pagado"
                        )
                        # Forzar la invalidación del caché después de una actualización
                        global _cached_sheet_data, _cache_timestamp
                        _cached_sheet_data = None
                        _cache_timestamp = None
                        print(f"INFO: Caché invalidado por actualización de pago.")
                    else:
                        print("WARNING: Pago aprobado pero sin 'external_reference'. No se puede actualizar la hoja.")
                else:
                    print(f"INFO: Estado del pago no aprobado: {payment.get('status')}")
            else:
                 print(f"WARNING: No se pudo obtener información detallada para el ID de pago: {payment_id}")

        except Exception as e:
            print(f"ERROR: Error al procesar el webhook de Mercado Pago: {e}")
            return {"status": "error", "message": "Internal server error"}
            
    return {"status": "notification received"}

# Endpoints de prueba y simulación (si se mantienen)
@app.get("/api/pdfs")
async def get_pdfs():
    # ... (código existente)
    pass

@app.post("/api/simulate-payment")
async def simulate_payment(payment_request: PaymentRequest):
    # ... (código existente)
    pass