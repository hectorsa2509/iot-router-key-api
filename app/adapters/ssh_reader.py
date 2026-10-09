import os
import subprocess
from dotenv import load_dotenv
import base64
import pathlib
from filelock import FileLock

load_dotenv()
SSH_KEYS_PATH = os.getenv("SSH_KEYS_PATH", "./ssh_keys")
AUTHORIZED_KEYS_PATH = os.getenv("AUTHORIZED_KEYS_PATH", str(pathlib.Path.home() / ".ssh/authorized_keys"))

os.makedirs(SSH_KEYS_PATH, exist_ok=True)

def get_key_filename(mac: str):
    return mac.replace(':', '')

def generate_ssh_key(mac: str):
    key_name = get_key_filename(mac)
    private_key_path = os.path.join(SSH_KEYS_PATH, key_name)
    public_key_path = private_key_path + ".pub"

    try:
        
        subprocess.run([
            "dropbearkey", "-t", "rsa", "-s", "1024", "-f", private_key_path
        ], check=True)

       
        result = subprocess.run(
            ["dropbearkey", "-y", "-f", private_key_path],
            check=True, stdout=subprocess.PIPE, text=True
        )

        pub_key = ""
        for line in result.stdout.splitlines():
            if line.startswith("ssh-rsa "):
                pub_key = line.strip()
                with open(public_key_path, "w") as pub_file:
                    pub_file.write(pub_key + "\n")
                break

        if not pub_key:
            print("No se encontró la clave pública en la salida de dropbearkey")
            return None

        
        ssh_dir = os.path.dirname(AUTHORIZED_KEYS_PATH)
        os.makedirs(ssh_dir, exist_ok=True)
        os.chmod(ssh_dir, 0o700)

        authorized_keys_file = pathlib.Path(AUTHORIZED_KEYS_PATH)

        
        existing_keys = []
        if authorized_keys_file.exists():
            existing_keys = authorized_keys_file.read_text().splitlines()

       
        if pub_key not in existing_keys:
            with authorized_keys_file.open("a") as ak_file:
                ak_file.write(pub_key + "\n")
                print(f"Clave pública añadida a {AUTHORIZED_KEYS_PATH}")
        else:
            print(f"Clave pública ya existe en {AUTHORIZED_KEYS_PATH}")

        # Permisos estrictos para seguridad
        authorized_keys_file.chmod(0o600)

        print(f"Clave SSH generada correctamente para MAC: {mac}")
        return private_key_path

    except subprocess.CalledProcessError as e:
        print(f"Error al generar clave SSH para {mac}: {e}")
        return None



def get_ssh_key(mac: str):
    key_name = get_key_filename(mac)
    private_key_path = os.path.join(SSH_KEYS_PATH, key_name)
    lock_path = private_key_path + ".lock"

    with FileLock(lock_path):
        if not os.path.exists(private_key_path):
            created_path = generate_ssh_key(mac)
            if created_path is None:
                return None

    with open(private_key_path, "rb") as f:
        encoded_key = base64.b64encode(f.read()).decode("utf-8")
        return encoded_key, os.path.basename(private_key_path)

