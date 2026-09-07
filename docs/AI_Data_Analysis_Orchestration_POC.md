# AI-Powered Data Analysis and Human-in-the-Loop Orchestration POC

Document Version: 1.0
Project Type: Proof of Concept (POC)
Status: Draft

# 1. Executive Summary

The objective of this POC is to build an AI-powered data analysis system that can understand a user's natural-language question, dynamically plan the required analysis, retrieve data from a database, perform calculations when required, synthesize the results into a structured response, and obtain human approval before presenting the final answer.

The system will demonstrate dynamic agent/tool orchestration, state management, sequential execution of dependent tasks, and Human-in-the-Loop (HITL) approval.

# 2. Business Objective

The primary objective is to allow users to interact with enterprise data using natural language instead of manually writing SQL queries or performing calculations.

Example user request:

"What were the total sales and average sales for Mumbai last month?"

The system should automatically determine that it needs to:

Retrieve the relevant data from the database.

Perform the required calculations.

Combine the retrieved and calculated results.

Generate a structured response.

Request human approval.

Display the approved response to the user.

# 3. Problem Statement

Traditional data-analysis workflows often require users to understand database structures, write SQL, extract data, perform calculations, interpret raw results, and prepare a final response.

Requires technical knowledge.

Increases the time required to obtain insights.

Introduces opportunities for manual errors.

Makes multi-step analysis difficult to manage.

Does not provide a controlled approval mechanism before an AI-generated answer is shown to the user.

# 4. Scope

## 4.1 In Scope

Natural-language user questions.

LLM-based planning and dynamic tool selection.

Dynamic selection of available tools by the Planner Agent.

Predefined SQL query execution.

Database interaction and retrieval of raw rows.

LLM-powered calculations and aggregations.

Passing outputs between dependent tools.

Final response synthesis.

Human approval with Approve/Reject actions.

Workflow interruption and resumption.

State management and checkpointing.

Sequential tool dependencies.

Observability of planner decisions, tool calls, tool outputs, and approval state.

## 4.2 Out of Scope

Automatic generation of arbitrary SQL for every database table.

Production-scale database optimization.

Automatic modification of production data.

Advanced authentication and authorization.

Large-scale multi-user deployment.

Advanced visualization generation.

Fully autonomous execution without human approval.

Production-grade security implementation.

LLM training or fine-tuning.

# 5. High-Level Architecture

The system consists of a Planner Agent, a deterministic Query Execution Tool, an LLM-powered Calculation Agent/Tool, a mandatory Synthesizer Agent, and a Human Approval stage.

USER QUESTION
        ↓
   PLANNER AGENT
        │
        │ LLM dynamically decides what to do, which tool to use, and the order
        │
   ┌────┴──────────────┐
   ↓                   ↓
QUERY EXECUTION     CALCULATION
     TOOL              AGENT/TOOL
   (No LLM)           (Has LLM)
   │                   │
   │ raw rows          │ calculations
   └─────────┬─────────┘
             ↓
       SYNTHESIZER AGENT
             │
             │ Question + Raw Rows + Calculations
             ↓
        HUMAN APPROVAL
          /         \
     APPROVE        REJECT
        │              │
        ↓              ↓
      USER        REVISE / RETRY

# 6. Functional Requirements

## FR-01: User Question Input

The system shall allow a user to submit a question in natural language. The question shall be passed to the Planner Agent.

## FR-02: Planner Agent – Intent Understanding

The Planner Agent shall use an LLM to understand the user's question and determine:

What information is required.

Whether database data is required.

Whether calculations or aggregations are required.

Which available tool or agent is appropriate for each task.

The order in which tools should be executed.

Whether the results obtained so far are sufficient.

## FR-03: Dynamic Tool Selection

The Planner Agent shall be provided with descriptions and capabilities of the available tools. The Planner Agent itself shall determine which tool should handle each task. The application shall not rely on a hard-coded task-to-tool mapping for this decision.

Example available capabilities:

Query Execution Tool – retrieves business data using predefined SQL queries.

Calculation Agent/Tool – performs calculations and aggregations on retrieved data.

# 7. Planner Agent Execution Loop

The Planner Agent shall support iterative tool use. After each tool execution, the tool result shall be returned to the Planner Agent so that the LLM can decide whether another tool is required or whether the planning task is complete.

Planner LLM
    ↓
Query Execution Tool
    ↓
Raw database rows
    ↓
Planner LLM
    ↓
Calculation Agent/Tool
    ↓
Calculation result
    ↓
Planner LLM
    ↓
DONE

The final Planner LLM step is not responsible for generating the user-facing answer. It only determines that the required planning/tool work is complete. Once the Planner Agent finishes, the fixed workflow proceeds to the Synthesizer Agent.

# 8. Query Execution Tool

## FR-04: Database Query Execution

The Query Execution Tool shall be a deterministic function and shall not require an LLM. For the POC, the tool shall contain approximately three to four predefined SQL queries.

Sales data query.

Order data query.

Customer data query.

Product data query.

The tool shall:

Receive the required query/data request from the Planner Agent.

Execute the appropriate predefined SQL query.

Execute the query against the POC database.

Retrieve the database result.

Return raw rows to the Planner Agent.

# 9. Calculation Agent/Tool

## FR-05: Data Calculation and Aggregation

The Calculation Agent/Tool shall process raw data returned by the Query Execution Tool. It shall have LLM capabilities and shall understand the user's calculation requirement.

