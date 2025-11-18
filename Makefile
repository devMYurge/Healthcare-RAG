
# Makefile for common developer tasks (uses centralized .venv)

.PHONY: venv install backend frontend dev docker-up docker-down clean

venv:
	@echo "Creating project virtualenv at ./.venv (if missing)..."
	@test -d ./.venv || python3 -m venv ./.venv

install: venv
	@echo "Installing Python dependencies into ./.venv..."
	@./.venv/bin/pip install --upgrade pip
	@./.venv/bin/pip install -r requirements.txt

backend:
	@echo "Starting backend (foreground)..."
	@./.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@echo "Starting frontend (will install deps if needed)..."
	@cd frontend && npm install && npm run dev

dev: install
	@echo "Running project dev helper script..."
	@./scripts/dev.sh

docker-up:
	@echo "Starting application via docker-compose..."
	@docker-compose up -d --build

docker-down:
	@echo "Stopping docker-compose services..."
	@docker-compose down

clean:
	@echo "Removing local .venv and frontend node_modules (if present)"
	@rm -rf ./.venv
	@cd frontend && rm -rf node_modules || true
