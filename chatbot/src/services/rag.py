from typing import List

from langchain_core.tools import tool
from src.services.agent import Agent
from src.services.entity_processor import EntityProcessor
from src.services.query_creator import QueryCreator
from src.services.retriever import Retriever
from src.settings import SETTINGS


@tool
async def retrieve_documents(
    user_input: str,
    top_k: int = 5,
) -> List[dict]:
    """Retrieve documents from Elasticsearch"""
    entities = EntityProcessor().get_entities(user_input)

    # Create and execute query
    queries = QueryCreator().create_query(
        entities=entities,
        index_name=SETTINGS.ELASTICSEARCH_INDEX,
        top_k=top_k,
    )
    if not queries:
        return []

    search_response = await Retriever().retriever.retrieve_documents(queries=queries)

    # Format results
    company_results = [
        CompanyRAG().format_search_results(hit, entities)
        for hit in search_response["hits"]
    ]

    if not company_results:
        return [{"info": "Not found"}]

    return company_results


class CompanyRAG:
    def __init__(self):
        self._input_validator = None
        self._agent = Agent(tools=[retrieve_documents])

    async def get_response(
        self,
        user_input: str,
    ):
        """Get response from RAG"""
        response = await self._agent.generate(message=user_input)
        return response

    async def clear_memory(self):
        self._agent.clear_memory()
        return None

    @staticmethod
    def format_search_results(
        hit: dict,
        entities: dict,
    ) -> dict:
        """Format search results into standard output format"""
        result = {
            "id": hit["_id"],
            "phone": hit["_source"].get("phone"),
            "email": hit["_source"].get("email"),
            "tax_code": hit["_source"].get("tax_code"),
            "address": hit["_source"].get("address"),
            "url": hit["_source"].get("url"),
            "products": hit["_source"].get("products"),
            "company_name": hit["_source"].get("name"),
            "information": hit["_source"].get("introduction"),
            "num_employees": hit["_source"].get("employees"),
        }

        if entities["product_names"]:
            result["products"] = [
                product
                for product in result.get("products", [])
                if entities["product_names"].lower() in product["product_name"].lower()
            ]
        else:
            result["products"] = result["products"][:3]

        print("result", result)
        return result
