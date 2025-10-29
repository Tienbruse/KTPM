from typing import Optional

from src.services.external.elasticsearch_service import ElasticsearchService


class Retriever:
    def __init__(
        self,
        index_name: Optional[str] = None,
    ):
        self.__retriever = ElasticsearchService(index_name=index_name)

    @property
    def retriever(self):
        return self.__retriever
