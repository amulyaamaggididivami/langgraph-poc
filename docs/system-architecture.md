---
daksh:
  type: architecture
  subtype: null
  stage: "30a"
  module: null
---

# System Architecture

This document defines the shared technical shape every module of langgraph-poc
inherits: the platform, the module cut, the shared rules, and the quality bar.
It implements [`docs/business-requirements.md`](business-requirements.md)
(approved 2026-09-07) — read that first for *what* the system must do; this
doc decides *how the platform is shaped* to do it. No `vision.md` or
`client-context.md` exists yet for this project (both `not_started`); this
architecture is grounded directly in the BRD and in the code already present
in the repository (`backend/`, `frontend/`)
`[derived/observed · src:backend/, frontend/ · 2026-09-07]`. The audience is
the delivery team building every module, plus whoever signs off before
implementation continues.

<details><summary>Graph: What shared system shape and rules does every module inherit?</summary>

```items
---
id: architecture-cognition
title: System Architecture cognition
default_open_depth: 1
default_color_by: kind
color_palette_source: .daksh/color-palette.json
width: 95vw
---
Orchestration Components:
  - comp-orchestration-module :: ORCHESTRATION module | kind: component | summary: "The single Daksh module covering the LangGraph planning/execution/synthesis/approval workflow and its API surface." | spec: [§Module Decomposition](system-architecture.md#module-decomposition) | boundary: "planned: backend/app/graph/, backend/app/api/routes/chat.py — both removed 2026-09-07 (were an echo-stub scaffold, not real work) and not yet rebuilt"
  - comp-planner :: Planner Agent | kind: component | summary: "LLM component that turns the question into a structured Plan of tasks, executors, and dependencies." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "not yet implemented — the prior stub echo node (backend/app/graph/graph.py) was deleted 2026-09-07 as setup scaffolding, not a starting point worth keeping"
  - comp-orchestrator :: Orchestration Layer | kind: component | summary: "Deterministic, non-LLM layer that executes the Plan, enforces task dependencies, and transitions to the Synthesizer." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "not yet implemented — the prior stub echo node (backend/app/graph/graph.py) was deleted 2026-09-07 as setup scaffolding, not a starting point worth keeping"
  - comp-query-tool :: Query Execution Tool | kind: component | summary: "Deterministic component that runs one of a small set of predefined SQL queries and returns raw rows." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "not yet implemented"
  - comp-calc-agent :: Calculation Agent | kind: component | summary: "LLM component that performs aggregations over rows returned by the Query Execution Tool." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "not yet implemented"
  - comp-synthesizer :: Synthesizer Agent | kind: component | summary: "LLM component that combines the question, raw rows, and calculation results into the final structured response. Always runs." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "not yet implemented"
  - comp-checkpoint-store :: Checkpoint Store (Postgres) | kind: component | summary: "Persists WorkflowState per thread_id so an interrupted run can resume (BRD decision-06)." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "not yet wired — no checkpointer code exists anywhere in the repo yet, no DATABASE_URL consumed yet"
Infrastructure:
  - infra-uvicorn :: Uvicorn Dev Server | kind: infrastructure | summary: "Runs the FastAPI backend locally with --reload (Makefile target `backend`)." | spec: [§Technology Baseline](system-architecture.md#technology-baseline) | boundary: "backend/, local process only"
  - infra-vite :: Vite Dev Server | kind: infrastructure | summary: "Runs the React frontend locally (Makefile target `frontend`)." | spec: [§Technology Baseline](system-architecture.md#technology-baseline) | boundary: "frontend/, local process only"
  - infra-postgres-container :: Postgres Container | kind: infrastructure | summary: "Local Postgres instance for checkpoint persistence — not yet provisioned; dummy credentials in backend/.env pending real values." | spec: [§Decisions](system-architecture.md#decisions) | boundary: "local Docker, decision-10"
Decisions:
  - decision-09 :: Single ORCHESTRATION module, no microservice split | kind: decision | summary: "The whole LangGraph workflow (planner, orchestration, tools, synthesizer) is tracked as one Daksh module for this POC." | spec: [§Module Decomposition](system-architecture.md#module-decomposition) | alternatives: "Splitting backend workflow logic and the frontend chat UI into two modules (ORCHESTRATION + CHAT) was considered and rejected for now — the codebase is one backend app with no internal service boundaries, and a POC-scale team gains nothing from tracking them separately." | reversal_trigger: "If the frontend grows its own roadmap independent of backend changes, split CHAT out as its own module."
  - decision-10 :: Local Postgres via Docker, no hosted instance | kind: decision | summary: "Checkpoint persistence runs against a local Postgres container; connection details currently in backend/.env are dummy placeholders pending real values from the PTL." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | alternatives: "A hosted instance (Supabase, RDS, Neon) was offered and declined for now — local Docker keeps the POC self-contained with no external account dependency." | reversal_trigger: "If the demo needs to run outside the PTL's machine (e.g. a shared staging link), move to a hosted instance and update this decision."
  - decision-11 :: No production deployment target | kind: decision | summary: "This POC has no deployment substrate beyond developer machines — no Docker image, no CI/CD, no cloud target." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | alternatives: "Standing up a shared cloud demo environment was considered and explicitly declined for this phase." | reversal_trigger: "If the POC needs to be demoed to people without access to the PTL's machine, define a deployment target then."
  - decision-12 :: Reviewer surface is a separate route family, not a shared endpoint | kind: decision | summary: "The Reviewer's /review surface gets its own frontend route and its own backend route family, never reusing the Chat AG-UI Channel — matching BRD decision-07's surface-only role separation." | spec: [§Permission Model and Governance](system-architecture.md#permission-model-and-governance) | alternatives: "A single shared endpoint gated by a role parameter was considered and rejected — it would let a caller flip roles by changing a request field instead of by which surface they reached, defeating decision-07's entire premise." | reversal_trigger: "If real authentication is added later (see constraint-security's reversal path), a single role-gated endpoint becomes viable and this split can be reconsidered."
  - decision-13 :: AG-UI protocol over SSE for both surfaces | kind: decision | summary: "Both /chat and /review communicate with the backend using the official ag-ui-langgraph (backend) and @ag-ui/client (frontend) SDKs over Server-Sent Events, not plain REST — the frontend renders Planner/Orchestrator/Synthesizer events as they stream, and the Reviewer's pending-response list updates the same way." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | alternatives: "Plain request/response REST (the original stub's shape) was the starting point but was rejected once streaming agent events became a requirement. WebSocket was the first choice but was rejected on verification (2026-09-07): the official AG-UI reference SDKs — ag-ui-langgraph's add_langgraph_fastapi_endpoint and @ag-ui/client's HttpAgent — only ship SSE (and a binary HTTP variant) out of the box; WebSocket is merely a theoretical protocol capability that would require a custom AbstractAgent subclass on the frontend and a hand-rolled route on the backend, forgoing both official helpers." | reversal_trigger: "If a future AG-UI SDK release ships a built-in WebSocket transport, or bidirectional push becomes a real requirement SSE cannot satisfy, revisit — custom transport code is a cost this POC has no reason to pay today."
Quality Requirements:
  - constraint-perf :: Performance — no numeric SLA | kind: constraint | summary: "Reasonable response time expected for plan/execute/synthesize/approve; no numeric target set (matches BRD NFR-Performance)." | spec: [§Quality Requirements](system-architecture.md#quality-requirements) | source: "docs/business-requirements.md §Non-Functional Requirements — deferred, POC demo context"
  - constraint-security :: Security — no auth, POC-only | kind: constraint | summary: "No authentication/authorization at the API layer; Reviewer vs. Business User separated by surface only (BRD decision-07)." | spec: [§Permission Model and Governance](system-architecture.md#permission-model-and-governance) | source: "docs/business-requirements.md constraint-03 — deferred, trusted internal demo audience only"
  - constraint-observability :: Observability — full trace required | kind: constraint | summary: "Target: 100% of runs expose plan, task assignments, dependencies, execution order, tool outputs, calculations, synthesis, and approval decision (BRD metric-02)." | spec: [§Quality Requirements](system-architecture.md#quality-requirements) | source: "docs/business-requirements.md §Non-Functional Requirements — Observability"
  - constraint-testing :: Testing — no suite authored yet | kind: constraint | summary: "httpx is present as a dev dependency but no test file exists in backend/ yet. Coverage targets are deferred to the TRD/Test Specification stages (50a/50b)." | spec: [§Quality Requirements](system-architecture.md#quality-requirements) | source: "backend/pyproject.toml [dependency-groups.dev] · 2026-09-07 — deferred to 50a/50b"
  - constraint-availability :: Availability — single local instance | kind: constraint | summary: "No uptime target; the system runs as a single local instance for demos, not a hosted service (decision-11)." | spec: [§Quality Requirements](system-architecture.md#quality-requirements) | source: "deferred, POC — no hosted deployment exists to set an uptime target against"
  - constraint-poc-scope :: POC scope — read-only database access | kind: constraint | summary: "The Query Execution Tool only ever runs predefined, read-only queries; the system never writes to the analysis database (BRD constraint-01)." | spec: [§Permission Model and Governance](system-architecture.md#permission-model-and-governance) | source: "docs/business-requirements.md §Scope, constraint-01"
Shared Platform Rules:
  - invariant-config :: Config via environment variables only | kind: invariant | summary: "Every component reads secrets and connection details from environment variables (backend/.env, gitignored); none are hardcoded in source." | spec: [§Shared Platform Rules](system-architecture.md#shared-platform-rules) | violation_signal: "A literal API key, password, or connection string appears in a tracked file."
  - invariant-cors :: CORS is explicitly allow-listed | kind: invariant | summary: "CORS_ALLOWED_ORIGINS names exact origins (currently http://localhost:5173); no wildcard origin is ever used, even in dev." | spec: [§Shared Platform Rules](system-architecture.md#shared-platform-rules) | violation_signal: "CORS_ALLOWED_ORIGINS contains \"*\" or an unreviewed origin."
  - invariant-state-shape :: One typed state shape end-to-end | kind: invariant | summary: "Every LangGraph node reads and writes a single typed state shape (today GraphState; BRD's WorkflowState once implemented) — no node invents its own ad hoc dict shape." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | violation_signal: "A graph node's return value has keys the declared state type does not define."

Interfaces:
  - iface-chat-api :: Chat AG-UI Channel | kind: interface | summary: "SSE connection carrying ag-ui-protocol events (plan, task progress, tool results, synthesis, approval status) between the Business User's frontend and the backend, via ag-ui-langgraph's add_langgraph_fastapi_endpoint. Replaces the deleted stub's plain POST /chat." | spec: [§Module Interactions and Interfaces](system-architecture.md#module-interactions-and-interfaces) | shape: "ag-ui-protocol event stream over SSE (decision-13) — concrete event-type mapping is TRD (50a) work" | version: "unversioned (v0, POC)" | compatibility: "breaking — no versioning scheme exists yet"
  - iface-review-api :: Review AG-UI Channel | kind: interface | summary: "SSE connection carrying ag-ui-protocol events between the Reviewer's frontend surface and the backend — lists pending responses and carries Approve/Reject actions. Never shares a connection with the Chat AG-UI Channel (decision-12)." | spec: [§Module Interactions and Interfaces](system-architecture.md#module-interactions-and-interfaces) | shape: "ag-ui-protocol event stream over SSE (decision-13) — concrete event-type mapping is TRD (50a) work" | version: "unversioned (not yet built)" | compatibility: "additive — no consumers exist yet to break"
  - iface-checkpoint-db :: Checkpoint DB Interface | kind: interface | summary: "The Orchestration Layer's connection to Postgres for reading/writing WorkflowState per thread_id." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | shape: "not yet defined — no checkpointer implementation exists" | version: "unversioned (not yet built)" | compatibility: "additive — no consumers exist yet to break"

comp-frontend-app :: Frontend Chat App (React) | kind: component | summary: "The React/Vite single-page app that renders the chat surface." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "frontend/src/"
comp-chatform :: ChatForm Component | kind: component | summary: "The only UI component today — a form that submits a message and renders the reply. Will move from a plain fetch to @ag-ui/client's HttpAgent over SSE (decision-13)." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "frontend/src/components/ChatForm.tsx"
comp-backend-api :: Backend API App (FastAPI) | kind: component | summary: "The FastAPI app: CORS middleware plus the health router. The chat router was removed 2026-09-07 with its echo-stub dependency." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "backend/app/main.py, backend/app/api/routes/health.py"
comp-chat-route :: Chat Route (/chat) | kind: component | summary: "Planned SSE route serving the Chat AG-UI Channel via ag-ui-langgraph's add_langgraph_fastapi_endpoint (decision-13); invokes the LangGraph graph and streams its events. Removed 2026-09-07 along with its stub graph dependency; not yet rebuilt." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "planned: backend/app/api/routes/chat.py — does not exist on disk right now"
comp-review-route :: Review Route (/review) | kind: component | summary: "Planned SSE route serving the Review AG-UI Channel — lists pending responses and accepts Approve/Reject (BRD decision-07, decision-08). Never built yet." | spec: [§Permission Model and Governance](system-architecture.md#permission-model-and-governance) | boundary: "planned: backend/app/api/routes/review.py — does not exist on disk"
env-local-dev :: Local Dev Environment | kind: environment | summary: "The only environment this POC runs in — a developer's own machine, started via `make backend` and `make frontend`." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "no staging or production environment exists (decision-11)"
pipeline-workflow :: Orchestration Workflow Pipeline | kind: pipeline | summary: "The intended run sequence per BRD UC-001: Planner plans, Orchestration Layer executes tasks against Query Tool/Calculation Agent per dependency, Synthesizer combines results, Human Approval gates the final response." | spec: [§Frontend, Backend, Database, and Deployment Architecture](system-architecture.md#frontend-backend-database-and-deployment-architecture) | boundary: "not yet built — the prior stub echo node (backend/app/graph/graph.py) was deleted 2026-09-07 as setup scaffolding"

edges:
  - comp-frontend-app -decomposes_into-> comp-chatform
  - comp-backend-api -decomposes_into-> comp-chat-route
  - comp-backend-api -decomposes_into-> comp-review-route
  - comp-orchestration-module -decomposes_into-> comp-planner
  - comp-orchestration-module -decomposes_into-> comp-orchestrator
  - comp-orchestration-module -decomposes_into-> comp-query-tool
  - comp-orchestration-module -decomposes_into-> comp-calc-agent
  - comp-orchestration-module -decomposes_into-> comp-synthesizer
  - comp-orchestration-module -decomposes_into-> comp-checkpoint-store
  - comp-chatform -enables-> iface-chat-api
  - comp-chat-route -produces-> iface-chat-api
  - comp-review-route -produces-> iface-review-api
  - comp-orchestrator -enables-> iface-checkpoint-db
  - comp-checkpoint-store -produces-> iface-checkpoint-db
  - comp-planner -enables-> comp-orchestrator
  - comp-orchestrator -enables-> comp-query-tool
  - comp-orchestrator -enables-> comp-calc-agent
  - comp-orchestrator -enables-> comp-synthesizer
  - pipeline-workflow -decomposes_into-> comp-planner
  - comp-backend-api -runs_on-> infra-uvicorn
  - comp-frontend-app -runs_on-> infra-vite
  - comp-checkpoint-store -runs_on-> infra-postgres-container
  - infra-uvicorn -lives_in-> env-local-dev
  - infra-vite -lives_in-> env-local-dev
  - infra-postgres-container -lives_in-> env-local-dev
  - decision-09 -governs-> comp-orchestration-module
  - decision-10 -governs-> comp-checkpoint-store
  - decision-10 -governs-> infra-postgres-container
  - decision-11 -governs-> env-local-dev
  - decision-12 -governs-> comp-review-route
  - decision-13 -governs-> iface-chat-api
  - decision-13 -governs-> iface-review-api
  - constraint-security -governs-> comp-backend-api
  - constraint-poc-scope -governs-> comp-query-tool
  - constraint-observability -governs-> comp-orchestrator
  - constraint-testing -governs-> comp-backend-api
  - invariant-config -governs-> comp-checkpoint-store
  - invariant-cors -governs-> comp-backend-api
  - invariant-state-shape -governs-> pipeline-workflow
```

