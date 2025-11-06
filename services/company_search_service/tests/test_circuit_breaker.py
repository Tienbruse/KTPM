from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from aiobreaker import CircuitBreakerError

from company_search_service.config import Settings
from company_search_service.search import ElasticsearchGateway
from company_search_service.telemetry import MetricsRecorder


@dataclass
class FakeResponse:
    body: dict


class AlwaysFailClient:
    """Client stub that raises the provided exception on every call."""

    def __init__(self, exc: Exception) -> None:
        self._exc = exc
        self.calls = 0

    async def search(self, **_: dict) -> FakeResponse:
        self.calls += 1
        raise self._exc


class ScriptedClient:
    """Client stub that replays a sequence of outcomes for successive calls."""

    def __init__(self, outcomes: list[Exception | dict]) -> None:
        self._outcomes = outcomes

    async def search(self, **_: dict) -> FakeResponse:
        if not self._outcomes:
            return FakeResponse({"hits": {"hits": []}, "took": 0})
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


class CircuitBreakerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        MetricsRecorder.reset()

    async def test_breaker_opens_after_failure_threshold(self) -> None:
        settings = Settings(
            breaker_failure_rate_threshold=0.5,
            breaker_minimum_calls=4,
            breaker_wait_duration_seconds=1,
            breaker_timeout_seconds=0.05,
            breaker_retry_attempts=2,
            breaker_retry_backoff_ms=0,
            breaker_retry_backoff_multiplier=1,
        )
        gateway = ElasticsearchGateway(
            client=AlwaysFailClient(RuntimeError("boom")), settings=settings
        )

        with self.assertRaises(RuntimeError):
            await gateway.search({"index": "company-data"})

        with self.assertRaises(CircuitBreakerError):
            await gateway.search({"index": "company-data"})

        breaker_snapshot = MetricsRecorder.instance().breaker_snapshot()
        self.assertEqual(breaker_snapshot["states"].get("elasticsearch"), "open")

    async def test_breaker_recovers_after_wait_duration(self) -> None:
        settings = Settings(
            breaker_failure_rate_threshold=0.5,
            breaker_minimum_calls=2,
            breaker_wait_duration_seconds=0.1,
            breaker_timeout_seconds=0.05,
            breaker_retry_attempts=0,
            breaker_retry_backoff_ms=0,
            breaker_retry_backoff_multiplier=1,
        )
        outcomes: list[Exception | dict] = [
            RuntimeError("temporary failure"),
            RuntimeError("temporary failure"),
            {"hits": {"hits": []}, "took": 1},
        ]
        gateway = ElasticsearchGateway(
            client=ScriptedClient(outcomes), settings=settings
        )

        with self.assertRaises(RuntimeError):
            await gateway.search({"index": "company-data"})

        with self.assertRaises(CircuitBreakerError):
            await gateway.search({"index": "company-data"})

        await asyncio.sleep(0.2)

        result = await gateway.search({"index": "company-data"})
        self.assertEqual(result["hits"]["hits"], [])

        breaker_snapshot = MetricsRecorder.instance().breaker_snapshot()
        self.assertEqual(breaker_snapshot["states"].get("elasticsearch"), "closed")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
