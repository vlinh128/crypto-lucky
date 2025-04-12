.PHONY: clean build up down logs ps

# Dừng containers và xóa tất cả
clean:
	docker compose down
	docker compose down --rmi all
	docker system prune -a -f

# Build lại images
build:
	docker compose build --no-cache

# Start các services
up:
	docker compose up -d

# Start có logs
up-logs:
	docker compose up

# Dừng các services
down:
	docker compose down

# Xem logs
logs:
	docker compose logs -f

# Xem trạng thái
ps:
	docker compose ps

# Clean và start lại (hay dùng nhất)
restart: clean build up

# Clean và start với logs
restart-logs: clean build up-logs

# Chỉ restart containers không clean
soft-restart:
	docker compose restart

# Build một service cụ thể
build-backend:
	docker compose build --no-cache backend

build-frontend:
	docker compose build --no-cache frontend

# Restart một service cụ thể
restart-backend: build-backend
	docker compose up -d --no-deps backend

restart-frontend: build-frontend
	docker compose up -d --no-deps frontend