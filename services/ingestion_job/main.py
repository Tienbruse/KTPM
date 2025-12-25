"""CLI skeleton for the ingestion microservice."""

import argparse
import asyncio
import csv
import logging
from pathlib import Path
from typing import Any, Dict, Iterable

import aiohttp

logger = logging.getLogger("ingestion_job")
logging.basicConfig(level=logging.INFO)


async def publish_batch(
    session: aiohttp.ClientSession, payload: list[Dict[str, Any]], endpoint: str
) -> None:
    async with session.post(endpoint, json={"documents": payload}) as response:
        if response.status >= 400:
            text = await response.text()
            raise RuntimeError(f"Failed to publish batch: {response.status} {text}")
        logger.info("Published batch", extra={"size": len(payload)})


def load_csv(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


async def main(file_path: str, endpoint: str) -> None:
    documents = list(load_csv(Path(file_path)))
    async with aiohttp.ClientSession() as session:
        batch_size = 50
        for index in range(0, len(documents), batch_size):
            batch = documents[index : index + batch_size]
            await publish_batch(session, batch, endpoint)
    logger.info("Ingestion completed", extra={"count": len(documents)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion microservice skeleton")
    parser.add_argument("--file", required=True, help="Path to CSV file")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:9010/v1/search/companies/index",
        help="Indexing endpoint exposed by company-search-service",
    )
    args = parser.parse_args()
    asyncio.run(main(args.file, args.endpoint))
