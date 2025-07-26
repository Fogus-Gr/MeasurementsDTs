# Docker H.264 Streaming Server Makefile

# Variables
IMAGE_NAME = h264-streaming-server
CONTAINER_NAME = h264-streaming-server
PORT = 8080
VIDEO_DIR = ./videos

# Default target
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  build       - Build the Docker image"
	@echo "  run         - Run the container with default settings"
	@echo "  run-dev     - Run container in development mode"
	@echo "  run-prod    - Run with nginx proxy (production)"
	@echo "  stop        - Stop the running container"
	@echo "  clean       - Remove container and image"
	@echo "  logs        - View container logs"
	@echo "  shell       - Get shell access to running container"
	@echo "  test        - Test the streaming endpoint"
	@echo "  setup       - Create necessary directories"

# Build the Docker image
.PHONY: build
build:
	docker build -t $(IMAGE_NAME) .

# Run container with default settings
.PHONY: run
run: setup
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p $(PORT):8080 \
		-v $(VIDEO_DIR):/app/videos:ro \
		--restart unless-stopped \
		$(IMAGE_NAME)

# Run in development mode (with live logs)
.PHONY: run-dev
run-dev: setup
	docker run --rm -it \
		--name $(CONTAINER_NAME)-dev \
		-p $(PORT):8080 \
		-v $(VIDEO_DIR):/app/videos:ro \
		-v $(PWD):/app \
		$(IMAGE_NAME) \
		python direct_stream_server.py --video /app/videos/video.mp4 --port 8080

# Run with docker-compose (production with nginx)
.PHONY: run-prod
run-prod: setup
	docker-compose --profile production up -d

# Stop the container
.PHONY: stop
stop:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

# Clean up Docker resources
.PHONY: clean
clean:
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true
	docker rmi $(IMAGE_NAME) || true
	docker-compose down --volumes --remove-orphans || true

# View logs
.PHONY: logs
logs:
	docker logs -f $(CONTAINER_NAME)

# Get shell access
.PHONY: shell
shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

# Test the streaming endpoint
.PHONY: test
test:
	@echo "Testing streaming endpoint..."
	curl -I http://localhost:$(PORT)/stream.h264 || echo "Server not responding"
	@echo "Test with: ffplay http://localhost:$(PORT)/stream.h264"

# Setup directories (Cross-platform)
.PHONY: setup
setup:
ifeq ($(OS),Windows_NT)
	@powershell -Command "if (!(Test-Path '$(VIDEO_DIR)')) { New-Item -ItemType Directory -Path '$(VIDEO_DIR)' -Force }"
	@powershell -Command "if (!(Test-Path 'config')) { New-Item -ItemType Directory -Path 'config' -Force }"
	@powershell -Command "if (!(Test-Path 'ssl')) { New-Item -ItemType Directory -Path 'ssl' -Force }"
	@echo Created directories: $(VIDEO_DIR), config, ssl
	@echo Place your video files in $(VIDEO_DIR)/
	@echo Rename your main video to 'video.mp4' or update the configuration
else
	mkdir -p $(VIDEO_DIR)
	mkdir -p ./config
	mkdir -p ./ssl
	@echo "Created directories: $(VIDEO_DIR), ./config, ./ssl"
	@echo "Place your video files in $(VIDEO_DIR)/"
	@echo "Rename your main video to 'video.mp4' or update the configuration"
endif

# Docker-compose shortcuts
.PHONY: up down restart
up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

# Health check
.PHONY: health
health:
	docker exec $(CONTAINER_NAME) curl -f http://localhost:8080/ || echo "Health check failed"

# Show container status
.PHONY: status
status:
	docker ps -a --filter name=$(CONTAINER_NAME)
	@echo ""
	docker stats $(CONTAINER_NAME) --no-stream || true
