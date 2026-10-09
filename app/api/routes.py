from fastapi import APIRouter, Depends, HTTPException
from app.api.security import require_api_key
from app.use_cases.get_device_key import handle_get_device_key
from fastapi.responses import PlainTextResponse
router = APIRouter()

ASCII_ART = "IoT Router Key API\n"


@router.get("/device/{mac}", dependencies=[Depends(require_api_key)])
def get_device(mac: str):
    try:
        result = handle_get_device_key(mac)
        if result is None:
            raise HTTPException(status_code=404, detail="Key not found")
        return result
    except Exception as e:
        print(f"Internal server error while fetching key for {mac}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_class=PlainTextResponse)
def root():
    return ASCII_ART

@router.get("/api", response_class=PlainTextResponse)
def api_info():
    return ASCII_ART