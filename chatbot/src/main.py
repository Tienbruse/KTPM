import logging
import tracemalloc
from contextlib import asynccontextmanager

from fastapi import FastAPI
from src.api.routers import api_router
from src.services.rag import CompanyRAG
from src.services.rag import search_client
from src.settings import APP_CONFIGS, SETTINGS
from src.utils.telemetry import (
    RequestContextMiddleware,
    configure_logging,
    metrics_endpoint,
)
from starlette.middleware.cors import CORSMiddleware

tracemalloc.start()


# Define the filter
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return (
            record.args is not None
            and len(record.args) >= 3
            and list(record.args)[2] not in ["/health", "/ready"]
        )


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_service = CompanyRAG()
    try:
        yield
    finally:
        await search_client.close()


app = FastAPI(**APP_CONFIGS, lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.CORS_ORIGINS,
    allow_origin_regex=SETTINGS.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=SETTINGS.CORS_HEADERS,
)


@app.get("/health", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def readycheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return await metrics_endpoint()


app.include_router(
    api_router,
    prefix=SETTINGS.API_V1_STR,
)
