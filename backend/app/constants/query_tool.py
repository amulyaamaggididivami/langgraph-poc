"""Predefined-query registry for TASK-ORCHESTRATION-004/023.

comp-query-tool dispatches one of 4 fixed SQL queries against the real
`appointments` table (BRD constraint-02 — no generated SQL, ever).
trd.md §Persistence Constraints names this exact set
(TASK-ORCHESTRATION-021's amendment).

Just two fields per entry — `question` and `sql` — nothing else. The
Planner (app/prompts/planner.py) carries only domain + tool knowledge;
it writes `Task.question` in its own free-text words, never trying to
reproduce one of these verbatim. Matching that free text to one of
these 4 entries is query_tool.py's job, and it derives its matching
signal from each entry's own `question` string at match time — no
separate hand-authored keyword/stem list lives here.
"""

PREDEFINED_QUERIES: list[dict[str, str]] = [
    {
        "question": "What is the cancellation rate?",
        "sql": """
            SELECT status, count(*) AS appointment_count
            FROM appointments
            GROUP BY 1
            ORDER BY 2 DESC
        """,
    },
    {
        "question": "How many appointments were there by month?",
        "sql": """
            SELECT date_trunc('month', appt_date)::date AS month,
                   count(*) AS appointment_count
            FROM appointments
            GROUP BY 1
            ORDER BY 1
        """,
    },
    {
        "question": "Which clinic generated the most revenue?",
        "sql": """
            SELECT replace(clinic_name, ', ', ' ') AS clinic_name,
                   sum(paid_amount) AS total_paid,
                   avg(paid_amount) AS average_paid,
                   count(*) AS appointment_count
            FROM appointments
            GROUP BY 1
            ORDER BY 1
        """,
    },
    {
        "question": "What is the total revenue?",
        "sql": """
            SELECT sum(paid_amount) AS total_paid,
                   avg(paid_amount) AS average_paid,
                   count(*) AS appointment_count
            FROM appointments
        """,
    },
]
