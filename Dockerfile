# Imagen base con Python 3.10
FROM python:3.10-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias necesarias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    dropbear-bin \
    gcc \
    libpq-dev \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Copiar los archivos del proyecto
COPY . .

# Instalar dependencias de Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Crear carpeta para llaves SSH
RUN mkdir -p /app/ssh_keys
RUN chmod 700 /app/ssh_keys

# Establecer variable de entorno para ruta de llaves
ENV SSH_KEYS_PATH=/app/ssh_keys

# Puerto expuesto (ajústalo si cambias FastAPI)
EXPOSE 8000

# Comando por defecto: ejecutar el servidor FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
