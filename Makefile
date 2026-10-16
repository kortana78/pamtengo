.PHONY: api-install api-test api-lint api-run web-install web-build web-test migrate seed

api-install:
	cd apps/api && pip install -e ".[dev]"

api-test:
	cd apps/api && python -m pytest -q

api-lint:
	cd apps/api && ruff check . && ruff format --check .

api-run:
	cd apps/api && uvicorn app.main:app --reload --port 8000

web-install:
	cd apps/web && npm install

web-build:
	cd apps/web && npm run build

web-test:
	cd apps/web && npm run typecheck

migrate:
	cd apps/api && alembic upgrade head

seed:
	python scripts/seed_demo.py
