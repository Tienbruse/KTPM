from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from aiohttp import ClientSession, ClientTimeout

from src.settings import SETTINGS
from src.utils.logger import logger


class SearchServiceClient:
    def __init__(self, base_url: Optional[str] = None) -> None:
        self._base_url = base_url or SETTINGS.SEARCH_SERVICE_URL
        self._session: Optional[ClientSession] = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> ClientSession:
        async with self._lock:
            if self._session is None or self._session.closed:
                self._session = ClientSession()
            return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def search(self, *, entities: Dict[str, Any], top_k: int, request_id: Optional[str] = None) -> Dict[str, Any]:
        session = await self._get_session()
        payload = {"entities": entities, "top_k": top_k}
        headers = {"Content-Type": "application/json"}
        if request_id:
            headers["X-Request-ID"] = request_id
        url = f"{self._base_url}/v1/search/companies"
        logger.info("Calling search service", extra={"url": url, "payload": payload})
        timeout = ClientTimeout(total=SETTINGS.SEARCH_SERVICE_TIMEOUT)
        async with session.post(url, data=json.dumps(payload), headers=headers, timeout=timeout) as response:
            if response.status >= 400:
                text = await response.text()
                logger.error(
                    "Search service error",
                    extra={"status": response.status, "body": text},
                )
                response.raise_for_status()
            return await response.json()
