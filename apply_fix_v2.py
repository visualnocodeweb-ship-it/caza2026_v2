import os
import re

target_file = 'c:/Users/emanuel/Desktop/Codigos/caza_2026_v2/caza_2026_v2_backend/main_api.py'
with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Enrich get_pagos with establishment names
old_get_pagos_loop = """        # Obtener pagos de inscripciones
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
            })"""

new_get_pagos_loop = """        # Obtener pagos de inscripciones
        inscripciones_records = await database.fetch_all(pagos.select())
        # Obtener pagos de permisos
        permisos_records = await database.fetch_all(pagos_permisos.select())

        # Obtener datos de nombres para enriquecer búsqueda
        from sqlalchemy import select
        insc_names_records = await database.fetch_all(inscripciones_data.select())
        perm_names_records = await database.fetch_all(permisos_caza.select())
        
        insc_map = {safe_str_id(r['numero_inscripcion']): r['nombre_establecimiento'] for r in insc_names_records}
        perm_map = {str(r['id']): r['nombre_establecimiento'] for r in perm_names_records}

        # Combinar y normalizar
        all_payments = []

        for record in inscripciones_records:
            insc_id = safe_str_id(record["inscription_id"])
            all_payments.append({
                "id": record["id"],
                "payment_id": record["payment_id"],
                "inscription_id": insc_id,
                "permiso_id": None,
                "status": record["status"],
                "status_detail": record["status_detail"],
                "amount": record["amount"],
                "email": record["email"],
                "date_created": record["date_created"],
                "establecimiento": insc_map.get(insc_id, "N/A")
            })

        for record in permisos_records:
            perm_id = str(record["permiso_id"])
            all_payments.append({
                "id": record["id"],
                "payment_id": record["payment_id"],
                "inscription_id": None,
                "permiso_id": record["permiso_id"],
                "status": record["status"],
                "status_detail": record["status_detail"],
                "amount": record["amount"],
                "email": record["email"],
                "date_created": record["date_created"],
                "establecimiento": perm_map.get(perm_id, "N/A")
            })"""

content = content.replace(old_get_pagos_loop, new_get_pagos_loop)

# 2. Add Google Sheets update to register_manual_payment
# We look for the database.execute(insert_query) and add the sheet update after it
old_insert_manual = """        await database.execute(insert_query)

        await log_activity('INFO', 'manual_payment_registered', f"Pago manual aprobado para {insc_id} por ${amount}")"""

new_insert_manual = """        await database.execute(insert_query)

        # Actualizar Google Sheets
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        try:
            sheets_services.update_payment_status(sheet_id, "inscrip", insc_id, "Pagado")
            await log_activity('INFO', 'manual_payment_sheet_updated', f"Hoja de cálculo actualizada para {insc_id}")
        except Exception as e_sheet:
            await log_activity('WARNING', 'manual_payment_sheet_update_failed', f"Error al actualizar hoja para {insc_id}: {e_sheet}")

        await log_activity('INFO', 'manual_payment_registered', f"Pago manual aprobado para {insc_id} por ${amount}")"""

content = content.replace(old_insert_manual, new_insert_manual)

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement complete.")
