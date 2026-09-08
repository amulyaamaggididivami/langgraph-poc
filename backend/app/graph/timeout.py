"""TASK-ORCHESTRATION-018: Bounded external-call timeout wrapper.

decision-24 bounds every `iface-business-db` and `iface-llm-provider`
call to 30 seconds — long enough not to cut off a legitimately slow LLM
response, short enough that a hung call fails one request instead of
hanging it forever. A timeout is `event-integration-failure`
(TRD-ORCHESTRATION-002): it fails only the request that hit it, never
retried automatically (`constraint-no-silent-retry`, the same rule
`already_decided` handling elsewhere in this module enforces).

Implemented with a thread pool, not `signal.alarm`: LangGraph's sync
nodes run inside a worker thread under uvicorn (FastAPI offloads sync
work off the event loop), and `signal.alarm` only fires on the main
thread — it would silently never trigger here.
"""

import concurrent.futures
from typing import Callable, TypeVar

DEFAULT_TIMEOUT_SECONDS = 30

T = TypeVar("T")


class IntegrationTimeoutError(Exception):
    """event-integration-failure — a bounded external call exceeded its
    deadline. Not a subclass of TimeoutError on purpose: callers should
    catch this specific type, not accidentally swallow an unrelated
    stdlib timeout somewhere else in the same call stack."""

    def __init__(self, seconds: float):
        super().__init__(f"External call exceeded the {seconds}s bound (event-integration-failure)")
        self.seconds = seconds


def with_timeout(fn: Callable[..., T], *args, seconds: float = DEFAULT_TIMEOUT_SECONDS, **kwargs) -> T:
    """Runs `fn(*args, **kwargs)` with a wall-clock deadline, raising
    `IntegrationTimeoutError` if it isn't done in time.

    Does not (cannot) forcibly kill `fn` on timeout — Python has no safe
    way to kill a running thread. The abandoned call keeps running in
    the background and its eventual result is discarded; this function
    itself returns as soon as the deadline passes, which is what matters
    for not hanging the request. Acceptable for a POC with no retry
    budget to worry about double-executing side effects."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args, **kwargs)
    try:
        result = future.result(timeout=seconds)
    except concurrent.futures.TimeoutError:
        executor.shutdown(wait=False)
        raise IntegrationTimeoutError(seconds) from None
    executor.shutdown(wait=False)
    return result