</details>

## Context and Architectural Drivers

Three goals from the BRD drive this architecture: natural-language data Q&A
(goal-01), a controlled human-approval gate (goal-02), and resumable,
observable orchestration (goal-03). None of these demand a distributed
system — a single backend process, a single frontend, and one persistence
store are sufficient. The dominant driver is therefore **simplicity over
scale**: this is a proof of concept for one PTL and a small internal
audience, not a multi-tenant product. The one property that must not be
compromised for simplicity is BRD goal-03's resumability, which is why
Postgres-backed checkpointing (decision-06 in the BRD) survives into this
architecture as decision-10 below, even though nothing else here needs a
database.

## Frontend, Backend, Database, and Deployment Architecture

**Frontend.** A React 19 + Vite single-page app
(`frontend/`). Today it has exactly one component, `ChatForm`
(`frontend/src/components/ChatForm.tsx`), which posts a message to the
backend over plain `fetch` and renders the reply — there is no routing, no
state management library, and no `/review` surface yet, even though BRD
decision-07 requires one for the Reviewer role (UC-002).
`[derived/observed · src:frontend/src · 2026-09-07]` Decision-13 replaces
that `fetch` call with `@ag-ui/client`'s `HttpAgent` over Server-Sent
Events, so `ChatForm` can render Planner/Orchestrator/Synthesizer events as
they stream instead of waiting for one final reply.

