import os
import secrets
from dotenv import load_dotenv
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.adapters.repository import get_device_port

load_dotenv()

# Lista separada por comas para poder rotar keys sin cortar a los routers
API_KEYS = [key.strip() for key in os.getenv("API_KEYS", "").split(",") if key.strip()]

# Routers ya en campo con firmware que no manda API key. Solo aplica a routers
# ya registrados; quitar cuando se actualice su firmware.
LEGACY_PORTS = set(range(23100, 23118)) | {
    22049, 22057, 22384, 22408, 22409, 22411, 22412,
    22416, 22418, 22421, 22645, 22654, 22747, 22749,
}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(mac: str, api_key: str = Security(api_key_header)):
    if not API_KEYS:
        print("API_KEYS is not configured; rejecting request")
        raise HTTPException(status_code=500, detail="Internal server error")

    if api_key and any(
        secrets.compare_digest(api_key.encode(), key.encode()) for key in API_KEYS
    ):
        return

    port = get_device_port(mac)
    if port in LEGACY_PORTS:
        print(f"Allowing request without API key for legacy router {mac} (port {port})")
        return

    raise HTTPException(status_code=401, detail="Invalid or missing API key")
