from __future__ import annotations

import logging
from collections import deque
from datetime import timedelta
from typing import Deque

from aiobreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerState

from .config import Settings
from .telemetry import MetricsRecorder

logger = logging.getLogger("company_search_service")


class DependencyBreakerListener(CircuitBreakerListener):
    """Emit logs and metrics whenever the circuit breaker changes state."""

    def __init__(self, breaker_name: str) -> None:
        self._breaker_name = breaker_name

    def state_change(
        self,
        breaker: CircuitBreaker,
        old: CircuitBreakerState,
        new: CircuitBreakerState,
    ) -> None:
        new_state = getattr(new, "state", new)
        old_state = getattr(old, "state", old)
        state_name = new_state.name.lower()
        MetricsRecorder.instance().record_breaker_state(self._breaker_name, state_name)
        if new_state is CircuitBreakerState.OPEN:
            logger.warning(
                "Circuit breaker transitioned to OPEN state",
                extra={
                    "breaker": breaker.name,
                    "previous_state": old_state.name.lower(),
                },
            )
        else:
            logger.info(
                "Circuit breaker state change",
                extra={
                    "breaker": breaker.name,
                    "previous_state": old_state.name.lower(),
                    "state": state_name,
                },
            )


def build_circuit_breaker(settings: Settings, name: str) -> CircuitBreaker:
    breaker = CircuitBreaker(
        fail_max=max(1, settings.breaker_minimum_calls),
        timeout_duration=timedelta(seconds=settings.breaker_wait_duration_seconds),
        name=name,
        listeners=[DependencyBreakerListener(name)],
    )
    # Initialize metrics with the default CLOSED state.
    MetricsRecorder.instance().record_breaker_state(name, "closed")
    return breaker


class FailureRateTracker:
    """Maintain a sliding window of outcomes to decide when to open the breaker."""

    def __init__(
        self,
        breaker: CircuitBreaker,
        settings: Settings,
        window_size: int | None = None,
    ) -> None:
        self._breaker = breaker
        self._settings = settings
        configured_size = window_size or settings.breaker_minimum_calls
        self._window_size = max(1, configured_size)
        self._history: Deque[bool] = deque(maxlen=self._window_size)
        threshold = settings.breaker_failure_rate_threshold
        self._failure_rate_threshold = max(0.0, min(1.0, threshold))
        self._dependency_name = breaker.name or "external"

    def record(self, dependency: str, operation: str, success: bool) -> bool:
        outcome = "success" if success else "failure"
        MetricsRecorder.instance().record_dependency_call(
            dependency, operation, outcome
        )
        self._history.append(success)

        if success or len(self._history) < self._window_size:
            return False

        failure_count = self._history.count(False)
        window = len(self._history)
        failure_rate = failure_count / window
        if failure_rate < self._failure_rate_threshold:
            return False

        if self._breaker.current_state is CircuitBreakerState.CLOSED:
            logger.warning(
                "Failure rate threshold reached, opening circuit breaker",
                extra={
                    "breaker": self._dependency_name,
                    "operation": operation,
                    "window": window,
                    "failures": failure_count,
                    "failure_rate": round(failure_rate, 2),
                    "threshold": self._failure_rate_threshold,
                },
            )
            self._breaker.open()
        return True