**Backend.** A FastAPI app (`backend/app/main.py`) with CORS middleware and
one router: `health`. A `chat` route and its LangGraph stub
(`backend/app/graph/graph.py`, a single echo node) existed at project
setup but implemented none of the Planner, Orchestration Layer, Query
Execution Tool, Calculation Agent, or Synthesizer described in the BRD —
the PTL had both deleted on 2026-09-07 as setup scaffolding rather than
carry a placeholder forward. `[derived/observed · src:backend/app/main.py ·
2026-09-07]` The route that replaces it will not be a plain REST endpoint:
decision-13 commits both `/chat` and the still-unbuilt `/review` to
`ag-ui-langgraph`'s `add_langgraph_fastapi_endpoint` helper, streaming
agent events over SSE rather than returning one JSON response. Building
the five workflow components, their AG-UI event mapping, and both routes
is squarely stage 50a (TRD) and 50d (Implementation) work; this document
fixes their boundaries and transport, not their internals. Note:
`frontend/src/components/ChatForm.tsx` still posts to `/chat` over plain
`fetch` and will get a 404 until the SSE route is built — expected during
this gap, not a bug to chase now.

**Database.** BRD decision-06 commits to Postgres for `WorkflowState`
checkpointing, keyed by `thread_id`. No checkpointer code exists anywhere
in the repo, and no `DATABASE_URL` was consumed by the app before this
stage — `backend/.env.example` only listed LLM API keys.
`[derived/observed · src:backend/.env.example · 2026-09-07]` This stage adds
`DATABASE_URL` / `POSTGRES_*` variables to `backend/.env` (dummy values —
decision-10) and `backend/.env.example` (documented, empty) so the shape
exists; wiring an actual LangGraph Postgres checkpointer is TRD/implementation
work.

