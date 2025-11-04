from typing import List

from langchain_core.tools import tool
from src.services.agent import Agent
from src.services.entity_processor import EntityProcessor
from src.services.search_client import SearchServiceClient

search_client = SearchServiceClient()


@tool
async def retrieve_documents(
    user_input: str,
    top_k: int = 5,
) -> List[dict]:
    """Retrieve documents from Elasticsearch"""
    entities = EntityProcessor().get_entities(user_input)

    search_response = await search_client.search(
        entities=entities,
        top_k=top_k,
    )

    company_results = search_response.get("results", [])

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

