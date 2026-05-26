import asyncio
import sqlalchemy
from databases import Database

DATABASE_URL = 'postgresql://base_datos_tablero_traful_pagina_general_user:bEKhclV6N026s8jNQcBDaH5sou0HZtmA@dpg-d64tk2i4d50c73eoksug-a.oregon-postgres.render.com/base_datos_tablero_traful_pagina_general'
database = Database(DATABASE_URL)

async def run():
    await database.connect()
    query = "SELECT * FROM pagos_permisos WHERE permiso_id = 'permiso_caza2669caababb6c09'"
    results = await database.fetch_all(query)
    for row in results:
        print(dict(row))
    await database.disconnect()

if __name__ == "__main__":
    asyncio.run(run())
