import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
MONGO_DB = os.getenv("MONGO_DB")

if not MONGO_URL or not MONGO_DB:
    raise ValueError("Faltan variables MONGO_URL o MONGO_DB en el entorno o archivo .env")


client = MongoClient(MONGO_URL)
db = client[MONGO_DB]
collection = db["routers"]


def parse_date(value):
    """Convierte strings o timestamps a datetime seguro."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 1e12 else value)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return datetime.min


pipeline = [
    {
        "$group": {
            "_id": {"$toLower": "$macAddress"},
            "docs": {"$push": "$$ROOT"},
            "count": {"$sum": 1}
        }
    },
    {"$match": {"count": {"$gt": 1}}}
]

duplicates = list(collection.aggregate(pipeline))
print(f"Se encontraron {len(duplicates)} MACs duplicadas.")

for group in duplicates:
    docs = group["docs"]
    docs.sort(key=lambda d: parse_date(d.get("updatedAt")), reverse=True)
    keep = docs[0]
    to_remove = docs[1:]

    keep["macAddress"] = keep["macAddress"].lower()

    merge_fields = ["householdId", "routerModelId", "lastCheckedAt", "port", "sshKeyFile"]
    for d in to_remove:
        for field in merge_fields:
            if (keep.get(field) in (None, "", "null")) and d.get(field) not in (None, "", "null"):
                keep[field] = d[field]

    for field in merge_fields:
        if field not in keep:
            keep[field] = None

    #  1. Borrar duplicados primero
    ids_to_delete = [d["_id"] for d in to_remove]
    if ids_to_delete:
        collection.delete_many({"_id": {"$in": ids_to_delete}})

    #  2. Actualizar el documento principal con la info combinada
    collection.update_one(
        {"_id": keep["_id"]},
        {"$set": {
            "macAddress": keep["macAddress"],
            "householdId": keep.get("householdId"),
            "routerModelId": keep.get("routerModelId"),
            "lastCheckedAt": keep.get("lastCheckedAt"),
            "port": keep.get("port"),
            "sshKeyFile": keep.get("sshKeyFile"),
        }}
    )

    print(f" Eliminados duplicados de {keep['macAddress']} -> {len(ids_to_delete)} registros")

print(" Limpieza completada con éxito.")
