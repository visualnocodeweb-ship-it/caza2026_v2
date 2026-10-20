import os
from databases import Database
import sqlalchemy
from dotenv import load_dotenv

# Cargar variables de entorno (puede estar en la raíz o en el backend)
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")


# SQLAlchemy 2.1 trata postgresql:// como psycopg 3. El proyecto instala psycopg2-binary.
db_url_for_sqlalchemy = DATABASE_URL
if db_url_for_sqlalchemy and db_url_for_sqlalchemy.startswith("postgres://"):
    db_url_for_sqlalchemy = db_url_for_sqlalchemy.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url_for_sqlalchemy and db_url_for_sqlalchemy.startswith("postgresql://"):
    db_url_for_sqlalchemy = db_url_for_sqlalchemy.replace("postgresql://", "postgresql+psycopg2://", 1)

database = Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

engine = sqlalchemy.create_engine(
    db_url_for_sqlalchemy
)
