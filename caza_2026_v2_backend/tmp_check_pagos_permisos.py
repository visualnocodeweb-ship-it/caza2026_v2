import asyncio
from database import database
from models import pagos_permisos

async def test():
    await database.connect()
    records = await database.fetch_all("SELECT * FROM pagos_permisos")
    for r in records:
        print(r.id, r.permiso_id, r.amount, r.status)
    await database.disconnect()

asyncio.run(test())
