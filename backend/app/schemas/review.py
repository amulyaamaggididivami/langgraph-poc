"""Pydantic mirrors of trd.md §API Contracts' JSON Schemas for
`iface-review-api` v1.0.0 — the pending-list response, the decision
request, and the one error shape all three endpoints (`/chat`,
`/review`, `/review/{thread_id}/decision`) share.
"""

from typing import Literal

from pydantic import BaseModel


class PendingReview(BaseModel):
    thread_id: str
    question_text: str
    updated_at: str


class DecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]


class ErrorResponse(BaseModel):
    code: Literal["not_found", "already_decided", "integration_timeout", "internal_error"]
    message: str
    retryable: bool
    user_facing_copy_key: str
