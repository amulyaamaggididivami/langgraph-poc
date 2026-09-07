from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.constants.config import (
    APP_TITLE,
    CORS_ALLOWED_HEADERS,
    CORS_ALLOWED_METHODS,
    CORS_ALLOWED_ORIGINS,
)

app = FastAPI(title=APP_TITLE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=CORS_ALLOWED_METHODS,
    allow_headers=CORS_ALLOWED_HEADERS,
)

app.include_router(health.router, tags=["health"])
