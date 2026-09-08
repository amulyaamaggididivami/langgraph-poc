"""Shared Postgres connection-string resolution.

trd.md §Deployment & Operations names `DATABASE_URL` as the primary
configuration surface, with the decomposed `DB_*` vars as the form
actually populated in backend/.env. Used by both the checkpointer
(app/persistence/checkpointer.py) and the requests-table repo
(app/persistence/requests_repo.py) — two logically separate connections
into the same `synergy` Postgres instance (decision-30), not a shared
pool, just the same resolution logic so it's a single edit point.
"""

import os


def resolve_conn_string() -> str:
    """Raises `KeyError` with a clear message if neither `DATABASE_URL`
    nor the full `DB_*` set is usable — fails loud, matching
    `get_llm()`'s philosophy elsewhere in this module."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    try:
        host = os.environ["DB_HOST"]
        port = os.environ["DB_PORT"]
        name = os.environ["DB_NAME"]
        user = os.environ["DB_USER"]
        password = os.environ["DB_PASSWORD"]
    except KeyError as e:
        raise KeyError(
            f"{e.args[0]} not set — required to connect to the synergy Postgres "
            "instance when DATABASE_URL is also unset (see backend/.env.example)"
        ) from e
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"
