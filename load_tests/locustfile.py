"""
Locust load test for chatbot + company search service.

Usage:
    uv tool install locust  # or pip install locust
    locust -f load_tests/locustfile.py --host=https://chat.example.com

Environment variables:
    CHATBOT_BASE_URL   Base URL (defaults to https://chat.example.com)
    SEARCH_ENDPOINT    Relative path for chatbot queries (/api/chatbot/query)
    FAULT_ENDPOINT     Optional path that triggers an Elasticsearch failure simulation.
"""

from __future__ import annotations

import os
import random
from typing import Any, Dict

from locust import HttpUser, between, events, task

DEFAULT_BASE = "https://chat.example.com"
DEFAULT_ENDPOINT = "/api/chatbot/query"

API_BASE = os.getenv("CHATBOT_BASE_URL", DEFAULT_BASE)
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT", DEFAULT_ENDPOINT)
FAULT_ENDPOINT = os.getenv("FAULT_ENDPOINT", "")

PAYLOADS: list[Dict[str, Any]] = [
    {"question": "Cho tôi biết thông tin công ty FPT?"},
    {"question": "Tìm doanh nghiệp chế biến thủy sản tại Hà Nội"},
    {"question": "Công ty TNHH ABC có sản phẩm gì nổi bật?"},
    {"question": "Danh sách doanh nghiệp trồng cà phê ở Tây Nguyên"},
]


class ChatbotUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(9)
    def ask_question(self) -> None:
        payload = random.choice(PAYLOADS)
        headers = {"Content-Type": "application/json"}
        with self.client.post(
            SEARCH_ENDPOINT,
            json=payload,
            headers=headers,
            name="chatbot-query",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 503:
                resp.failure("Circuit breaker open / backend unavailable")
            else:
                resp.failure(f"{resp.status_code}: {resp.text[:120]}")

    @task(1)
    def induce_failure(self) -> None:
        """Optional helper to trigger a backend fault (no-op if FAULT_ENDPOINT unset)."""
        if FAULT_ENDPOINT:
            self.client.post(
                FAULT_ENDPOINT,
                name="simulate-fault",
                timeout=5,
            )


@events.test_start.add_listener
def on_test_start(environment, **kwargs):  # type: ignore[no-untyped-def]
    environment.runner.environment.logger.info(
        "Load test targeting %s%s (fault endpoint: %s)",
        API_BASE,
        SEARCH_ENDPOINT,
        FAULT_ENDPOINT or "disabled",
    )
