from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import MemorySaver

from app.api.routes import health
from app.api.routes.chat import register_chat_route
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

# MemorySaver until TASK-ORCHESTRATION-013 wires a real PostgresSaver —
# ag-ui-langgraph requires the compiled graph to have a checkpointer at
# all (confirmed by the TASK-ORCHESTRATION-001 spike), independent of
# whether the approval gate (TASK-014) exists yet.
register_chat_route(app, checkpointer=MemorySaver())
