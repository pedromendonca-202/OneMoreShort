import pytest

from app.core.errors import InvalidTransition
from app.core.states import NEVER_UPLOAD, PIPELINE_ORDER, State, assert_transition, next_state


def test_pipeline_order_matches_spec():
    assert [s.value for s in PIPELINE_ORDER] == [
        "DISCOVERING", "SELECTED", "RESEARCHING", "SCRIPTING", "STORYBOARDING",
        "GENERATING", "VALIDATING", "EDITING", "QUALITY_CHECK", "READY",
        "UPLOADING", "PUBLISHED", "ANALYZING", "LEARNED",
    ]


def test_forward_transition_ok():
    assert_transition(State.SCRIPTING, State.STORYBOARDING)
    assert next_state(State.SCRIPTING) == State.STORYBOARDING


def test_skipping_stage_is_invalid():
    with pytest.raises(InvalidTransition):
        assert_transition(State.SCRIPTING, State.GENERATING)


def test_error_states_reachable_from_anywhere():
    for s in PIPELINE_ORDER:
        assert_transition(s, State.FAILED)
        assert_transition(s, State.NEEDS_HUMAN_ACTION)
        assert_transition(s, State.PAUSED_BUDGET)


def test_retrying_returns_to_pipeline():
    assert_transition(State.FAILED, State.RETRYING)
    assert_transition(State.RETRYING, State.GENERATING)


def test_never_upload_set():
    assert {State.BLOCKED, State.FAILED, State.NEEDS_REVIEW, State.NEEDS_HUMAN_ACTION, State.PAUSED_BUDGET} <= NEVER_UPLOAD
    assert State.READY not in NEVER_UPLOAD
