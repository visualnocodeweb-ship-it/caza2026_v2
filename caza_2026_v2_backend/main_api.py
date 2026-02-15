import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import datetime
from sqlalchemy import select, func
from .database import database, engine, metadata
from .models import logs # Only logs needed for this minimal example
import math # Needed for ceil in get_logs
from sqlalchemy.dialects.postgresql import insert # Needed for log_activity

# --- Logging Centralizado (minimal for this test) ---
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
    await log_activity('INFO', 'startup_minimal', 'Aplicación mínima iniciada.')

@app.on_event("shutdown")
async def shutdown():
    await log_activity('INFO', 'shutdown_minimal', 'Aplicación mínima cerrándose.')
    await database.disconnect()

# --- CORS (minimal for this test) ---
origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "https://caza2026-frontend.onrender.com",
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/")
async def read_root():
    await log_activity('INFO', 'root_access', 'Acceso al endpoint raíz.')
    return {"message": "Hello from minimal FastAPI app!"}

@app.get("/api/logs")
async def get_logs_minimal(page: int = 1, limit: int = 15):
    try:
        total_records_query = select(func.count()).select_from(logs)
        total_records = await database.fetch_val(total_records_query)
        offset = (page - 1) * limit
        total_pages = math.ceil(total_records / limit)
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
        await log_activity('ERROR', 'get_logs_minimal_failed', f"Error al obtener logs minimos: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch minimal logs.")
