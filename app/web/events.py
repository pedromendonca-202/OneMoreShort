"""In-process event bus (for Server-Sent Events) and the single-worker job runner.

Orchestrator methods are synchronous and can take minutes (narration, render). The panel runs them on
one background thread so two jobs never touch the same production at once, and reports progress by
publishing `job` events that the SSE endpoint streams to the browser.
"""
from __future__ import annotations

import asyncio
import itertools
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

from app.core.errors import HumanActionRequired
from app.core.logging import get_logger

log = get_logger(component="web")

# Human readable stage names for the progress bar (orchestrator `_stage` names).
STAGE_LABELS: dict[str, str] = {
    "discover": "Escolhendo o tema",
    "research": "Pesquisando o tema",
    "script": "Escrevendo o roteiro",
    "storyboard": "Montando o storyboard",
    "prompts": "Gerando os 5 prompts",
    "validate": "Validando os clipes",
    "narration": "Gravando a narração",
    "mix": "Mixando o áudio",
    "captions": "Gerando as legendas",
    "render": "Renderizando o vídeo final",
    "metadata": "Escrevendo título e descrição",
    "quality_gate": "Verificação de qualidade",
    "upload": "Publicando no YouTube",
    "analytics": "Coletando analytics",
    "intelligence": "Aprendendo com os dados",
}


class EventBus:
    """Fan-out of JSON-serialisable events to any number of async subscribers."""

    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self.history: list[dict[str, Any]] = []

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        with self._lock:
            self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._queues.discard(queue)

    def publish(self, type_: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {"type": type_, "at": datetime.now(UTC).isoformat(), "data": data or {}}
        with self._lock:
            self.history.append(event)
            del self.history[:-200]
            queues = list(self._queues)
        for queue in queues:
            self._deliver(queue, event)
        return event

    def _deliver(self, queue: asyncio.Queue, event: dict[str, Any]) -> None:
        def put() -> None:
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(event)

        loop = self._loop
        if loop is None or loop.is_closed():
            put()
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            put()
        else:
            loop.call_soon_threadsafe(put)


@dataclass
class Job:
    id: int
    name: str
    production_id: str | None
    status: str = "queued"  # queued | running | done | failed | human_action
    stage: str | None = None
    stage_label: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None
    human_action: dict[str, str] | None = None
    result: Any = None

    def as_dict(self) -> dict[str, Any]:
        elapsed_end = self.finished_at or time.time()
        return {
            "id": self.id, "name": self.name, "production_id": self.production_id, "status": self.status,
            "stage": self.stage, "stage_label": self.stage_label, "elapsed_s": round(max(0.0, elapsed_end - self.started_at), 1),
            "error": self.error, "human_action": self.human_action,
        }


class JobRunner:
    def __init__(self, bus: EventBus, orchestrator: Any | None = None):
        self.bus = bus
        self.orchestrator = orchestrator
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="oms-job")
        self._ids = itertools.count(1)
        self._jobs: dict[int, Job] = {}
        self._lock = threading.Lock()
        self.current: Job | None = None
        if orchestrator is not None:
            orchestrator.on_stage = self._on_stage

    def _on_stage(self, stage: str, status: str) -> None:
        job = self.current
        if job is None:
            return
        if status == "started":
            job.stage, job.stage_label = stage, STAGE_LABELS.get(stage, stage)
        self.bus.publish("job", {**job.as_dict(), "stage_status": status})

    def get(self, job_id: int) -> Job | None:
        return self._jobs.get(job_id)

    def active_for(self, production_id: str | None) -> Job | None:
        job = self.current
        if job is not None and job.status in {"queued", "running"} and (production_id is None or job.production_id == production_id):
            return job
        with self._lock:
            for candidate in self._jobs.values():
                if candidate.status == "queued" and (production_id is None or candidate.production_id == production_id):
                    return candidate
        return None

    def submit(self, name: str, fn: Callable[[], Any], *, production_id: str | None = None) -> Job:
        job = Job(id=next(self._ids), name=name, production_id=production_id)
        with self._lock:
            self._jobs[job.id] = job
            del_keys = sorted(self._jobs)[:-100]
            for key in del_keys:
                self._jobs.pop(key, None)
        self.bus.publish("job", job.as_dict())
        self._executor.submit(self._run, job, fn)
        return job

    def _run(self, job: Job, fn: Callable[[], Any]) -> None:
        job.status, job.started_at = "running", time.time()
        self.current = job
        self.bus.publish("job", job.as_dict())
        try:
            job.result = fn()
            job.status = "done"
        except HumanActionRequired as err:
            job.status, job.human_action, job.error = "human_action", err.as_dict(), err.problem
        except Exception as err:  # reported to the UI, never swallowed
            job.status, job.error = "failed", str(err) or err.__class__.__name__
            log.error("job.failed", job=job.name, production_id=job.production_id, error=job.error, trace=traceback.format_exc()[-1500:])
        finally:
            job.finished_at = time.time()
            if self.current is job:
                self.current = None
            self.bus.publish("job", job.as_dict())
            self.bus.publish("state", {"production_id": job.production_id})

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
