# AI-Powered Data Analysis and Human-in-the-Loop Orchestration POC

Document Version: 1.1  
Project Type: Proof of Concept (POC)  
Status: Draft

# 1. Executive Summary

The objective of this POC is to build an AI-powered data analysis system that can understand a user's natural-language question, create a plan for the required analysis, execute that plan through an orchestration layer, retrieve data from a database, perform calculations when required, synthesize the results into a structured response, and obtain human approval before presenting the final answer.

The Planner Agent is responsible only for planning and assigning tasks. The orchestration layer is responsible for executing the planned tasks, managing dependencies and state, and controlling the workflow.

# 2. Business Objective

The primary objective is to allow users to interact with enterprise data using natural language instead of manually writing SQL queries or performing calculations.

Example user request:

"What were the total sales and average sales for Mumbai last month?"

The system should automatically:

1. Determine the tasks required to answer the question.
2. Assign each task to the appropriate tool or agent.
3. Execute the tasks in the required order.
4. Pass outputs between dependent tasks.
5. Combine the retrieved and calculated results.
6. Generate a structured response.
7. Request human approval.
8. Display the approved response to the user.

# 3. Problem Statement

Traditional data-analysis workflows often require users to understand database structures, write SQL, extract data, perform calculations, interpret raw results, and prepare a final response.

- Requires technical knowledge.
- Increases the time required to obtain insights.
- Introduces opportunities for manual errors.
- Makes multi-step analysis difficult to manage.
- Does not provide a controlled approval mechanism before an AI-generated answer is shown to the user.

# 4. Scope

## 4.1 In Scope

- Natural-language user questions.
- LLM-based planning and dynamic task-to-tool assignment.
- Planner-generated task dependencies and execution order.
- Deterministic predefined SQL query execution.
- Database interaction and retrieval of raw rows.
- LLM-powered calculations and aggregations.
- Sequential execution of dependent tasks.
- Passing outputs between dependent tasks.
- Final response synthesis.
- Human approval with Approve/Reject actions.
- Workflow interruption and resumption.
- State management and checkpointing.
- Observability of planner decisions, task execution, tool outputs, synthesis, and approval state.

## 4.2 Out of Scope

- Automatic generation of arbitrary SQL for every database table.
- Production-scale database optimization.
- Automatic modification of production data.
- Advanced authentication and authorization.
- Large-scale multi-user deployment.
- Advanced visualization generation.
- Fully autonomous execution without human approval.
- Production-grade security implementation.
- LLM training or fine-tuning.

# 5. High-Level Architecture

```text
                         USER QUESTION
                              │
                              ▼
                     ┌─────────────────┐
                     │  PLANNER AGENT  │
                     │       LLM       │
                     │                 │
                     │ Creates plan:   │
                     │ - tasks         │
                     │ - executor      │
                     │ - dependencies  │
                     └────────┬────────┘
                              │
                              │ Plan
                              ▼
                     ┌─────────────────┐
                     │  ORCHESTRATION  │
                     │      LAYER      │
                     │      CODE       │
                     │                 │
                     │ Executes plan   │
                     │ and dependencies│
                     └────────┬────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
             QUERY EXECUTION      CALCULATION
                  TOOL              AGENT/TOOL
               (No LLM)             (Has LLM)
                    │                   ▲
                    │                   │
                 Raw Rows ──────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   SYNTHESIZER   │
                     │       LLM       │
                     │                 │
                     │ Question        │
                     │ Raw Rows        │
                     │ Calculations    │
                     └────────┬────────┘
                              │
                              ▼
                       HUMAN APPROVAL
                         /         \
                    APPROVE       REJECT
                       │             │
                       ▼             ▼
                     USER        REVISE / RETRY
```

# 6. Component Responsibilities

## 6.1 Planner Agent

The Planner Agent is an LLM-based planning component.

Its responsibility is to:

- Understand the user's question.
- Identify the tasks required to answer the question.
- Determine which available tool or agent should execute each task.
- Define dependencies between tasks.
- Define the required execution order.
- Produce a structured execution plan.

