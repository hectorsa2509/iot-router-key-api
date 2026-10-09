from datetime import datetime
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, model_validator
# === Helper para MAC ===
def format_mac(raw_mac: str) -> str:
    """
    Convierte una MAC en diferentes formatos posibles
    al estándar en minúsculas con ':'
    Ejemplo: '9483c470bb3f' -> '94:83:c4:70:bb:3f'
    """
    if not raw_mac:
        return None
    raw_mac = raw_mac.strip().lower().replace(":", "").replace("-", "")
    if len(raw_mac) != 12:
        return raw_mac  # si no es válido, lo regresa tal cual
    return ":".join(raw_mac[i:i+2] for i in range(0, 12, 2))

class Router(BaseModel):
    mac_address: str = Field(..., alias="macAddress", max_length=17)
    router_model_id: Optional[str] = Field(None, alias="routerModelId")
    household_id: Optional[str] = Field(None, alias="householdId")
    version: str = "1.0.0"
    active: bool = True
    port: Optional[int] = None
    ssh_key_file: Optional[str] = Field(None, alias="sshKeyFile")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    last_checked_at: Optional[datetime] = Field(None, alias="lastCheckedAt")
    v: int = Field(0, alias="__v")

    # 🔧 Validador de modelo para convertir ObjectId → str
    @model_validator(mode="before")
    def convert_objectids(cls, values):
        """
        Convierte todos los ObjectId (routerModelId, householdId, etc.)
        a string antes de validar el modelo.
        """
        for field in ("routerModelId", "householdId"):
            if isinstance(values.get(field), ObjectId):
                values[field] = str(values[field])
        return values

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}