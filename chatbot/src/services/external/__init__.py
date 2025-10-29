from abc import abstractmethod
from typing import Any, Dict, List

from langchain_core.documents import Document


class BaseRetriever:
    __retriever: None

    @property
    def client(self):
        return self.__retriever

    @abstractmethod
    def index_documents(self, documents: List[Document]):
        raise NotImplementedError

    def retrieve_documents(
        self, query: Dict[str, Any], top_k: int
    ) -> List[Document]:
        raise NotImplementedError
