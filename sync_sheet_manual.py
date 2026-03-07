import os
import sys
from caza_2026_v2_backend import sheets_services
from dotenv import load_dotenv

load_dotenv('c:/Users/emanuel/Desktop/Codigos/caza_2026_v2/caza_2026_v2_backend/.env')

sheet_id = os.getenv("GOOGLE_SHEET_ID")
# IDs for Parque Diana that were already registered in DB but not sheet
ids_to_fix = ["fau_inscr698feb1424980", "fau_inscr698fe6daeae93"]

for insc_id in ids_to_fix:
    print(f"Updating sheet for {insc_id}...")
    try:
        res = sheets_services.update_payment_status(sheet_id, "inscrip", insc_id, "Pagado")
        print(f"Result for {insc_id}: {res}")
    except Exception as e:
        print(f"Error for {insc_id}: {e}")

print("Done.")
