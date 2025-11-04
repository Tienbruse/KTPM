from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from .config import get_settings
from .models import CompanyResult, IndexRequest, Product, SearchMeta, SearchRequest, SearchResponse


class QueryCreator:
    def create_query(self, entities: Dict[str, Any], top_k: int) -> Optional[Dict[str, Any]]:
        bf = entities.get("business_field") or ""
        verbs = ["sản xuất", "kinh doanh", "phân phối", "chế tạo", "buôn bán"]
        bf_lower = bf.lower()
        for verb in verbs:
            if bf_lower.startswith(verb):
                prod_name = bf[len(verb) :].strip()
                if prod_name:
                    entities["product_names"] = prod_name
                    entities["business_field"] = None
                break

        must_query: List[Dict[str, Any]] = []
        should_query: List[Dict[str, Any]] = []
        must_not_query: List[Dict[str, Any]] = []
        filter_query: List[Dict[str, Any]] = []

        if entities.get("product_names"):
            prod_v = entities["product_names"]
            must_query.append(
                {
                    "nested": {
                        "path": "products",
                        "query": {
                            "multi_match": {
                                "query": prod_v,
                                "type": "cross_fields",
                                "fields": [
                                    "products.product_name",
                                    "products.product_name.without_accent_normalized_analyzer",
                                    "products.product_name.with_accent_normalized_analyzer",
                                    "products.product_description",
                                ],
                                "operator": "and",
                                "boost": 1.0,
                            }
                        },
                    }
                }
            )
        elif entities.get("business_field"):
            bf_v = entities["business_field"]
            must_query.append(
                {
                    "bool": {
                        "should": [
                            {"match_phrase_prefix": {"name": {"query": bf_v, "boost": 1.0}}},
                            {"match": {"information": {"query": bf_v, "boost": 1.0}}},
                            {
                                "nested": {
                                    "path": "products",
                                    "query": {
                                        "bool": {
                                            "should": [
                                                {
                                                    "match_phrase_prefix": {
                                                        "products.product_name": {"query": bf_v, "boost": 1.0}
                                                    }
                                                },
                                                {
                                                    "match_phrase_prefix": {
                                                        "products.product_description": {"query": bf_v, "boost": 1.0}
                                                    }
                                                },
                                            ],
                                            "minimum_should_match": 1,
                                        }
                                    },
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )

        if entities.get("company_name"):
            must_query.append(self._create_match_phrase_prefix_query("name", entities["company_name"]))
            should_query.append(
                self._create_fuzzy_query(
                    entity_name="name",
                    value=entities["company_name"],
                    fuzziness="AUTO",
                    weight=0.8,
                )
            )
            should_query.append(
                self._create_match_single_query(
                    entity_name="name.edge_ngram",
                    value=entities["company_name"],
                    weight=0.5,
                )
            )

        if entities.get("address"):
            must_query.append(self._create_accents_query("address", entities["address"]))

        if entities.get("num_employees") and entities.get("num_employees_operator"):
            operator = entities["num_employees_operator"]
            lower = entities["num_employees"] if operator == "gte" else None
            upper = entities["num_employees"] if operator == "lte" else None
            must_query.append(
                self._create_range_query("employees", lower_bound=lower, upper_bound=upper)
            )

        if entities.get("product_names"):
            product_list = [v.strip() for v in entities["product_names"].split(",")]
            nested_filters = [
                self._create_match_phrase_prefix_query("products.product_name", name)
                for name in product_list
                if name
            ]
            if nested_filters:
                filter_query.append(
                    {"nested": {"path": "products", "query": {"bool": {"filter": nested_filters}}}}
                )

        if not (must_query or should_query or filter_query or must_not_query):
            return None

        bool_body = {
            "filter": filter_query,
            "must": must_query,
            "should": should_query,
            "must_not": must_not_query,
        }
        query_body = {"function_score": {"query": {"bool": bool_body}}}
        sort: List[Any] = []
        payload = {
            "query": query_body,
            "size": top_k,
            "sort": sort,
            "_source": True,
        }
        settings = get_settings()
        log_payload = json.dumps(payload, ensure_ascii=False)
        return {"index": settings.elasticsearch_index, **payload, "log_payload": log_payload}

    @staticmethod
    def _create_match_single_query(entity_name: str, value: Any, weight: float = 1.0) -> Dict[str, Any]:
        return {"match": {entity_name: {"query": value, "boost": weight}}}

    @staticmethod
    def _create_match_phrase_prefix_query(entity_name: str, value: Any, weight: float = 1.0) -> Dict[str, Any]:
        return {"match_phrase_prefix": {entity_name: {"query": value, "boost": weight}}}

    @staticmethod
    def _create_range_query(entity_name: str, lower_bound: Optional[Any] = None, upper_bound: Optional[Any] = None) -> Dict[str, Any]:
        condition: Dict[str, Any] = {}
        if lower_bound is not None:
            condition["gte"] = lower_bound
        if upper_bound is not None:
            condition["lte"] = upper_bound
        return {"range": {entity_name: condition}}

    @staticmethod
    def _create_accents_query(entity_name: str, value: Any, weight: float = 1.0) -> Dict[str, Any]:
        return {
            "multi_match": {
                "query": value,
                "fields": [
                    f"{entity_name}.without_accent_normalized_analyzer",
                    f"{entity_name}.with_accent_normalized_analyzer",
                ],
                "type": "phrase_prefix",
                "boost": weight,
            }
        }

    @staticmethod
    def _create_fuzzy_query(
        entity_name: str,
        value: Any,
        fuzziness: str = "AUTO",
        prefix_length: int = 1,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        return {
            "fuzzy": {
                entity_name: {
                    "value": value,
                    "fuzziness": fuzziness,
                    "prefix_length": prefix_length,
                    "max_expansions": 50,
                    "boost": weight,
                }
            }
        }


class ElasticsearchGateway:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncElasticsearch(
            [f"http://{settings.elasticsearch_host}:{settings.elasticsearch_port}"],
            http_auth=(settings.elasticsearch_user, settings.elasticsearch_password),
            http_compress=True,
            verify_certs=False,
            request_timeout=120,
        )

    async def search(self, query: Dict[str, Any]) -> Dict[str, Any]:
        payload = query.copy()
        payload.pop("log_payload", None)
        response = await self._client.search(**payload)
        return response.body

    async def close(self) -> None:
        await self._client.close()

    async def bulk_index(self, documents: List[Dict[str, Any]]) -> None:
        settings = get_settings()
        actions = []
        for document in documents:
            doc_id = document.get("id")
            action = {
                "_index": settings.elasticsearch_index,
                "_source": document,
            }
            if doc_id:
                action["_id"] = doc_id
            actions.append(action)
        if not actions:
            return
        await async_bulk(self._client, actions)


class SearchService:
    def __init__(self) -> None:
        self._query_creator = QueryCreator()
        self._gateway = ElasticsearchGateway()

    async def search(self, request: SearchRequest) -> SearchResponse:
        query_payload = self._query_creator.create_query(
            entities=request.entities.model_dump(exclude_none=True),
            top_k=request.top_k,
        )
        if not query_payload:
            return SearchResponse(results=[], meta=SearchMeta(total=0, took_ms=0.0), raw_hits=[])

        raw_response = await self._gateway.search(query_payload)
        hits = raw_response.get("hits", {}).get("hits", [])
        took_ms = raw_response.get("took", 0)
        results = [self._format_hit(hit, request.entities.product_names) for hit in hits]
        total = raw_response.get("hits", {}).get("total", {}).get("value", len(results))
        meta = SearchMeta(total=total, took_ms=took_ms)
        return SearchResponse(results=results, meta=meta, raw_hits=hits)

    @staticmethod
    def _format_hit(hit: Dict[str, Any], product_names: Optional[str]) -> CompanyResult:
        source = hit.get("_source", {})
        products = source.get("products", [])
        if product_names:
            wanted = product_names.lower()
            products = [
                product
                for product in products
                if wanted in (product.get("product_name") or "").lower()
            ]
        else:
            products = products[:3]

        return CompanyResult(
            id=hit.get("_id", ""),
            company_name=source.get("name"),
            phone=source.get("phone"),
            email=source.get("email"),
            tax_code=source.get("tax_code"),
            address=source.get("address"),
            url=source.get("url"),
            information=source.get("introduction"),
            num_employees=source.get("employees"),
            products=[Product(**product) for product in products],
        )

    async def close(self) -> None:
        await self._gateway.close()

    async def index(self, request: IndexRequest) -> dict[str, Any]:
        await self._gateway.bulk_index(request.documents)
        return {"indexed": len(request.documents)}