The Planner does not execute the tools.

The Planner does not generate the final user-facing response.

The Planner does not decide whether the Synthesizer should be called. The Synthesizer is a mandatory downstream stage after planned work is complete.

## 6.2 Orchestration Layer

The orchestration layer is workflow/control logic rather than another planning LLM.

Its responsibility is to:

- Receive the Planner's execution plan.
- Determine which planned task is ready for execution.
- Enforce task dependencies.
- Execute the assigned tool or agent.
- Pass outputs from completed tasks to dependent tasks.
- Maintain workflow state.
- Track task completion and failures.
- Move the workflow to the Synthesizer after all required tasks are complete.
- Pause and resume execution for human approval.
- Maintain checkpointed state where required.

The orchestration layer executes the plan; it does not independently decide the business tasks.

## 6.3 Query Execution Tool

The Query Execution Tool is a deterministic function and does not require an LLM.

For the POC, the tool shall contain approximately three to four predefined SQL queries, such as:

- Sales data query.
- Order data query.
- Customer data query.
- Product data query.

The tool shall:

1. Receive the required query/data request.
2. Select the appropriate predefined SQL query.
3. Execute it against the POC database.
4. Retrieve the result.
5. Return raw rows.

## 6.4 Calculation Agent/Tool

The Calculation Agent/Tool processes data returned by the Query Execution Tool.

It shall have LLM capabilities and understand the requested calculation based on the original question and available task context.

Supported example operations include:

- Sum.
- Average.
- Minimum and maximum.
- Count.
- Percentage.
- Percentage change.
- Difference.
- Ratio.
- Group-based aggregation.
- Derived metrics.

## 6.5 Synthesizer Agent

The Synthesizer Agent is always executed after the required planned tasks have completed.

It receives:

- Original user question.
- Planner-generated plan.
- Raw database rows.
- Calculation results.

It converts these inputs into a structured, concise, user-friendly response.

The Synthesizer is responsible for final response generation; the Planner is not.

## 6.6 Human Approval

After the Synthesizer generates the proposed response, the workflow pauses and requests human approval.

The reviewer can:

- APPROVE — return the synthesized response to the user.
- REJECT — prevent publication and initiate the configured revision/retry path.

# 7. Planner Output

The Planner should produce a structured plan containing tasks, executors, and dependencies.

Example:

```json
{
  "tasks": [
    {
      "id": "task_1",
      "description": "Retrieve Mumbai sales data",
      "executor": "query_execution_tool",
      "depends_on": []
    },
    {
      "id": "task_2",
      "description": "Calculate total and average sales",
      "executor": "calculation_agent",
      "depends_on": ["task_1"]
    }
  ]
}
```

The Planner decides that `task_2` belongs to the Calculation Agent and depends on `task_1`.

The application should not hard-code that mapping for this decision.

# 8. Plan Execution and Orchestration

Once the Planner produces the plan, the orchestration layer executes it.

For example:

```text
Planner
   │
   │ Plan
   ▼
Orchestrator
   │
   │ task_1 has no dependencies
   ▼
Query Execution Tool
   │
   │ raw_rows
   ▼
Orchestrator
   │
   │ task_2 depends on task_1
   ▼
Calculation Agent
   │
   │ calculation_result
   ▼
Orchestrator
   │
   │ all required tasks complete
   ▼
Synthesizer
```

The orchestrator determines what is ready to execute from the dependency information supplied by the Planner.

For a task with no dependencies, the task is immediately eligible for execution.

For a task that depends on another task, execution waits until the dependency is successfully completed.

# 9. Dependency Management

The system shall support dependencies between planned tasks.

Example:

```text
Task 1: Retrieve Mumbai sales
        │
        ▼
Task 2: Calculate average sales
```

The output of Task 1 becomes an input to Task 2.

If there are independent tasks:

```text
        ┌── Task 1: Get sales ──────┐
        │                            │
START ──┤                            ├── Task 3
        │                            │
        └── Task 2: Get customers ──┘
```

Tasks 1 and 2 may be executed independently or in parallel, while Task 3 waits for its required dependencies.

