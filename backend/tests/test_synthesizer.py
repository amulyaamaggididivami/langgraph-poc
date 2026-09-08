"""Unit tests for TASK-ORCHESTRATION-007 (Synthesizer node).

Covers TEST-ORCHESTRATION-006. Whether the LLM's actual output includes
the right numbers and never leaks schema names is a live-model property,
not something a unit test against a fake LLM can verify — these tests
cover the node's contract (what goes into the prompt, what comes back
out) and lock in the schema-leak instruction's presence in the prompt.
"""

from app.constants.synthesizer import SYSTEM_PROMPT
from app.graph.nodes.synthesizer import synthesizer_node


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    def __init__(self, fixed_content):
        self._fixed_content = fixed_content
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return _FakeResponse(self._fixed_content)


def test_synthesizer_returns_llm_response_as_synthesized_response():
    fake = _FakeLLM("Total sales were $476,750 across all regions.")
    state = {
        "question": "what were total sales?",
        "raw_rows": [{"region": "North", "amount": 125000.0}],
        "calculations": {"sum": 476750.0},
    }

    update = synthesizer_node(state, llm=fake)

    assert update == {"synthesized_response": "Total sales were $476,750 across all regions."}


def test_synthesizer_includes_question_rows_and_calculations_in_the_prompt():
    fake = _FakeLLM("answer")
    state = {
        "question": "what were total sales?",
        "raw_rows": [{"region": "North", "amount": 125000.0}],
        "calculations": {"sum": 476750.0},
    }

    synthesizer_node(state, llm=fake)

    user_message = fake.last_messages[1].content
    assert "what were total sales?" in user_message
    assert "125000.0" in user_message
    assert "476750.0" in user_message


def test_synthesizer_handles_missing_calculations():
    fake = _FakeLLM("answer")
    state = {"question": "list rows", "raw_rows": [{"region": "North", "amount": 1.0}]}

    synthesizer_node(state, llm=fake)

    user_message = fake.last_messages[1].content
    assert "Calculations:" not in user_message


def test_synthesizer_handles_missing_raw_rows():
    fake = _FakeLLM("answer")
    state = {"question": "some question"}

    synthesizer_node(state, llm=fake)

    user_message = fake.last_messages[1].content
    assert "Raw rows:" not in user_message
    assert "Calculations:" not in user_message


def test_system_prompt_instructs_against_leaking_schema_details():
    # requirement-08 / system.md SY-006 — locking in the instruction's presence
    assert "table" in SYSTEM_PROMPT.lower()
    assert "schema" in SYSTEM_PROMPT.lower()
