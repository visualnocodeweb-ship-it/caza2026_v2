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

pagos_permisos = sqlalchemy.Table(
    "pagos_permisos",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("payment_id", sqlalchemy.BigInteger, index=True, unique=True),
    sqlalchemy.Column("permiso_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("status_detail", sqlalchemy.String),
    sqlalchemy.Column("amount", sqlalchemy.Float),
    sqlalchemy.Column("email", sqlalchemy.String),
    sqlalchemy.Column("date_created", sqlalchemy.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

cobros_enviados = sqlalchemy.Table(
    "cobros_enviados",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("inscription_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("email", sqlalchemy.String),
    sqlalchemy.Column("amount", sqlalchemy.Float),
    sqlalchemy.Column("date_sent", sqlalchemy.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

permisos_enviados = sqlalchemy.Table(
    "permisos_enviados",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("permiso_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("email", sqlalchemy.String),
    sqlalchemy.Column("date_sent", sqlalchemy.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

sent_items = sqlalchemy.Table(
    "sent_items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("item_id", sqlalchemy.String, index=True),
    sqlalchemy.Column("item_type", sqlalchemy.String), # 'inscripcion' or 'permiso'
    sqlalchemy.Column("sent_type", sqlalchemy.String), # 'cobro', 'credencial', 'pdf'
    sqlalchemy.Column("date_sent", sqlalchemy.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
)

logs = sqlalchemy.Table(
    "logs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    sqlalchemy.Column("level", sqlalchemy.String),
    sqlalchemy.Column("event", sqlalchemy.String),
    sqlalchemy.Column("details", sqlalchemy.String),
)
