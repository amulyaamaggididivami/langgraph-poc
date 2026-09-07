---
daksh:
  type: test-specification
  subtype: null
  stage: "50b"
  module: ORCHESTRATION
---

# ORCHESTRATION Test Specification

This is the Test Specification for **ORCHESTRATION** — the evidence plan
proving every promise made across
[`solution.md`](solution.md) (`SS-*`),
[`system.md`](system.md) (`SY-*`), and
[`trd.md`](trd.md) (`TRD-*`), all approved 2026-09-07. No `TEST-*` here
has actually run yet — every graph edge below is `watches` (set up to
measure), never `proves` (which needs confirmed evidence). The audience
is whoever implements this module next (stage 50c/50d), plus the PTL
confirming coverage is real before implementation starts.

## Scope, Risks, and Test Environments

**Scope.** Every `SS-ORCHESTRATION-NNN` (4), `SY-ORCHESTRATION-NNN` (12),
and `TRD-ORCHESTRATION-NNN` (10) requirement gets at least one `TEST-*`
mapping below — no exceptions, per this stage's own rule that an
unmapped requirement blocks approval.

**Risks this plan is designed against:** `risk-02` (no automated test
suite existed before this document — regressions caught only by manual
replay, per roadmap) and `risk-03`/`risk-07` (unvalidated `ag-ui-langgraph`
and `deepagents` integration behavior) are the direct reasons Integration
and E2E layers exist below, not just Unit tests.

**Test environments.** Two, both local (no staging/production substrate
exists — architecture decision-11):
- **Unit** — no real Postgres, no real LLM. `comp-planner`/`comp-calc-agent`/
  `comp-synthesizer` are exercised against a fake `ChatGoogleGenerativeAI`
  returning fixed structured output; `comp-query-tool` against an in-memory
  row fixture.
- **Integration/E2E** — a real local Postgres instance (the `synergy`
  database, decision-30) seeded per test, real `PostgresSaver`, a fake
  LLM (same fixture as Unit) to keep runs deterministic and fast. No test
  in this document calls the real Gemini API — nondeterministic model
  output has no place in an automated pass/fail gate.

## Traceability

| Requirement | Traces to Test(s) |
|---|---|
| SS-ORCHESTRATION-001 | TEST-ORCHESTRATION-001, TEST-ORCHESTRATION-017 |
| SS-ORCHESTRATION-002 | TEST-ORCHESTRATION-018 |
| SS-ORCHESTRATION-003 | TEST-ORCHESTRATION-019 |
| SS-ORCHESTRATION-004 | TEST-ORCHESTRATION-002, TEST-ORCHESTRATION-020 |
| SY-ORCHESTRATION-001 | TEST-ORCHESTRATION-001, TEST-ORCHESTRATION-017 |
| SY-ORCHESTRATION-002 | TEST-ORCHESTRATION-018 |
| SY-ORCHESTRATION-003 | TEST-ORCHESTRATION-019 |
| SY-ORCHESTRATION-004 | TEST-ORCHESTRATION-002, TEST-ORCHESTRATION-020 |
| SY-ORCHESTRATION-005 | TEST-ORCHESTRATION-021 |
| SY-ORCHESTRATION-006 | TEST-ORCHESTRATION-006 |
| SY-ORCHESTRATION-007 | TEST-ORCHESTRATION-017, TEST-ORCHESTRATION-018, TEST-ORCHESTRATION-020 (each asserts its own terminal trace entry) |
| SY-ORCHESTRATION-008 | TEST-ORCHESTRATION-022 |
| SY-ORCHESTRATION-009 | TEST-ORCHESTRATION-023 |
| SY-ORCHESTRATION-010 | TEST-ORCHESTRATION-024 |
| SY-ORCHESTRATION-011 | TEST-ORCHESTRATION-025 |
| SY-ORCHESTRATION-012 | TEST-ORCHESTRATION-010 |
| TRD-ORCHESTRATION-001 | TEST-ORCHESTRATION-009 |
| TRD-ORCHESTRATION-002 | TEST-ORCHESTRATION-010 |
| TRD-ORCHESTRATION-003 | TEST-ORCHESTRATION-011 |
| TRD-ORCHESTRATION-004 | TEST-ORCHESTRATION-003 |
| TRD-ORCHESTRATION-005 | TEST-ORCHESTRATION-012 |
| TRD-ORCHESTRATION-006 | TEST-ORCHESTRATION-013 |
| TRD-ORCHESTRATION-007 | TEST-ORCHESTRATION-004, TEST-ORCHESTRATION-014 |
| TRD-ORCHESTRATION-008 | TEST-ORCHESTRATION-015 |
| TRD-ORCHESTRATION-009 | TEST-ORCHESTRATION-019, TEST-ORCHESTRATION-025 |
| TRD-ORCHESTRATION-010 | TEST-ORCHESTRATION-016 |

