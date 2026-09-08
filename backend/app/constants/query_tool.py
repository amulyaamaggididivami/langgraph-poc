"""Fixture predefined-query registry for TASK-ORCHESTRATION-004.

comp-query-tool dispatches one of a small, fixed set of predefined
queries (BRD constraint-02 — no generated SQL, ever). The real
business-data schema and query SQL are TASK-ORCHESTRATION-022/023
(Engineer A, not yet built) — until then, each registry entry returns
fixture rows shaped like the eventual real result, so the rest of the
pipeline (Calculation Agent, Synthesizer) can be built and tested
against a stable contract. Swapping a fixture's `rows` for a real SQL
call is the only change TASK-022/023 needs to make here.
"""

PREDEFINED_QUERIES = {
    "total_sales": {
        "keywords": ("total sales", "total revenue", "overall sales"),
        "rows": [
            {"region": "North", "amount": 125000.0},
            {"region": "South", "amount": 98000.0},
            {"region": "East", "amount": 143500.0},
            {"region": "West", "amount": 110250.0},
        ],
    },
    "sales_by_region": {
        "keywords": ("by region", "per region", "region breakdown"),
        "rows": [
            {"region": "North", "amount": 125000.0},
            {"region": "South", "amount": 98000.0},
        ],
    },
    "monthly_revenue": {
        "keywords": ("monthly", "last quarter", "this quarter", "revenue trend"),
        "rows": [
            {"month": "2026-06", "amount": 82000.0},
            {"month": "2026-07", "amount": 91000.0},
            {"month": "2026-08", "amount": 88500.0},
        ],
    },
}

# Used when a Task's description doesn't match any registered keyword —
# the Planner already decided this Task belongs to the query tool, so a
# fixture default is a reasonable stand-in until real intent-to-query
# mapping exists (TASK-ORCHESTRATION-023).
DEFAULT_QUERY_KEY = "total_sales"