**Deployment.** None. `make backend` runs `uvicorn --reload` locally;
`make frontend` runs `npm run dev` locally (decision-11). There is no
Dockerfile, no CI/CD pipeline, and no cloud target in the repository today.

## Permission Model and Governance

There is no authentication layer (constraint-security, inheriting BRD
constraint-03). BRD decision-07 distinguishes the Business User from the
Reviewer purely by which frontend surface they reach: `/chat` for the
Business User, `/review` for the Reviewer, with no login on either. Today
only the Business User's surface exists in code — `ChatForm` posting to
`/chat` (constraint-poc-scope's read-only boundary is enforced by the Query
Execution Tool never issuing writes, once built). The Reviewer's `/review`
surface, and the backend route(s) it needs to list pending responses and
record Approve/Reject, do not exist yet. Decision-12 settles their shape (a
second frontend route and a second backend route family, never sharing a
connection with the Chat AG-UI Channel) and decision-13 settles their
transport (the same ag-ui-langgraph/@ag-ui/client-over-SSE pattern as
`/chat`, not a different protocol per surface) — building the concrete
screens and event contract is Solution/System (30c/30d) and TRD (50a)
work, not a further architecture decision.

## Technology Baseline

`[derived/observed · src:backend/pyproject.toml, backend/.python-version, frontend/package.json · 2026-09-07]`

