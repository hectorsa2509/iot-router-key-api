#!/bin/bash
set -e

SSH_KEYS_DIR="${SSH_KEYS_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ssh_keys}"
AUTHORIZED_KEYS="${AUTHORIZED_KEYS:-$HOME/.ssh/authorized_keys}"
KEY_OWNER="${KEY_OWNER:-$(id -un)}"
KEY_GROUP="${KEY_GROUP:-$(id -gn)}"

# Asegurar .ssh
mkdir -p "$(dirname "$AUTHORIZED_KEYS")"
chown "$KEY_OWNER:$KEY_GROUP" "$(dirname "$AUTHORIZED_KEYS")"
chmod 700 "$(dirname "$AUTHORIZED_KEYS")"

# Asegurar authorized_keys
touch "$AUTHORIZED_KEYS"
chown "$KEY_OWNER:$KEY_GROUP" "$AUTHORIZED_KEYS"
chmod 600 "$AUTHORIZED_KEYS"

for pubkey in "$SSH_KEYS_DIR"/*.pub; do
    [ -f "$pubkey" ] || continue

    chown "$KEY_OWNER:$KEY_GROUP" "$pubkey"
    chmod 644 "$pubkey"

    if ! grep -qxF "$(cat "$pubkey")" "$AUTHORIZED_KEYS"; then
        cat "$pubkey" >> "$AUTHORIZED_KEYS"
        echo "✅ Añadida clave pública: $(basename "$pubkey")"
    fi
done