<details><summary>Graph: What evidence proves each promised behavior?</summary>

```items
---
id: orchestration-test-cognition
title: ORCHESTRATION Test Specification cognition
default_open_depth: 1
default_color_by: kind
color_palette_source: .daksh/color-palette.json
width: 95vw
---
Unit Tests:
  - test-001 :: Planner produces valid Plan for a matching question | kind: test | summary: "Fake LLM returns a structured Plan; asserts task ids/executors/depends_on match the schema." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching backend/app/graph/nodes/planner.py"
  - test-002 :: Planner produces Decline for an unmatched question | kind: test | summary: "Fake LLM returns a Decline; asserts no Plan is ever created alongside it (invariant-decline-no-plan)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching planner.py"
  - test-003 :: requests table rejects decline_reason without Declined state | kind: test | summary: "Direct SQL INSERT/UPDATE against a seeded Postgres asserts the CHECK constraint fires." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every migration change to the requests table"
  - test-004 :: Calculation Agent selects the correct tool for a given task description | kind: test | summary: "Fake LLM + real tool functions (average, percentage_change); asserts the right tool fires with the right args." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching calc_agent.py"
  - test-005 :: Task.status is always one of the four closed values | kind: test | summary: "Property-based check across every Task produced by the Planner fixture — no fifth value ever appears." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching the Plan schema"
  - test-006 :: Synthesized response never contains schema or table names | kind: test | summary: "Keyword/regex check against fake-LLM-produced responses for leaked identifiers (e.g. table names from iface-business-db's fixture schema)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching synthesizer.py"
Persistence and Checkpoint Tests:
  - test-007 :: Orchestrator dispatches tasks in dependency order | kind: test | summary: "A Plan with a dependent Task pair asserts the dependent task never starts before its dependency completes (FR-008)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching graph.py"
  - test-008 :: Query Execution Tool returns raw rows read-only | kind: test | summary: "Against a seeded synergy fixture schema, asserts a SELECT-only query executes and no write is ever issued (constraint-01)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching query_tool.py"
  - test-009 :: PostgresSaver writes a checkpoint after every superstep | kind: test | summary: "Runs a full plan-execute-synthesize sequence against real PostgresSaver; asserts get_state_history returns one checkpoint per step, not one total." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run in CI-equivalent (manual, per roadmap decision-18) before each milestone"
  - test-010 :: External call timeout raises event-integration-failure | kind: test | summary: "A deliberately slow fake call (>30s) asserts the bounded wait fires and only that Request fails." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching the timeout wrapper"
  - test-014 :: deepagents internal tool calls checkpoint individually | kind: test | summary: "A Calculation Agent run needing 2 chained tool calls asserts 2+ distinct checkpoint entries appear under the parent's checkpoint history, not 1." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching calc_agent.py's subgraph registration"
  - test-015 :: Business tables and checkpoint tables coexist without collision | kind: test | summary: "Schema inspection against the synergy database asserts no table name overlap, and a write to requests/checkpoints never mutates business tables." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every migration change"
API Contract Tests:
  - test-011 :: /chat returns a valid ag-ui-protocol SSE stream | kind: test | summary: "Asserts the response is text/event-stream and every event parses as a valid BaseEvent." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching chat.py"
  - test-012 :: /review pending list is served by the partial index | kind: test | summary: "EXPLAIN ANALYZE asserts idx_requests_awaiting_review is used; result set matches exactly the AwaitingReview rows." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching review.py"
  - test-013 :: Second decision on an already-resumed thread returns already_decided | kind: test | summary: "Two sequential POST /review/{thread_id}/decision calls; asserts the second gets the error, not a silent no-op or duplicate delivery." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching review.py"
  - test-016 :: All three endpoints share one error schema | kind: test | summary: "Triggers one error per endpoint; asserts every response validates against the same JSON Schema." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching any route"
End-to-End Tests:
  - test-017 :: Full happy path — question to delivered answer | kind: test | summary: "Live local run: question → Plan → Query Tool → Calc Agent → Synthesizer → Approve → Delivered, over real SSE." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before every milestone demo (roadmap milestone-01/03)"
  - test-018 :: Reject flow — response withheld, thread terminates | kind: test | summary: "Live run to AwaitingReview, then Reject; asserts no further event reaches /chat and the thread cannot be re-acted on." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before every milestone demo"
  - test-019 :: Resume flow — interrupt and recover mid-review | kind: test | summary: "Live run to AwaitingReview, kill the process, restart, resume; asserts Delivered is reached with no repeated work (roadmap milestone-02)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before every milestone demo"
  - test-020 :: Decline flow — unsupported question | kind: test | summary: "Live run with a question matching no predefined query; asserts a clean decline message, never a guess." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before every milestone demo"
Edge, Failure, and Recovery Tests:
  - test-021 :: Concurrent requests are isolated on failure | kind: test | summary: "Two simultaneous requests, one forced to fail its external call; asserts the other completes unaffected (requirement-07)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before milestone-03"
  - test-022 :: Normal wait vs. crash-interrupted wait are distinguishable | kind: test | summary: "One request left genuinely AwaitingReview, one killed mid-wait; asserts the trace shows which is which without inspecting checkpoint internals (requirement-10)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before milestone-02"
  - test-023 :: Decline produces exactly one trace entry | kind: test | summary: "Asserts a declined request's trace has neither zero nor two decline entries." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching planner.py"
  - test-024 :: Resumed response traces back to the original question | kind: test | summary: "After interrupt-and-resume, asserts the final delivered response can be linked to the exact original question text (requirement-12)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before milestone-02"
  - test-025 :: Resume never re-invokes a completed Task | kind: test | summary: "A call-count assertion on the Query Tool fixture proves it is invoked exactly once across an interrupt-and-resume cycle, not twice." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run before milestone-02"
  - test-026 :: Demo-day latency is observed, not asserted | kind: test | summary: "One manual timing pass through the full happy path, recorded (not pass/failed against a number — constraint-perf sets none)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run once, at milestone-03"
Reused Invariants:
  - invariant-task-status-closed :: Task.status is exactly one of four values | kind: invariant | summary: "Reused from system.md." | spec: [system.md §Business Rules and Validation](system.md#business-rules-and-validation) | violation_signal: "A Task's status field holds any value outside the closed four."
  - invariant-decline-no-plan :: A declined Request never has a Plan | kind: invariant | summary: "Reused from system.md." | spec: [system.md §Business Rules and Validation](system.md#business-rules-and-validation) | violation_signal: "A Request has both a Plan and a Decline Reason."
  - invariant-response-immutable :: A synthesized Response never changes after creation | kind: invariant | summary: "Reused from system.md." | spec: [system.md §Business Rules and Validation](system.md#business-rules-and-validation) | violation_signal: "A Response's content differs between AwaitingReview entry and Approve/Reject."
  - invariant-single-checkpoint-per-request :: At most one active checkpoint per Request | kind: invariant | summary: "Reused from system.md." | spec: [system.md §Business Rules and Validation](system.md#business-rules-and-validation) | violation_signal: "Two Checkpoint Records exist for the same Request with no supersede relationship."
Reused Decisions:
  - decision-23 :: LangGraph's own PostgresSaver, not hand-rolled persistence | kind: decision | summary: "Reused from trd.md." | spec: [trd.md §Persistence Constraints](trd.md#persistence-constraints) | alternatives: "See trd.md." | reversal_trigger: "See trd.md."
  - decision-24 :: 30-second bounded wait for external calls | kind: decision | summary: "Reused from trd.md." | spec: [trd.md §Idempotency and Failure Contracts](trd.md#idempotency-and-failure-contracts) | alternatives: "See trd.md." | reversal_trigger: "See trd.md."
  - decision-25 :: SSE via ag-ui-langgraph's add_langgraph_fastapi_endpoint | kind: decision | summary: "Reused from trd.md." | spec: [trd.md §API Contracts](trd.md#api-contracts) | alternatives: "See trd.md." | reversal_trigger: "See trd.md."
  - decision-29 :: Calculation Agent built with deepagents | kind: decision | summary: "Reused from trd.md." | spec: [trd.md §Technology Choices](trd.md#technology-choices) | alternatives: "See trd.md." | reversal_trigger: "See trd.md."
  - decision-30 :: Business database is project-owned, same Postgres instance as checkpoints | kind: decision | summary: "Reused from trd.md." | spec: [trd.md §Persistence Constraints](trd.md#persistence-constraints) | alternatives: "See trd.md." | reversal_trigger: "See trd.md."

test-027 :: ChatForm submits a question and renders streamed events | kind: test | summary: "Frontend component test — mocked SSE stream; asserts ChatForm renders each event as it arrives. No accessibility assertions: no Experience Design Spec exists to test against (stage 40 not selected)." | spec: [§Traceability](test-specification.md#traceability) | trigger: "Run on every commit touching frontend/src/components/ChatForm.tsx"

edges:
  - test-005 -watches-> invariant-task-status-closed
  - test-002 -watches-> invariant-decline-no-plan
  - test-006 -watches-> invariant-response-immutable
  - test-009 -watches-> invariant-single-checkpoint-per-request
  - test-009 -watches-> decision-23
  - test-010 -watches-> decision-24
  - test-011 -watches-> decision-25
  - test-014 -watches-> decision-29
  - test-015 -watches-> decision-30
```

