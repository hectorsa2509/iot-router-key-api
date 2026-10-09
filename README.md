# iot-router-key-api

A minimal, secure FastAPI-based service that generates and manages SSH public keys for IoT routers based on their MAC addresses. It also stores access logs and device metadata in a PostgreSQL database.

## Features

* Automatically generates RSA 2048 SSH key pairs for given MAC addresses.
* Stores private/public keys on a persistent Docker volume.
* Records device info in PostgreSQL:

  * MAC address
  * SSH public key file name
  * First access date
  * Last query date
* RESTful endpoint to request a device's public key.
* Dockerized and easily deployable.
* Compatible with Google Cloud SQL using Cloud SQL Auth Proxy.

## Project Structure

```
app/
├── main.py                 # FastAPI entry point
├── api/
│   └── routes.py           # API routes
├── use_cases/
│   └── get_device_key.py   # Use case: generate key + save device
├── adapters/
│   ├── ssh_reader.py       # Generate/read SSH keys
│   └── repository.py       # DB operations
models.py                   # SQLAlchemy device model
database.py                 # SQLAlchemy session config
migrate.py                  # Create tables in PostgreSQL
Dockerfile                  # Docker image build config
Makefile                    # Developer task runner
```

## API Endpoint

### GET /device/{mac}

Returns the SSH public key for a given MAC address. If it doesn't exist, it generates it.

Requires the `X-API-Key` header. Valid keys are set in the `API_KEYS` environment variable (comma-separated, so a key can be rotated without downtime). Routers already registered with a port in `LEGACY_PORTS` (23100–23117 plus a list of 22xxx ports, see `app/api/security.py`) are allowed without a key until their firmware is updated. Generate a key with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Response (200 OK)

```
{
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "ssh_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD...",
  "fecha_ingreso": "2025-07-09T23:00:00Z",
  "fecha_consulta": "2025-07-10T00:12:00Z"
}
```

#### Response (401)

```
{
  "detail": "Invalid or missing API key"
}
```

#### Response (500 or 404)

```
{
  "detail": "Llave no encontrada"
}
```

## Running with Docker

### Build the image

```bash
make build
```

### Run the API with persistent SSH key volume

```bash
make run
```

### Access the container

```bash
make shell
```

### Test the API

```bash
make test API_KEY=<your-key>
```

Or manually:

```bash
curl -H "X-API-Key: <your-key>" http://localhost:8000/device/aa:bb:cc:dd:ee:ff
```

## Database: PostgreSQL (via Google Cloud SQL)

This project is compatible with:

* Public IP access (you must whitelist your IP)
* Recommended: Cloud SQL Auth Proxy

You can connect via:

```python
DATABASE_URL = "postgresql://<user>:<password>@localhost:5432/<database>"
```

Or use docker-compose.yml to run the Auth Proxy container.

## Makefile Commands

```bash
make build      # Build the Docker image
make run        # Start the container
make shell      # Enter container shell
make migrate    # Create tables in DB
make logs       # View API logs
make test API_KEY=<key>  # Hit test endpoint
make stop       # Stop container
make clean      # Remove image and volume
```

## Requirements

* Python 3.10+
* Docker
* ssh-keygen (installed in container)
* Google Cloud SQL (optional, recommended with Auth Proxy)



## License

MIT License
