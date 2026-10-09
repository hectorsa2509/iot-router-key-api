"""
Quita las llaves SSH de los routers eliminados de la base.

Lee el export JSON de los routers borrados, mueve sus archivos de SSH_KEYS_PATH
a ssh_keys_backup/<fecha>/ y quita sus llaves publicas de authorized_keys.
Solo toca llaves cuya fecha de archivo cae entre el createdAt y el ultimo
lastCheckedAt/updatedAt de su router. Sin --apply solo muestra lo que haria;
con --list imprime cada archivo con su fecha y la de su router.

Uso: python delete_router_keys.py <routers_deleted.json> [--list] [--apply]
"""
import base64
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from dotenv import load_dotenv

from database import routers_collection

load_dotenv()

SSH_KEYS_PATH = os.getenv("SSH_KEYS_PATH", "./ssh_keys")
AUTHORIZED_KEYS_PATH = os.getenv("AUTHORIZED_KEYS_PATH")
BACKUP_ROOT = os.getenv("KEYS_BACKUP_PATH", "./ssh_keys_backup")

# Los routers piden su llave con la MAC en minusculas y sin ':'
ROUTER_KEY_NAME = re.compile(r"^[0-9a-f]{12}$")

# Tolerancia entre la fecha del archivo y las fechas del router en la base
DATE_MARGIN = timedelta(minutes=5)


def key_names(router):
    names = {router.get("sshKeyFile"), (router.get("macAddress") or "").replace(":", "")}
    return {name for name in names if name}


def is_safe_name(name):
    return name == os.path.basename(name) and name not in (".", "..") and "\x00" not in name


def key_stem(filename):
    for suffix in (".pub", ".lock"):
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    return filename


def parse_date(value):
    if isinstance(value, dict):
        value = value.get("$date")
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


def router_window(router):
    """Rango en que se pudieron escribir los archivos de la llave del router."""
    created = parse_date(router.get("createdAt"))
    if created is None:
        return None
    last = max(d for d in (created, parse_date(router.get("lastCheckedAt")),
                           parse_date(router.get("updatedAt"))) if d)
    return created - DATE_MARGIN, last + DATE_MARGIN


def file_date(path):
    return datetime.fromtimestamp(os.stat(path).st_mtime, timezone.utc)


def fmt(date):
    return date.strftime("%Y-%m-%d %H:%M:%S") if date else "?"


def fingerprint(blob):
    digest = hashlib.sha256(base64.b64decode(blob)).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


def sample(items, limit=15):
    items = sorted(items)
    shown = ", ".join(repr(item) for item in items[:limit])
    return shown + (f" ... (+{len(items) - limit})" if len(items) > limit else "")


