from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.api.routes.chat import register_chat_route
from app.constants.config import (
    APP_TITLE,
    CORS_ALLOWED_HEADERS,
    CORS_ALLOWED_METHODS,
    CORS_ALLOWED_ORIGINS,
)
from app.persistence.checkpointer import build_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Real AsyncPostgresSaver (TASK-ORCHESTRATION-013) — the
    # requests/checkpoint tables live in the same Postgres instance as
    # the business tables (decision-30). Built here, not at module
    # import time, because building it is async (see checkpointer.py's
    # module docstring for why it must be the async saver, not the sync
    # one). ag-ui-langgraph requires the compiled graph to have a
    # checkpointer at all (confirmed by the TASK-ORCHESTRATION-001
    # spike), independent of whether the approval gate (TASK-014)
    # exists yet.
    checkpointer = await build_checkpointer()
    register_chat_route(app, checkpointer=checkpointer)
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=CORS_ALLOWED_METHODS,
    allow_headers=CORS_ALLOWED_HEADERS,
)

app.include_router(health.router, tags=["health"])
