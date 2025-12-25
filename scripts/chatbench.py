"""
Simple load test for the chatbot endpoint.

Usage:
    BENCH_TOTAL=50 BENCH_CONCURRENCY=10 BENCH_ENDPOINT=http://localhost:8910/michelin-recommendation/api/v1/retrieve/ \
        python scripts/chatbench.py

Env vars:
  - BENCH_TOTAL: number of requests to send (default 50)
  - BENCH_CONCURRENCY: parallel requests (default 10)
  - BENCH_ENDPOINT: chatbot endpoint URL (default http://localhost:8910/michelin-recommendation/api/v1/retrieve/)
  - BENCH_QUERY: user_input content (default "tìm công ty điện lực ở hà tĩnh")
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import List

from aiohttp import ClientSession


async def run_benchmark() -> None:
    endpoint = os.getenv(
        "BENCH_ENDPOINT",
        "http://localhost:8910/michelin-recommendation/api/v1/retrieve/",
    )
    payload = {"user_input": os.getenv("BENCH_QUERY", "tìm công ty điện lực ở hà tĩnh")}
    total = int(os.getenv("BENCH_TOTAL", "50"))
    concurrency = int(os.getenv("BENCH_CONCURRENCY", "10"))

    latencies: List[float] = []
    errors: List[str] = []
    counter = 0
    lock = asyncio.Lock()

    async def worker(session: ClientSession, sem: asyncio.Semaphore) -> None:
        nonlocal counter
        while True:
            async with sem:
                async with lock:
                    if counter >= total:
                        return
                    counter += 1
            start = time.perf_counter()
            try:
                async with session.post(endpoint, json=payload) as resp:
                    await resp.text()
                    if resp.status != 200:
                        errors.append(f"HTTP {resp.status}")
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(str(exc))
            finally:
                latencies.append((time.perf_counter() - start) * 1000)

    sem = asyncio.Semaphore(concurrency)
    async with ClientSession() as session:
        await asyncio.gather(
            *[asyncio.create_task(worker(session, sem)) for _ in range(concurrency)]
        )

    latencies.sort()

    def pct(p: float) -> float | None:
        if not latencies:
            return None
        idx = int((p / 100.0) * (len(latencies) - 1))
        return round(latencies[idx], 2)

    summary = {
        "requests": len(latencies),
        "errors": len(errors),
        "p50_ms": pct(50),
        "p90_ms": pct(90),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "min_ms": round(latencies[0], 2) if latencies else None,
        "max_ms": round(latencies[-1], 2) if latencies else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        print("Errors sample:", errors[:5])


if __name__ == "__main__":
    asyncio.run(run_benchmark())
