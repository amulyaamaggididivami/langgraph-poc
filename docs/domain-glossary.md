# Domain Glossary

This is the project-specific vocabulary — entity names, status terms,
role names, business processes. It is **separate** from
`docs/glossary.md`, which holds Daksh process terms (BRD, PRD, sprint,
PTL, etc).

The BRD (stage 20) seeds this file. Module TRDs (stage 40c) append to
it when State Machines introduce new state vocabulary. Every domain
term used in any downstream doc must appear here verbatim — drift
across docs starts when the same concept gets renamed.

## Entities

- **Planner Agent** — the LLM component that reads the user's question and
  produces a structured `Plan` of tasks, executors, and dependencies. Does
  not execute tools or generate the final response.
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
- **Orchestration Layer** — the deterministic (non-LLM) workflow/control
  code that executes a `Plan`, enforces task dependencies, passes outputs
  between dependent tasks, and transitions to the Synthesizer once all
  tasks complete.
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
- **Query Execution Tool** — a deterministic, non-LLM component that runs
  one of a small set of predefined SQL queries and returns raw rows.
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
- **Calculation Agent** — the LLM component that performs aggregations
  (sum, average, count, percentage, ratio, group-based aggregation, etc.)
  over rows returned by the Query Execution Tool.
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
- **Synthesizer Agent** — the LLM component that combines the original
  question, raw rows, and calculation results into the final structured
  response. Always runs; never skipped by the Planner.
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
- **Plan** — the Planner's structured output: a list of `Task` entries
  with id, description, executor, and dependencies.
  First appearance: [business-requirements.md §Data Models](business-requirements.md#data-models).
- **Task** — one unit of planned work inside a `Plan`, with an id,
  description, assigned executor, and `depends_on` list.
  First appearance: [business-requirements.md §Data Models](business-requirements.md#data-models).
- **Thread** — the unique identifier binding one question, its plan, and
  its execution state together across pause/resume.
  First appearance: [business-requirements.md §Data Models](business-requirements.md#data-models).
- **WorkflowState** — the per-thread checkpointed state: question, plan,
  task statuses, task results, raw rows, calculations, synthesized
  response, and human approval status.
  First appearance: [business-requirements.md §Data Models](business-requirements.md#data-models).

## Status terms

`Task.status` is a closed four-value enum, decided via decision-04
(resolves oq-01, formerly open):

- **PENDING** — task is in the plan but not all its dependencies are
  `COMPLETED` yet, or it hasn't been dispatched. Not terminal.
- **RUNNING** — the orchestrator has dispatched the task to its executor
  and is waiting on a result. Not terminal.
- **COMPLETED** — the executor returned successfully; dependent tasks
  may start and receive its result (FR-008). Terminal.
- **FAILED** — the executor errored or returned an invalid result; the
  orchestration layer halts that branch of the plan. Terminal.

First appearance: [business-requirements.md §Data Models](business-requirements.md#data-models).
`SKIPPED`/`CANCELLED` were considered and deliberately excluded for this
POC (no optional or cancellable tasks exist yet) — see decision-04.
Downstream docs must reuse these four values verbatim; do not invent
additional status literals without a new decision that updates this
entry.

## Roles

- **Business User** — submits the natural-language question and consumes
  the approved answer. Audience: `end_customer`. Status: `placeholder`
  (not yet interviewed for this POC).
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
- **Reviewer / Approver** — reviews each synthesized response and
  selects Approve or Reject. Reject withholds the response and halts
  the workflow for that thread, with no retry (decision-05). Audience:
  `client`. Identity/authorization undefined — see oq-04. Status:
  `placeholder`.
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
- **PTL** — accountable for POC scope and architecture decisions.
  Audience: `delivery`. Status: `validated` (Vara, per manifest
  `team_roster`).
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).

## Business processes

- **Plan Execution** — the Orchestration Layer running a Planner-produced
  `Plan`, in dependency order, until every task reaches a terminal status.
  First appearance: [business-requirements.md §Use Cases](business-requirements.md#use-cases).
- **Human Approval** — the mandatory pause after synthesis where a
  Reviewer selects Approve (response is shown to the Business User) or
  Reject (response withheld; the workflow simply stops for that thread
  — no automatic revision, replan, or retry, per decision-05, resolving
  oq-02). A new answer after a Reject means resubmitting the question
  as a fresh run, not a system-initiated retry.
  First appearance: [business-requirements.md §Use Cases](business-requirements.md#use-cases).
- **Checkpoint & Resume** — persisting `WorkflowState` at execution
  points so an interrupted run can resume from the same `Thread` without
  losing prior task results.
  First appearance: [business-requirements.md §Use Cases](business-requirements.md#use-cases).
- **Role Separation by Surface** — how a Reviewer is told apart from a
  Business User with no login: `/chat` is the Business User's surface
  (ask a question, see only approved responses); `/review` is the
  Reviewer's surface (see pending responses, Approve/Reject them). No
  identity is verified on either — the two roles are just wired to
  different UI/endpoints (decision-07, resolving oq-04). Since nothing
  gates `/review`, two concurrent requests could act on the same
  pending thread; resolved as first-write-wins (decision-08, resolving
  oq-05) — the graph is no longer paused once resumed once, so a later
  request has nothing left to act on.
  First appearance: [business-requirements.md §Stakeholders](business-requirements.md#stakeholders).
