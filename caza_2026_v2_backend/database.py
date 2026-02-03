import os
from databases import Database
import sqlalchemy

DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy requiere un dialecto específico en la URL para asyncpg
db_url_for_sqlalchemy = DATABASE_URL
if db_url_for_sqlalchemy and db_url_for_sqlalchemy.startswith("postgres://"):
    db_url_for_sqlalchemy = db_url_for_sqlalchemy.replace("postgres://", "postgresql://", 1)

database = Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

engine = sqlalchemy.create_engine(
    db_url_for_sqlalchemy
)
