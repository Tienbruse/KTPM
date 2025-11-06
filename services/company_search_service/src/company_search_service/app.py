from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from aiobreaker import CircuitBreakerError
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import APP_CONFIG, Settings, get_settings
from .models import IndexRequest, SearchRequest
from .search import SearchService
from .telemetry import RequestContextMiddleware, configure_logging, metrics_endpoint

configure_logging()
logger = logging.getLogger("company_search_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    service = SearchService()
    app.state.search_service = service
    try:
        yield
    finally:
        await service.close()


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service


def get_router(settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.post("/search/companies")
    async def search_companies(
        request: SearchRequest,
        search_service: SearchService = Depends(get_search_service),
    ) -> JSONResponse:
        try:
            response = await search_service.search(request)
        except CircuitBreakerError as exc:
            # Let the global handler convert this into a 503 response.
            raise exc
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception(
                "Search request failed",
                extra={"path": "/search/companies"},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="search backend error"
            ) from exc
        return JSONResponse(content=response.model_dump())

    @router.post("/search/companies/index", status_code=status.HTTP_202_ACCEPTED)
    async def index_companies(
        request: IndexRequest,
        search_service: SearchService = Depends(get_search_service),
    ) -> JSONResponse:
        result = await search_service.index(request)
        return JSONResponse(content=result)

    return router


settings = get_settings()
app = FastAPI(**APP_CONFIG, lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_methods=["*"],
    allow_headers=settings.cors_headers,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return await metrics_endpoint()


router = get_router(settings)
app.include_router(router, prefix=settings.api_prefix)


@app.exception_handler(CircuitBreakerError)
async def handle_circuit_breaker_error(
    _: Request, exc: CircuitBreakerError
) -> JSONResponse:
    logger.warning(
        "Circuit breaker prevented downstream call", extra={"error": str(exc)}
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Search backend temporarily unavailable"},
    )
