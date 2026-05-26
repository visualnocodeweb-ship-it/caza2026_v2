import asyncio
from databases import Database

DATABASE_URL = "postgresql://caza2026_db_user:9bkZN0K0rud5LeT6bNqI2vi3QvIOoBBU@dpg-d615e1fgi27c739999f0-a.virginia-postgres.render.com/caza2026_db"

async def run_query():
    db = Database(DATABASE_URL)
    try:
        await db.connect()
        # Buscar en pagos_permisos
        q = "SELECT * FROM pagos_permisos WHERE permiso_id = 'permiso_caza2669caababb6c09'"
        res = await db.fetch_all(q)
        print("Resultados en pagos_permisos:")
        for r in res:
            print(dict(r))
            
        # También buscar en logs para ver qué pasó
        q_logs = "SELECT * FROM logs WHERE event ILIKE '%permiso_caza2669caababb6c09%' ORDER BY timestamp DESC LIMIT 5"
        res_logs = await db.fetch_all(q_logs)
        print("\nLogs relacionados:")
        for r in res_logs:
            print(dict(r))
            
        await db.disconnect()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_query())
