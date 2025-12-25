from typing import List

from langchain_core.tools import tool

from src.services.agent import Agent
from src.services.entity_processor import EntityProcessor
from src.services.search_client import SearchServiceClient
from src.utils.logger import logger

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

    async def _retrieve_companies(self, user_input: str, top_k: int = 5) -> List[dict]:
        entities = EntityProcessor().get_entities(user_input)
        search_response = await search_client.search(entities=entities, top_k=top_k)
        return search_response.get("results", [])

    def _format_results(self, companies: List[dict]) -> str:
        lines: List[str] = []
        for idx, company in enumerate(companies, start=1):
            lines.append(
                f"{idx}. {company.get('company_name') or company.get('Name') or 'Không rõ tên'}"
            )
            if company.get("tax_code"):
                lines.append(f"   Mã số thuế: {company.get('tax_code')}")
            if company.get("address"):
                lines.append(f"   Địa chỉ: {company.get('address')}")
            if company.get("phone"):
                lines.append(f"   Điện thoại: {company.get('phone')}")
            if company.get("email"):
                lines.append(f"   Email: {company.get('email')}")
            if company.get("information"):
                lines.append(f"   Giới thiệu: {company.get('information')}")
            products = company.get("products") or []
            if products:
                lines.append("   Sản phẩm:")
                for product in products[:3]:
                    name = product.get("product_name") or "Không rõ tên"
                    desc = product.get("product_description") or ""
                    lines.append(f"     - {name}{': ' + desc if desc else ''}")
        return "\n".join(lines) if lines else "Không tìm thấy công ty phù hợp."

    async def get_response(
        self,
        user_input: str,
        thread_id: str | None = None,
    ):
        """Get response from RAG"""
        try:
            companies = await self._retrieve_companies(user_input=user_input)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Search pipeline failed, returning safe message",
                extra={"error": str(exc)},
            )
            return "Hệ thống tìm kiếm đang gặp sự cố, vui lòng thử lại sau."

        if companies:
            return self._format_results(companies)

        return "Không tìm thấy công ty phù hợp trong cơ sở dữ liệu."

    async def clear_memory(self):
        self._agent.clear_memory()
        return None
