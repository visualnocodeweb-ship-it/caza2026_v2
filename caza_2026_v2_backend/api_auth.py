"""
Autenticación de la API — JWT para el dashboard y API keys para integraciones externas.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

DEFAULT_AUTH_USERS = {
    "Karen": "Karen321",
    "Emanuel": "Emanuel321",
    "Nico": "Nico321",
    "algar": "algarmariano",
    "fauna1": "fauna1nqn",
    "cazamenor": "cazamenor",
    "Maga": "Maga123",
}

DEFAULT_JWT_SECRET = "caza-dev-change-me-in-production"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 2

# Rutas totalmente públicas (sin credenciales)
PUBLIC_API_PATHS: Set[str] = {
    "/api/auth/login",
    "/api/pagos/webhook",
    "/health",
    "/api/fiscalizador/health",
}

PUBLIC_API_PREFIXES = (
    "/api/view-credential/",
)

# Rutas de lectura para apps externas (permisos, fiscalizador, tablero Fauna) con X-API-Key o ?api_key=
EXTERNAL_READ_PREFIXES = (
    "/api/permisos",
    "/api/permisos-menor",
    "/api/fiscalizador/",
    "/api/stats/",
    "/api/inscripciones",
    "/api/reses/stats",
    "/api/guias-traslados/stats",
)

# GETs que el navegador abre sin header Authorization (token por query param)
BROWSER_GET_PREFIXES = (
    "/api/guias-traslados/",
    "/api/reses/view-pdf/",
    "/api/convert-heic",
)

SENSITIVE_LIST_FIELDS = {
    "pdf_link",
    "payment_id",
    "fecha_pago",
    "sent_statuses",
    "docx_link",
    "docx_id",
}


def get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)


def get_auth_users() -> Dict[str, str]:
    raw = os.getenv("AUTH_USERS_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return DEFAULT_AUTH_USERS.copy()


def get_external_api_keys() -> Set[str]:
    raw = os.getenv("EXTERNAL_API_KEYS", "")
    keys = {k.strip() for k in raw.split(",") if k.strip()}
    return keys


def get_allowed_origins() -> List[str]:
    raw = os.getenv(
        "ALLOWED_ORIGINS",
        "https://caza2026-frontend.onrender.com,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "https://fiscalizador-caza-2026.onrender.com,"
        "http://localhost:5174",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


def authenticate_user(username: str, password: str) -> Optional[str]:
    users = get_auth_users()
    user_key = next((k for k in users if k.lower() == username.lower()), None)
    if user_key and users[user_key] == password:
        return user_key
    return None


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "scope": "admin",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _is_public_path(path: str) -> bool:
    if path in PUBLIC_API_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES)


def _is_external_read_path(path: str, method: str) -> bool:
    if method != "GET":
        return False
    return any(path.startswith(prefix) for prefix in EXTERNAL_READ_PREFIXES)


def _extract_api_key(request: Request) -> Optional[str]:
    header_key = request.headers.get("X-API-Key")
    if header_key:
        return header_key.strip()
    query_key = request.query_params.get("api_key")
    if query_key:
        return query_key.strip()
    return None


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    query_token = request.query_params.get("access_token")
    if query_token:
        return query_token.strip()
    return None


def resolve_auth_scope(request: Request) -> Optional[str]:
    """Devuelve 'admin', 'external_read' o None si no está autenticado."""
    api_key = _extract_api_key(request)
    external_keys = get_external_api_keys()

    if api_key and api_key in external_keys:
        if _is_external_read_path(request.url.path, request.method):
            return "external_read"
        return None

    token = _extract_bearer_token(request)
    if token:
        payload = decode_access_token(token)
        if payload and payload.get("scope") == "admin":
            return "admin"

    return None


def sanitize_external_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Quita campos sensibles en respuestas para integraciones externas."""
    return {k: v for k, v in record.items() if k not in SENSITIVE_LIST_FIELDS}


def sanitize_external_list(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [sanitize_external_record(item) for item in data]


class APIAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if not path.startswith("/api"):
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        if _is_public_path(path):
            request.state.auth_scope = "public"
            return await call_next(request)

        scope = resolve_auth_scope(request)

        if scope:
            request.state.auth_scope = scope
            return await call_next(request)

        # PDFs / imágenes abiertas en el navegador: aceptar token en query string
        if request.method == "GET" and any(path.startswith(p) for p in BROWSER_GET_PREFIXES):
            token = _extract_bearer_token(request)
            if token and decode_access_token(token):
                request.state.auth_scope = "admin"
                return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "Autenticación requerida. Inicie sesión o envíe X-API-Key."},
        )
