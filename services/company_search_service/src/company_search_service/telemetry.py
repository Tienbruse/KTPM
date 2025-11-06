from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("company_search_service")
logger.setLevel(logging.INFO)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request identifier and basic timing for observability."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # pragma: no cover - defensive logging
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Unhandled exception",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"

        MetricsRecorder.instance().record(
            request.method, request.url.path, response.status_code, duration_ms
        )
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response


class MetricsRecorder:
    _instance: "MetricsRecorder" | None = None

    def __init__(self) -> None:
        self._totals = defaultdict(int)
        self._latency = defaultdict(list)
        self._dependency_calls = defaultdict(int)
        self._breaker_state: dict[str, str] = {}
        self._breaker_open_total = defaultdict(int)

    @classmethod
    def instance(cls) -> "MetricsRecorder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def record(
        self, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        key = (method.upper(), path, status_code)
        self._totals[key] += 1
        self._latency[key].append(duration_ms)

    def record_dependency_call(
        self, dependency: str, operation: str, outcome: str
    ) -> None:
        key = (dependency, operation, outcome)
        self._dependency_calls[key] += 1

    def record_breaker_state(self, breaker_name: str, state: str) -> None:
        previous = self._breaker_state.get(breaker_name)
        self._breaker_state[breaker_name] = state
        if state == "open" and previous != "open":
            self._breaker_open_total[breaker_name] += 1

    def snapshot(self) -> dict[str, list[dict[str, float]]]:
        buckets: dict[str, list[dict[str, float]]] = defaultdict(list)
        for (method, path, status_code), count in self._totals.items():
            latencies = self._latency[(method, path, status_code)]
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            p95_index = max(int(0.95 * (len(latencies) - 1)), 0)
            p95_value = sorted(latencies)[p95_index]
            buckets[path].append(
                {
                    "method": method,
                    "status_code": status_code,
                    "count": float(count),
                    "avg_ms": round(avg_latency, 2),
                    "p95_ms": round(p95_value, 2),
                    "max_ms": round(max_latency, 2),
                }
            )
        return buckets

    def dependency_snapshot(self) -> dict[str, dict[str, dict[str, float]]]:
        snapshot: dict[str, dict[str, dict[str, float]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        for (dependency, operation, outcome), count in self._dependency_calls.items():
            snapshot[dependency][operation][outcome] = float(count)
        return snapshot

    def breaker_snapshot(self) -> dict[str, dict[str, float | str]]:
        return {
            "states": self._breaker_state.copy(),
            "opens": {
                name: float(count) for name, count in self._breaker_open_total.items()
            },
        }


async def metrics_endpoint() -> PlainTextResponse:
    recorder = MetricsRecorder.instance()
    snapshot = recorder.snapshot()
    lines = [
        "# HELP http_requests_total Total number of HTTP requests",
        "# TYPE http_requests_total summary",
    ]
    for path, records in snapshot.items():
        for record in records:
            labels = {
                "path": path,
                "method": record["method"],
                "status_code": int(record["status_code"]),
            }
            label_str = ",".join(f'{key}="{value}"' for key, value in labels.items())
            lines.append(f"http_requests_total{{{label_str}}} {int(record['count'])}")
            lines.append(
                f"http_request_duration_ms_avg{{{label_str}}} {record['avg_ms']}"
            )
            lines.append(
                f"http_request_duration_ms_p95{{{label_str}}} {record['p95_ms']}"
            )
            lines.append(
                f"http_request_duration_ms_max{{{label_str}}} {record['max_ms']}"
            )

    dep_snapshot = recorder.dependency_snapshot()
    if dep_snapshot:
        lines.append(
            "# HELP circuit_breaker_calls_total Total calls to external dependencies grouped by outcome"
        )
        lines.append("# TYPE circuit_breaker_calls_total counter")
        for dependency, operations in dep_snapshot.items():
            for operation, outcomes in operations.items():
                for outcome, count in outcomes.items():
                    label_str = f'dependency="{dependency}",operation="{operation}",outcome="{outcome}"'
                    lines.append(
                        f"circuit_breaker_calls_total{{{label_str}}} {int(count)}"
                    )

    breaker_snapshot = recorder.breaker_snapshot()
    if breaker_snapshot["states"]:
        lines.append(
            "# HELP circuit_breaker_state Current state of the circuit breaker (0=closed,1=half_open,2=open)"
        )
        lines.append("# TYPE circuit_breaker_state gauge")
        for name, state in breaker_snapshot["states"].items():
            state_value = {"closed": 0, "half_open": 1, "open": 2}.get(state, -1)
            label_str = f'name="{name}",state="{state}"'
            lines.append(f"circuit_breaker_state{{{label_str}}} {state_value}")
    if breaker_snapshot["opens"]:
        lines.append(
            "# HELP circuit_breaker_open_total Number of times the circuit breaker transitioned to open"
        )
        lines.append("# TYPE circuit_breaker_open_total counter")
        for name, count in breaker_snapshot["opens"].items():
            label_str = f'name="{name}"'
            lines.append(f"circuit_breaker_open_total{{{label_str}}} {int(count)}")
    return PlainTextResponse("\n".join(lines) + "\n")


def configure_logging() -> None:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        json.dumps(
            {
                "level": "%(levelname)s",
                "time": "%(asctime)s",
                "logger": "%(name)s",
                "message": "%(message)s",
            }
        )
    )
    handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(handler)
