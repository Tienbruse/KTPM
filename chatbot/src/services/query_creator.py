import re
import json
from typing import Any, Dict, List, Optional

from src.utils.logger import logger


class QueryCreator:
    def create_query(
        self,
        entities: Dict[str, Any],
        index_name: str,
        top_k: int,
    ) -> Optional[Dict[str, Any]]:
        """Create query in Elasticsearch based on extracted entities"""
        # General preprocessing: if business_field starts with a known verb, extract product name
        bf = entities.get("business_field", "") or ""
        verbs = ["sản xuất", "kinh doanh", "phân phối", "chế tạo", "buôn bán"]
        bf_lower = bf.lower()
        for verb in verbs:
            if bf_lower.startswith(verb):
                prod_name = bf[len(verb):].strip()
                if prod_name:
                    entities["product_names"] = prod_name
                    entities["business_field"] = None
                break

        must_query: List[Dict[str, Any]] = []
        should_query: List[Dict[str, Any]] = []
        must_not_query: List[Dict[str, Any]] = []
        filter_query: List[Dict[str, Any]] = []

        # Prioritize product_names search
        if entities.get("product_names"):
            prod_v = entities["product_names"]
            must_query.append({
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
                                "products.product_description"
                            ],
                            "operator": "and",
                            "boost": 1.0
                        }
                    }
                }
            })
        # Otherwise, match business_field across company fields and product descriptions
        elif entities.get("business_field"):
            bf_v = entities["business_field"]
            must_query.append({
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
                                            {"match_phrase_prefix": {"products.product_name": {"query": bf_v, "boost": 1.0}}},
                                            {"match_phrase_prefix": {"products.product_description": {"query": bf_v, "boost": 1.0}}}
                                        ],
                                        "minimum_should_match": 1
                                    }
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            })

        # Company name exact + fuzzy + edge_ngram
        if entities.get("company_name"):
            must_query.append(
                self._create_match_pharse_prefix_query(
                    entity_name="name",
                    value=entities["company_name"],
                )
            )
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

        # Address search
        if entities.get("address"):
            must_query.append(
                self._create_accents_query(
                    entity_name="address",
                    value=entities["address"],
                )
            )

        # Number of employees range
        if entities.get("num_employees") and entities.get("num_employees_operator"):
            operator = entities["num_employees_operator"]
            lower = entities["num_employees"] if operator == "gte" else None
            upper = entities["num_employees"] if operator == "lte" else None
            must_query.append(
                self._create_range_query(
                    entity_name="employees",
                    lower_bound=lower,
                    upper_bound=upper,
                )
            )

        # Additional filter: exact product name matches
        if entities.get("product_names"):
            product_list = [v.strip() for v in entities["product_names"].split(",")]
            nested_filters = [
                self._create_match_pharse_prefix_query(
                    entity_name="products.product_name",
                    value=name,
                ) for name in product_list
            ]
            if nested_filters:
                filter_query.append(
                    {"nested": {"path": "products", "query": {"bool": {"filter": nested_filters}}}}
                )

        # If no clauses, return None
        if not (must_query or should_query or filter_query or must_not_query):
            return None

        bool_body = {"filter": filter_query, "must": must_query, "should": should_query, "must_not": must_not_query}
        query_body = {"function_score": {"query": {"bool": bool_body}}}
        sort: List[Any] = []

        # Log
        log_payload = {"query": query_body, "size": top_k, "sort": sort, "_source": True}
        logger.info(
            "Retrieve_documents full query with index %s:\n%s",
            index_name,
            json.dumps(log_payload, ensure_ascii=False, indent=2),
        )

        return {"index": index_name, "query": query_body, "size": top_k, "sort": sort, "_source": True}


    def _create_match_single_query(
        self,
        entity_name: str,
        value: Any,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        return {
            "match": {
                entity_name: {
                    "query": value,
                    "boost": weight,
                }
            }
        }

    def _create_match_pharse_prefix_query(
        self,
        entity_name: str,
        value: Any,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        return {
            "match_phrase_prefix": {
                entity_name: {
                    "query": value,
                    "boost": weight,
                },
            }
        }

    def _create_range_query(
        self,
        entity_name: str,
        lower_bound: Optional[Any] = None,
        upper_bound: Optional[Any] = None,
    ) -> Dict[str, Any]:
        condition = {}
        if lower_bound is not None:
            condition["gte"] = lower_bound
        if upper_bound is not None:
            condition["lte"] = upper_bound
        return {"range": {entity_name: condition}}

    def _create_accents_query(
        self,
        entity_name: str,
        value: Any,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
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

    def _create_multi_match_query(
        self, entity_name: List[str], entity_weight: List[str], value: Any
    ) -> Dict[str, Any]:
        return {
            "multi_match": {
                "query": value,
                "fields": [
                    f"{name}^{weight}"
                    for name, weight in zip(entity_name, entity_weight)
                ],
            }
        }

    def replace_strings(self, response: str) -> str:
        response = re.sub(
            r"[Tt][hH][oOôÔơƠỏỎổỔởỞ][ ][DdĐđ][iIíìỊị][aA][ ][Mm][oO][mM][oO]",
            "Thổ Địa Momo",
            response,
        )  # noqa: E501
        return response
    
    def _create_fuzzy_query(
        self,
        entity_name: str,
        value: Any,
        fuzziness: str = "AUTO", # AUTO: 0 lỗi cho từ 1-2 ký tự, 1 lỗi cho 3-5 ký tự, 2 lỗi cho >5 ký tự
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
