"""TASK-ORCHESTRATION-018: Bounded external-call timeout wrapper.

decision-24 bounds every `iface-business-db` and `iface-llm-provider`
call to 50 seconds (raised from the original 30s — the reversal_trigger
fired directly during development: a real Planner call genuinely hung
for 2.5+ minutes against the live LiteLLM proxy with no timeout at all,
and 30s was routinely too tight for legitimately-slow-but-working real
LLM responses even outside that incident) — long enough not to cut off
a legitimately slow LLM response, short enough that a hung call fails
one request instead of hanging it forever. A timeout is `event-integration-failure`
(TRD-ORCHESTRATION-002): it fails only the request that hit it, never
retried automatically (`constraint-no-silent-retry`, the same rule
`already_decided` handling elsewhere in this module enforces).

Implemented with a raw thread, not `signal.alarm`: LangGraph's sync
nodes run inside a worker thread under uvicorn (FastAPI offloads sync
work off the event loop), and `signal.alarm` only fires on the main
thread — it would silently never trigger here.

Also not `concurrent.futures.ThreadPoolExecutor`, despite that being the
obvious first reach for exactly this pattern — its worker threads are
non-daemon by default, and `executor.shutdown(wait=False)` does not
change that. Found the hard way: a genuinely slow call that actually
times out leaves that non-daemon thread running in the background, and
Python's interpreter shutdown sequence *waits for every non-daemon
thread to finish* before the process can exit — confirmed directly via
a hung `pytest` run whose `SIGINT` traceback pointed at
`threading._shutdown` -> `_wait_for_tstate_lock`, not at anything
async/Postgres-related (the more usual suspect elsewhere in this
project). A plain `threading.Thread(daemon=True)` doesn't have this
problem: daemon threads are exactly the ones the interpreter does *not*
wait for.
"""

import queue
import threading
from typing import Callable, TypeVar

DEFAULT_TIMEOUT_SECONDS = 50

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
    for not hanging the request. The thread is daemonized specifically so
    an abandoned, still-running call can never block process exit either
    — see the module docstring. Acceptable for a POC with no retry
    budget to worry about double-executing side effects."""
    result_queue: "queue.Queue[tuple[str, object]]" = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            result_queue.put(("ok", fn(*args, **kwargs)))
        except Exception as exc:  # re-raised on the caller's side below
            result_queue.put(("error", exc))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=seconds)

    if thread.is_alive():
        raise IntegrationTimeoutError(seconds)

    status, value = result_queue.get()
    if status == "error":
        raise value
    return value
