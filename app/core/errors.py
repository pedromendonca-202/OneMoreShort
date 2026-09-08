"""Typed errors shared across the platform."""
from __future__ import annotations


class OMSError(Exception):
    """Base class for all OneMoreShort errors."""


class InvalidTransition(OMSError):
    pass


class BudgetExceeded(OMSError):
    def __init__(self, spent: float, limit: float, upcoming: float):
        self.spent, self.limit, self.upcoming = spent, limit, upcoming
        super().__init__(
            f"Daily budget exceeded: spent ${spent:.2f} + upcoming ${upcoming:.2f} > limit ${limit:.2f}"
        )


class CircuitOpen(OMSError):
    pass


class FFmpegError(OMSError):
    def __init__(self, cmd: list[str], stderr: str, returncode: int | None = None):
        self.cmd, self.stderr, self.returncode = cmd, stderr, returncode
        super().__init__(f"ffmpeg failed (rc={returncode}): {stderr[-800:]}")


class ValidationFailed(OMSError):
    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__("; ".join(issues))


class ExternalAPIError(OMSError):
    def __init__(self, api: str, message: str, retryable: bool = True):
        self.api, self.retryable = api, retryable
        super().__init__(f"[{api}] {message}")


class RateLimited(ExternalAPIError):
    def __init__(self, api: str, message: str = "rate limited"):
        super().__init__(api, message, retryable=True)


class StageError(OMSError):
    def __init__(self, stage: str, message: str, retryable: bool = True):
        self.stage, self.retryable = stage, retryable
        super().__init__(f"[{stage}] {message}")


class HumanActionRequired(OMSError):
    """Raised when an official platform step needs a human. Never bypassed."""

    def __init__(self, *, problem: str, root_cause: str, automated: str, remains: str, action: str, next_step: str):
        self.problem, self.root_cause, self.automated = problem, root_cause, automated
        self.remains, self.action, self.next_step = remains, action, next_step
        super().__init__(problem)

    def report(self) -> str:
        return (
            "WAITING_FOR_HUMAN_ACTION\n"
            f"PROBLEM: {self.problem}\n"
            f"ROOT CAUSE: {self.root_cause}\n"
            f"WHAT WAS AUTOMATED: {self.automated}\n"
            f"WHAT REMAINS: {self.remains}\n"
            f"EXACT HUMAN ACTION REQUIRED: {self.action}\n"
            f"NEXT AUTOMATIC STEP: {self.next_step}"
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "problem": self.problem,
            "root_cause": self.root_cause,
            "automated": self.automated,
            "remains": self.remains,
            "action": self.action,
            "next_step": self.next_step,
        }
