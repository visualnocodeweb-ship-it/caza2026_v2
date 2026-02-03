from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import datetime
import pandas as pd
import mercadopago
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from dateutil import parser # Importar el parser de fechas

# --- Nuevas importaciones de base de datos ---
from .database import database, engine, metadata
from .models import pagos

# --- Importaciones de servicios existentes ---
from .sheets_services import read_sheet_data, get_sheets_service, GOOGLE_SHEET_ID, GOOGLE_SHEET_NAME
from .drive_services import list_pdfs_in_folder, GOOGLE_DRIVE_FOLDER_ID
from .email_services import send_simple_email

# --- Configuración ---
load_dotenv(encoding='latin-1')

MAIN_SHEET_ID = GOOGLE_SHEET_ID
MAIN_SHEET_NAME = GOOGLE_SHEET_NAME
PRICES_SHEET_ID = os.getenv("PRICES_SHEET_ID", GOOGLE_SHEET_ID)
PRICES_SHEET_NAME = os.getenv("PRICES_SHEET_NAME", "precios")
SENDER_EMAIL_RESEND = os.getenv("SENDER_EMAIL_RESEND")
if not SENDER_EMAIL_RESEND:
    raise ValueError("SENDER_EMAIL_RESEND environment variable not set.")

# Configuración de Mercado Pago
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
    print("WARNING: MERCADOPAGO_ACCESS_TOKEN no configurado.")

# --- Creación de la tabla de la base de datos ---
metadata.create_all(bind=engine)

app = FastAPI()

# --- Eventos de Startup y Shutdown de la App ---
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# --- Pydantic Models ---
class SendPaymentLinkRequest(BaseModel):
    inscription_id: str
    email: str
    nombre_establecimiento: str

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

@app.get("/api/inscripciones")
async def get_inscripciones(page: int = 1, limit: int = 10):
    try:
        # 1. Leer datos de la hoja de Google (sigue siendo la fuente de verdad para inscripciones)
        inscripciones_df = read_sheet_data(MAIN_SHEET_ID, MAIN_SHEET_NAME)
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
        print(f"ERROR al obtener inscripciones: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch inscripciones: {e}")

@app.post("/api/send-payment-link")
async def send_payment_link(request: SendPaymentLinkRequest):
    # (Esta función no necesita cambios, ya que su lógica interna sigue siendo válida)
    try:
        # Código existente para crear preferencia y enviar email
        if not mp_sdk_initialized:
            raise HTTPException(status_code=503, detail="Mercado Pago no está configurado.")
    
        fixed_price = get_sheets_service().spreadsheets().values().get(spreadsheetId=PRICES_SHEET_ID, range=f"'{PRICES_SHEET_NAME}'!B2").execute().get('values', [['0']])[0][0]
        fixed_price = float(fixed_price)
        if fixed_price <= 0:
            raise ValueError("Precio de pago no válido.")

        preference_data = {
            "items": [{"title": f"Cuota Anual Caza 2026 - {request.nombre_establecimiento}", "quantity": 1, "unit_price": fixed_price}],
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
            <p><strong>Monto:</strong> ${fixed_price}</p>
            <a href="{payment_link}" target="_blank" style="padding: 15px; background-color: #009ee3; color: white; text-decoration: none; border-radius: 5px;">Pagar Ahora</a>
        """
        
        send_simple_email(
            to_email=request.email, subject=email_subject,
            html_content=email_html, sender_email=SENDER_EMAIL_RESEND
        )
        return {"status": "success", "message": "Email con enlace de pago enviado."}
    
    except Exception as e:
        print(f"ERROR al procesar envío de pago: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el envío de pago: {e}")

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
        print(f"INFO: Notificación de pago recibida para ID: {payment_id}")
        try:
            if not mp_sdk_initialized:
                raise Exception("Webhook recibido pero Mercado Pago SDK no está inicializado.")

            payment_info = mp_sdk.payment().get(payment_id)
            payment = payment_info.get("response")

            if payment:
                # --- NUEVA LÓGICA: Guardar en PostgreSQL ---
                date_str = payment.get('date_created')
                # Asegurar que la fecha sea siempre timezone-aware (consciente de la zona horaria)
                if date_str:
                    parsed_date = parser.isoparse(date_str)
                    # Si la fecha parseada es "naive" (sin zona horaria), se asume que es UTC.
                    if parsed_date.tzinfo is None:
                        parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                else:
                    # Si no hay fecha, usar la hora actual en UTC.
                    parsed_date = datetime.datetime.now(datetime.timezone.utc)

                values = {
                    "payment_id": payment.get('id'),
                    "inscription_id": payment.get('external_reference'),
                    "status": payment.get('status'),
                    "status_detail": payment.get('status_detail'),
                    "amount": payment.get('transaction_amount'),
                    "email": payment.get('payer', {}).get('email'),
                    "date_created": parsed_date
                }
                
                # 'Upsert': Inserta una nueva fila. Si ya existe un pago con el mismo payment_id,
                # actualiza los campos 'status' y 'status_detail'.
                insert_stmt = insert(pagos).values(values)
                update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['payment_id'],
                    set_=dict(status=values['status'], status_detail=values['status_detail'])
                )
                await database.execute(update_stmt)
                print(f"INFO: Pago ID {payment_id} guardado/actualizado en la base de datos.")

        except Exception as e:
            print(f"ERROR: Error al procesar el webhook de Mercado Pago: {e}")
            return {"status": "error", "message": "Internal server error"}
            
    return {"status": "notification received"}