---
daksh:
  type: roadmap
  subtype: null
  stage: "30b"
  module: null
---

# Implementation Roadmap

This document sequences the single **ORCHESTRATION** module
[`docs/system-architecture.md`](system-architecture.md#module-decomposition)
defines (decision-09) into a build order, milestones, and a lightweight
sprint plan. It reads
[`docs/business-requirements.md`](business-requirements.md) (approved
2026-09-07) for *what* must work and reuses its three milestones verbatim
(`milestone-01`, `milestone-02`, `milestone-03`) rather than re-numbering
them — Architecture decides *what the system is*; this stage decides *what
the team builds first and why*. `docs/system-architecture.md` itself is
still `pending_approval` (0/1) as of this writing — proceeding is a PTL
call, already made, not an oversight. The audience is the delivery team
(currently just the PTL, Vara) and whoever signs off before implementation
starts.

<details><summary>Graph: What order must modules ship in, and what gates each?</summary>

```items
---
id: roadmap-cognition
title: Implementation Roadmap cognition
default_open_depth: 1
default_color_by: kind
color_palette_source: .daksh/color-palette.json
width: 95vw
---
Milestones:
  - milestone-01 :: Planner-to-Orchestrator core loop works | kind: milestone | summary: "Planner produces a valid dependent-task plan and the orchestrator executes task_1 then task_2 in order." | spec: [business-requirements.md §Use Cases](business-requirements.md#use-cases) | due: "Week 1" | definition_of_done: "A representative question produces a structured plan and the orchestrator executes it respecting the declared dependency, streamed live over the Chat AG-UI Channel."
  - milestone-02 :: Human-in-the-loop interrupt/resume demonstrated | kind: milestone | summary: "Workflow pauses after synthesis, persists state, and resumes correctly on Approve; on Reject it halts cleanly instead." | spec: [business-requirements.md §Use Cases](business-requirements.md#use-cases) | due: "Week 2" | definition_of_done: "A paused workflow is resumed from checkpointed Postgres state on Approve, and on Reject the workflow terminates for that thread with no retry (decision-05) — both paths exercised via the Review AG-UI Channel."
  - milestone-03 :: Full end-to-end demo with observable trace | kind: milestone | summary: "The complete reference flow runs live with the orchestration trace visible, using real (non-dummy) Postgres credentials." | spec: [business-requirements.md §Use Cases](business-requirements.md#use-cases) | due: "Weeks 3-4" | definition_of_done: "The full flow runs end to end, every stage of the trace is inspectable per the observability NFR, and demo-day latency has been observed at least once."
Decisions:
  - decision-14 :: Sequential build order, no parallel workstreams | kind: decision | summary: "Milestones ship strictly 01 → 02 → 03; nothing in milestone-02 starts before milestone-01's definition of done is met." | spec: [§Priority Rule and Constraints](implementation-roadmap.md#priority-rule-and-constraints) | alternatives: "Parallelizing the Postgres checkpointing work (milestone-02) alongside the core loop (milestone-01) was considered and rejected — there is one engineer (Vara) on this POC, so parallel workstreams would only context-switch, not speed delivery." | reversal_trigger: "If a second engineer joins the POC, split checkpointing and the core loop into parallel tracks."
  - decision-15 :: Informal weekly checkpoints, no Jira board | kind: decision | summary: "Progress is tracked by the manifest's progress table and a weekly PTL check-in against the milestones, not a Jira board — matches this project's jira_sync: optional rule." | spec: [§Sprint Sequence, Capacity, and Dependencies](implementation-roadmap.md#sprint-sequence-capacity-and-dependencies) | alternatives: "Standing up a Jira board was considered and declined — the project's own rules already mark Jira sync optional for a small/solo POC, and daily-granularity tracking has no audience of more than one person to serve." | reversal_trigger: "If the team grows beyond the PTL, or a client wants visible sprint tracking, turn Jira sync on and register a board."
  - decision-16 :: AG-UI/SSE plumbing built in milestone-01, not bolted on later | kind: decision | summary: "The Chat AG-UI Channel (architecture decision-13, revised to SSE 2026-09-07) is built alongside the Planner/Orchestrator core loop in milestone-01, not added afterward on top of a working REST version." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | alternatives: "Building a plain REST /chat first and converting to AG-UI/SSE later was considered and rejected — it would mean writing the request/response contract twice and re-testing the whole core loop after the swap." | reversal_trigger: "If ag-ui-langgraph's add_langgraph_fastapi_endpoint proves unworkable against the pinned LangGraph version once actually wired up, fall back to plain REST for milestone-01 and revisit AG-UI adoption as a milestone-03 stretch goal."
  - decision-17 :: Real Postgres credentials are a milestone-03 gate | kind: decision | summary: "The dummy Postgres credentials architecture decision-10 introduced stay in place through milestone-01 and milestone-02; swapping in real values is scoped explicitly to milestone-03, right before the full demo." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | alternatives: "Requesting real credentials immediately, before any checkpointing code exists, was considered and rejected — there is nothing to connect to a real database until milestone-02's checkpointer is written." | reversal_trigger: "If milestone-02's checkpointer needs to be tested against real Postgres behavior (not just any local instance), pull the real-credentials swap forward into milestone-02."
  - decision-18 :: No automated test gate between milestones | kind: decision | summary: "Milestone completion is verified manually by running the reference example, not by an automated test suite — matches architecture's constraint-testing deferral to stage 50b." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | alternatives: "Writing a minimal pytest suite before milestone-01 was considered and deferred — Test Specification (stage 50b) is where coverage targets get decided; writing tests against a design that may still shift wastes effort." | reversal_trigger: "If a regression between milestones goes unnoticed until demo day, add a minimal smoke-test suite before milestone-02 instead of waiting for stage 50b."
Risks:
  - risk-01 :: Postgres credentials still dummy | kind: risk | summary: "backend/.env holds placeholder values; milestone-03's step-03c cannot complete until the PTL supplies real ones (decision-17)." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | source: "docs/system-architecture.md decision-10"
  - risk-02 :: No automated test suite | kind: risk | summary: "Regressions between milestones are caught only by manual replay of the reference example (decision-18) — a silent break in milestone-01 could surface late, at milestone-03." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | source: "docs/system-architecture.md constraint-testing"
  - risk-03 :: ag-ui-langgraph / LangGraph version compatibility — mostly retired | kind: risk | summary: "Verified 2026-09-07 against published PyPI metadata: ag-ui-langgraph needs langgraph>=0.6.0,<2 and langchain-core>=0.3.0, both satisfied by this project's pins. One residual gap remains — plain langchain (>=1.2.0) is not yet a project dependency and must be added during step-01e; nothing is installed or version-pinned yet." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | source: "docs/system-architecture.md decision-13, Technology Baseline — verified against pypi.org/project/ag-ui-langgraph"
  - risk-04 :: Review UI/UX not designed | kind: risk | summary: "No Solution or System spec has been written for the Reviewer surface yet; step-02d has a decided shape (decision-12/13) but no screen design to build against." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | source: "docs/system-architecture.md decision-12 — Solution/System (30c/30d) not yet run"
  - risk-05 :: Single-person team | kind: risk | summary: "Vara is the only engineer on this POC; the sequential build order (decision-14) has no redundancy if the PTL is unavailable during the 4-week window." | spec: [§Sprint Sequence, Capacity, and Dependencies](implementation-roadmap.md#sprint-sequence-capacity-and-dependencies) | source: "docs/.daksh/manifest.json team_roster"
  - risk-06 :: No CI pipeline | kind: risk | summary: "There is no automated regression gate (decision-11, decision-18) — manual verification is the only thing standing between a milestone-01 regression and a broken milestone-03 demo." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | source: "docs/system-architecture.md decision-11"
  - risk-07 :: No performance/load target validated | kind: risk | summary: "constraint-perf sets no numeric SLA; demo-day latency across Planner → Orchestrator → Tools → Synthesizer → Approval has never been measured." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | source: "docs/system-architecture.md constraint-perf"
  - risk-08 :: No vision.md or client-context.md exist | kind: risk | summary: "Both this roadmap and the architecture it builds on are grounded directly in the BRD and the code, with no upstream vision or client-context sign-off — an inherited, already-acknowledged risk (manifest RISK-001, RISK-002)." | spec: [business-requirements.md](business-requirements.md) | source: "docs/.daksh/manifest.json risk_register"
  - risk-09 :: Custom WebSocket transport — retired, not needed | kind: risk | summary: "Originally: architecture decision-13 chose WebSocket, which the official AG-UI SDKs don't support out of the box, meaning custom transport code on both sides. Retired 2026-09-07 — decision-13 was revised to SSE (the SDKs' built-in transport) before any WebSocket code was written, so this risk never materialized." | spec: [§Build Order](implementation-roadmap.md#build-order-and-risk-retirement) | source: "docs/system-architecture.md decision-13 revision, 2026-09-07"

comp-orchestration-module :: ORCHESTRATION module | kind: component | summary: "The single Daksh module this roadmap sequences — reused from Architecture, not redefined here." | spec: [system-architecture.md §Module Decomposition](system-architecture.md#module-decomposition) | boundary: "backend/app/graph/ (planned), backend/app/api/routes/ (planned), frontend/src/"

step-01a :: Planner produces valid structured Plan | kind: task | summary: "Implements FR-002/FR-003/FR-004 — LLM turns the question into task id/description/executor/dependencies." | spec: [business-requirements.md §Functional Requirements](business-requirements.md#functional-requirements)
step-01b :: Orchestrator executes plan respecting dependencies | kind: task | summary: "Implements FR-005/FR-008/FR-009 — deterministic execution in dependency order." | spec: [business-requirements.md §Functional Requirements](business-requirements.md#functional-requirements)
step-01c :: Query and Calculation tools wired in | kind: task | summary: "Implements FR-006/FR-007 — predefined SQL execution plus aggregation over results." | spec: [business-requirements.md §Functional Requirements](business-requirements.md#functional-requirements)
step-01d :: Synthesizer produces final response | kind: task | summary: "Implements FR-010 — combines question, rows, and calculations into one structured response." | spec: [business-requirements.md §Functional Requirements](business-requirements.md#functional-requirements)
step-01e :: Chat AG-UI Channel streams the core loop live | kind: task | summary: "Implements FR-001 plus architecture decision-13/decision-16 — SSE ag-ui-protocol events (via ag-ui-langgraph/@ag-ui/client) replace the deleted stub's plain fetch." | spec: [system-architecture.md §Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture)
step-02a :: Human Approval gate wired | kind: task | summary: "Implements FR-011/FR-012/FR-013 — Approve shows the response, Reject halts the thread with no retry (decision-05)." | spec: [business-requirements.md §Functional Requirements](business-requirements.md#functional-requirements)
step-02b :: Postgres checkpoint store wired | kind: task | summary: "Implements FR-014 — WorkflowState persisted per thread_id (decision-06/decision-10), still against dummy credentials." | spec: [business-requirements.md §Functional Requirements](business-requirements.md#functional-requirements)
step-02c :: Resume from persisted state | kind: task | summary: "Implements FR-015 — an interrupted run resumes without re-executing completed tasks." | spec: [business-requirements.md §Functional Requirements](business-requirements.md#functional-requirements)
step-02d :: Review AG-UI Channel and /review route built | kind: task | summary: "Implements architecture decision-12/decision-13 — the Reviewer's separate SSE surface, still needing Solution/System design (risk-04)." | spec: [system-architecture.md §Module Interactions and Interfaces](system-architecture.md#module-interactions-and-interfaces)
step-03a :: Full reference example runs end-to-end live | kind: task | summary: "The complete UC-001/UC-002/UC-003 path, demoed live rather than replayed from a log." | spec: [business-requirements.md §Use Cases](business-requirements.md#use-cases)
step-03b :: Orchestration trace fully inspectable | kind: task | summary: "Implements BRD metric-02 / architecture constraint-observability — every run's plan, tasks, results, and approval decision are visible." | spec: [business-requirements.md §Non-Functional Requirements](business-requirements.md#non-functional-requirements)
step-03c :: Real Postgres credentials swapped in | kind: task | summary: "Implements decision-17 — backend/.env's dummy values are replaced with the PTL's real Postgres instance right before the full demo." | spec: [system-architecture.md §Decisions](system-architecture.md#decisions)

edges:
  - milestone-01 -decomposes_into-> step-01a
  - milestone-01 -decomposes_into-> step-01b
  - milestone-01 -decomposes_into-> step-01c
  - milestone-01 -decomposes_into-> step-01d
  - milestone-01 -decomposes_into-> step-01e
  - milestone-02 -decomposes_into-> step-02a
  - milestone-02 -decomposes_into-> step-02b
  - milestone-02 -decomposes_into-> step-02c
  - milestone-02 -decomposes_into-> step-02d
  - milestone-03 -decomposes_into-> step-03a
  - milestone-03 -decomposes_into-> step-03b
  - milestone-03 -decomposes_into-> step-03c
  - decision-14 -governs-> comp-orchestration-module
  - decision-15 -governs-> milestone-01
  - decision-16 -governs-> step-01e
  - decision-17 -governs-> step-03c
  - decision-18 -governs-> risk-02
  - risk-01 -threatens-> step-03c
  - risk-02 -threatens-> step-01b
  - risk-03 -threatens-> step-01e
  - risk-04 -threatens-> step-02d
  - risk-05 -threatens-> milestone-03
  - risk-06 -threatens-> step-01b
  - risk-07 -threatens-> step-03a
  - risk-08 -threatens-> milestone-01
  - risk-09 -threatens-> step-01e
```

</details>

## Priority Rule and Constraints

Priority follows the BRD's own milestone order, unchanged: goal-03
(resumable, observable orchestration) cannot be demonstrated without
goal-01 (the core Q&A loop) working first, and goal-02 (the approval gate)
sits between them because BRD decision-03 makes the Synthesizer — and the
approval step right after it — mandatory, never skippable. There is no
constraint forcing a different order: no external deadline exists beyond
the project's own "< 4 weeks" weight-class estimate, and no client
dependency gates any step. The one real constraint is capacity — a single
engineer (decision-14, risk-05) — which is why the order is strictly
sequential rather than parallelized.

## Module Dependency Graph

Trivial by design: this project registers exactly one module,
**ORCHESTRATION** (architecture decision-09), so there are no
cross-module dependencies to sequence
(`manifest.rules.cross_module_contracts` is `false`). If a second module
is ever split out — architecture decision-09's reversal trigger describes
when that might happen — this section is where its dependency on
ORCHESTRATION's Chat/Review AG-UI Channels would be recorded.

## Build Order and Risk Retirement

| Step | Retires | Milestone |
|---|---|---|
| step-01a Planner produces valid Plan | — (foundational) | milestone-01 |
| step-01b Orchestrator executes in dependency order | risk-02, risk-06 (first point a regression could hide) | milestone-01 |
| step-01c Query + Calculation tools wired | — | milestone-01 |
| step-01d Synthesizer produces response | — | milestone-01 |
| step-01e Chat AG-UI Channel streams live | risk-03 fully retired (langchain added, versions pinned); risk-09 already retired by the SSE decision — this step is where it gets proven against real code, not just docs | milestone-01 |
| step-02a Human Approval gate wired | — | milestone-02 |
| step-02b Postgres checkpoint store wired | — (risk-01 stays open — dummy credentials, decision-17) | milestone-02 |
| step-02c Resume from persisted state | — | milestone-02 |
| step-02d Review AG-UI Channel + /review route | risk-04 partially — building it surfaces exactly what Solution/System design is still missing | milestone-02 |
| step-03a Full reference example end-to-end | risk-05 (proves the solo build order actually worked) | milestone-03 |
| step-03b Orchestration trace inspectable | risk-07 partially — first real chance to observe demo-day latency | milestone-03 |
| step-03c Real Postgres credentials swapped in | risk-01 (fully retired) | milestone-03 |

Two risks are never fully retired by this roadmap and are named here so
they are not mistaken for oversights: risk-04 (Review UI/UX design) is
retired by running Solution/System (30c/30d) for ORCHESTRATION, not by
this roadmap directly; risk-06 (no CI) is an accepted, decided condition
(decision-18), not a gap awaiting a fix.

## Milestones

See the graph above for `milestone-01` through `milestone-03` — reused
verbatim from the BRD, with `due` dates added (Week 1, Week 2, Weeks 3-4)
since assigning a build order is this stage's job, not the BRD's. Each
milestone's `definition_of_done` is unchanged from the BRD except
milestone-01's and milestone-02's, which now name the AG-UI channel
explicitly (architecture decision-13 postdates the BRD).

## Sprint Sequence, Capacity, and Dependencies

One engineer (Vara, PTL) — capacity is one person's time across a roughly
4-week window (decision-14, risk-05). No sprint framework or Jira board
tracks this work (decision-15); progress is read directly off the table
below, updated as steps complete. Named dependencies are the
`decomposes_into` edges in the graph above: no step in milestone-02 can
start before its parent milestone-01 sibling steps are done, since
milestone-01 is the core loop every later step calls into.

## Progress Table

This table is the thing that changes week to week — Architecture and this
roadmap's build order do not need editing just because a step's status
changes.

| Step | Status |
|---|---|
| step-01a Planner produces valid Plan | not_started |
| step-01b Orchestrator executes in dependency order | not_started |
| step-01c Query + Calculation tools wired | not_started |
| step-01d Synthesizer produces response | not_started |
| step-01e Chat AG-UI Channel streams live | not_started |
| step-02a Human Approval gate wired | not_started |
| step-02b Postgres checkpoint store wired | not_started |
| step-02c Resume from persisted state | not_started |
| step-02d Review AG-UI Channel + /review route | not_started |
| step-03a Full reference example end-to-end | not_started |
| step-03b Orchestration trace inspectable | not_started |
| step-03c Real Postgres credentials swapped in | not_started |

## Open Questions

No open questions remain at the roadmap level — every ambiguity resolved
into either a decision above or a named risk. The nine risks are
deliberately not reframed as questions: none of them block starting
step-01a, and each already names what would retire it.

## Approval

Approved by: Vara
Role:        PTL
Date:        2026-09-07
Hash:        2c41539f94b1…
