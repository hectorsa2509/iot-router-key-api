import os
import psycopg2
from pymongo import MongoClient
from sqlalchemy.engine.url import make_url
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# === PostgreSQL ===
DATABASE_URL = os.getenv("DATABASE_URL")
pg_url = make_url(DATABASE_URL)

pg_conn = psycopg2.connect(
    host=pg_url.host,
    port=pg_url.port,
    dbname=pg_url.database,
    user=pg_url.username,
    password=pg_url.password
)
pg_cursor = pg_conn.cursor()

# === MongoDB ===
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "raw-personicore")

mongo_client = MongoClient(MONGO_URL)
mongo_db = mongo_client[MONGO_DB]
routers_collection = mongo_db["routers"]

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

print("Migrando datos de PostgreSQL a MongoDB (colección routers)...")

pg_cursor.execute("""
    SELECT mac_address, ssh_key_file, port, created_at, last_checked_at
    FROM "devices-log";
""")

rows = pg_cursor.fetchall()

for row in rows:
    mac_address, ssh_key_file, port, created_at, last_checked_at = row

    now = datetime.utcnow()
    formatted_mac = format_mac(mac_address)

    doc = {
        "macAddress": formatted_mac, 
        "sshKeyFile": ssh_key_file,
        "port": port,
        "routerModelId": None,        
        "householdId": None,
        "version": "1.0.0",
        "active": True,
        "createdAt": created_at or now,
        "updatedAt": last_checked_at or now,
        "lastCheckedAt": last_checked_at, 
        "__v": 0
    }

    routers_collection.update_one(
        {"macAddress": formatted_mac},  
        {"$set": doc},
        upsert=True
    )

print(f"Migración completada: {len(rows)} routers transferidos.")
