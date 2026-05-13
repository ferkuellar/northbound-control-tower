from __future__ import annotations

import time

from celery import Celery
from celery.signals import task_failure, task_postrun, task_prerun, worker_process_init

from core.config import settings
from core.logging import configure_logging
from observability.metrics import CELERY_TASK_DURATION_SECONDS, CELERY_TASKS_TOTAL

try:
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
except ImportError:  # pragma: no cover - optional dependency guard
    CeleryInstrumentor = None


celery_app = Celery(
    "northbound_control_tower",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

_task_started_at: dict[str, float] = {}


@worker_process_init.connect(weak=False)
def init_worker_observability(*args: object, **kwargs: object) -> None:
    configure_logging()
    if settings.observability_enabled and settings.otel_tracing_enabled and CeleryInstrumentor is not None:
        CeleryInstrumentor().instrument()


@task_prerun.connect(weak=False)
def record_task_started(task_id: str | None = None, task: object | None = None, **kwargs: object) -> None:
    if task_id:
        _task_started_at[task_id] = time.perf_counter()
    task_name = getattr(task, "name", "unknown")
    CELERY_TASKS_TOTAL.labels(task_name, "started").inc()


@task_postrun.connect(weak=False)
def record_task_completed(task_id: str | None = None, task: object | None = None, state: str | None = None, **kwargs: object) -> None:
    task_name = getattr(task, "name", "unknown")
    status = (state or "completed").lower()
    started = _task_started_at.pop(task_id, None) if task_id else None
    CELERY_TASKS_TOTAL.labels(task_name, status).inc()
    if started is not None:
        CELERY_TASK_DURATION_SECONDS.labels(task_name, status).observe(time.perf_counter() - started)


@task_failure.connect(weak=False)
def record_task_failed(task_id: str | None = None, task: object | None = None, **kwargs: object) -> None:
    task_name = getattr(task, "name", "unknown")
    CELERY_TASKS_TOTAL.labels(task_name, "failed").inc()
