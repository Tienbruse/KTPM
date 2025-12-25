from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from src.settings import SETTINGS
from src.utils.logger import logger


class SearchServiceClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        max_retries: int = 2,
        backoff_seconds: float = 0.2,
    ) -> None:
        self._base_url = base_url or SETTINGS.SEARCH_SERVICE_URL
        self._session: Optional[ClientSession] = None
        self._lock = asyncio.Lock()
        self._max_retries = max(0, max_retries)
        self._backoff_seconds = max(0.0, backoff_seconds)

    async def _get_session(self) -> ClientSession:
        async with self._lock:
            if self._session is None or self._session.closed:
                self._session = ClientSession()
            return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def search(
        self, *, entities: Dict[str, Any], top_k: int, request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        session = await self._get_session()
        payload = {"entities": entities, "top_k": top_k}
        headers = {"Content-Type": "application/json"}
        if request_id:
            headers["X-Request-ID"] = request_id
        url = f"{self._base_url}/v1/search/companies"
        timeout = ClientTimeout(total=SETTINGS.SEARCH_SERVICE_TIMEOUT)
        for attempt in range(self._max_retries + 1):
            try:
                logger.info(
                    "Calling search service",
                    extra={
                        "url": url,
                        "payload": payload,
                        "attempt": attempt,
                    },
                )
                async with session.post(
                    url, data=json.dumps(payload), headers=headers, timeout=timeout
                ) as response:
                    if response.status >= 500:
                        text = await response.text()
                        raise RuntimeError(f"Search service {response.status}: {text}")
                    if response.status >= 400:
                        text = await response.text()
                        logger.error(
                            "Search service error",
                            extra={"status": response.status, "body": text},
                        )
                        response.raise_for_status()
                    return await response.json()
            except ClientResponseError as exc:
                # Do not retry client errors
                logger.error(
                    "Search service returned client error",
                    extra={
                        "url": url,
                        "status": exc.status,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                raise
            except (asyncio.TimeoutError, ClientError, RuntimeError) as exc:
                if attempt >= self._max_retries:
                    logger.error(
                        "Search service call failed after retries",
                        extra={"url": url, "attempts": attempt, "error": str(exc)},
                    )
                    raise
                sleep_for = self._backoff_seconds * (2**attempt)
                logger.warning(
                    "Retrying search service call",
                    extra={
                        "url": url,
                        "attempt": attempt,
                        "next_backoff_s": round(sleep_for, 2),
                        "error": str(exc),
                    },
                )
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
