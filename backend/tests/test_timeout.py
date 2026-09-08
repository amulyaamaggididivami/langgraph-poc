"""Unit tests for TASK-ORCHESTRATION-018 (bounded external-call timeout
wrapper). Covers TEST-ORCHESTRATION-010.
"""

import time

import pytest

from app.graph.timeout import IntegrationTimeoutError, with_timeout


def test_returns_the_result_when_the_call_finishes_in_time():
    assert with_timeout(lambda: 42, seconds=1) == 42


def test_forwards_args_and_kwargs():
    def add(a, b, *, c):
        return a + b + c

    assert with_timeout(add, 1, 2, c=3, seconds=1) == 6


def test_raises_integration_timeout_error_when_the_call_is_too_slow():
    # TEST-ORCHESTRATION-010
    def slow():
        time.sleep(1)
        return "too late"

    with pytest.raises(IntegrationTimeoutError):
        with_timeout(slow, seconds=0.05)


def test_timeout_returns_promptly_without_waiting_for_the_slow_call():
    def slow():
        time.sleep(1)
        return "irrelevant"

    started = time.monotonic()
    with pytest.raises(IntegrationTimeoutError):
        with_timeout(slow, seconds=0.05)
    elapsed = time.monotonic() - started

    assert elapsed < 0.5


def test_propagates_the_original_exception_when_the_call_fails_fast():
    def boom():
        raise ValueError("business db rejected the query")

    with pytest.raises(ValueError, match="business db rejected the query"):
        with_timeout(boom, seconds=1)
