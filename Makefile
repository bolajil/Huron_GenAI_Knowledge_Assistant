.PHONY: help up up-test up-prod-like down build test test-int lint typecheck clean

# ── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Huron GenAI — Developer Commands"
	@echo "---------------------------------"
	@echo "  make up            Start local dev (SQLite, no external deps)"
	@echo "  make up-test       Start integration test env (PostgreSQL + Redis)"
	@echo "  make up-prod-like  Start prod-like env (same as up-test + built images)"
	@echo "  make down          Stop all containers"
	@echo "  make build         Build both Docker images"
	@echo "  make test          Run backend unit tests"
	@echo "  make test-int      Run backend integration tests (requires up-test)"
	@echo "  make lint          Lint frontend (ESLint) + backend (ruff)"
	@echo "  make typecheck     TypeScript type-check frontend"
	@echo "  make clean         Remove containers, volumes, and build cache"
	@echo ""

# ── Local dev ────────────────────────────────────────────────────────────────
up:
	docker compose -f docker-compose.local.yml up --build

down:
	docker compose -f docker-compose.local.yml down
	docker compose -f docker-compose.test.yml down

# ── Integration test env ──────────────────────────────────────────────────────
up-test:
	docker compose -f docker-compose.test.yml up -d --build
	@echo "Waiting for services…"
	@sleep 5
	@docker compose -f docker-compose.test.yml ps

up-prod-like: up-test

# ── Build ─────────────────────────────────────────────────────────────────────
build:
	docker compose -f docker-compose.local.yml build

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	@echo "==> Running backend unit tests"
	cd backend && python -m pytest ../tests/unit -v --tb=short

test-int:
	@echo "==> Running backend integration tests (needs up-test first)"
	@echo "    Backend URL: http://localhost:8005"
	cd backend && DATABASE_URL=postgresql://huron:hurontest@localhost:5437/huron_test \
		REDIS_URL=redis://localhost:6380/0 \
		JWT_SECRET_KEY=test-jwt-secret-key-32-bytes-xx \
		MCP_ENCRYPTION_KEY=test-mcp-key-32-bytes-xxxxxxxx \
		python -m pytest ../tests/integration -v --tb=short

# ── Lint / typecheck ──────────────────────────────────────────────────────────
lint:
	@echo "==> ESLint (frontend)"
	cd frontend && npm run lint
	@echo "==> ruff (backend)"
	cd backend && python -m ruff check . || true

typecheck:
	@echo "==> TypeScript check (frontend)"
	cd frontend && npx tsc --noEmit

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	docker compose -f docker-compose.local.yml down -v --remove-orphans
	docker compose -f docker-compose.test.yml down -v --remove-orphans
	docker system prune -f
