from fastapi import APIRouter
from src.api.endpoints import retrieval

api_router = APIRouter()
api_router.include_router(retrieval.router, prefix="/retrieve", tags=["Retriever"])