def main():
    flags = {"--apply", "--list"}
    args = [arg for arg in sys.argv[1:] if arg not in flags]
    apply = "--apply" in sys.argv[1:]
    show_list = "--list" in sys.argv[1:]
    if len(args) != 1:
        sys.exit(__doc__)

    with open(args[0]) as f:
        deleted = json.load(f)
    deleted_ids = [ObjectId(router["_id"]["$oid"]) for router in deleted]

    # Llaves que todavia usa algun router que se queda en la base
    protected = set()
    for router in routers_collection.find(
        {"_id": {"$nin": deleted_ids}}, {"macAddress": 1, "sshKeyFile": 1}
    ):
        protected |= key_names(router)

    unsafe, skipped, candidates = set(), set(), {}
    for router in deleted:
        for name in key_names(router):
            if not is_safe_name(name):
                unsafe.add(name)
            elif name in protected:
                skipped.add(name)
            else:
                candidates.setdefault(name, []).append(router)

    # Una llave se quita solo si todos sus archivos tienen fecha dentro del rango de su router
    files, dated, out_of_range = set(), [], []
    for name, routers in candidates.items():
        paths = [
            path for path in (os.path.join(SSH_KEYS_PATH, name + s) for s in ("", ".pub", ".lock"))
            if os.path.isfile(path) and not os.path.islink(path)
        ]
        if not paths:
            continue
        dates = {path: file_date(path) for path in paths}
        windows = [w for w in (router_window(r) for r in routers) if w]
        created = parse_date(routers[0].get("createdAt"))
        bad = sorted(d for d in dates.values() if not any(start <= d <= end for start, end in windows))
        if bad:
            out_of_range.append((bad[0], created, name))
        else:
            files.update(paths)
            dated += [(d, created, os.path.basename(path)) for path, d in dates.items()]

    blobs = set()
    for path in files:
        if path.endswith(".pub"):
            with open(path) as f:
                parts = f.read().split()
            if len(parts) >= 2 and parts[0].startswith("ssh-"):
                blobs.add(parts[1])

    authorized_lines, revoked_lines = [], []
    if AUTHORIZED_KEYS_PATH and os.path.isfile(AUTHORIZED_KEYS_PATH):
        with open(AUTHORIZED_KEYS_PATH) as f:
            authorized_lines = f.read().splitlines()
        revoked_lines = [line for line in authorized_lines if blobs & set(line.split())]

    moving = {os.path.basename(path) for path in files}
    out_of_range_names = {name for _, _, name in out_of_range}
    leftovers = {
        filename for filename in os.listdir(SSH_KEYS_PATH)
        if filename not in moving
        and key_stem(filename) not in out_of_range_names
        and not ROUTER_KEY_NAME.match(key_stem(filename))
        and key_stem(filename) not in protected
    }

    if show_list:
        print("fecha archivo (UTC)  router creado (UTC)  archivo")
        for file_dt, created, filename in sorted(dated):
            print(f"{fmt(file_dt)}  {fmt(created)}  {filename!r}")
        print()

    print(f"Routers en el JSON: {len(deleted)}")
    print(f"Archivos a quitar de {SSH_KEYS_PATH}: {len(files)} ({len(blobs)} llaves publicas)")
    if dated:
        print("  Por fecha del archivo (UTC):")
        for day, count in sorted(Counter(fmt(d)[:10] for d, _, _ in dated).items()):
            print(f"    {day}: {count}")
    if AUTHORIZED_KEYS_PATH:
        print(f"Lineas a quitar de {AUTHORIZED_KEYS_PATH}: {len(revoked_lines)} de {len(authorized_lines)}")
    else:
        print("AUTHORIZED_KEYS_PATH no definido: no se revisa authorized_keys")
    if out_of_range:
        print(f"\nOmitidas porque la fecha del archivo no coincide con la de su router ({len(out_of_range)}):")
        for file_dt, created, name in sorted(out_of_range)[:15]:
            print(f"  {name!r}: archivo {fmt(file_dt)}, router creado {fmt(created)}")
        if len(out_of_range) > 15:
            print(f"  ... (+{len(out_of_range) - 15})")
    if skipped:
        print(f"Omitidas porque un router que sigue en la base las usa: {sample(skipped)}")
    if unsafe:
        print(f"Omitidos por nombre invalido: {sample(unsafe)}")
    if leftovers:
        print(f"\nOtros archivos en {SSH_KEYS_PATH} que no parecen de un router y no estan en el JSON "
              f"({len(leftovers)}), revisar a mano: {sample(leftovers)}")

    if not apply:
        print("\nModo prueba: no se cambio nada. Agrega --apply para aplicar.")
        return

    backup_dir = os.path.join(BACKUP_ROOT, datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(backup_dir, mode=0o700)

    for path in files:
        if os.path.isfile(path):
            shutil.move(path, os.path.join(backup_dir, os.path.basename(path)))

    if revoked_lines:
        shutil.copy2(AUTHORIZED_KEYS_PATH, os.path.join(backup_dir, "authorized_keys.bak"))
        kept = [line for line in authorized_lines if not blobs & set(line.split())]
        # Se reescribe en el mismo archivo para conservar dueno y permisos
        with open(AUTHORIZED_KEYS_PATH, "w") as f:
            f.write("".join(line + "\n" for line in kept))

    with open(os.path.join(backup_dir, "fingerprints.txt"), "w") as f:
        f.write("".join(fingerprint(blob) + "\n" for blob in sorted(blobs)))

    print(f"\nListo. {len(files)} archivos movidos y {len(revoked_lines)} lineas quitadas de authorized_keys.")
    print(f"Respaldo y huellas de las llaves revocadas en: {backup_dir}")


if __name__ == "__main__":
    main()
