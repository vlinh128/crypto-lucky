.PHONY: clean build up down logs ps install test run test-file test-coverage format lint

# Docker commands
# Dừng containers và xóa tất cả
clean-docker:
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
restart: clean-docker build up

# Clean và start với logs
restart-logs: clean-docker build up-logs

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

# Python development commands
# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	PYTHONPATH=. pytest tests/ -v

# Run specific test file
test-file:
	PYTHONPATH=. pytest $(file) -v

# Run the application
run:
	python web_server.py

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +

# Run all tests with coverage report
test-coverage:
	PYTHONPATH=. pytest tests/ --cov=src --cov-report=html -v

# Format code using black
format:
	black src/ tests/

# Check code style using flake8
lint:
	flake8 src/ tests/ 