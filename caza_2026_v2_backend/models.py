import sqlalchemy
from .database import metadata
from datetime import datetime, timezone

pagos = sqlalchemy.Table(
    "pagos",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("payment_id", sqlalchemy.BigInteger, index=True, unique=True),
    sqlalchemy.Column("inscription_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("status_detail", sqlalchemy.String),
    sqlalchemy.Column("amount", sqlalchemy.Float),
    sqlalchemy.Column("email", sqlalchemy.String),
    sqlalchemy.Column("date_created", sqlalchemy.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)
