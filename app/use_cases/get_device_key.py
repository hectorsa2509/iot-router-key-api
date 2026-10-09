from app.adapters.repository import (
    get_or_create_device,
    update_device_ssh_key
)
from app.adapters.ssh_reader import get_ssh_key


def handle_get_device_key(mac: str):
   
    device = get_or_create_device(mac, key_file=None)

    key_data = get_ssh_key(mac)
    if key_data is None:
        return None

    private_key, filename = key_data
    
    update_device_ssh_key(mac, filename)

    return {
        "mac_address": device.mac_address,
        "port": device.port,
        "ssh_private_key": private_key,
        "last_checked_at": device.last_checked_at,
        "created_at": device.created_at
    }
