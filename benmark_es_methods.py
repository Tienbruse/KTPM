"""
Benchmark Elasticsearch get/search vs mget/msearch and tune refresh/flush settings.

Usage:
  ES_HOST=http://localhost:9200 ES_INDEX=company-data python benmark_es_methods.py

Env vars:
  - ES_HOST, ES_USER, ES_PASS, ES_INDEX
  - BENCH_SEED: seed synthetic docs (default false)
  - BENCH_DOCS: number of docs to seed (default 1000)
  - BENCH_BULK_CHUNK: bulk chunk size (default 500)
  - BENCH_ID_COUNT: number of ids for get/mget (default 200)
  - BENCH_MGET_BATCH: ids per mget request (default 50)
  - BENCH_SEARCHES_PER_ITER: searches per iteration (default 50)
  - BENCH_MSEARCH_BATCH: searches per msearch request (default 10)
  - BENCH_ITERATIONS: iterations per benchmark (default 3)
  - BENCH_REFRESH_INTERVAL_BULK: refresh interval during seed (default -1)
  - BENCH_REFRESH_INTERVAL: refresh interval during benchmark (default 1s)
  - BENCH_FLUSH_THRESHOLD: translog flush threshold size (e.g. 512mb)
  - BENCH_FORCE_FLUSH: force flush before benchmark (default false)
  - BENCH_RESTORE_SETTINGS: restore original settings after benchmark (default true)
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk


@dataclass(frozen=True)
class BenchConfig:
    host: str
    user: str
    password: str
    index: str
    seed: bool
    doc_count: int
    bulk_chunk: int
    id_count: int
    mget_batch: int
    searches_per_iter: int
    msearch_batch: int
    iterations: int
    refresh_interval_bulk: str
    refresh_interval: str
    flush_threshold: str | None
    force_flush: bool
    restore_settings: bool


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def chunked(items: Sequence[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(items), size):
        yield list(items[i : i + size])


def build_summary(
    latencies_ms: List[float], requests: int, docs: int, total_time_s: float
) -> Dict[str, Any]:
    latencies_ms.sort()

    def pct(p: float) -> float | None:
        if not latencies_ms:
            return None
        idx = int((p / 100.0) * (len(latencies_ms) - 1))
        return round(latencies_ms[idx], 2)

    total_ms = round(total_time_s * 1000, 2)
    rps = round(requests / total_time_s, 2) if total_time_s > 0 else None
    dps = round(docs / total_time_s, 2) if total_time_s > 0 else None

    return {
        "requests": requests,
        "docs": docs,
        "total_ms": total_ms,
        "rps": rps,
        "docs_per_sec": dps,
        "p50_ms": pct(50),
        "p90_ms": pct(90),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "min_ms": round(latencies_ms[0], 2) if latencies_ms else None,
        "max_ms": round(latencies_ms[-1], 2) if latencies_ms else None,
    }


def build_seed_docs(count: int) -> Iterable[Dict[str, Any]]:
    for i in range(count):
        category = f"cat-{i % 10}"
        doc = {
            "name": f"Company {i}",
            "category": category,
            "content": f"Sample content for company {i} in {category}.",
            "value": i,
        }
        yield {"_id": f"bench-{i}", "_source": doc}


def build_queries(count: int) -> List[Dict[str, Any]]:
    queries = []
    for i in range(count):
        category = f"cat-{i % 10}"
        queries.append(
            {
                "query": {"term": {"category": category}},
                "size": 10,
                "track_total_hits": False,
            }
        )
    return queries


async def safe_put_settings(
    es: AsyncElasticsearch, index: str, settings: Dict[str, Any]
) -> None:
    if not settings:
        return
    try:
        await es.indices.put_settings(index=index, settings=settings)
    except TypeError:
        await es.indices.put_settings(index=index, body=settings)


async def safe_mget(
    es: AsyncElasticsearch, index: str, ids: Sequence[str]
) -> Dict[str, Any]:
    try:
        return await es.mget(index=index, ids=list(ids))
    except TypeError:
        return await es.mget(index=index, body={"ids": list(ids)})


async def safe_msearch(
    es: AsyncElasticsearch, index: str, searches: List[Dict[str, Any]]
) -> Dict[str, Any]:
    try:
        return await es.msearch(index=index, searches=searches)
    except TypeError:
        return await es.msearch(index=index, body=searches)


async def create_index_if_missing(
    es: AsyncElasticsearch, index: str, refresh_interval: str
) -> None:
    exists = await es.indices.exists(index=index)
    if exists:
        return
    settings = {"index": {"number_of_shards": 1, "refresh_interval": refresh_interval}}
    mappings = {
        "properties": {
            "name": {"type": "text"},
            "category": {"type": "keyword"},
            "content": {"type": "text"},
            "value": {"type": "integer"},
        }
    }
    try:
        await es.indices.create(index=index, settings=settings, mappings=mappings)
    except TypeError:
        await es.indices.create(
            index=index, body={"settings": settings, "mappings": mappings}
        )


async def get_current_settings(
    es: AsyncElasticsearch, index: str
) -> Tuple[str | None, str | None]:
    resp = await es.indices.get_settings(index=index)
    settings = resp.get(index, {}).get("settings", {}).get("index", {})
    refresh_interval = settings.get("refresh_interval")
    flush_threshold = settings.get("translog", {}).get("flush_threshold_size")
    return refresh_interval, flush_threshold


async def seed_index(
    es: AsyncElasticsearch, index: str, config: BenchConfig
) -> List[str]:
    actions = (
        {"_index": index, "_id": doc["_id"], "_source": doc["_source"]}
        for doc in build_seed_docs(config.doc_count)
    )
    await async_bulk(
        es,
        actions,
        chunk_size=config.bulk_chunk,
        refresh=False,
        stats_only=True,
    )
    await es.indices.refresh(index=index)
    ids = [f"bench-{i}" for i in range(config.doc_count)]
    return ids[: config.id_count]


async def pick_ids(es: AsyncElasticsearch, index: str, count: int) -> List[str]:
    resp = await es.search(
        index=index,
        body={
            "query": {"match_all": {}},
            "size": count,
            "sort": ["_doc"],
            "track_total_hits": False,
            "_source": False,
        },
    )
    return [hit["_id"] for hit in resp.get("hits", {}).get("hits", [])]


async def bench_get(
    es: AsyncElasticsearch, index: str, ids: Sequence[str], iterations: int
) -> Dict[str, Any]:
    latencies: List[float] = []
    requests = 0
    docs = 0
    start_total = time.perf_counter()
    for _ in range(iterations):
        for doc_id in ids:
            start = time.perf_counter()
            await es.get(index=index, id=doc_id)
            latencies.append((time.perf_counter() - start) * 1000)
            requests += 1
            docs += 1
    total_time = time.perf_counter() - start_total
    return build_summary(latencies, requests, docs, total_time)


async def bench_mget(
    es: AsyncElasticsearch,
    index: str,
    ids: Sequence[str],
    batch_size: int,
    iterations: int,
) -> Dict[str, Any]:
    latencies: List[float] = []
    requests = 0
    docs = 0
    start_total = time.perf_counter()
    for _ in range(iterations):
        for batch in chunked(list(ids), batch_size):
            start = time.perf_counter()
            await safe_mget(es, index, batch)
            latencies.append((time.perf_counter() - start) * 1000)
            requests += 1
            docs += len(batch)
    total_time = time.perf_counter() - start_total
    return build_summary(latencies, requests, docs, total_time)


async def bench_search(
    es: AsyncElasticsearch,
    index: str,
    queries: Sequence[Dict[str, Any]],
    iterations: int,
) -> Dict[str, Any]:
    latencies: List[float] = []
    requests = 0
    docs = 0
    start_total = time.perf_counter()
    for _ in range(iterations):
        for query in queries:
            start = time.perf_counter()
            await es.search(index=index, body=query)
            latencies.append((time.perf_counter() - start) * 1000)
            requests += 1
            docs += 1
    total_time = time.perf_counter() - start_total
    return build_summary(latencies, requests, docs, total_time)


async def bench_msearch(
    es: AsyncElasticsearch,
    index: str,
    queries: Sequence[Dict[str, Any]],
    batch_size: int,
    iterations: int,
) -> Dict[str, Any]:
    latencies: List[float] = []
    requests = 0
    docs = 0
    start_total = time.perf_counter()
    for _ in range(iterations):
        for batch in chunked(list(queries), batch_size):
            searches: List[Dict[str, Any]] = []
            for query in batch:
                searches.append({"index": index})
                searches.append(query)
            start = time.perf_counter()
            await safe_msearch(es, index, searches)
            latencies.append((time.perf_counter() - start) * 1000)
            requests += 1
            docs += len(batch)
    total_time = time.perf_counter() - start_total
    return build_summary(latencies, requests, docs, total_time)


def load_config() -> BenchConfig:
    return BenchConfig(
        host=os.getenv("ES_HOST", "http://localhost:9200"),
        user=os.getenv("ES_USER", "admin"),
        password=os.getenv("ES_PASS", "admin"),
        index=os.getenv("ES_INDEX", "company-data"),
        seed=parse_bool(os.getenv("BENCH_SEED"), default=False),
        doc_count=parse_int(os.getenv("BENCH_DOCS"), 1000),
        bulk_chunk=parse_int(os.getenv("BENCH_BULK_CHUNK"), 500),
        id_count=parse_int(os.getenv("BENCH_ID_COUNT"), 200),
        mget_batch=parse_int(os.getenv("BENCH_MGET_BATCH"), 50),
        searches_per_iter=parse_int(os.getenv("BENCH_SEARCHES_PER_ITER"), 50),
        msearch_batch=parse_int(os.getenv("BENCH_MSEARCH_BATCH"), 10),
        iterations=parse_int(os.getenv("BENCH_ITERATIONS"), 3),
        refresh_interval_bulk=os.getenv("BENCH_REFRESH_INTERVAL_BULK", "-1"),
        refresh_interval=os.getenv("BENCH_REFRESH_INTERVAL", "1s"),
        flush_threshold=os.getenv("BENCH_FLUSH_THRESHOLD"),
        force_flush=parse_bool(os.getenv("BENCH_FORCE_FLUSH"), default=False),
        restore_settings=parse_bool(os.getenv("BENCH_RESTORE_SETTINGS"), default=True),
    )


async def main() -> None:
    config = load_config()
    async with AsyncElasticsearch(
        [config.host],
        basic_auth=(config.user, config.password),
        http_compress=True,
        verify_certs=False,
        request_timeout=60,
    ) as es:
        await create_index_if_missing(es, config.index, config.refresh_interval)

        original_refresh, original_flush = await get_current_settings(es, config.index)
        applied_settings = False
        try:
            if config.seed:
                await safe_put_settings(
                    es,
                    config.index,
                    {"index": {"refresh_interval": config.refresh_interval_bulk}},
                )
                applied_settings = True

            if config.flush_threshold:
                await safe_put_settings(
                    es,
                    config.index,
                    {
                        "index": {
                            "translog": {"flush_threshold_size": config.flush_threshold}
                        }
                    },
                )
                applied_settings = True

            if config.seed:
                ids = await seed_index(es, config.index, config)
                await safe_put_settings(
                    es,
                    config.index,
                    {"index": {"refresh_interval": config.refresh_interval}},
                )
                applied_settings = True
            else:
                ids = await pick_ids(es, config.index, config.id_count)

            if config.force_flush:
                await es.indices.flush(index=config.index, wait_if_ongoing=True)

            if not ids:
                print(
                    json.dumps(
                        {
                            "error": "no documents found for benchmark",
                            "hint": "set BENCH_SEED=true to seed synthetic data",
                        },
                        indent=2,
                    )
                )
                return

            queries = build_queries(config.searches_per_iter)
            results = {
                "get": await bench_get(es, config.index, ids, config.iterations),
                "mget": await bench_mget(
                    es, config.index, ids, config.mget_batch, config.iterations
                ),
                "search": await bench_search(
                    es, config.index, queries, config.iterations
                ),
                "msearch": await bench_msearch(
                    es, config.index, queries, config.msearch_batch, config.iterations
                ),
            }

            output = {
                "index": config.index,
                "doc_ids": len(ids),
                "iterations": config.iterations,
                "refresh_interval_bulk": config.refresh_interval_bulk
                if config.seed
                else None,
                "refresh_interval": config.refresh_interval,
                "flush_threshold": config.flush_threshold,
                "force_flush": config.force_flush,
                "benchmarks": results,
            }
            print(json.dumps(output, indent=2))
        finally:
            if config.restore_settings and applied_settings:
                restore: Dict[str, Any] = {"index": {}}
                if original_refresh is not None:
                    restore["index"]["refresh_interval"] = original_refresh
                if original_flush is not None:
                    restore["index"]["translog"] = {
                        "flush_threshold_size": original_flush
                    }
                if restore["index"]:
                    await safe_put_settings(es, config.index, restore)


if __name__ == "__main__":
    asyncio.run(main())
