import asyncio
from database import database
import os

async def fetch_logs():
    await database.connect()
    # Fetch latest 20 logs
    query = "SELECT timestamp, level, event, details FROM logs ORDER BY timestamp DESC LIMIT 20"
    records = await database.fetch_all(query)
    for r in records:
        print(f"[{r['timestamp']}] {r['level']} - {r['event']}: {r['details']}")
    
    print("\n--- PAGOS MENOR ---")
    query2 = "SELECT * FROM pagos_permisos_menor ORDER BY date_created DESC LIMIT 5"
    records2 = await database.fetch_all(query2)
    for r in records2:
        print(dict(r))

    print("\n--- PAGOS MAYOR ---")
    query3 = "SELECT * FROM pagos_permisos ORDER BY date_created DESC LIMIT 5"
    records3 = await database.fetch_all(query3)
    for r in records3:
        print(dict(r))
        
    await database.disconnect()

asyncio.run(fetch_logs())
