VOLUME_NAME=my-ssh-keys
IMAGE_NAME=my-fastapi-app
CONTAINER_NAME=my-fastapi-container
PORT=8000
AUTHORIZED_KEYS ?= $(HOME)/.ssh/authorized_keys
.PHONY: help build run stop volume clean logs shell migrate delete-keys check-container restart

help:
	@echo "Comandos disponibles:"
	@echo "  make build        - Construir la imagen Docker"
	@echo "  make run          - Ejecutar el contenedor con volumen persistente"
	@echo "  make stop         - Detener y eliminar el contenedor"
	@echo "  make volume       - Crear volumen Docker"
	@echo "  make clean        - Eliminar imagen y contenedor"
	@echo "  make logs         - Logs del contenedor"
	@echo "  make shell        - Acceder al contenedor"
	@echo "  make delete-keys FILE=<json> [LIST=1] [APPLY=1] - Quitar llaves de routers eliminados"

volume:
	docker volume create $(VOLUME_NAME)

build:
	docker build -t $(IMAGE_NAME) .


run: stop
	docker run -d \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		-p $(PORT):8000 \
		-v ./ssh_keys:/keys \
		-v $(CURDIR):/app \
		--env SSH_KEYS_PATH=/keys \
		$(IMAGE_NAME)

check-container:
	@docker ps -q -f name=$(CONTAINER_NAME) | grep -q . || \
		( echo "❌ El contenedor '$(CONTAINER_NAME)' no está corriendo. Ejecuta 'make run' primero."; exit 1 )


migrate:
	docker run --rm \
		-v ./ssh_keys:/keys \
		-v $(CURDIR):/app \
		--env SSH_KEYS_PATH=/keys \
		$(IMAGE_NAME) \
		python migrate.py

# Sin APPLY=1 solo muestra lo que haria
delete-keys:
	@test -n "$(FILE)" || ( echo "Uso: make delete-keys FILE=routers_deleted.json [LIST=1] [APPLY=1]"; exit 1 )
	@test -f "$(FILE)" || ( echo "❌ No existe $(FILE)"; exit 1 )
	@test -f "$(AUTHORIZED_KEYS)" || ( echo "❌ No existe $(AUTHORIZED_KEYS)"; exit 1 )
	docker run --rm \
		-v ./ssh_keys:/keys \
		-v $(CURDIR):/app \
		-v $(abspath $(FILE)):/routers_deleted.json:ro \
		-v $(AUTHORIZED_KEYS):/authorized_keys \
		--env SSH_KEYS_PATH=/keys \
		--env AUTHORIZED_KEYS_PATH=/authorized_keys \
		$(IMAGE_NAME) \
		python delete_router_keys.py /routers_deleted.json $(if $(LIST),--list) $(if $(APPLY),--apply)

shell: check-container
	docker exec -it $(CONTAINER_NAME) /bin/bash

stop:
	-docker stop $(CONTAINER_NAME)
	-docker rm $(CONTAINER_NAME)

logs:
	docker logs -f $(CONTAINER_NAME)


clean: stop
	docker rm -f $(CONTAINER_NAME)
	docker rmi -f $(IMAGE_NAME) || true
	docker volume rm $(VOLUME_NAME) || true

test:
	curl -X GET -H "X-API-Key: $(API_KEY)" http://localhost:8000/device/aabbccddee21

restart: stop run
