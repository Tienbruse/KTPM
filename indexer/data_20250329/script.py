import asyncio
import json
import math
import warnings
from typing import Any, Dict, List

import pandas as pd
from constants import ACCENT_FIELDS, NESTED_FIELDS, NUM_FIELDS, TEXT_FIELDS
from elasticsearch import AsyncElasticsearch, ElasticsearchWarning
from elasticsearch.helpers import async_bulk
from elasticsearch.helpers import errors as es_errors
from elasticsearch_config import get_properties, get_settings
from logger import logger

es_host = "http://localhost:9200"
es_index = "company-data"
es_username = "admin"
es_password = "admin"

# (Tuỳ chọn) bỏ qua warning về không bật security
warnings.filterwarnings("ignore", category=ElasticsearchWarning)


all_fields = TEXT_FIELDS + ACCENT_FIELDS + NUM_FIELDS + [nf["key"] for nf in NESTED_FIELDS]
logger.info(f"🛠️  Using index name: {es_index}")

def get_data(path: str) -> List[Dict[str, Any]]:
    """Load JSON vào DataFrame rồi build list các action update/upsert."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    df = pd.DataFrame(data)
    actions: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        body = row.to_dict()
        doc: Dict[str, Any] = {}
        info_count = 0

        for f in all_fields:
            val = body.get(f)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                continue
            # Nếu là list/dict, xét có non-empty
            if isinstance(val, (list, dict)) and len(val) == 0:
                continue
            # Nếu chuỗi rỗng
            if isinstance(val, str) and not val.strip():
                continue

            # gán vào doc bình thường...
            doc[f] = val
            info_count += 1
        
        doc["info_count"] = info_count
        

        # Text và accent fields
        for field in TEXT_FIELDS + ACCENT_FIELDS:
            if field in body and not pd.isna(body[field]):
                doc[field] = body[field]

        # Nested fields
        for nf in NESTED_FIELDS:
            key = nf["key"]
            if key in body:
                doc[key] = body[key]

        # Numeric fields
        for field in NUM_FIELDS:
            raw = body.get(field)
            # nếu raw là chuỗi "null" hay "None", xóa luôn
            if isinstance(raw, str) and raw.strip().lower() in ("null", "none", ""):
                raw = None

            # xử lý số và NaN
            if raw is None or (isinstance(raw, float) and math.isnan(raw)):
                value = None
            else:
                try:
                    # ép thành int nếu có thể
                    value = int(raw)
                except (ValueError, TypeError):
                    # ✋ nếu không ép nổi, giữ None
                    value = None

            doc[field] = value

        actions.append({
            "_op_type": "update",
            "_index": es_index,
            "_id": str(idx),
            "doc_as_upsert": True,
            "doc": doc,
        })
    
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    logger.info(f"🔍 Loaded {len(data)} records from {path}")
    df = pd.DataFrame(data)

    return actions


async def sync_es(es: AsyncElasticsearch) -> None:
    """Tạo index nếu chưa có."""
    exists = await es.indices.exists(index=es_index)
    if not exists:
        logger.info(f"Creating index `{es_index}`")
        await es.indices.create(
            index=es_index,
            body={
                "settings": get_settings(),
                "mappings": {"properties": get_properties()}
            }
        )
        logger.info(f"Index `{es_index}` created")
    else:
        logger.info(f"Index `{es_index}` already exists")


async def index_data(es: AsyncElasticsearch, actions: List[Dict[str, Any]]) -> None:
    """Bulk index (update/upsert) và log kết quả."""
    try:
        success, failed = await async_bulk(
            es, actions, stats_only=True
        )
        logger.info(f"Bulk finished: {success} succeeded, {failed} failed.")
    except es_errors.BulkIndexError as e:
        logger.error(f"BulkIndexError – total errors: {len(e.errors)}")
        # err0 = e.errors[0].get("index", {}).get("error", {})
        # logger.error(f"First error reason: {err0.get('reason')!r}")
        first = e.errors[0]
        logger.error("First bulk error detail:\n" + json.dumps(first, indent=2, ensure_ascii=False))
    except Exception as e:
        logger.error(f"Unexpected error during bulk: {e}")


async def main():
    # Khởi tạo client trong context để tự đóng session
    async with AsyncElasticsearch(
        [es_host],
        basic_auth=(es_username, es_password),
        http_compress=True,
        verify_certs=False,
        request_timeout=120,
    ) as es:
        await sync_es(es)
        actions = get_data("/Users/Tienbruse/tmdt/Backend/company-llm/data/data_20250329_clean.json")
        await index_data(es, actions)


if __name__ == "__main__":
    asyncio.run(main())