</details>

## Unit Tests

Prose before the case blocks (doc-narrator rule): every Unit test below
runs against a fake LLM and in-memory fixtures — no Postgres, no network
call, fast enough to run on every commit.

**TEST-ORCHESTRATION-001 — Planner produces valid Plan for a matching question**
- Preconditions: fake LLM configured to return a fixed `PlannerOutput.plan`.
- Data: a question string matching a known predefined-query intent.
- Steps: invoke `planner_node` with the question in state.
- Expected result: returned `plan` validates against the `Plan` schema; every task has a valid `executor`.
- Layer: unit. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-002 — Planner produces Decline for an unmatched question**
- Preconditions: fake LLM configured to return `PlannerOutput.decline`.
- Data: a question string matching no known intent.
- Steps: invoke `planner_node`.
- Expected result: `decline_reason` is set; no `plan` key is present (`invariant-decline-no-plan`).
- Layer: unit. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-003 — `requests` table rejects `decline_reason` without `Declined` state**
- Preconditions: seeded local Postgres with the `requests` table migrated.
- Data: an INSERT with `state='AwaitingReview'`, `decline_reason='out_of_scope'`.
- Steps: execute the INSERT.
- Expected result: the `decline_reason_only_when_declined` CHECK constraint raises an error.
- Layer: unit (schema-level). Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-004 — Calculation Agent selects the correct tool**
- Preconditions: real `average`/`percentage_change` tool functions; fake LLM returns a fixed tool-call decision.
- Data: a task description asking for an average, and raw rows.
- Steps: invoke the Calculation Agent subgraph.
- Expected result: `average` is called with the correct row values; result matches manual computation.
- Layer: unit. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-005 — `Task.status` is always one of four values**
- Preconditions: Planner fixture producing several Plans.
- Data: a range of question/dependency shapes.
- Steps: inspect every `Task.status` produced across all fixture Plans.
- Expected result: every value is one of `PENDING`/`RUNNING`/`COMPLETED`/`FAILED`; none other appears.
- Layer: unit (property-based). Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-006 — Response never leaks schema/table names**
- Preconditions: fake LLM Synthesizer output containing a deliberately-injected table name, to catch a broken filter.
- Data: a fixture Response referencing a known business-table name.
- Steps: run the leak check against Synthesizer output.
- Expected result: check fails loudly on injected leaks (proves the check itself works) and passes on clean fixtures.
- Layer: unit. Owner: backend. Automation: automated.

