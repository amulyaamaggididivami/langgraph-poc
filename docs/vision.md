---
daksh:
  type: vision
  subtype: null
  stage: "10"
  module: null
---

# Vision

This is Daksh's stage-10 [Vision](glossary#vision) for the LangGraph
orchestration [POC](glossary#poc), grounded in `business-requirements.md`
and the source research write-up,
[AI-Powered Data Analysis and Human-in-the-Loop Orchestration POC](AI_Data_Analysis_Orchestration_POC.md).
Everywhere this document restates a fact the BRD already established (a
Goal, a Decision, a User), it carries the same ID as the BRD — this is the
same entity reappearing in a second document, not a new one; see
[Cross-doc IDs](business-requirements.md) in that file's own graph. What
this document adds on top of the BRD's decisions is the *thesis* framing:
the one deep module the product is, what would invalidate it, and the
open questions that sit above BRD altitude.

What cognition should this graph accelerate? *What is the thesis, what
alternatives were rejected, and what would invalidate it?*

<details><summary>Graph: What is the thesis, what alternatives were rejected, and what would invalidate it?</summary>

```items
---
id: vision-cognition
title: Vision cognition
default_open_depth: 1
default_color_by: kind
color_palette_source: .daksh/color-palette.json
width: 95vw
---
Goals:
  - goal-01 :: Natural-language data Q&A | kind: goal | summary: "Let users get sales/data answers in plain English instead of writing SQL." | spec: [§Vision Statement](vision.md#vision-statement) | success_measure: "Representative business question answered end-to-end without the user writing SQL or performing manual calculation."
  - goal-02 :: Controlled human approval gate | kind: goal | summary: "Every AI-generated answer is reviewed by a human before being shown to the requester." | spec: [§Vision Statement](vision.md#vision-statement) | success_measure: "No synthesized response reaches the user without an explicit Approve action."
  - goal-03 :: Resumable, observable orchestration | kind: goal | summary: "The workflow can pause, checkpoint, resume, and expose its internal decisions for demo and debugging." | spec: [§The One Deep Module](vision.md#the-one-deep-module) | success_measure: "A paused workflow resumes from persisted state and every stage of its trace is inspectable."
Decisions:
  - decision-01 :: Separate LLM planner from code-based executor | kind: decision | summary: "Deep because the Orchestration Layer hides plan-dependency resolution, state checkpointing, and human-interrupt/resume behind one seam every future analysis workflow can reuse — instead of a single agent that both plans and executes." | spec: [§The One Deep Module](vision.md#the-one-deep-module) | alternatives: "A single agent that both plans and executes was considered and rejected — it makes dependency enforcement and state management implicit and hard to test deterministically." | reversal_trigger: "If a plan needs runtime re-planning mid-execution, the strict plan-then-execute split needs revisiting."
  - decision-02 :: Deterministic predefined queries over text-to-SQL | kind: decision | summary: "The Query Execution Tool ships 3-4 hand-defined SQL queries selected by the orchestrator, rather than generating SQL per question." | spec: [§Scope](vision.md#scope) | alternatives: "Full text-to-SQL generation over arbitrary tables was considered and rejected for the POC — out of scope on safety and production-readiness grounds." | reversal_trigger: "If the in-scope question set outgrows what 3-4 predefined queries can answer, revisit toward parameterized or generated queries."
  - decision-03 :: Synthesizer is mandatory, not planner-optional | kind: decision | summary: "The Synthesizer always runs after planned tasks complete; the Planner cannot skip it — this is what makes goal-02's approval gate universal rather than conditional." | spec: [§Vision Statement](vision.md#vision-statement) | alternatives: "Letting the Planner decide whether synthesis is needed was considered and rejected — it would create a path where an unreviewed result reaches the user." | reversal_trigger: "None identified; revisit only if approval latency becomes unacceptable for trivial answers."
  - decision-04 :: Task-status enum is PENDING, RUNNING, COMPLETED, FAILED | kind: decision | summary: "Every task carries one of exactly four statuses; COMPLETED and FAILED are terminal, PENDING and RUNNING are not." | spec: [§The One Deep Module](vision.md#the-one-deep-module) | alternatives: "A richer enum adding SKIPPED/CANCELLED was considered and deferred — the POC's task graph has no optional or cancellable tasks, so those states would sit unused." | reversal_trigger: "If a future plan introduces optional or cancellable tasks, extend the enum with SKIPPED and revisit this decision."
  - decision-05 :: Reject halts the workflow; no retry or replan | kind: decision | summary: "Reject is a deliberate, final action for this POC: it withholds the response and the workflow simply stops for that thread — nothing more happens. No automatic revision, replanning, or retry is planned." | spec: [§Success Metrics](vision.md#success-metrics) | alternatives: "A configured revision/retry path was considered per the source research — rejected as unneeded complexity for this POC; Reject terminates rather than looping." | reversal_trigger: "Only if a future engagement (not this POC) needs automated recovery after a Reject would a retry/replan policy get designed."
  - decision-06 :: Postgres is the checkpoint persistence backend | kind: decision | summary: "WorkflowState checkpoints are persisted to Postgres, keyed by thread_id, rather than kept in memory." | spec: [§The One Deep Module](vision.md#the-one-deep-module) | alternatives: "An in-memory store was considered for demo simplicity but rejected — it would not survive a process restart, defeating the point of checkpoint/resume." | reversal_trigger: "If a fully offline/no-DB demo environment is required, fall back to an embedded or file-based store and revisit."
  - decision-07 :: Reviewer vs. Business User differ by surface, not identity | kind: decision | summary: "No login is checked, by design. A Business User is whoever reaches /chat; a Reviewer is whoever reaches /review. The two roles are separated structurally by which UI/endpoint exposes which action — that is the whole mechanism, not a placeholder for one." | spec: [§Target Users](vision.md#target-users) | alternatives: "Real authentication and role-based authorization were considered — rejected as out of scope for the POC; surface separation with no additional gate is the intended, final mechanism for this POC." | reversal_trigger: "Only if this moves beyond a POC to a real multi-user deployment would surface separation get replaced with real authentication and role-based authorization."
  - decision-08 :: First review response wins; later ones are no-ops | kind: decision | summary: "Whichever Approve/Reject request reaches the resume endpoint first for a given thread_id is final; the graph is no longer paused once it resumes." | spec: [§Success Metrics](vision.md#success-metrics) | alternatives: "An explicit hard-conflict response was considered — deferred; the graph's own state transition already prevents a second resume from having any effect." | reversal_trigger: "If reviewers report confusion from a silent second request, add an explicit 'already decided' response instead of a silent no-op."
  - decision-09 :: Demo data is real database data, not synthetic | kind: decision | summary: "The sales/order/customer/product data the predefined queries hit is real database data, not a synthetic or generated placeholder — resolves oq-10, and is what makes metric-05's 'repeat use' mean something real." | spec: [§Open Questions](vision.md#open-questions) | alternatives: "A synthetic/generated dataset was considered for demo simplicity and isolation — rejected: real data is what makes a resumed run and a 'repeat use' metric mean something." | reversal_trigger: "If real data ever poses an exposure concern in an unauthenticated demo (constraint-03), fall back to a sanitized or synthetic copy and revisit."
  - decision-10 :: Representative question list fixed at implementation stage | kind: decision | summary: "The literal list of business questions used to sign milestone-03 off is fixed in the implementation doc, not in Vision — Vision commits to the shape (3-4 predefined queries, decision-02), not the exact question text. Resolves oq-09." | spec: [§Open Questions](vision.md#open-questions) | alternatives: "Fixing the exact question list at Vision altitude was considered — rejected: the literal question-to-query mapping is an implementation-stage artifact, not a thesis-level commitment." | reversal_trigger: "If the implementation stage never actually produces this list, milestone-03 has no concrete sign-off criteria and this decision needs revisiting."
  - decision-11 :: Generalization beyond this one domain is out of scope for this POC | kind: decision | summary: "Whether the plan-execute-approve pattern works for a second, unrelated business domain is not tested here, by design — this POC exists to prove the pattern for sales/order/customer/product Q&A, not to prove it's portable. Resolves oq-06 by scoping it out, not by claiming the answer is yes." | spec: [§Open Questions](vision.md#open-questions) | alternatives: "Running a second, unrelated domain through the same Orchestration Layer inside this POC was considered — rejected: it doubles scope to prove a claim this engagement was never chartered to prove." | reversal_trigger: "If a future engagement wants to reuse this architecture for a different domain, that engagement's own vision tests generalization then — not this one."
Use Cases:
  - flow-01 :: UC-001 Ask a question, get an approved answer | kind: flow | summary: "End-to-end happy path from question to approved response." | spec: [§Core Capabilities](vision.md#core-capabilities) | actor: "Business User" | trigger: "Business User submits a natural-language question" | outcome: "Approved, structured response is shown to the Business User"
  - flow-02 :: UC-002 Reject a synthesized response | kind: flow | summary: "Reviewer rejects a proposed answer; the response is withheld and the workflow halts for that thread." | spec: [§Core Capabilities](vision.md#core-capabilities) | actor: "Reviewer" | trigger: "Reviewer selects Reject on a synthesized response" | outcome: "Response withheld; workflow terminates for that thread"
  - flow-03 :: UC-003 Resume an interrupted workflow | kind: flow | summary: "A paused/interrupted workflow resumes execution from its last checkpointed state." | spec: [§Core Capabilities](vision.md#core-capabilities) | actor: "Reviewer" | trigger: "Workflow execution is interrupted after pausing for approval" | outcome: "Workflow continues from persisted state without losing prior task results"
Constraints:
  - constraint-01 :: No production data modification | kind: constraint | summary: "The POC only reads data; it does not write, update, or delete production records." | spec: [§Scope](vision.md#scope) | source: "Out of Scope"
  - constraint-02 :: Predefined queries only | kind: constraint | summary: "The Query Execution Tool is limited to 3-4 predefined SQL queries; it does not generate SQL for arbitrary tables." | spec: [§Scope](vision.md#scope) | source: "Out of Scope"
  - constraint-03 :: No production-grade auth or security hardening | kind: constraint | summary: "The POC does not implement advanced authentication, authorization, or production-grade security controls." | spec: [§Scope](vision.md#scope) | source: "Out of Scope"
Assumptions:
  - assumption-01 :: 3-4 predefined queries cover the in-scope question set | kind: assumption | summary: "The representative business questions the POC targets can be answered by a small, fixed set of SQL queries." | spec: [§Leap-of-Faith Assumptions](vision.md#leap-of-faith-assumptions) | validation_plan: "Exercise the POC against sample business questions and confirm each maps to an existing predefined query."
  - assumption-02 :: An LLM can reliably choose the right tool/agent per task | kind: assumption | summary: "The Planner LLM can map each task to query_execution_tool or calculation_agent correctly without hard-coded rules." | spec: [§Leap-of-Faith Assumptions](vision.md#leap-of-faith-assumptions) | validation_plan: "Run the reference example and additional sample questions; confirm executor assignment matches expectation without manual override."
  - assumption-03 :: One mandatory synthesis + approval step is acceptable latency | kind: assumption | summary: "Adding a mandatory Synthesizer plus human-approval step does not make the POC's response time unacceptable for demo purposes." | spec: [§Leap-of-Faith Assumptions](vision.md#leap-of-faith-assumptions) | validation_plan: "Measure end-to-end latency across the reference example during the POC."
  - assumption-04 :: The plan-execute-approve pattern generalizes beyond this domain | kind: assumption | summary: "Once proven for sales/order/customer/product Q&A, the same planner/executor/synthesizer/approval shape answers other enterprise question domains without a redesign." | spec: [§Leap-of-Faith Assumptions](vision.md#leap-of-faith-assumptions) | validation_plan: "Not validated in this POC — it exercises exactly one domain. Treat as unvalidated until a second, unrelated question domain runs through the same orchestration layer unchanged."
Risks:
  - risk-02 :: Trusted-audience assumption breaks outside the demo | kind: risk | summary: "No authentication exists (constraint-03); the moment this reaches anyone outside a trusted internal demo, both Reviewer and Business User identity are unverified." | spec: [§Problem Statements](vision.md#problem-statements) | likelihood: "Low while POC stays internal" | impact: "Any unreviewed party could reach /review and Approve/Reject on someone else's behalf." | mitigation: "Keep the POC on a private, internal-only deployment; never expose /review publicly." | phase: "design"
  - risk-04 :: LLM-computed calculations may be wrong | kind: risk | summary: "The Calculation Agent is LLM-based; arithmetic and aggregation errors are a known LLM failure mode, and nothing in the POC's scope adds independent verification of its output." | spec: [§Problem Statements](vision.md#problem-statements) | likelihood: "Medium" | impact: "A wrong sum/average/ratio reaches the Synthesizer and, if the Reviewer doesn't independently check the arithmetic, past the approval gate too." | mitigation: "Spot-check Calculation Agent output against the raw rows during the POC; do not treat Approve as proof the math is correct." | phase: "design"
  - risk-05 :: Observability trace may show steps without making failures legible | kind: risk | summary: "Exposing plan, assignments, outputs, and calculations (goal-03) is not the same as making a failure's root cause obvious to whoever is watching the demo." | spec: [§Core Capabilities](vision.md#core-capabilities) | likelihood: "Medium" | impact: "A failed run produces a trace nobody can actually read fast enough to diagnose live." | mitigation: "Treat the observability trace's legibility, not just its presence, as part of milestone-03's definition of done." | phase: "design"
Metrics:
  - metric-01 :: Plan correctness and dynamic assignment | kind: metric | summary: "The Planner assigns tasks to tools/agents without a hard-coded mapping and produces a structurally valid plan." | spec: [§Success Metrics](vision.md#success-metrics) | baseline: "Not measured" | target: "Plan validates against schema; executor is Planner-chosen, not hard-coded" | current: "Draft"
  - metric-02 :: End-to-end trace observability | kind: metric | summary: "Every stage of a run is inspectable: plan, assignments, execution order, tool outputs, calculations, synthesis, approval." | spec: [§Success Metrics](vision.md#success-metrics) | baseline: "Not measured" | target: "All observability items are visible for one full run" | current: "Draft"
  - metric-03 :: Approval gate integrity | kind: metric | summary: "No synthesized response reaches the Business User without an explicit Approve." | spec: [§Success Metrics](vision.md#success-metrics) | baseline: "Not measured" | target: "Zero unapproved responses surfaced across test runs" | current: "Draft"
  - metric-04 :: Resume correctness | kind: metric | summary: "A resumed workflow continues from the exact checkpointed state with no lost or duplicated task results." | spec: [§Success Metrics](vision.md#success-metrics) | baseline: "Not measured" | target: "State after resume matches state at pause for all tracked fields" | current: "Draft"
  - metric-05 :: Repeat use beyond the reference demo | kind: metric | summary: "A signal that the POC's value survives past the scripted Mumbai-sales example — someone asks it a question nobody rehearsed." | spec: [§Success Metrics](vision.md#success-metrics) | baseline: "Not measured — no real users yet" | target: "At least one unscripted business question, inside the predefined-query set, answered and approved after handoff" | current: "Not started"
Milestones:
  - milestone-01 :: Planner-to-Orchestrator core loop works | kind: milestone | summary: "Planner produces a valid dependent-task plan and the orchestrator executes task_1 then task_2 in order." | spec: [§Success Metrics](vision.md#success-metrics) | due: "TBD - internal POC target" | definition_of_done: "A representative question produces a structured plan and the orchestrator executes it respecting the declared dependency."
  - milestone-02 :: Human-in-the-loop interrupt/resume demonstrated | kind: milestone | summary: "Workflow pauses after synthesis, persists state, and resumes correctly on Approve; on Reject it halts cleanly instead." | spec: [§Success Metrics](vision.md#success-metrics) | due: "TBD - internal POC target" | definition_of_done: "A paused workflow is resumed from checkpointed state on Approve, and on Reject the workflow terminates for that thread with no retry — both paths are exercised."
  - milestone-03 :: Full end-to-end demo with observable trace | kind: milestone | summary: "The complete reference flow runs live with the orchestration trace visible." | spec: [§Success Metrics](vision.md#success-metrics) | due: "TBD - internal POC target" | definition_of_done: "The full flow runs end to end and every stage of the trace is inspectable."
Open Questions:
  - oq-06 :: Does the pattern generalize beyond this one question domain? | kind: openquestion | summary: "The POC only ever exercises sales/order/customer/product questions against 3-4 predefined queries; whether the planner/executor/synthesizer/approval shape holds for a genuinely different domain is untested." | spec: [§Open Questions](vision.md#open-questions)
  - oq-09 :: What counts as a 'representative' business question for demo sign-off? | kind: openquestion | summary: "assumption-01 assumes the in-scope question set is covered by the 3-4 predefined queries, but no fixed, agreed list of representative questions exists yet to sign milestone-03 off against." | spec: [§Open Questions](vision.md#open-questions)
  - oq-10 :: Is the demo data real or synthetic, and does that matter for handoff? | kind: openquestion | summary: "constraint-01 keeps the POC read-only, but whether the underlying sales/order/customer/product data is a realistic sample or a synthetic placeholder isn't stated, and it changes what metric-05's 'repeat use' would even mean." | spec: [§Open Questions](vision.md#open-questions)
Users:
  - user-01 :: Business User | kind: user | summary: "Asks natural-language data questions and consumes the approved answer." | spec: [§Target Users](vision.md#target-users) | role: "Business User" | audience: end_customer | status: placeholder
  - user-02 :: Reviewer / Approver | kind: user | summary: "Reviews the synthesized response and selects Approve or Reject; Reject halts the workflow for that run, with no retry." | spec: [§Target Users](vision.md#target-users) | role: "Reviewer" | audience: client | status: placeholder
  - user-03 :: PTL | kind: user | summary: "Accountable for scoping and sign-off on POC decisions." | spec: [§Target Users](vision.md#target-users) | role: "PTL" | audience: delivery | status: validated
decision-01 -> goal-01 | relation: enables
decision-01 -> goal-03 | relation: enables
decision-01 -> milestone-01 | relation: governs
decision-02 -> goal-01 | relation: enables
decision-02 -> milestone-01 | relation: governs
decision-03 -> goal-02 | relation: enables
decision-03 -> milestone-03 | relation: governs
decision-04 -> milestone-01 | relation: governs
decision-05 -> goal-02 | relation: governs
decision-05 -> milestone-02 | relation: governs
decision-06 -> goal-03 | relation: enables
decision-07 -> goal-02 | relation: enables
decision-08 -> milestone-02 | relation: governs
decision-09 -> oq-10 | relation: decides
decision-09 -> metric-05 | relation: enables
decision-10 -> oq-09 | relation: decides
decision-10 -> milestone-03 | relation: governs
decision-11 -> oq-06 | relation: decides
constraint-01 -> goal-01 | relation: governs
constraint-02 -> decision-02 | relation: governs
constraint-03 -> decision-07 | relation: governs
assumption-01 -> decision-02 | relation: enables
assumption-02 -> decision-01 | relation: enables
assumption-03 -> decision-03 | relation: enables
assumption-04 -> decision-01 | relation: enables
risk-02 -> goal-02 | relation: threatens
risk-04 -> goal-01 | relation: threatens
risk-05 -> goal-03 | relation: threatens
metric-01 -> goal-01 | relation: watches
metric-02 -> goal-01 | relation: watches
metric-02 -> goal-03 | relation: watches
metric-03 -> goal-02 | relation: watches
metric-04 -> goal-03 | relation: watches
metric-05 -> goal-01 | relation: watches
user-01 -> flow-01 | relation: experiences
user-01 -> flow-03 | relation: experiences
user-02 -> flow-01 | relation: experiences
user-02 -> flow-02 | relation: experiences
user-02 -> milestone-02 | relation: owns
user-03 -> decision-01 | relation: owns
user-03 -> decision-02 | relation: owns
user-03 -> decision-03 | relation: owns
user-03 -> milestone-03 | relation: owns
```

</details>

## Vision Statement

Prove that separating LLM **planning** from deterministic **execution** —
with a mandatory synthesis step and a human approval gate — lets a
business user get a trustworthy natural-language answer to a data
question, without writing SQL, and without an ungoverned AI response ever
reaching them (goal-01, goal-02).

The Synthesizer being mandatory (decision-03) is what makes that promise
universal rather than conditional: there is no code path where a plan
completes and a response reaches a user without passing through both
synthesis and approval.

## The One Deep Module

The product's thesis is not "an LLM that answers data questions." It is
that the **Orchestration Layer is the one deep module worth building
carefully**, and everything LLM-shaped around it — Planner, Calculation
Agent, Synthesizer — are interchangeable participants it coordinates
(decision-01).

Its interface is small: *take a plan, execute it, checkpoint it, gate it
on a human decision, hand back a result.* What that small interface hides
is not small: dependency-graph execution order (decision-04's status
enum), state persistence across process restarts (decision-06, Postgres
keyed by `thread_id`), and pause/resume semantics for a human-in-the-loop
interrupt. Run the deletion test on it: delete the Orchestration Layer,
and this complexity does not vanish — every future analysis workflow that
wants dependency-aware execution, checkpointing, or an approval gate
would have to re-solve all three itself. That's the signature of a deep
module, not a shallow pass-through.

**What would invalidate this thesis:**

- If a plan needs runtime re-planning mid-execution — the Planner
  reacting to a task's result by inventing new tasks — the strict
  plan-then-execute split (decision-01) stops holding, because the
  Orchestrator would need to hand control back to the Planner mid-run
  instead of just executing a fixed plan. This is decision-01's own
  `reversal_trigger`.
- If the checkpoint/resume machinery (goal-03) is never exercised by a
  real interruption — only ever demoed on command — its depth is
  unproven. A capability nobody's process restart ever needed is a
  feature, not evidence of leverage.
- If the pattern is ever asked to prove itself on a second, unrelated
  question domain, the "one deep module, many callers" claim is
  unverified — it may just be one module, one caller, dressed up as an
  abstraction. This POC deliberately doesn't test that (decision-11);
  assumption-04 stays an open leap of faith precisely because nobody
  checked.

## Target Users

| User | Role | What changes for them |
|---|---|---|
| user-01 — Business User | `end_customer`, `status: placeholder` (not yet interviewed) | Gets a sales/data answer by typing a question in plain English instead of writing SQL, waiting on a data analyst, or doing the math by hand. |
| user-02 — Reviewer / Approver | `client`, `status: placeholder` | Sees every AI-generated answer before the Business User does, and can withhold it (decision-05) — a control that doesn't exist in the "traditional" workflow described in the Problem Statements below. |
| user-03 — PTL (Vara) | `delivery`, `status: validated` | Owns the architecture decisions (decision-01, -02, -03) and the full-demo milestone (milestone-03); accountable for scope, not for using the product day to day. |

Reviewer and Business User are told apart by **which door they walk
through** — `/review` vs `/chat` — not by a checked credential
(decision-07). That is the intended, final mechanism for this POC, not a
stopgap awaiting a real identity model; decision-07's own
`reversal_trigger` names the one thing that would change it — this
becoming a real multi-user deployment, which this engagement is not.

## Problem Statements

Three problems this product exists to remove, each carrying its own known
risk or constraint:

1. **Getting a data answer requires technical skill.** Traditional
   workflows require the requester to understand the schema, write SQL,
   and do their own math (goal-01). *Constraint:* the POC deliberately
   answers this with a small, deterministic set of predefined queries
   (constraint-02, decision-02) — not automatic SQL generation. That's an
   intentional design choice, not a gap to close later; the actual
   remaining question is downstream of it, in the LLM step that consumes
   the query's output. *Risk:* risk-04 — the Calculation Agent is LLM-
   based, and nothing in scope independently checks its arithmetic.
2. **No governed gate exists before an AI answer reaches someone.**
   Without a mandatory approval step, an ungrounded or wrong AI answer
   reaches the requester with no human in the loop (goal-02). Reject
   (decision-05) is the whole gate: it withholds the response and stops
   the workflow for that thread — no revision, no replan, nothing further
   is in scope for this POC.
3. **Multi-step analysis (retrieval + calculation) is hard to manage and
   reproduce.** Without an explicit plan/dependency model, a multi-part
   question's sub-steps are done ad hoc, with no record of what depended
   on what (goal-03). *Constraint:* the POC's read-only stance
   (constraint-01) and lack of production-grade security (constraint-03)
   mean this problem is being solved for a **trusted internal
   demonstration**, not a hardened deployment. *Risk:* risk-02 — that
   trusted-audience assumption breaks the moment this reaches anyone
   outside the demo; risk-05 — an observability trace that shows every
   step but still doesn't make a failure's cause obvious.

## Core Capabilities

At a high level, without implementation detail:

- Accept a natural-language question (flow-01).
- Turn it into a dependency-ordered plan, with the Planner — not
  hard-coded application logic — deciding which tool or agent handles
  each step.
- Retrieve data deterministically and calculate over it, passing outputs
  between dependent steps.
- Always synthesize a single structured response before anyone sees it
  (decision-03).
- Always pause for a human Approve/Reject decision before that response
  is shown (goal-02); Reject withholds it and ends the run (flow-02).
- Persist and resume workflow state across an interruption (flow-03),
  keyed to a `thread_id`.
- Make every internal decision — plan, assignments, execution order,
  tool outputs, calculations, synthesis, approval — inspectable
  end-to-end (goal-03).

## Scope

**In scope for this POC:** everything the six capabilities above cover,
bounded by three constraints carried over from the BRD and reused here
verbatim because they are the same facts, not new ones — constraint-01
(read-only, no production data modification), constraint-02 (3-4
predefined queries, no generated SQL), constraint-03 (no production-grade
auth or security hardening).

**Out of scope, by design — not gaps, decisions:**

| Cut for this POC | Why it's intentional | Would only be reconsidered if |
|---|---|---|
| Arbitrary text-to-SQL over any table | decision-02: predefined, deterministic queries are the point — safer and more testable than generated SQL for a POC | The in-scope question set outgrows 3-4 predefined queries |
| Retry/replan after Reject | decision-05: Reject is meant to simply stop the workflow, nothing more | A future engagement beyond this POC needs automated recovery after a Reject |
| Real authentication / role-based authorization | decision-07: surface separation (`/chat` vs `/review`) is the intended mechanism, not a stand-in for one | This moves past POC into a real multi-user deployment |
| Large-scale multi-user deployment, advanced visualization, LLM training/fine-tuning | Not part of what this POC is trying to prove | Not applicable to this engagement's scope at all — a different engagement, not a later POC phase |

## Leap-of-Faith Assumptions

Four beliefs this product rests on. None are validated yet — the POC
exists to test them, not to assume they're already true:

- **assumption-01** — 3-4 predefined queries cover the in-scope question
  set. *Not validated.* Test by running sample business questions against
  the fixed query set.
- **assumption-02** — an LLM can reliably choose the right tool/agent per
  task without hard-coded rules. *Not validated.* Test by checking
  executor assignment against expectation on the reference example and
  variants.
- **assumption-03** — one mandatory synthesis + approval step is
  acceptable latency for a demo. *Not validated.* Test by measuring
  end-to-end latency.
- **assumption-04** — the plan-execute-approve pattern generalizes beyond
  this one domain. *Not validated, and not even exercised* — decision-11
  scopes testing this out of the POC entirely. This is the biggest of
  the four precisely because it stays untested: if it's wrong, the POC
  proves the pattern works for exactly one demo, not that the deep
  module (§The One Deep Module) has real leverage beyond it. Closing
  oq-06 by decision didn't make this assumption true — it just says this
  engagement isn't the one that checks.

## Success Metrics

**At handoff** — the three milestones this POC must clear, and the
metrics that watch them (none are measured yet; all are `current: Draft`
until a run produces evidence):

- milestone-01 (Planner→Orchestrator core loop) — watched by metric-01
  (plan correctness) and metric-02 (trace observability).
- milestone-02 (human-in-the-loop interrupt/resume) — watched by
  metric-03 (approval gate integrity); governed by decision-05 (Reject
  halts, no retry) and decision-08 (first-write-wins on concurrent
  review actions).
- milestone-03 (full end-to-end demo with observable trace) — watched by
  metric-04 (resume correctness) and metric-02.

**At user adoption** — beyond handoff, the one metric that isn't about
the demo running correctly but about the demo *mattering*: metric-05,
repeat use beyond the reference demo. Nobody has asked this system an
unscripted question yet; until someone does, adoption is aspirational,
not measured.

## Open Questions

Every open question the BRD raised (oq-01 through oq-05) is already
resolved there by decision-04 through decision-08 — see
[business-requirements.md §Open Questions](business-requirements.md#open-questions).
Restating them here would be duplication, not lineage, so this section
raises only what sits **above** BRD altitude.

To be explicit about what is *not* open: the predefined-query design
(decision-02), the no-retry Reject behavior (decision-05), and the
surface-based Reviewer/Business-User separation (decision-07) are all
settled, intentional choices for this POC — not questions awaiting an
answer. All three this document raised itself are now resolved too:

- **oq-09** — what counts as a "representative" business question for
  signing milestone-03 off? *Resolved* by decision-10: the exact list is
  fixed in the implementation doc, not here — Vision only commits to the
  shape (decision-02), not the literal question text.
- **oq-10** — is the demo data real or synthetic? *Resolved* by
  decision-09: it's real database data, not a synthetic placeholder.
- **oq-06** — does the pattern generalize beyond this one question
  domain? *Resolved* by decision-11 — not by proving it generalizes, but
  by scoping the question itself out of this POC. Untested is a
  different thing from unresolved: whether the pattern actually
  generalizes stays an open leap of faith (assumption-04); what's
  resolved is that this engagement isn't the one that finds out.

No open question in this document remains without a decision closing it.
That is not the same claim as "no risk remains" — assumption-04 and
risk-02, risk-04, risk-05 are still live, exactly as intended.

## Approval

Approved by: Vara
Role:        PTL
Date:        2026-09-07
Hash:        28b21fc63fd3…
