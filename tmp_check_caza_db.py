import asyncio
from databases import Database

DATABASE_URL = "postgresql://caza2026_db_user:9bkZN0K0rud5LeT6bNqI2vi3QvIOoBBU@dpg-d615e1fgi27c739999f0-a.virginia-postgres.render.com/caza2026_db"

async def list_tables():
    db = Database(DATABASE_URL)
    try:
        await db.connect()
        q = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        res = await db.fetch_all(q)
        print("Tablas encontradas:", [r[0] for r in res])
        await db.disconnect()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_tables())
