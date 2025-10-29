import asyncio
import math
from typing import Any, Dict, List

import pandas as pd
from constants import ACCENT_FIELDS, NUM_FIELDS, TEXT_FIELDS
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from elasticsearch.helpers import errors as es_errors
from elasticsearch_config import get_properties, get_settings
from logger import logger

es_host = "http://localhost:9200"
es_index = "company-thongtindoanhnghiep"
es_username = "admin"
es_password = "admin"
es_client = AsyncElasticsearch(
    [es_host],
    http_auth=(es_username, es_password),
    http_compress=True,
    verify_certs=False,
    request_timeout=120,
)


async def sync_es():
    has_existing = await es_client.indices.exists(index=es_index)
    if not has_existing:
        logger.info(f"Creating index {es_index}")
        await es_client.indices.create(
            index=es_index,
            mappings={"properties": get_properties()},
            settings={"index": get_settings()},
        )
        logger.info(f"Index {es_index} created")
    else:
        logger.info(f"Index {es_index} already exists")
    return has_existing


def get_data(path: str) -> List[Dict[str, Any]]:
    df = pd.read_excel(path)
    actions = []

    for id, row in df.iterrows():
        body = row.to_dict()

        doc = {}
        for field in TEXT_FIELDS + ACCENT_FIELDS:
            if field in body and not pd.isna(body[field]):
                doc[field] = body[field]

        # Numeric fields
        for field in NUM_FIELDS:
            value = body.get(field)
            doc[field] = (
                None
                if pd.isna(value) or (isinstance(value, float) and math.isnan(value))
                else value
            )

        action = {
            "_op_type": "update",
            "_index": es_index,
            "doc_as_upsert": True,
            "_id": id,
            "doc": doc,
        }
        actions.append(action)
    return actions


async def index_data(actions: List[Dict[str, Any]]):
    total_success = 0
    total_failed = 0

    try:
        success, failed = await async_bulk(
            es_client,
            actions,
            stats_only=True,
        )
        total_success += success
        total_failed += failed if isinstance(failed, int) else len(failed)
    except es_errors.BulkIndexError as e:
        total_failed += len(e.errors)
        logger.error(f"Failed to index data: {e}")
        firstError = e.errors[0].get("index", {}).get("error", {})
        logger.error(
            f"First error reason in index `{es_index}`: {firstError.get('reason')}"
        )
    except Exception as e:
        logger.error(f"Failed to index data: {e}")


async def main():
    await sync_es()
    data = get_data("data/thongtindoanhnghiep.xlsx")
    await index_data(data)


if __name__ == "__main__":
    asyncio.run(main())
