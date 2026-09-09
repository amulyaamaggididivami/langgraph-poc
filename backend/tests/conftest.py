"""Loads backend/.env before any test module's own imports run.

Without this, whether real-infra-dependent tests (e.g. the synergy
Postgres reachability check in test_query_tool.py) see the real env
vars would depend on which test file pytest happens to import first —
app.graph.llm's own `load_dotenv()` call is a side effect of importing
it, not something to rely on from an unrelated test module.
"""

from dotenv import load_dotenv

load_dotenv()
