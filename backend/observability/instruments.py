from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace


@contextmanager
def operation_span(name: str, **attributes: str | int | float | bool | None) -> Iterator[None]:
    tracer = trace.get_tracer("northbound-control-tower")
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield
