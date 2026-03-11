import os
import asyncio
from datetime import datetime, timezone
import pandas as pd
from dotenv import load_dotenv
from databases import Database

# Cargar entorno y servicios localmente en cwd
load_dotenv('.env', encoding='latin-1')
import sheets_services

URL_CAZA2026 = "postgresql://caza2026_db_user:9bkZN0K0rud5LeT6bNqI2vi3QvIOoBBU@dpg-d615e1fgi27c739999f0-a.virginia-postgres.render.com/caza2026_db"

async def process():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("GOOGLE_SHEET_ID no configurado")
        return

    # Buscar ID de Estancia Los Lirios
    print("Buscando Inscripción de 'Los Lirios'...")
    try:
        df_insc = sheets_services.read_sheet_data(sheet_id, "inscrip")
        match_insc = df_insc[df_insc.astype(str).apply(lambda x: x.str.contains('Lirios', case=False).any(), axis=1)]
        insc_id = None
        if not match_insc.empty:
            insc_id = match_insc.iloc[0].get('numero_inscripcion')
            print(f"ID Inscripción encontrado: {insc_id}")
        else:
            print("No se encontró 'Los Lirios' en inscripciones.")
    except Exception as e:
        print(f"Error leyendo inscripciones: {e}")
        insc_id = None

    db = Database(URL_CAZA2026)
    await db.connect()
    try:
        now = datetime.now(timezone.utc)
        
        # PARAMETROS DE PAGOS
        # 1. Permiso Maria Gabriela
        p_id = "permiso_caza2669982a53d2365"
        categoria_m = "PERMISO RESIDENTE PAIS SELECCIÓN - AREA LIBRE"
        try:
            amt_p = sheets_services.get_price_for_categoria(sheet_id, "precios", categoria_m)
        except Exception as e:
            print(f"No se pudo hallar precio exacto para el permiso ({e}). Usando 65637.0")
            amt_p = 65637.0
            
        pid1 = int(now.timestamp()) + 10
        q_check_p = "SELECT id FROM pagos_permisos WHERE permiso_id = :p_id"
        ext_p = await db.fetch_one(query=q_check_p, values={"p_id": p_id})
        
        if ext_p:
            await db.execute("UPDATE pagos_permisos SET status='approved', amount=:amt WHERE permiso_id=:p_id", values={"amt": amt_p, "p_id": p_id})
            print(f"Permiso {p_id} actualizado a approved.")
        else:
            q_ins_p = """
            INSERT INTO pagos_permisos (payment_id, permiso_id, status, status_detail, amount, email, date_created)
            VALUES (:pid, :p_id, 'approved', 'accredited', :amt, :email, :date)
            """
            await db.execute(q_ins_p, values={"pid": pid1, "p_id": p_id, "amt": amt_p, "email": 'lolag@smandes.com.ar', "date": now})
            print(f"Permiso {p_id} insertado como approved (Monto: {amt_p}).")

        # 2. Inscripción Estancia Los Lirios
        if insc_id:
            try:
                amt_i = sheets_services.get_price_for_establishment(sheet_id, "precios", "Area Libre")
            except Exception as e:
                print(f"No se pudo hallar precio exacto para Area Libre ({e}). Usando 150000.0")
                amt_i = 150000.0
                
            pid2 = int(now.timestamp()) + 20
            q_check_i = "SELECT id FROM pagos WHERE inscription_id = :iid"
            ext_i = await db.fetch_one(query=q_check_i, values={"iid": insc_id})
            
            if ext_i:
                await db.execute("UPDATE pagos SET status='approved', amount=:amt WHERE inscription_id=:iid", values={"amt": amt_i, "iid": insc_id})
                print(f"Inscripción {insc_id} actualizada a approved.")
            else:
                q_ins_i = """
                INSERT INTO pagos (payment_id, inscription_id, status, status_detail, amount, email, date_created)
                VALUES (:pid, :iid, 'approved', 'accredited', :amt, :email, :date)
                """
                await db.execute(q_ins_i, values={"pid": pid2, "iid": insc_id, "amt": amt_i, "email": 'estanciaquillen@yahoo.com.ar', "date": now})
                print(f"Inscripción {insc_id} insertada como approved (Monto: {amt_i}).")

    except Exception as e:
        print(f"Error registrando en DB: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(process())
