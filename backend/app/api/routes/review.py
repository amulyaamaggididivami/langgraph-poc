"""TASK-ORCHESTRATION-015: Review Route (/review).

comp-review-route (trd.md §API Contracts, `iface-review-api` v1.0.0) —
`POST /review` (list pending, a plain JSON snapshot, not a stream) and
`POST /review/{thread_id}/decision` (SSE, resumes the paused graph).

Same SSE mechanism as `/chat` (decision-25: `ag_ui_langgraph`'s
`LangGraphAgent` + `EventEncoder`) but NOT `/chat`'s auto-mounting
`add_langgraph_fastapi_endpoint` helper — that helper supports exactly
one fixed path with `thread_id` inside the POST body
(`RunAgentInput.threadId`), and trd.md's literal contract puts
`thread_id` in the URL path instead. Calling `LangGraphAgent.run()` and
`ag_ui.encoder.EventEncoder` directly (both verified present in the
installed `ag-ui-langgraph`/`ag-ui-protocol` packages) keeps the exact
same event-translation/serialization decision-25 specifies, just wired
to this route's own shape.

`/review` gets its own compiled graph + `LangGraphAgent` (a separate
Python object from `/chat`'s), built against the same checkpointer
instance — never sharing a connection with `/chat` (architecture
decision-12). Since all real state lives in the shared Postgres
checkpointer, not in either graph object's memory, this is safe: any
compiled graph built against the same checkpointer sees the same
threads (verified throughout TASK-ORCHESTRATION-013/014's testing —
separate processes reading/resuming the same thread_id all agreed).

TASK-ORCHESTRATION-017 hardens the error path: both endpoints now catch
unexpected exceptions and return the shared `ErrorResponse` schema
rather than FastAPI's own default `{"detail": ...}` 500 body (verified
this was a real gap, not a theoretical one — `list_pending()` had no
exception handling at all before this). One honest limit that stays:
once `decide()`'s `StreamingResponse` starts, its HTTP status and
headers are already sent — an error that happens *inside*
`event_generator()` (mid-stream) cannot become a differently-shaped
JSON body at that point; only errors before streaming starts (`get_request`,
`aget_state`, the already_decided/not_found checks) can. This is an SSE
transport constraint, not something to work around inside this route —
matching `/chat`'s already-documented deviation (a validation error
there similarly can't retroactively change an in-flight stream).
"""

from typing import Optional
from uuid import uuid4

from ag_ui.core import ResumeEntry, RunAgentInput
from ag_ui.encoder import EventEncoder
from ag_ui_langgraph import LangGraphAgent
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.graph.graph import build_graph
from app.persistence import requests_repo
from app.schemas.review import DecisionRequest, ErrorResponse, PendingReview


def _error_response(code: str, message: str, *, status_code: int, retryable: bool = False) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, retryable=retryable, user_facing_copy_key=f"error.{code}")
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _internal_error_response(exc: Exception) -> JSONResponse:
    return _error_response("internal_error", str(exc), status_code=500, retryable=True)


def register_review_route(app: FastAPI, *, checkpointer: Optional[BaseCheckpointSaver] = None) -> None:
    """Registers `POST /review` and `POST /review/{thread_id}/decision`
    on `app`."""
    graph = build_graph(checkpointer=checkpointer)
    agent = LangGraphAgent(name="review", graph=graph)

    @app.post("/review")
    async def list_pending():
        try:
            rows = await requests_repo.get_pending_reviews()
        except Exception as exc:  # TEST-ORCHESTRATION-016: same shape on failure as the other two endpoints
            return _internal_error_response(exc)
        return [
            PendingReview(
                thread_id=str(row["thread_id"]),
                question_text=row["question_text"],
                updated_at=row["updated_at"].isoformat(),
            )
            for row in rows
        ]

    @app.post("/review/{thread_id}/decision")
    async def decide(thread_id: str, body: DecisionRequest, request: Request):
        try:
            row = await requests_repo.get_request(thread_id)
            if row is None:
                return _error_response("not_found", f"No request found for thread_id {thread_id}", status_code=404)
            if row["state"] != "AwaitingReview":
                return _error_response(
                    "already_decided",
                    f"Thread {thread_id} is already {row['state']}, not AwaitingReview",
                    status_code=409,
                )

            config = {"configurable": {"thread_id": thread_id}}
            state_snapshot = await graph.aget_state(config)
            if not state_snapshot.interrupts:
                return _error_response(
                    "not_found", f"No pending interrupt for thread_id {thread_id}", status_code=404
                )
            interrupt_id = state_snapshot.interrupts[0].id
        except Exception as exc:
            return _internal_error_response(exc)

        run_input = RunAgentInput(
            threadId=thread_id,
            runId=str(uuid4()),
            messages=[],
            tools=[],
            context=[],
            forwardedProps=None,
            resume=[ResumeEntry(interruptId=interrupt_id, status="resolved", payload={"decision": body.decision})],
        )

        accept_header = request.headers.get("accept")
        encoder = EventEncoder(accept=accept_header)
        request_agent = agent.clone()

        async def event_generator():
            async for event in request_agent.run(run_input):
                yield encoder.encode(event)
            final_state = "Delivered" if body.decision == "approve" else "Withheld"
            await requests_repo.update_state(thread_id, final_state)

        return StreamingResponse(event_generator(), media_type=encoder.get_content_type())
