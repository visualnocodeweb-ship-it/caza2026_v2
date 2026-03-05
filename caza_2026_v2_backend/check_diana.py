import asyncio
import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import select, create_engine, text

# Initialize dotenv
load_dotenv(encoding='latin-1')

# Hardcode DATABASE_URL from memory
DATABASE_URL = "postgresql://base_datos_tablero_traful_pagina_general_user:bEKhclV6N026s8jNQcBDaH5sou0HZtmA@dpg-d64tk2i4d50c73eoksug-a.oregon-postgres.render.com/base_datos_tablero_traful_pagina_general"
os.environ["DATABASE_URL"] = DATABASE_URL
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# Load google sheet data
from caza_2026_v2_backend import sheets_services
from caza_2026_v2_backend import database
from caza_2026_v2_backend import models

async def main():
    await database.database.connect()
    
    # 1. Get inscriptions from sheets
    df = sheets_services.read_sheet_data(GOOGLE_SHEET_ID, "inscrip")
    print(f"Total rows in sheets: {len(df)}")
    
    # 2. Find Parque diana
    diana_rows = df[df.apply(lambda row: row.astype(str).str.contains('Parque diana', case=False).any(), axis=1)]
    print(f"\nFound {len(diana_rows)} rows matching 'Parque diana':")
    
    for idx, row in diana_rows.iterrows():
        insc_id = str(row.get('numero_inscripcion', '')).strip()
        nombre = row.get('nombre_establecimiento', '') or row.get('razon_social', '')
        estado_sheet = row.get('Estado de Pago', '')
        print(f"\n-- Inscription ID: '{insc_id}' | Name: {nombre} | Sheet Status: {estado_sheet}")
        
        # Check DB
        if insc_id:
            query = select(models.pagos).where(models.pagos.c.inscription_id == insc_id)
            result = await database.database.fetch_all(query)
            if not result:
                print(f"   => Not found in DB 'pagos' table.")
            else:
                for r in result:
                    print(f"   => Found in DB: status='{r['status']}', amount='{r.get('amount', '')}', date='{r.get('date_created', '')}'")
    
    # Also let's check if there are ANY records in `pagos` for checking matching logic
    print("\n--- Checking 5 recent payments in DB ---")
    query = select(models.pagos).order_by(models.pagos.c.date_created.desc()).limit(5)
    recent = await database.database.fetch_all(query)
    for r in recent:
        print(f"   ID DB: '{r['inscription_id']}', status='{r['status']}'")

    await database.database.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
