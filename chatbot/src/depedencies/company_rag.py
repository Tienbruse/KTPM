from fastapi import Request
from src.services.rag import CompanyRAG


def get_rag_service(request: Request) -> CompanyRAG:
    return request.app.state.rag_service