| Layer | Choice | Version | Package manager |
|---|---|---|---|
| Backend language | Python | 3.11+ | `uv` (`uv.lock` committed) |
| Backend framework | FastAPI | ≥0.141.1 | — |
| Orchestration | LangGraph | ≥1.2.11 | — |
| Orchestration support | langchain-core | ≥1.6.2 | — |
| Backend server | uvicorn (`[standard]`) | ≥0.52.4 | — |
| Backend config | python-dotenv | ≥1.2.3 | — |
| Backend test tooling | httpx (dev) | ≥0.28.1 | — |
| Agent–UI protocol (backend) | `ag-ui-langgraph` (needs `langgraph>=0.6.0,<2`, `langchain>=1.2.0`, `langchain-core>=0.3.0`, `ag-ui-protocol>=0.1.22` — all satisfied by or addable to this project's pins) | not yet added — decision-13 | `uv` |
| Frontend framework | React | ^19.2.8 | npm (`package-lock.json` committed) |
| Frontend build tool | Vite | ^8.2.2 | — |
| Frontend language | TypeScript | ~6.0.2 | — |
| Frontend lint | oxlint | ^1.79.0 | — |
| Agent–UI protocol (frontend) | `@ag-ui/client` (official TS/JS SDK, `HttpAgent` over SSE) | not yet added — decision-13 | npm |

Shared choice: every environment variable (LLM API keys, Postgres
connection details) lives in `backend/.env` (gitignored); `.env.example`
documents the shape with empty values (invariant-config). Both AG-UI rows
are decided but not yet installed — verified 2026-09-07 against published
package metadata: `ag-ui-langgraph` needs `langgraph>=0.6.0,<2` (this
project's `>=1.2.11` pin satisfies it) and `langchain-core>=0.3.0` (this
project's `>=1.6.2` pin satisfies it), but it also needs plain `langchain`
(`>=1.2.0`), which is not yet a dependency here — adding it, plus pinning
exact `ag-ui-langgraph`/`@ag-ui/client` versions, is TRD/implementation
work, not an architecture-stage task.
`[derived/observed · src:pypi.org/project/ag-ui-langgraph, pypi.org/project/ag-ui-protocol, npmjs.com/package/@ag-ui/client · 2026-09-07]`

## Module Decomposition

This POC registers a single module, **ORCHESTRATION**, at the upcoming
Roadmap stage (30b): the LangGraph planning/execution/synthesis/approval
workflow and the API surface that fronts it (decision-09). Its owner is
Vara (PTL). Internally it decomposes into five components carried over
directly from the BRD's Stakeholders section — Planner Agent, Orchestration
Layer, Query Execution Tool, Calculation Agent, Synthesizer Agent — plus the
Checkpoint Store this architecture adds for decision-06. The frontend
(`comp-frontend-app`, `comp-chatform`) is tracked inside the same module for
now; decision-09 explains why and what would change that.

## Module Interactions and Interfaces

With one module, there are no cross-module contracts yet
(`manifest.rules.cross_module_contracts` is `false` for this project). Three
intra-module interfaces exist or are planned, two of them AG-UI channels
over SSE (decision-13) rather than request/response REST:

| Interface | Producer | Consumer | Shape | Version |
|---|---|---|---|---|
| Chat AG-UI Channel | `comp-chat-route` | `comp-chatform` | Planned: ag-ui-protocol event stream over SSE, replacing the deleted stub's plain `{ message }` → `{ reply }` contract | v0, unversioned |
| Review AG-UI Channel | `comp-review-route` | Reviewer frontend (not yet built) | Planned: ag-ui-protocol event stream over SSE — pending responses and Approve/Reject actions | Not yet built |
| Checkpoint DB Interface | `comp-checkpoint-store` | `comp-orchestrator` | Not yet defined — no checkpointer implementation exists | Not yet built |

Each is single-producer, single-consumer. The Chat and Review AG-UI
Channels never share a connection — Business User and Reviewer must stay
separated by surface per decision-07 and decision-12 — but both use the
same protocol, transport, and official SDK helpers per decision-13, so the
backend gains one SSE-handling pattern to maintain, not two.

## Shared Platform Rules

- **Config via environment variables only** (invariant-config) — no
  secret, connection string, or API key is ever committed to a tracked
  file. `backend/.env` is gitignored; `backend/.env.example` documents the
  shape with empty values.
- **CORS is explicitly allow-listed** (invariant-cors) — `CORS_ALLOWED_ORIGINS`
  names exact origins; a wildcard origin is never acceptable, even in dev.
- **One typed state shape end-to-end** (invariant-state-shape) — every
  LangGraph node reads and writes the same declared state type. Today that
  is the stub `GraphState`; once the Planner/Orchestrator/Tools/Synthesizer
  are built, it becomes the BRD's `WorkflowState` shape verbatim — no node
  invents its own ad hoc dict.

## Quality Requirements

Every row below either states a number or an explicit reason it is
deferred — none are silently unset.

| Dimension | Target | Status |
|---|---|---|
| Performance | No numeric SLA | Deferred — POC demo context (matches BRD NFR-Performance) |
| Security | No auth/production hardening | Deferred — trusted internal demo audience only (BRD constraint-03) |
| Load | Not tested | Deferred — POC, single-demo-user assumption |
| Availability | No uptime target | Deferred — single local instance, no hosted deployment exists (decision-11) |
| Logging / Observability | 100% of runs must expose plan, task assignments, dependencies, execution order, tool outputs, calculations, synthesis, and approval decision | Active target — BRD metric-02 |
| Monitoring | None | Deferred — no ops surface exists for a POC |
| Testing | No coverage target set yet | Deferred to TRD / Test Specification stages (50a/50b) — `httpx` is present as a dev dependency but no test file exists yet |

## Decisions

See the graph above (`decision-09` through `decision-13`) for alternatives
and reversal triggers. In summary: one module for the whole POC
(decision-09); a local Postgres container with dummy credentials the PTL
will replace when ready — not a blocker, since nothing in this architecture
depends on them being real yet (decision-10); no production deployment
target (decision-11); the Reviewer's `/review` surface gets its own route
family rather than a shared, role-gated endpoint (decision-12); and both
`/chat` and `/review` communicate over the official `ag-ui-langgraph`/
`@ag-ui/client` SDKs on SSE rather than plain REST or a hand-rolled
WebSocket transport (decision-13, revised 2026-09-07 after verifying the
official SDKs don't ship WebSocket support).

## Open Questions

No open questions remain at the architecture level.

- Postgres credentials are intentionally dummy for now (decision-10) —
  tracked as a to-do for the PTL, not an architectural ambiguity.
- The Reviewer surface's shape is decided (decision-12); its concrete
  screens and API contract are Solution/System (30c/30d) and TRD (50a)
  work for the ORCHESTRATION module, not an open question here.
- Testing coverage targets are deferred by design to the Test
  Specification stage (50b) — see [Quality Requirements](#quality-requirements).

## Approval

Approved by: Vara
Role:        PTL
Date:        2026-09-07
Hash:        c3deb109e3f3…
