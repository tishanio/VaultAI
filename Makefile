.PHONY: help install dev test lint build deploy clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	cd frontend/dashboard && npm install
	pip install -r services/api-gateway/requirements.txt

dev: ## Start all services with Docker Compose
	docker compose up -d postgres redis
	@sleep 3
	cd services/api-gateway && alembic upgrade head &
	cd services/api-gateway && uvicorn main:app --reload --port 8000 &
	cd frontend/dashboard && npm run dev

dev-docker: ## Start everything with Docker Compose
	docker compose up

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd services/api-gateway && pytest --cov=. --cov-report=term -v

test-frontend: ## Run frontend tests
	cd frontend/dashboard && npm test -- --run

test-load: ## Run load tests
	cd tests/load && k6 run --vus 10 --duration 30s scenario.js

lint: ## Run linters
	ruff check vault/ services/
	cd frontend/dashboard && npm run lint

typecheck: ## Run type checks
	cd frontend/dashboard && npm run typecheck

build: ## Build all Docker images
	docker compose build

clean: ## Clean up
	docker compose down -v
	rm -rf frontend/dashboard/node_modules
	rm -rf services/api-gateway/__pycache__

seed-demo: ## Seed demo data
	curl -X POST http://localhost:8000/api/v1/demo/seed

health: ## Check all service health
	@echo "API Gateway:     $$(curl -s http://localhost:8000/health | python -m json.tool)"
	@echo "Usage Intel:     $$(curl -s http://localhost:8001/health | python -m json.tool)"
	@echo "Trust:           $$(curl -s http://localhost:8002/health | python -m json.tool)"
	@echo "Matching:        $$(curl -s http://localhost:8003/health | python -m json.tool)"
	@echo "Financial:       $$(curl -s http://localhost:8004/health | python -m json.tool)"
	@echo "Compliance:      $$(curl -s http://localhost:8005/health | python -m json.tool)"
