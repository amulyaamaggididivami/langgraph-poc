.PHONY: backend frontend migrate

backend:
	cd backend && uv run uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

# Applies backend/migrations/*.sql in order against $DATABASE_URL.
migrate:
	for f in backend/migrations/*.sql; do \
		echo "applying $$f"; \
		psql "$(DATABASE_URL)" -v ON_ERROR_STOP=1 -f "$$f" || exit 1; \
	done
