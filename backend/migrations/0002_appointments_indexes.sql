-- TASK-ORCHESTRATION-022: business database schema (indexes).
--
-- The `appointments` table itself already existed in `synergy`, seeded
-- with real clinic data before this project's migration tooling did
-- (trd.md §Persistence Constraints, TASK-ORCHESTRATION-021 amendment,
-- 2026-09-08) — there is no CREATE TABLE here, only the indexes that
-- section commits to, one per predefined query (TASK-ORCHESTRATION-023):
--   idx_appointments_appt_date    -> appointment_count_by_month
--   idx_appointments_clinic_name  -> revenue_by_clinic
--   idx_appointments_status      -> cancellation_rate
-- No table-name collision with `requests` or LangGraph's own checkpoint
-- tables (checkpoints/checkpoint_blobs/checkpoint_writes) — confirmed
-- against the live `synergy` instance before writing this file.

CREATE INDEX IF NOT EXISTS idx_appointments_appt_date
    ON appointments (appt_date);

CREATE INDEX IF NOT EXISTS idx_appointments_clinic_name
    ON appointments (clinic_name);

CREATE INDEX IF NOT EXISTS idx_appointments_status
    ON appointments (status);