## Integration and Interface Contract Tests

Every test below runs against a real, seeded local Postgres (`synergy`)
and a real `PostgresSaver` — the fake LLM stays fake, since model output
determinism is not what these tests are proving.

**TEST-ORCHESTRATION-007 — Orchestrator dispatches tasks in dependency order**
- Preconditions: a Plan with Task B depending on Task A.
- Steps: run the graph; record dispatch order.
- Expected result: Task A completes before Task B starts; Task B receives Task A's output (FR-008).
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-008 — Query Execution Tool is read-only**
- Preconditions: seeded fixture business tables in `synergy`.
- Steps: run a predefined query task; inspect the SQL issued.
- Expected result: only `SELECT` statements are issued; no row is modified (`constraint-01`).
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-009 — Checkpoint written after every superstep**
- Preconditions: real `PostgresSaver`.
- Steps: run a full plan-execute-synthesize sequence; call `get_state_history`.
- Expected result: one checkpoint exists per graph step, not one checkpoint total for the whole run.
- Layer: integration. Owner: backend. Automation: automated (manual trigger per roadmap decision-18 — no CI exists).

**TEST-ORCHESTRATION-010 — External call timeout raises `event-integration-failure`**
- Preconditions: a fake external call configured to hang past 30s.
- Steps: invoke the wrapped call.
- Expected result: the call is aborted at 30s; `event-integration-failure` fires; the Request fails, nothing else does.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-011 — `/chat` returns a valid SSE stream**
- Preconditions: backend running locally.
- Steps: `POST /chat` with a valid question.
- Expected result: `Content-Type: text/event-stream`; every event parses as a valid `ag-ui-protocol` `BaseEvent`.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-012 — `/review` pending list uses the partial index**
- Preconditions: seeded `requests` rows in mixed states.
- Steps: `EXPLAIN ANALYZE` the pending-list query; call `GET /review`.
- Expected result: query plan shows `idx_requests_awaiting_review`; response contains exactly the `AwaitingReview` rows.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-013 — Second decision returns `already_decided`**
- Preconditions: a Request already resumed via Approve.
- Steps: `POST /review/{thread_id}/decision` a second time.
- Expected result: response is the `already_decided` error, not a silent 200 or a duplicate delivery.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-014 — `deepagents` tool calls checkpoint individually**
- Preconditions: a calculation requiring 2 chained tool calls (e.g. a ratio).
- Steps: run the Calculation Agent; inspect checkpoint history under the parent's namespace.
- Expected result: 2 or more distinct checkpoint entries appear for the subgraph's internal steps.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-015 — Business and checkpoint tables coexist without collision**
- Preconditions: `synergy` database with both table sets migrated.
- Steps: inspect `information_schema.tables`; write to `requests`, then read business tables.
- Expected result: no table name overlap; the business-table read reflects no changes from the `requests` write.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-016 — Shared error schema across all endpoints**
- Preconditions: one failure trigger per endpoint (`/chat`, `/review`, `/review/{thread_id}/decision`).
- Steps: trigger each; validate the response body.
- Expected result: every error response validates against the same JSON Schema (§API Contracts, `trd.md`).
- Layer: integration. Owner: backend. Automation: automated.

