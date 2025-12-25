import time

from fastapi import APIRouter, Depends, Request, status

from src.depedencies.company_rag import get_rag_service
from src.schemas.retrieval import RetrievalInput
from src.services.rag import CompanyRAG
from src.settings import SETTINGS
from src.utils.logger import logger

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=str,
)
async def retrieve_restaurants(
    input: RetrievalInput,
    request: Request,
    rag_service: CompanyRAG = Depends(get_rag_service),
) -> str:
    start = time.perf_counter()
    thread_id = request.headers.get("x-request-id")
    response = await rag_service.get_response(
        user_input=input.user_input,
        thread_id=thread_id,
    )
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "Response sent",
        extra={
            "duration_ms": round(duration_ms, 2),
            "request_id": thread_id,
            "entity_extractor_mode": SETTINGS.ENTITY_EXTRACTOR_MODE,
        },
    )

    return response


@router.post(
    "/reset",
    status_code=status.HTTP_200_OK,
)
async def reset_memory(
    rag_service: CompanyRAG = Depends(get_rag_service),
) -> None:
    await rag_service.clear_memory()
    logger.info("Memory cleared")
    return None
