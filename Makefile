.PHONY: backend

backend:
	cd backend && uv run uvicorn app.main:app --reload
