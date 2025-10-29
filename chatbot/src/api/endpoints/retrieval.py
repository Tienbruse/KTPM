from fastapi import APIRouter, Depends, status
from src.depedencies.company_rag import get_rag_service
from src.schemas.retrieval import RetrievalInput
from src.services.rag import CompanyRAG
from src.utils.logger import logger

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=str,
)
async def retrieve_restaurants(
    input: RetrievalInput,
    rag_service: CompanyRAG = Depends(get_rag_service),
) -> str:
    response = await rag_service.get_response(
        user_input=input.user_input,
    )
    logger.info(f"Response: {response}")

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