The Planner defines the dependency relationships. The orchestration layer enforces them.

# 10. Execution State

The workflow state should track information such as:

```text
question
plan
task_status
task_results
raw_rows
calculations
synthesized_response
human_approval
```

Example task status:

```text
task_1 → COMPLETED
task_2 → COMPLETED
```

This allows the orchestration layer to determine which tasks are ready and when the planned work is complete.

# 11. Functional Requirements

## FR-01: User Question Input

The system shall allow a user to submit a question in natural language.

## FR-02: Planner Intent Understanding

The Planner Agent shall use an LLM to understand the user's question and determine:

- What information is required.
- Whether database data is required.
- Whether calculations or aggregations are required.
- Which available tool or agent should handle each task.
- Dependencies between tasks.
- Required execution order.

## FR-03: Dynamic Task-to-Tool Assignment

The Planner Agent shall determine which available tool or agent should execute each task.

The application shall not rely on a hard-coded task-to-tool mapping for this decision.

## FR-04: Plan Generation

The Planner shall return a structured execution plan containing:

- Task identifier.
- Task description.
- Assigned executor.
- Dependencies.
- Required task inputs.

## FR-05: Plan Execution

The orchestration layer shall execute tasks according to the Planner-generated plan.

## FR-06: Database Query Execution

The Query Execution Tool shall execute predefined SQL queries and return raw database rows.

## FR-07: Calculation and Aggregation

The Calculation Agent/Tool shall process the required raw data and perform calculations or aggregations.

## FR-08: Dependent Task Execution

The orchestration layer shall make the output of a completed task available to tasks that depend on it.

## FR-09: Completion Detection

The orchestration layer shall detect when all required planned tasks have successfully completed and then transition to the mandatory Synthesizer stage.

## FR-10: Final Response Generation

The Synthesizer Agent shall receive the original question and collected results and generate the structured response.

## FR-11: Human Approval

The workflow shall pause after synthesis and request human approval.

## FR-12: Approval Flow

If the human selects Approve, the workflow shall continue to the final user response.

## FR-13: Rejection Flow

If the human selects Reject, the response shall not be presented as the final answer. The POC shall support a configured revision/retry path.

# 12. Workflow State and Checkpointing

The POC shall evaluate checkpointing so that workflow state can be persisted at execution points and restored when the workflow resumes after an interruption.

Persisted state may include:

- User question.
- Planner-generated plan.
- Task statuses.
- Tool calls and outputs.
- Raw database rows.
- Calculation results.
- Synthesized response.
- Human approval status.

# 13. Human-in-the-Loop Interruption and Resume

The workflow shall demonstrate that execution can pause after synthesis, wait for a human decision, and resume using the existing workflow state.

The approval state shall be associated with the relevant workflow execution.

# 14. Thread Management

Each workflow conversation/execution shall have a unique thread identifier.

The thread identifier shall associate:

- User question.
- Planner plan.
- Task execution state.
- Tool outputs.
- Calculation results.
- Synthesized response.
- Human approval state.

with the same execution context.

# 15. End-to-End Example

User question:

> "What was the total sales in Mumbai last month and what was the average?"

### Step 1 — Planner

The Planner creates:

```text
Task 1
Description: Retrieve Mumbai sales data
Executor: Query Execution Tool
Depends on: None

Task 2
Description: Calculate total and average sales
Executor: Calculation Agent
Depends on: Task 1
```

### Step 2 — Orchestrator

The orchestration layer examines the dependencies.

Task 1 has no dependency, so it is executed first.

### Step 3 — Query Tool

The Query Execution Tool executes the predefined SQL query and returns raw rows.

Example:

```text
[
  { "sale": 10000 },
  { "sale": 20000 },
  { "sale": 30000 }
]
```

### Step 4 — Orchestrator

Task 2 depends on Task 1.

Because Task 1 is complete, the orchestration layer provides its result to Task 2.

### Step 5 — Calculation Agent

The Calculation Agent calculates:

```text
Total = 60,000
Average = 20,000
```

