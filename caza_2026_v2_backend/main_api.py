import logging
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import datetime
import pandas as pd # Import pandas for data manipulation
from sqlalchemy import select, func, desc
from .database import database, engine, metadata
from .models import logs, pagos, pagos_permisos, cobros_enviados, permisos_enviados, sent_items
from . import sheets_services, email_services, drive_services, mercadopago_services # Importar los servicios
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
    date_sent: Optional[datetime.datetime] = None  # Opcional, se genera en el servidor si no se proporciona

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

# --- No-Cache Middleware for API ---
@app.middleware("http")
async def add_no_cache_header(request, call_next):
    # Log ALL requests to see what is hitting the server
    print(f"DEBUG MIDDLEWARE: Incoming request: {request.method} {request.url.path}", flush=True)
    
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# --- Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok"}

print("DEBUG: Registering /api/inscripciones route")
@app.get("/api/inscripciones", response_model=Dict[str, Any])
async def get_inscripciones(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    print(f"DEBUG: Executing get_inscripciones page={page} limit={limit}")
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
        
        # Invertir el DataFrame para que los registros más nuevos (abajo en la hoja) aparezcan primero
        if not df.empty:
            df = df.iloc[::-1]
        
        if df.empty:
            return {"data": [], "total_records": 0, "page": page, "limit": limit, "total_pages": 0}

        total_records = len(df)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0

        # Aplicar paginación al DataFrame
        paginated_data = df.iloc[offset : offset + limit].to_dict(orient="records")

        # Buscar PDFs de inscripciones
        inscripciones_folder_id = "1a1VEA7I5N5sMvqLQWuoDpQ3WSiayQbK9"
        pdfs = drive_services.list_pdfs_in_folder(inscripciones_folder_id)
        await log_activity('INFO', 'pdfs_found', f"PDFs de inscripciones encontrados: {len(pdfs)}")
        pdf_dict = {pdf['name'].replace('.pdf', ''): pdf.get('webViewLink', '') for pdf in pdfs if 'name' in pdf}

        # Enriquecer con estado de pago desde la base de datos
        for inscripcion in paginated_data:
            numero_inscripcion = inscripcion.get('numero_inscripcion')

            # Asociar PDF
            if numero_inscripcion and numero_inscripcion in pdf_dict:
                inscripcion['pdf_link'] = pdf_dict[numero_inscripcion]

            if numero_inscripcion:
                # Buscar si hay un pago aprobado en la base de datos
                pago_query = select(pagos).where(
                    pagos.c.inscription_id == numero_inscripcion,
                    pagos.c.status == 'approved'
                )
                pago_result = await database.fetch_one(pago_query)

                if pago_result:
                    inscripcion['Estado de Pago'] = 'Pagado'
                    inscripcion['payment_id'] = pago_result['payment_id']
                    inscripcion['fecha_pago'] = pago_result['date_created'].isoformat() if pago_result['date_created'] else None
                else:
                    # Verificar si existe algún pago (aunque no esté aprobado)
                    any_pago_query = select(pagos).where(pagos.c.inscription_id == numero_inscripcion)
                    any_pago = await database.fetch_one(any_pago_query)

                    if any_pago:
                        inscripcion['Estado de Pago'] = any_pago['status'].capitalize()
                    else:
                        inscripcion['Estado de Pago'] = 'Pendiente'

            # Enriquecer con estados de envío desde sent_items
            if numero_inscripcion:
                sent_query = select(sent_items.c.sent_type).where(
                    sent_items.c.item_id == numero_inscripcion,
                    sent_items.c.item_type == 'inscripcion'
                )
                sent_results = await database.fetch_all(sent_query)
                inscripcion['sent_statuses'] = list(set([r['sent_type'] for r in sent_results]))
            else:
                inscripcion['sent_statuses'] = []


        return {
            "data": paginated_data,
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    except Exception as e:
        await log_activity('ERROR', 'get_inscripciones_failed', f"Error al obtener inscripciones: {e}")
        # print(f"DEBUG EXCEPTION: {e}") # Uncomment if needed
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener inscripciones: {e}")

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

@app.post("/api/link-data", response_model=Dict[str, Any])
async def link_data_endpoint():
    """
    Sincroniza datos entre la base de datos, Google Sheets y Mercado Pago.
    
    Realiza las siguientes acciones:
    1. Lee inscripciones desde Google Sheets
    2. Consulta estados de pago desde la base de datos
    3. Actualiza Google Sheets con los estados de pago actualizados
    4. Devuelve un resumen de las actualizaciones realizadas
    """
    await log_activity('INFO', 'link_data_request', 'Iniciando vinculación de datos.')
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        inscripciones_tab_name = "inscrip"
        
        print(f"DEBUG link-data: sheet_id={sheet_id}, tab={inscripciones_tab_name}", flush=True)
        
        if not sheet_id:
            error_msg = "GOOGLE_SHEET_ID no configurado"
            print(f"ERROR link-data: {error_msg}", flush=True)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 1. Leer inscripciones desde Google Sheets
        print("DEBUG link-data: Llamando a sheets_services.read_sheet...", flush=True)
        inscripciones_data = sheets_services.read_sheet(sheet_id, inscripciones_tab_name)
        print(f"DEBUG link-data: Leídas {len(inscripciones_data) if inscripciones_data else 0} filas", flush=True)
        
        if not inscripciones_data or len(inscripciones_data) < 2:
            msg = "No hay inscripciones para vincular."
            print(f"DEBUG link-data: {msg}", flush=True)
            return {"message": msg, "updated_count": 0, "total_checked": 0}
        
        headers = inscripciones_data[0]
        rows = inscripciones_data[1:]
        print(f"DEBUG link-data: Headers={headers[:5]}...", flush=True)
        
        # Encontrar índice de columnas importantes
        try:
            numero_inscripcion_idx = headers.index('numero_inscripcion')
            estado_pago_idx = headers.index('Estado de Pago') if 'Estado de Pago' in headers else None
            print(f"DEBUG link-data: numero_inscripcion_idx={numero_inscripcion_idx}, estado_pago_idx={estado_pago_idx}", flush=True)
        except ValueError as e:
            error_msg = f"Columna requerida no encontrada: {e}"
            print(f"ERROR link-data: {error_msg}", flush=True)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # 2. Sincronizar con base de datos
        updated_count = 0
        updates_to_write = []
        
        print(f"DEBUG link-data: Procesando {len(rows)} filas...", flush=True)
        
        for row_idx, row in enumerate(rows, start=2):  # start=2 porque la fila 1 son headers
            if len(row) <= numero_inscripcion_idx:
                continue
                
            numero_inscripcion = row[numero_inscripcion_idx]
            if not numero_inscripcion:
                continue
            
            # Consultar estado de pago en la base de datos
            pago_query = select(pagos).where(
                (pagos.c.inscription_id == numero_inscripcion) & 
                (pagos.c.status == 'approved')
            ).order_by(desc(pagos.c.date_created))
            
            pago_result = await database.fetch_one(pago_query)
            
            # Determinar nuevo estado
            if pago_result:
                nuevo_estado = "Pagado"
            else:
                # Verificar si existe algún pago (aunque no esté aprobado)
                any_pago_query = select(pagos).where(pagos.c.inscription_id == numero_inscripcion)
                any_pago = await database.fetch_one(any_pago_query)
                nuevo_estado = any_pago['status'].capitalize() if any_pago else "Pendiente"
            
            # Verificar si necesita actualización
            estado_actual = row[estado_pago_idx] if estado_pago_idx is not None and len(row) > estado_pago_idx else ""
            
            if estado_actual != nuevo_estado:
                # Preparar actualización
                if estado_pago_idx is not None:
                    updates_to_write.append({
                        'row': row_idx,
                        'col': estado_pago_idx + 1,  # +1 porque Sheets usa índice 1-based
                        'value': nuevo_estado,
                        'inscripcion_id': numero_inscripcion
                    })
                    updated_count += 1
        
        print(f"DEBUG link-data: {updated_count} actualizaciones preparadas", flush=True)
        
        # 3. Escribir actualizaciones a Google Sheets
        if updates_to_write:
            print(f"DEBUG link-data: Escribiendo {len(updates_to_write)} actualizaciones...", flush=True)
            for update in updates_to_write:
                try:
                    col_letter = chr(64 + update['col'])  # 64 + 1 = 65 = 'A'
                    cell_range = f"{inscripciones_tab_name}!{col_letter}{update['row']}"
                    print(f"DEBUG link-data: Actualizando {cell_range} = {update['value']}", flush=True)
                    sheets_services.update_cell(sheet_id, cell_range, [[update['value']]])
                except Exception as update_error:
                    print(f"ERROR link-data: Fallo al actualizar {update.get('inscripcion_id')}: {update_error}", flush=True)
                    # Continuar con las demás actualizaciones
        
        await log_activity('INFO', 'link_data_success', f'Vinculación completada. {updated_count} registros actualizados.')
        
        result = {
            "message": f"Datos vinculados exitosamente. {updated_count} registros actualizados.",
            "updated_count": updated_count,
            "total_checked": len(rows)
        }
        print(f"DEBUG link-data: Resultado={result}", flush=True)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error al vincular datos: {str(e)}"
        print(f"ERROR link-data EXCEPTION: {error_msg}", flush=True)
        import traceback
        traceback.print_exc()
        await log_activity('ERROR', 'link_data_failed', error_msg)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)


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
        
        sheets_services.append_sheet_data(sheet_id, inscripciones_tab_name, values_to_append)
        
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

        # Invertir el DataFrame para que los registros más nuevos (abajo en la hoja) aparezcan primero
        if not df.empty:
            df = df.iloc[::-1]
        
        if df.empty:
            return {"data": [], "total_records": 0, "page": page, "limit": limit, "total_pages": 0}

        total_records = len(df)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0

        paginated_data = df.iloc[offset : offset + limit].to_dict(orient="records")

        # Buscar PDFs de permisos
        permisos_folder_id = "1ZynwbJewIsSodT8ogIm2AXanL2Am0IUt"
        pdfs = drive_services.list_pdfs_in_folder(permisos_folder_id)
        await log_activity('INFO', 'pdfs_found', f"PDFs de permisos: {[pdf.get('name', 'SIN_NOMBRE') for pdf in pdfs[:3]]}")
        pdf_dict = {pdf['name'].replace('.pdf', ''): pdf.get('webViewLink', '') for pdf in pdfs if 'name' in pdf}

        # Enriquecer con estado de pago desde la base de datos
        for permiso in paginated_data:
            permiso_id = permiso.get('ID')

            # Asociar PDF
            if permiso_id and permiso_id in pdf_dict:
                permiso['pdf_link'] = pdf_dict[permiso_id]

            if permiso_id:
                # Buscar si hay un pago aprobado en la base de datos
                pago_query = select(pagos_permisos).where(
                    pagos_permisos.c.permiso_id == permiso_id,
                    pagos_permisos.c.status == 'approved'
                )
                pago_result = await database.fetch_one(pago_query)

                if pago_result:
                    permiso['Estado de Pago'] = 'Pagado'
                    permiso['payment_id'] = pago_result['payment_id']
                    permiso['fecha_pago'] = pago_result['date_created'].isoformat() if pago_result['date_created'] else None
                else:
                    # Verificar si existe algún pago (aunque no esté aprobado)
                    any_pago_query = select(pagos_permisos).where(pagos_permisos.c.permiso_id == permiso_id)
                    any_pago = await database.fetch_one(any_pago_query)

                    if any_pago:
                        permiso['Estado de Pago'] = any_pago['status'].capitalize()
                    else:
                        permiso['Estado de Pago'] = 'Pendiente'

            # Enriquecer con estados de envío desde sent_items
            if permiso_id:
                sent_query = select(sent_items.c.sent_type).where(
                    sent_items.c.item_id == permiso_id,
                    sent_items.c.item_type == 'permiso'
                )
                sent_results = await database.fetch_all(sent_query)
                permiso['sent_statuses'] = list(set([r['sent_type'] for r in sent_results]))
            else:
                permiso['sent_statuses'] = []

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
        
        sheets_services.append_sheet_data(sheet_id, permisos_tab_name, values_to_append)
        
        # Opcional: registrar en la base de datos si tienes un modelo para permisos
        # await database.execute(permisos.insert().values(...))

        await log_activity('INFO', 'permiso_creado', f'Permiso {permiso_id} creado.')
        return {"message": "Permiso creado exitosamente", "permiso_id": permiso_id}
    except Exception as e:
        await log_activity('ERROR', 'create_permiso_failed', f"Error al crear permiso: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al crear permiso: {e}")

@app.get("/api/permisos/stats", response_model=Dict[str, Any])
async def get_permisos_stats():
    await log_activity('INFO', 'get_permisos_stats_request', 'Solicitud de estadísticas de permisos')
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        main_sheet_name_env = os.getenv("GOOGLE_SHEET_NAME")
        permisos_tab_name = "permisos"
        
        if not sheet_id or not main_sheet_name_env:
            raise ValueError("GOOGLE_SHEET_ID o GOOGLE_SHEET_NAME no configurados.")

        df = sheets_services.read_sheet_data(sheet_id, permisos_tab_name)
        
        if df.empty:
            return {"total_permisos": 0, "daily_stats": [], "monthly_stats": []}

        # Intentar identificar la columna de fecha
        date_col = None
        possible_date_cols = ['Fecha', 'Fecha Creacion', 'fecha', 'timestamp', 'Timestamp', 'Date']
        
        # Buscar por nombre
        for col in df.columns:
            if any(p.lower() in col.lower() for p in possible_date_cols):
                date_col = col
                break
        
        # Si no se encuentra por nombre, usar la última columna si parece fecha
        if not date_col and not df.empty:
             date_col = df.columns[-1]

        total_permisos = len(df)
        daily_stats = []
        monthly_stats = []

        if date_col:
            try:
                # Convertir a datetime, manejando errores
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
                # Filtrar fechas inválidas (NaT)
                df_dates = df.dropna(subset=[date_col])

                # Agrupar por día
                daily_counts = df_dates.groupby(df_dates[date_col].dt.date).size().reset_index(name='count')
                daily_stats = [{"date": str(row[date_col]), "count": row['count']} for _, row in daily_counts.iterrows()]
                
                # Agrupar por mes
                monthly_counts = df_dates.groupby(df_dates[date_col].dt.to_period('M')).size().reset_index(name='count')
                monthly_stats = [{"month": str(row[date_col]), "count": row['count']} for _, row in monthly_counts.iterrows()]

            except Exception as e:
                await log_activity('WARNING', 'stats_date_parsing_failed', f"Error al procesar fechas en columna {date_col}: {e}")
        
        return {
            "total_permisos": total_permisos,
            "daily_stats": daily_stats,
            "monthly_stats": monthly_stats
        }

    except Exception as e:
        await log_activity('ERROR', 'get_permisos_stats_failed', f"Error al obtener estadísticas: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al obtener estadísticas: {e}")

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
@app.get("/api/pagos/webhook", status_code=status.HTTP_200_OK)  # MercadoPago también envía GET
async def handle_payment_webhook(id: str = Query(None), topic: str = Query(None), type: str = Query(None)):
    await log_activity('INFO', 'payment_webhook_received', f"Webhook de MercadoPago recibido - ID: {id}, Topic: {topic}, Type: {type}")

    # MercadoPago envía notificaciones con diferentes formatos
    if not id or (not topic and not type):
        return {"status": "ignored"}

    try:
        # Solo procesamos notificaciones de pagos
        if topic == "payment" or type == "payment":
            # Obtener detalles del pago desde MercadoPago
            payment_info = mercadopago_services.sdk.payment().get(id)

            if payment_info.get("status") != 200:
                await log_activity('WARNING', 'payment_webhook_api_error', f"Error al obtener info de pago {id}: {payment_info}")
                return {"status": "error"}

            payment = payment_info["response"]
            external_reference = payment.get("external_reference")
            status_payment = payment.get("status")
            status_detail = payment.get("status_detail")
            amount = payment.get("transaction_amount")
            payer_email = payment.get("payer", {}).get("email")

            await log_activity('INFO', 'payment_details', f"Pago {id} - Ref: {external_reference}, Status: {status_payment}, Amount: {amount}")

            # Registrar el pago en la base de datos
            if external_reference and "inscr" in external_reference.lower():  # Es una inscripción
                # Verificar si el pago ya existe
                existing_query = select(pagos).where(pagos.c.payment_id == int(id))
                existing_pago = await database.fetch_one(existing_query)

                if existing_pago:
                    # Actualizar el pago existente
                    update_query = pagos.update().where(pagos.c.payment_id == int(id)).values(
                        status=status_payment,
                        status_detail=status_detail,
                        amount=amount,
                        email=payer_email
                    )
                    await database.execute(update_query)
                    await log_activity('INFO', 'inscripcion_pago_actualizado', f"Pago {id} para inscripción {external_reference} actualizado a status {status_payment}")
                else:
                    # Insertar nuevo pago
                    insert_query = pagos.insert().values(
                        payment_id=int(id),
                        inscription_id=external_reference,
                        status=status_payment,
                        status_detail=status_detail,
                        amount=amount,
                        email=payer_email,
                        date_created=datetime.datetime.now(datetime.timezone.utc)
                    )
                    await database.execute(insert_query)
                    await log_activity('INFO', 'inscripcion_pago_creado', f"Pago {id} para inscripción {external_reference} creado con status {status_payment}")

            elif external_reference and "per" in external_reference.lower():  # Es un permiso
                # Verificar si el pago ya existe
                existing_query = select(pagos_permisos).where(pagos_permisos.c.payment_id == int(id))
                existing_pago = await database.fetch_one(existing_query)

                if existing_pago:
                    # Actualizar el pago existente
                    update_query = pagos_permisos.update().where(pagos_permisos.c.payment_id == int(id)).values(
                        status=status_payment,
                        status_detail=status_detail,
                        amount=amount,
                        email=payer_email
                    )
                    await database.execute(update_query)
                    await log_activity('INFO', 'permiso_pago_actualizado', f"Pago {id} para permiso {external_reference} actualizado a status {status_payment}")
                else:
                    # Insertar nuevo pago
                    insert_query = pagos_permisos.insert().values(
                        payment_id=int(id),
                        permiso_id=external_reference,
                        status=status_payment,
                        status_detail=status_detail,
                        amount=amount,
                        email=payer_email,
                        date_created=datetime.datetime.now(datetime.timezone.utc)
                    )
                    await database.execute(insert_query)
                    await log_activity('INFO', 'permiso_pago_creado', f"Pago {id} para permiso {external_reference} creado con status {status_payment}")

        return {"status": "ok"}

    except Exception as e:
        await log_activity('ERROR', 'payment_webhook_failed', f"Error al procesar webhook de pago: {e}")
        # No lanzar excepción para que MercadoPago no reintente
        return {"status": "error", "message": str(e)}

@app.post("/api/pagos/fetch/{payment_id}")
async def fetch_payment_from_mercadopago(payment_id: str):
    """Trae un pago específico de MercadoPago y lo guarda en la DB"""
    await log_activity('INFO', 'fetch_payment', f"Consultando pago {payment_id} en MercadoPago")
    try:
        payment_info = mercadopago_services.sdk.payment().get(payment_id)

        if payment_info.get("status") != 200:
            raise HTTPException(status_code=404, detail=f"Pago no encontrado en MercadoPago")

        payment = payment_info["response"]
        external_reference = payment.get("external_reference")
        status_payment = payment.get("status")
        status_detail = payment.get("status_detail")
        amount = payment.get("transaction_amount")
        payer_email = payment.get("payer", {}).get("email")
        date_created = payment.get("date_created")

        await log_activity('INFO', 'payment_details', f"Ref: {external_reference}, Status: {status_payment}, Amount: {amount}")

        if not external_reference:
            raise HTTPException(status_code=400, detail="Pago sin referencia externa")

        # Guardar según tipo
        if "inscr" in external_reference.lower():
            existing = await database.fetch_one(select(pagos).where(pagos.c.payment_id == int(payment_id)))
            if existing:
                return {"status": "already_exists", "payment_id": payment_id}

            await database.execute(pagos.insert().values(
                payment_id=int(payment_id),
                inscription_id=external_reference,
                status=status_payment,
                status_detail=status_detail,
                amount=amount,
                email=payer_email,
                date_created=date_created
            ))
            await log_activity('INFO', 'payment_fetched', f"Pago {payment_id} guardado para inscripción {external_reference}")
            return {"status": "ok", "type": "inscripcion", "payment_id": payment_id}

        elif "pc" in external_reference.lower() or "per" in external_reference.lower():
            existing = await database.fetch_one(select(pagos_permisos).where(pagos_permisos.c.payment_id == int(payment_id)))
            if existing:
                return {"status": "already_exists", "payment_id": payment_id}

            await database.execute(pagos_permisos.insert().values(
                payment_id=int(payment_id),
                permiso_id=external_reference,
                status=status_payment,
                status_detail=status_detail,
                amount=amount,
                email=payer_email,
                date_created=date_created
            ))
            await log_activity('INFO', 'payment_fetched', f"Pago {payment_id} guardado para permiso {external_reference}")
            return {"status": "ok", "type": "permiso", "payment_id": payment_id}

        raise HTTPException(status_code=400, detail="Tipo de referencia no reconocido")

    except HTTPException:
        raise
    except Exception as e:
        await log_activity('ERROR', 'fetch_payment_failed', f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pagos", response_model=Dict[str, Any])
async def get_pagos(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    await log_activity('INFO', 'get_pagos_request', f'Solicitud de pagos - Página: {page}, Límite: {limit}')
    try:
        # Obtener pagos de inscripciones
        inscripciones_records = await database.fetch_all(pagos.select())
        # Obtener pagos de permisos
        permisos_records = await database.fetch_all(pagos_permisos.select())

        # Combinar y normalizar
        all_payments = []

        for record in inscripciones_records:
            all_payments.append({
                "id": record["id"],
                "payment_id": record["payment_id"],
                "inscription_id": record["inscription_id"],
                "permiso_id": None,
                "status": record["status"],
                "status_detail": record["status_detail"],
                "amount": record["amount"],
                "email": record["email"],
                "date_created": record["date_created"]
            })

        for record in permisos_records:
            all_payments.append({
                "id": record["id"],
                "payment_id": record["payment_id"],
                "inscription_id": None,
                "permiso_id": record["permiso_id"],
                "status": record["status"],
                "status_detail": record["status_detail"],
                "amount": record["amount"],
                "email": record["email"],
                "date_created": record["date_created"]
            })

        # Ordenar por fecha (más reciente primero)
        all_payments.sort(key=lambda x: x["date_created"] if x["date_created"] else "", reverse=True)

        # Aplicar paginación
        total_records = len(all_payments)
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0
        offset = (page - 1) * limit
        paginated_payments = all_payments[offset:offset + limit]

        return {
            "data": paginated_payments,
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
        # Leer de sent_items filtrando por inscripciones y tipo cobro
        total_records_query = select(func.count()).select_from(sent_items).where(
            (sent_items.c.item_type == 'inscripcion') & (sent_items.c.sent_type == 'cobro')
        )
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0

        query = sent_items.select().where(
            (sent_items.c.item_type == 'inscripcion') & (sent_items.c.sent_type == 'cobro')
        ).order_by(desc(sent_items.c.date_sent)).offset(offset).limit(limit)
        cobros_records = await database.fetch_all(query)

        # Mapear los campos para que coincidan con el formato esperado
        data = [{
            "id": record["id"],
            "inscription_id": record["item_id"],
            "email": None,  # sent_items no tiene email
            "amount": None,  # sent_items no tiene amount
            "date_sent": record["date_sent"]
        } for record in cobros_records]

        return {
            "data": data,
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
        # Leer de sent_items filtrando por permisos y tipo cobro
        total_records_query = select(func.count()).select_from(sent_items).where(
            (sent_items.c.item_type == 'permiso') & (sent_items.c.sent_type == 'cobro')
        )
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit) if total_records > 0 else 0

        query = sent_items.select().where(
            (sent_items.c.item_type == 'permiso') & (sent_items.c.sent_type == 'cobro')
        ).order_by(desc(sent_items.c.date_sent)).offset(offset).limit(limit)
        permiso_cobros_records = await database.fetch_all(query)

        # Mapear los campos para que coincidan con el formato esperado
        data = [{
            "id": record["id"],
            "permiso_id": record["item_id"],
            "email": None,  # sent_items no tiene email
            "amount": None,  # sent_items no tiene amount
            "date_sent": record["date_sent"]
        } for record in permiso_cobros_records]

        return {
            "data": data,
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
            date_sent=datetime.datetime.now(datetime.timezone.utc)
        )
        await database.execute(query)
        return {"message": "Ítem enviado registrado exitosamente."}
    except Exception as e:
        await log_activity('ERROR', 'log_sent_item_failed', f"Error al registrar ítem enviado: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al registrar ítem enviado: {e}")

@app.post("/api/send-payment-link", response_model=Dict[str, str])
async def send_payment_link_endpoint(request_data: SendPaymentLinkRequest):
    await log_activity('INFO', 'send_payment_link_request', f'Solicitud para enviar link de pago a: {request_data.email} para inscripción: {request_data.inscription_id}')
    try:
        # Leer la pestaña de precios desde Google Sheets
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID no configurado.")

        precios_df = sheets_services.read_sheet_data(sheet_id, "precios")

        # Buscar el precio según el tipo de establecimiento
        tipo_establecimiento = request_data.tipo_establecimiento
        precio_row = None

        # Mapear el tipo de establecimiento a la actividad en la pestaña precios
        if tipo_establecimiento and "area libre" in tipo_establecimiento.lower():
            precio_row = precios_df[precios_df['Actividad'].str.contains("Area Libre", case=False, na=False)]
        elif tipo_establecimiento and "criadero" in tipo_establecimiento.lower():
            precio_row = precios_df[precios_df['Actividad'].str.contains("Criadero", case=False, na=False) &
                                   precios_df['Actividad'].str.contains("Establecimiento", case=False, na=False)]

        if precio_row is None or precio_row.empty:
            raise ValueError(f"No se encontró precio para el tipo de establecimiento: {tipo_establecimiento}")

        # Obtener el valor y limpiarlo (remover $, espacios, comas)
        precio_str = precio_row.iloc[0]['Valor']
        precio_limpio = precio_str.replace('$', '').replace(',', '').replace('.', '').strip()
        precio = float(precio_limpio) / 100  # Convertir centavos a pesos

        # Crear preferencia de pago en MercadoPago
        payment_result = mercadopago_services.create_payment_preference(
            title=f"Inscripción {tipo_establecimiento} - {request_data.inscription_id}",
            price=precio,
            external_reference=request_data.inscription_id,
            payer_email=request_data.email
        )

        if not payment_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear link de pago: {payment_result['error']}"
            )

        payment_link = payment_result["init_point"]

        # Formatear el precio para mostrar
        precio_formateado = f"${precio:,.2f}".replace(',', '.')

        subject = f"Enlace de pago para su inscripción {request_data.inscription_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Pago de Inscripción</h2>
                <p>Estimado/a <strong>{request_data.nombre_establecimiento}</strong>,</p>
                <p>Adjunto encontrará el enlace para realizar el pago de su inscripción:</p>
                <div style="background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-left: 4px solid #009ee3;">
                    <p><strong>Número de Inscripción:</strong> {request_data.inscription_id}</p>
                    <p><strong>Tipo:</strong> {request_data.tipo_establecimiento}</p>
                    <p><strong>Monto:</strong> {precio_formateado} ARS</p>
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{payment_link}" style="background-color: #009ee3; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                        💳 Pagar con MercadoPago
                    </a>
                </div>
                <p style="font-size: 12px; color: #666;">Será redirigido a MercadoPago para completar el pago de forma segura.</p>
                <p>Gracias por su inscripción.</p>
                <p><strong>El equipo de Caza 2026</strong></p>
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

        await log_activity('INFO', 'payment_link_sent', f'Envío de cobro (Inscripción) - ID: {request_data.inscription_id}, Monto: {precio_formateado}, Email: {request_data.email}. Preference ID: {payment_result["preference_id"]}')
        return {"message": "Email de cobro enviado exitosamente con link de MercadoPago."}
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
        # Leer la pestaña de precios desde Google Sheets
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID no configurado.")

        precios_df = sheets_services.read_sheet_data(sheet_id, "precios")

        # Buscar el precio según la categoría del permiso
        categoria = request_data.categoria
        if not categoria:
            raise ValueError("Categoría del permiso no especificada.")

        # Normalización para búsqueda robusta
        def normalize(t):
            return " ".join(str(t).lower().strip().split())

        cat_norm = normalize(categoria)
        
        # Intentar coincidencia exacta primero (normalizada)
        precios_df['Actividad_Norm'] = precios_df['Actividad'].apply(normalize)
        precio_row = precios_df[precios_df['Actividad_Norm'] == cat_norm]

        # Si no hay coincidencia exacta, intentar con contains (sin regex para evitar problemas con paréntesis)
        if precio_row.empty:
            precio_row = precios_df[precios_df['Actividad_Norm'].str.contains(cat_norm, regex=False, na=False)]

        if precio_row.empty:
            # Si sigue fallando, loguear las opciones disponibles para depuración
            available = precios_df['Actividad'].tolist()
            await log_activity('WARNING', 'price_lookup_failed', f"No se encontró '{categoria}'. Opciones: {available}")
            raise ValueError(f"No se encontró precio para la categoría de permiso: {categoria}")

        # Obtener el valor y limpiarlo
        precio_str = str(precio_row.iloc[0]['Valor'])
        # Limpieza robusta: quitar $, espacios, y manejar separadores
        # Si tiene coma y punto, eliminar el separador de miles
        p_clean = precio_str.replace('$', '').strip()
        if ',' in p_clean and '.' in p_clean:
            # Determinar cuál es el de miles. Si el punto está antes de la coma: 1.234,56
            if p_clean.find('.') < p_clean.find(','):
                p_clean = p_clean.replace('.', '').replace(',', '.')
            else: # 1,234.56
                p_clean = p_clean.replace(',', '')
        elif ',' in p_clean:
            # Solo tiene coma. En AR es decimal.
            p_clean = p_clean.replace(',', '.')
        
        try:
            precio = float(p_clean)
        except ValueError:
            # Fallback al método anterior si falló el nuevo, por si acaso
            precio_limpio_old = precio_str.replace('$', '').replace(',', '').replace('.', '').strip()
            precio = float(precio_limpio_old) / 100

        # Crear preferencia de pago en MercadoPago
        payment_result = mercadopago_services.create_payment_preference(
            title=f"Permiso de Caza - {categoria} - {request_data.permiso_id}",
            price=precio,
            external_reference=request_data.permiso_id,
            payer_email=request_data.email
        )

        if not payment_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al crear link de pago: {payment_result['error']}"
            )

        payment_link = payment_result["init_point"]

        # Formatear el precio para mostrar
        precio_formateado = f"${precio:,.2f}".replace(',', '.')

        subject = f"Enlace de pago para su permiso de caza {request_data.permiso_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Pago de Permiso de Caza</h2>
                <p>Estimado/a <strong>{request_data.nombre_apellido}</strong>,</p>
                <p>Adjunto encontrará el enlace para realizar el pago de su permiso de caza:</p>
                <div style="background-color: #f5f5f5; padding: 15px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <p><strong>Número de Permiso:</strong> {request_data.permiso_id}</p>
                    <p><strong>Categoría:</strong> {request_data.categoria}</p>
                    <p><strong>Monto:</strong> {precio_formateado} ARS</p>
                </div>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{payment_link}" style="background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                        💳 Pagar con MercadoPago
                    </a>
                </div>
                <p style="font-size: 12px; color: #666;">Será redirigido a MercadoPago para completar el pago de forma segura.</p>
                <p>Gracias.</p>
                <p><strong>El equipo de Caza 2026</strong></p>
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

        await log_activity('INFO', 'permiso_payment_link_sent', f'Envío de cobro (Permiso) - ID: {request_data.permiso_id}, Monto: {precio_formateado}, Email: {request_data.email}. Preference ID: {payment_result["preference_id"]}')
        return {"message": "Email de cobro de permiso enviado exitosamente con link de MercadoPago."}
    except Exception as e:
        await log_activity('ERROR', 'send_permiso_payment_link_failed', f"Error al enviar link de pago de permiso: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al enviar link de pago de permiso: {e}")

@app.post("/api/send-permiso-email", response_model=Dict[str, str])
async def send_permiso_email_endpoint(request_data: SendPermisoEmailRequest):
    await log_activity('INFO', 'send_permiso_email_request', f'Solicitud para enviar permiso a: {request_data.email} para permiso: {request_data.permiso_id}')
    try:
        # Buscar PDF del permiso
        permisos_folder_id = "1ZynwbJewIsSodT8ogIm2AXanL2Am0IUt"
        pdfs = drive_services.list_pdfs_in_folder(permisos_folder_id)
        pdf_id = None
        pdf_filename = None

        for pdf in pdfs:
            if 'name' in pdf and pdf['name'].replace('.pdf', '') == request_data.permiso_id:
                pdf_id = pdf.get('id')
                pdf_filename = pdf.get('name')
                break

        subject = f"Su permiso de caza {request_data.permiso_id}"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Permiso de Caza</h2>
                <p>Estimado/a <strong>{request_data.nombre_apellido}</strong>,</p>
                <p>Adjunto encontrará su permiso de caza <b>{request_data.permiso_id}</b>.</p>
                <p>Por favor, conserve este permiso para su presentación cuando sea requerido.</p>
                <p>Gracias.</p>
                <p><strong>El equipo de Caza 2026</strong></p>
            </body>
        </html>
        """
        sender_email = os.getenv("SENDER_EMAIL_RESEND", "onboarding@resend.dev")

        if pdf_id and pdf_filename:
            # Descargar PDF de Google Drive
            pdf_content = drive_services.download_file(pdf_id)

            if pdf_content:
                # Enviar email con PDF adjunto
                email_sent = email_services.send_email_with_attachment(
                    to_email=request_data.email,
                    subject=subject,
                    html_content=html_content,
                    sender_email=sender_email,
                    attachment_content=pdf_content,
                    attachment_filename=pdf_filename
                )
            else:
                raise HTTPException(status_code=500, detail="No se pudo descargar el PDF")
        else:
            # Sin PDF, enviar email simple
            email_sent = email_services.send_simple_email(
                to_email=request_data.email,
                subject=subject,
                html_content=f"<p>Estimado/a {request_data.nombre_apellido},</p><p>Su permiso está siendo procesado.</p>",
                sender_email=sender_email
            )

        if not email_sent:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallo al enviar el email del permiso.")

        return {"message": "Permiso enviado exitosamente por email con PDF adjunto."}
    except Exception as e:
        await log_activity('ERROR', 'send_permiso_email_failed', f"Error al enviar permiso por email: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al enviar permiso por email: {e}")

# --- Serve React Frontend (Deployment Fix) ---
# Adjust path to where the frontend build is located relative to this file
# Assuming structure:
# /root
#   /caza_2026_v2_backend/main_api.py
#   /caza_2026_v2_frontend/build
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "caza_2026_v2_frontend", "build")

@app.get("/api/test-routing")
async def test_routing():
    return {"status": "routing_works", "message": "Si ves esto, las rutas API funcionan."}

if os.path.exists(frontend_build_path):
    # Mount static assets (JS, CSS, images)
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build_path, "static")), name="static")
    
    # Catch-all route to serve index.html for SPA routing
    # This must be the Last route defined
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Normalize path to remove leading slash
        path = full_path.lstrip('/')
        
        # Check if a specific file was requested (e.g. manifest.json, favicon.ico)
        file_path = os.path.join(frontend_build_path, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Fallback to index.html for React Router
        print(f"DEBUG: CATCH-ALL HIT. full_path='{full_path}' path='{path}'") 
        response = FileResponse(os.path.join(frontend_build_path, "index.html"))
        response.headers["X-Debug-Path"] = full_path
        response.headers["X-Debug-Check"] = f"serving index.html for SPA"
        return response
else:
    print(f"WARNING: Frontend build directory not found at {frontend_build_path}. Static files will not be served.")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: __file__ location: {os.path.abspath(__file__)}")
    print(f"DEBUG: Computed frontend_build_path: {os.path.abspath(frontend_build_path)}")
