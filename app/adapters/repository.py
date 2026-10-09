from database import routers_collection
from datetime import datetime
from models import Router,format_mac  
PORT_RANGE = range(22000, 29999)
from pymongo.errors import DuplicateKeyError
def assign_available_port():
    used_ports = set(routers_collection.distinct("port"))
    for port in PORT_RANGE:
        if port not in used_ports and port is not None:  # evita los null
            return port
    raise Exception("No available ports")



def get_or_create_device(mac: str, key_file: str) -> Router:
    now = datetime.utcnow()
    formatted_mac = format_mac(mac)

    device = routers_collection.find_one({"macAddress": formatted_mac})
    if device:
        routers_collection.update_one(
            {"macAddress": formatted_mac},
            {"$set": {
                "lastCheckedAt": now,
                "sshKeyFile": key_file,
                "updatedAt": now
            }}
        )
        device = routers_collection.find_one({"macAddress": formatted_mac})
        return Router(**device)

    for _ in range(10):  # hasta 10 intentos
        try:
            port = assign_available_port()
            device = {
                "macAddress": formatted_mac,
                "sshKeyFile": key_file,
                "port": port,
                "routerModelId": None,
                "householdId": None,
                "version": "1.0.2",
                "active": True,
                "createdAt": now,
                "updatedAt": now,
                "lastCheckedAt": now,
                "__v": 0
            }
            routers_collection.insert_one(device)
            return Router(**device)

        except DuplicateKeyError:
            # alguien más tomó ese puerto, reintenta
            continue

    raise Exception("No available ports after retries")


def get_device_port(mac: str):
    device = routers_collection.find_one({"macAddress": format_mac(mac)}, {"port": 1})
    return device.get("port") if device else None


def update_device_ssh_key(mac: str, key_file: str):
    formatted_mac = format_mac(mac)

    routers_collection.update_one(
        {"macAddress": formatted_mac},
        {
            "$set": {
                "sshKeyFile": key_file,
                "updatedAt": datetime.utcnow(),
                "lastCheckedAt": datetime.utcnow()
            }
        }
    )