## Frontend Automation

**TEST-ORCHESTRATION-027 — ChatForm renders streamed events**
- Preconditions: mocked SSE stream emitting a sequence of `BaseEvent`s.
- Steps: render `ChatForm`; feed the mocked stream.
- Expected result: the component updates as each event arrives, ending on the final response.
- Layer: component (frontend). Owner: frontend. Automation: automated.
- No accessibility assertions are specified — no Experience Design Spec exists for this module (stage 40 not selected) to test against. If stage 40 is added later, this test gets a11y assertions then, not invented here.

## End-to-End Tests

Every E2E test below is a **live, local run** — real Postgres, real
frontend, real backend process, fake LLM (for determinism). These are
the tests closest to what a demo actually looks like.

**TEST-ORCHESTRATION-017 — Full happy path**
- Preconditions: backend and frontend running locally, seeded business data.
- Steps: submit a matching question via the UI; wait for synthesis; approve via `/review`.
- Expected result: the Business User sees the delivered response; the trace shows `Received → BeingAnalyzed → AwaitingReview → Delivered`.
- Layer: e2e. Owner: backend+frontend. Automation: automated where feasible, manual demo check otherwise.

**TEST-ORCHESTRATION-018 — Reject flow**
- Preconditions: a request reaches `AwaitingReview`.
- Steps: Reject via `/review`.
- Expected result: no further event reaches `/chat`; the thread is terminal; a second decision attempt gets `already_decided`.
- Layer: e2e. Owner: backend+frontend. Automation: automated where feasible.

**TEST-ORCHESTRATION-019 — Resume after interruption**
- Preconditions: a request reaches `AwaitingReview`.
- Steps: kill the backend process; restart it; Approve.
- Expected result: the response is delivered with no re-execution of already-completed tasks (TRD-ORCHESTRATION-009).
- Layer: e2e. Owner: backend. Automation: automated where feasible.

