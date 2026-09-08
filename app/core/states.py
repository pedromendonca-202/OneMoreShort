"""Production state machine."""
from __future__ import annotations

from enum import Enum

from app.core.errors import InvalidTransition


class State(str, Enum):
    DISCOVERING = "DISCOVERING"
    SELECTED = "SELECTED"
    RESEARCHING = "RESEARCHING"
    SCRIPTING = "SCRIPTING"
    STORYBOARDING = "STORYBOARDING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    EDITING = "EDITING"
    QUALITY_CHECK = "QUALITY_CHECK"
    READY = "READY"
    UPLOADING = "UPLOADING"
    PUBLISHED = "PUBLISHED"
    ANALYZING = "ANALYZING"
    LEARNED = "LEARNED"
    # hold / error states
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    BLOCKED = "BLOCKED"
    NEEDS_HUMAN_ACTION = "NEEDS_HUMAN_ACTION"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    PAUSED_BUDGET = "PAUSED_BUDGET"


PIPELINE_ORDER: list[State] = [
    State.DISCOVERING, State.SELECTED, State.RESEARCHING, State.SCRIPTING, State.STORYBOARDING,
    State.GENERATING, State.VALIDATING, State.EDITING, State.QUALITY_CHECK, State.READY,
    State.UPLOADING, State.PUBLISHED, State.ANALYZING, State.LEARNED,
]
PIPELINE_SET = set(PIPELINE_ORDER)
HOLD_STATES = {
    State.FAILED, State.RETRYING, State.BLOCKED, State.NEEDS_HUMAN_ACTION, State.NEEDS_REVIEW, State.PAUSED_BUDGET,
}
NEVER_UPLOAD = {
    State.BLOCKED, State.FAILED, State.NEEDS_REVIEW, State.NEEDS_HUMAN_ACTION, State.PAUSED_BUDGET, State.RETRYING,
}
TERMINAL = {State.LEARNED}


def next_state(state: State) -> State | None:
    if state not in PIPELINE_SET:
        return None
    idx = PIPELINE_ORDER.index(state)
    return PIPELINE_ORDER[idx + 1] if idx + 1 < len(PIPELINE_ORDER) else None


def is_valid_transition(src: State, dst: State) -> bool:
    if src == dst:
        return True
    if dst in HOLD_STATES and dst != State.RETRYING:
        return True  # any state can fail / pause / need a human
    if dst == State.RETRYING:
        return src in HOLD_STATES
    if src in HOLD_STATES:
        return dst in PIPELINE_SET  # resume back into the pipeline at the recorded stage
    return next_state(src) == dst


def assert_transition(src: State, dst: State) -> None:
    if not is_valid_transition(src, dst):
        raise InvalidTransition(f"{src.value} -> {dst.value} is not allowed")
