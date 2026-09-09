-- TASK-ORCHESTRATION-011: requests table migration
-- DDL frozen in trd.md §Data Model / §Persistence Constraints — no new
-- design here. Applies to the project-owned `synergy` Postgres instance
-- (decision-30), separate from LangGraph's own checkpoint tables, which
-- `PostgresSaver.setup()` creates itself (decision-23).

-- CREATE TYPE has no IF NOT EXISTS — make.migrate reapplies every file on
-- every run (no migration-state tracking table exists), so this must
-- tolerate being run twice.
DO $$ BEGIN
    CREATE TYPE request_state AS ENUM (
        'Received', 'BeingAnalyzed', 'AwaitingReview',
        'Interrupted', 'Declined', 'Delivered', 'Withheld'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE decline_reason AS ENUM (
        'unmatched_intent', 'ambiguous_query', 'out_of_scope'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS requests (
    thread_id    UUID PRIMARY KEY,
    question_text TEXT NOT NULL,
    state        request_state NOT NULL DEFAULT 'Received',
    decline_reason decline_reason NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT decline_reason_only_when_declined
        CHECK (decline_reason IS NULL OR state = 'Declined')
);

CREATE INDEX IF NOT EXISTS idx_requests_awaiting_review
    ON requests (state)
    WHERE state = 'AwaitingReview';
