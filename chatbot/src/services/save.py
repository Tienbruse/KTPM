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
        """Create query in Elasticsearch

        Args:
            entities (Dict[str, Any]): Entities from user's message
            index_name (str): Elasticsearch index name
            top_k (int): Number of results to return

        Returns:
            Optional[Dict[str, Any]]: Elasticsearch query body or None
        """
        must_query: List[Dict[str, Any]] = []
        should_query: List[Dict[str, Any]] = []
        must_not_query: List[Dict[str, Any]] = []
        filter_query: List[Dict[str, Any]] = []

        # 1. Company name exact + fuzzy + edge_ngram
        if entities.get("company_name"):
            # Exact phrase prefix match on name
            must_query.append(
                self._create_match_pharse_prefix_query(
                    entity_name="name",
                    value=entities["company_name"],
                )
            )
            # Fuzzy match on name
            should_query.append(
                self._create_fuzzy_query(
                    entity_name="name",
                    value=entities["company_name"],
                    fuzziness="AUTO",
                    weight=0.8,
                )
            )
            # Edge-ngram match on name
            should_query.append(
                self._create_match_single_query(
                    entity_name="name.edge_ngram",
                    value=entities["company_name"],
                    weight=0.5,
                )
            )

        # 2. Business field filter: only return docs with keyword in name/information or product fields
        if entities.get("business_field"):
            v = entities["business_field"]
            # Build clauses to check for the keyword in four places
            specialty_clauses = [
                # a) name
                {"match_phrase_prefix": {"name": {"query": v, "boost": 1.0}}},
                # b) information (company intro)
                {"match": {"information": {"query": v, "boost": 1.0}}},
                # c) products.product_name
                {"nested": {
                    "path": "products",
                    "query": {"bool": {
                        "filter": [{"match_phrase_prefix": {"products.product_name": {"query": v, "boost": 1.0}}}]
                    }}
                }},
                # d) products.product_description
                {"nested": {
                    "path": "products",
                    "query": {"bool": {
                        "filter": [{"match_phrase_prefix": {"products.product_description": {"query": v, "boost": 1.0}}}]
                    }}
                }}
            ]
            # Add to filter: require at least one clause
            filter_query.append({
                "bool": {"should": specialty_clauses, "minimum_should_match": 1}
            })

        # 3. Address search with accent-insensitive analyzer
        if entities.get("address"):
            filter_query.append(
                self._create_accents_query(
                    entity_name="address",
                    value=entities["address"],
                )
            )

        # 4. Employee range filter
        if entities.get("num_employees") and entities.get("num_employees_operator"):
            op = entities["num_employees_operator"]
            lower = entities["num_employees"] if op == "gte" else None
            upper = entities["num_employees"] if op == "lte" else None
            must_query.append(
                self._create_range_query(
                    entity_name="employees",
                    lower_bound=lower,
                    upper_bound=upper,
                )
            )

        # 5. Specific product names filter
        if entities.get("product_names"):
            names = [n.strip() for n in entities["product_names"].split(",")]
            nested_filters = [
                {"match_phrase_prefix": {"products.product_name": {"query": nm, "boost": 1.0}}}
                for nm in names
            ]
            if nested_filters:
                filter_query.append({
                    "nested": {
                        "path": "products",
                        "query": {"bool": {"filter": nested_filters}}
                    }
                })

        # 6. Return None if no conditions at all
        if not (must_query or should_query or filter_query or must_not_query):
            return None

        # 7. Build final bool query
        bool_body: Dict[str, Any] = {
            "filter": filter_query,
            "must": must_query,
            "should": should_query,
            "must_not": must_not_query,
        }

        # 8. Wrap in function_score for potential score functions
        query_body = {"function_score": {"query": {"bool": bool_body}}}
        sort: List[Any] = []

        # 9. Log query payload
        payload = {"query": query_body, "size": top_k, "sort": sort, "_source": True}
        logger.info(
            "Retrieve_documents full query with index %s:\n%s",
            index_name,
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

        # 10. Return request body
        return {
            "index": index_name,
            "query": query_body,
            "size": top_k,
            "sort": sort,
            "_source": True,
        }

    # --- Helper methods unchanged ---
    def _create_match_single_query(
        self,
        entity_name: str,
        value: Any,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        return {"match": {entity_name: {"query": value, "boost": weight}}}

    def _create_match_pharse_prefix_query(
        self,
        entity_name: str,
        value: Any,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        return {"match_phrase_prefix": {entity_name: {"query": value, "boost": weight}}}

    def _create_range_query(
        self,
        entity_name: str,
        lower_bound: Optional[Any] = None,
        upper_bound: Optional[Any] = None,
    ) -> Dict[str, Any]:
        cond: Dict[str, Any] = {}
        if lower_bound is not None:
            cond["gte"] = lower_bound
        if upper_bound is not None:
            cond["lte"] = upper_bound
        return {"range": {entity_name: cond}}

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

    def _create_fuzzy_query(
        self,
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