Supported example operations include:

Sum

Average

Minimum and maximum

Count

Percentage

Percentage change

Difference

Ratio

Group-based aggregation

Derived metrics

# 10. Tool Dependency

The system shall support dependencies between tool calls. The output of the Query Execution Tool shall be available to the Calculation Agent when the Planner determines that a calculation is required.

Query Execution Tool
        ↓
     Raw rows
        ↓
Calculation Agent
        ↓
Calculation result
        ↓
Planner LLM

# 11. Synthesizer Agent

## FR-06: Final Response Generation

The Synthesizer Agent shall always execute after the Planner Agent completes its required work. The Planner Agent shall not be responsible for deciding whether the Synthesizer should be called.

The Synthesizer shall receive:

Original user question.

Planner output/plan.

Raw database rows.

Calculation results.

The Synthesizer shall transform these inputs into a structured, concise, user-friendly response.

# 12. Human-in-the-Loop

## FR-07: Human Approval

After the Synthesizer generates the proposed response, the workflow shall pause and request human approval before the response is presented as the final answer.

The reviewer shall have two options:

APPROVE – publish/return the synthesized response.

REJECT – prevent publication and initiate the configured revision/retry path.

## FR-08: Approval Flow

If the human selects Approve, the workflow shall continue to the final user response.

## FR-09: Rejection Flow

If the human selects Reject, the response shall not be presented as the final answer. The POC shall support a revision/retry path. The exact retry behavior may be finalized during implementation.

# 13. LangGraph Orchestration Requirements

The workflow orchestration layer shall maintain the overall state, control the high-level workflow, support interruption/resumption for human approval, and support checkpointing.

A conceptual state may contain:

question

plan

raw_rows

calculations

synthesized_response

human_approval

The high-level workflow shall follow:

START
  ↓
Planner Agent
  ↓
Synthesizer Agent
  ↓
Human Approval
  ↓
APPROVE → END
REJECT → configured revise/retry path

# 14. Checkpointing and State Persistence

The POC shall evaluate checkpointing so that workflow state can be persisted at execution points and restored when the workflow resumes after an interruption.

The persisted state may include:

User question.

Planner decisions.

Tool calls and outputs.

Raw database rows.

Calculation results.

Synthesized response.

Human approval status.

# 15. Human-in-the-Loop Interruption and Resume

The workflow shall demonstrate that execution can pause after synthesis, wait for a human decision, and resume using the existing workflow state.

# 16. Thread Management

Each workflow conversation/execution shall have a unique thread identifier. The thread identifier shall associate the workflow state, tool outputs, synthesized response, and human approval state with the same execution context.

# 17. End-to-End Example

User question:

"What was the total sales in Mumbai last month and what was the average?"

Step 1 – Planner: The Planner determines that database data is required and selects the Query Execution Tool.

Step 2 – Query Tool: The predefined SQL query executes and returns raw sales rows.

Step 3 – Planner: The Planner receives the raw rows and determines that a calculation is required.

Step 4 – Calculation Agent: The Calculation Agent calculates the requested total and average.

Step 5 – Planner: The Planner receives the calculation result and determines that the required work is complete.

Step 6 – Synthesizer: The Synthesizer receives the original question, raw rows, and calculation results and creates the structured response.

Step 7 – Human Approval: The workflow pauses and asks the reviewer to Approve or Reject the proposed response.

Step 8 – Approved: The approved response is returned to the user.

# 18. Non-Functional Requirements

## 18.1 Performance

The POC should provide reasonable response times for:

Planner execution.

Database query execution.

Calculation.

Synthesis.

Human approval/resume operation.

## 18.2 Reliability

The system should gracefully handle:

Database query failures.

Invalid tool calls.

Missing or empty data.

Calculation failures.

LLM failures.

Human rejection.

## 18.3 Observability

The POC should make the orchestration trace visible enough to demonstrate the sequence of Planner decisions, tool calls, tool outputs, synthesis, interruption, and human approval.

# 19. Success Criteria

A user can submit a natural-language data question.

The Planner Agent can understand the question.

The Planner Agent can dynamically select the appropriate tool.

The Query Execution Tool can retrieve raw database data.

The Planner can use tool results to determine subsequent actions.

The Calculation Agent can perform required calculations/aggregations.

Dependent tool execution can be handled sequentially.

The Planner can determine when its work is complete.

The Synthesizer receives the original question, raw rows, and calculation results.

The Synthesizer generates a structured response.

The workflow pauses for human approval.

The workflow can resume after approval or follow the configured rejection path.

Workflow state can be checkpointed and restored.

The orchestration flow is observable and demonstrable end to end.

# 20. Final POC Flow

USER QUESTION
                              │
                              ▼
                     ┌─────────────────┐
                     │  PLANNER AGENT  │
                     │       LLM       │
                     │                 │
                     │ Dynamic tool    │
                     │ selection and   │
                     │ sequencing      │
                     └────────┬────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
          QUERY EXECUTION            CALCULATION
              TOOL                     AGENT/TOOL
           (No LLM)                   (Has LLM)
                 │                         │
                 │ raw rows                │ result
                 └────────────┬────────────┘
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

Architecture principle: The Planner Agent is responsible for dynamic planning and tool selection; the Synthesizer is a mandatory downstream stage; and the orchestration layer is responsible for workflow state, checkpointing, interruption, and human approval.
