from typing import Any, Dict, Optional

from elasticsearch import AsyncElasticsearch
from src.exceptions.base import ServerError
from src.services.external import BaseRetriever
from src.settings import SETTINGS


class ElasticsearchService(BaseRetriever):
    def __init__(self, index_name: Optional[str] = None):
        self.host = SETTINGS.ELASTICSEARCH_HOST
        self.port = SETTINGS.ELASTICSEARCH_PORT
        self.username = SETTINGS.ELASTICSEARCH_USER
        self.password = SETTINGS.ELASTICSEARCH_PASSWORD

        if not index_name:
            self.index_name = SETTINGS.ELASTICSEARCH_INDEX
        else:
            self.index_name = index_name

        self._client = AsyncElasticsearch(
            [f"http://{self.host}:{self.port}"],
            http_auth=(self.username, self.password),
            http_compress=True,
            verify_certs=False,
            request_timeout=120,
        )
        super().__init__()

    async def retrieve_documents(
        self,
        queries: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Retrieve documents from Elasticsearch

        Args:
            queries (Dict[str, Any]): query conditions
            index_name: elastic search index_name use to search
        Raises:
            ServerError: Latitude and longitude are required for geo search

        Returns:
            dict: Concatenated restaurant information
        """

        if self._client is None:
            raise ServerError("Elasticsearch client is not initialized")

        if not queries:
            return {}
        
        search_resp = await self._client.search(**queries)
        search_response = search_resp.body["hits"]

        return search_response