**TEST-ORCHESTRATION-020 — Decline flow**
- Preconditions: none beyond a running backend.
- Steps: submit a question matching no predefined query.
- Expected result: a clean decline message reaches the Business User; no partial or guessed answer appears.
- Layer: e2e. Owner: backend+frontend. Automation: automated where feasible.

## Edge, Failure, Security, Performance, and Recovery Tests

**TEST-ORCHESTRATION-021 — Concurrent requests are isolated**
- Preconditions: two requests submitted near-simultaneously, one forced to hit a failing external call.
- Steps: submit both; wait for both outcomes.
- Expected result: the failing request fails alone; the other reaches `Delivered` normally.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-022 — Normal wait vs. crash distinguishable**
- Preconditions: one request left genuinely `AwaitingReview`; one killed mid-wait and restarted.
- Steps: inspect the trace for both.
- Expected result: the two are distinguishable in the trace without manual checkpoint inspection.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-023 — Decline produces exactly one trace entry**
- Preconditions: a declined request.
- Steps: inspect the trace.
- Expected result: exactly one decline entry — never zero, never two.
- Layer: unit/integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-024 — Resumed response traces to original question**
- Preconditions: an interrupt-and-resume cycle.
- Steps: inspect the delivered response's linkage back to `requests.question_text`.
- Expected result: the exact original question text is still linked, not lost or altered.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-025 — Resume never re-invokes a completed Task**
- Preconditions: a Plan with 2+ tasks, one already `COMPLETED` before an interruption.
- Steps: interrupt after Task A completes; resume; count invocations of Task A's executor.
- Expected result: Task A's executor is called exactly once across the whole run, not twice.
- Layer: integration. Owner: backend. Automation: automated.

**TEST-ORCHESTRATION-026 — Demo-day latency observed**
- Preconditions: full happy path ready to run.
- Steps: time one complete run, start to `Delivered`.
- Expected result: recorded, not pass/failed — `constraint-perf` sets no numeric target.
- Layer: e2e (manual). Owner: PTL. Automation: manual, once, at milestone-03.

## Setup, Fixtures, Factories, and Cleanup

- **Fake LLM fixture** — a `ChatGoogleGenerativeAI`-shaped stub returning
  pre-configured `PlannerOutput`/calculation/synthesis results per test.
  Used everywhere except TEST-026 (which needs real latency).
- **Postgres fixture** — a disposable `synergy`-schema Postgres instance
  (local Docker or a test-scoped schema), migrated fresh per test run via
  `PostgresSaver.setup()` and the `requests` table DDL; seeded business
  tables per §Data Model in `trd.md`.
- **Cleanup** — every integration/E2E test truncates its own `requests`
  rows and drops its own checkpoint namespace after running; tests never
  share state across runs (no test depends on another test's leftover row).
- **Factories** — a `make_request(state=..., question=...)` helper for
  seeding `requests` rows directly, bypassing the full graph when a test
  only needs a specific state to exist (e.g. TEST-012's pending-list check).

## Coverage Targets and Evidence Location

No formal coverage percentage target is set — `constraint-perf`/`NFR
Design` in `trd.md` set no numeric targets project-wide, and this is a
POC, not a production service. The real target is qualitative: **every
`SS-*`, `SY-*`, and `TRD-*` requirement has at least one `TEST-*` mapped**
(see §Traceability) — that mapping being complete is the pass condition
for this document, per this stage's own rule. Evidence (test run output,
pass/fail history) will live alongside the implementation once stage 50d
begins; this document does not itself produce evidence, only the plan for it.

## Open Questions

- **Automated CI for these tests** — roadmap decision-18 already decided
  no automated test gate exists between milestones for this POC; these
  tests are designed to be automatable, but nothing runs them
  automatically yet. Whether that's revisited is a roadmap-level call, not
  this document's. `[open]`
- **Seeded business data realism** — vision.md's oq-10/decision-09 already
  settled that demo data is real (not synthetic), but the exact fixture
  rows these tests seed are not yet chosen — deferred to stage 50c/50d
  when the actual predefined queries (constraint-02) are written. `[open]`

## Approval

Approved by: Vara
Role:        PTL
Date:        2026-09-07
Hash:        6e337be4e319…
