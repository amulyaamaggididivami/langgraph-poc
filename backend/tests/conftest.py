"""Loads backend/.env before any test module's own imports run.

Without this, whether real-infra-dependent tests (e.g. the synergy
Postgres reachability check in test_query_tool.py) see the real env
vars would depend on which test file pytest happens to import first —
app.graph.llm's own `load_dotenv()` call is a side effect of importing
it, not something to rely on from an unrelated test module.
"""

import psycopg
import pytest
from dotenv import load_dotenv

load_dotenv()

_TEST_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/eb-local-poc"


@pytest.fixture(scope="session", autouse=True)
def _clean_requests_table_after_the_suite():
    """The integration test files (test_requests_repo.py,
    test_review_route.py, test_milestone_02.py, ...) all point at the
    same real `eb-local-poc` database the dev server and its Review
    queue UI read from — there's no per-test transaction to roll back
    since these tests exercise real cross-process persistence on
    purpose. Left alone, every suite run leaves rows behind that show up
    as confusing stale entries in the actual Review queue someone is
    looking at. Truncating once at session end (not per-test) keeps
    tests within the same file free to build on each other's rows."""
    yield
    try:
        with psycopg.connect(_TEST_CONN_STRING, connect_timeout=2) as conn:
            conn.execute("TRUNCATE requests")
    except psycopg.OperationalError:
        pass  # no reachable Postgres — nothing to clean up