### Step 6 — Orchestrator

All required planned tasks are now complete.

The orchestration layer transitions to the mandatory Synthesizer stage.

### Step 7 — Synthesizer

The Synthesizer receives:

```text
Question
+
Raw Rows
+
Calculation Results
```

and produces a structured response.

### Step 8 — Human Approval

The workflow pauses and asks the reviewer to Approve or Reject the proposed response.

### Step 9 — Approved

If approved, the response is returned to the user.

# 16. Final POC Workflow

```text
                         USER QUESTION
                              │
                              ▼
                     ┌─────────────────┐
                     │  PLANNER AGENT  │
                     │       LLM       │
                     │                 │
                     │ Creates plan    │
                     │ and assigns     │
                     │ tasks/executors │
                     └────────┬────────┘
                              │
                              │ Structured Plan
                              ▼
                     ┌─────────────────┐
                     │  ORCHESTRATION  │
                     │      LAYER      │
                     │      CODE       │
                     │                 │
                     │ Executes plan   │
                     │ Resolves        │
                     │ dependencies    │
                     └────────┬────────┘
                              │
                     ┌────────┴────────┐
                     │                 │
                     ▼                 ▼
              QUERY EXECUTION    CALCULATION
                   TOOL             AGENT
                (No LLM)          (Has LLM)
                     │                 ▲
                     │ raw rows        │
                     └─────────────────┘
                              │
                              │ All planned tasks complete
                              ▼
                     ┌─────────────────┐
                     │   SYNTHESIZER   │
                     │       LLM       │
                     │                 │
                     │ Question        │
                     │ Raw Rows        │
                     │ Calculations    │
                     └────────┬────────┘
                              │
                              ▼
                       HUMAN APPROVAL
                         /         \
                    APPROVE       REJECT
                       │             │
                       ▼             ▼
                     USER        REVISE / RETRY
```

# 17. Architecture Principles

1. **Planner plans; it does not execute.**
2. **The Planner dynamically assigns tasks to available tools or agents.**
3. **The orchestration layer executes the Planner's plan.**
4. **The orchestration layer enforces task dependencies and execution order.**
5. **Tools and worker agents perform the actual tasks.**
6. **The Synthesizer is a mandatory downstream stage and owns final response generation.**
7. **Human approval is required before the response is presented as final.**
8. **Workflow state should be maintained and checkpointed to support interruption and resumption.**

# 18. Non-Functional Requirements

## 18.1 Performance

The POC should provide reasonable response times for:

- Planner execution.
- Database query execution.
- Calculation.
- Synthesis.
- Human approval/resume operation.

## 18.2 Reliability

The system should gracefully handle:

- Database query failures.
- Invalid task assignments.
- Missing or empty data.
- Calculation failures.
- LLM failures.
- Task dependency failures.
- Human rejection.

## 18.3 Observability

The POC should make the orchestration trace visible enough to demonstrate:

- Planner-generated plan.
- Task-to-tool assignments.
- Task dependencies.
- Task execution order.
- Tool outputs.
- Calculation results.
- Synthesis.
- Human interruption.
- Approval decision.
- Workflow resumption.

# 19. Success Criteria

- A user can submit a natural-language data question.
- The Planner Agent can understand the question.
- The Planner Agent can generate a structured task plan.
- The Planner Agent can dynamically assign tasks to the appropriate tools/agents.
- The Planner Agent can define dependencies between tasks.
- The Planner does not execute the tools.
- The orchestration layer can execute the generated plan.
- Dependent tasks execute only after their dependencies complete.
- Query Execution Tool can retrieve raw database data.
- Calculation Agent can perform required calculations/aggregations.
- Outputs from one task can be passed to dependent tasks.
- The orchestration layer can determine when all required tasks are complete.
- The Synthesizer receives the original question, raw rows, and calculation results.
- The Synthesizer generates a structured response.
- The workflow pauses for human approval.
- The workflow can resume after approval or follow the configured rejection path.
- Workflow state can be checkpointed and restored.
- The complete orchestration flow is observable end to end.
