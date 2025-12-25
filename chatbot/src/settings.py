from typing import Any, Optional

from pydantic_settings import BaseSettings


class ExternalConfig(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8910
    ROOT_PATH: str = "/michelin-recommendation/api"
    API_V1_STR: str = "/v1"
    CORS_ORIGINS: Any = ["*"]
    CORS_ORIGINS_REGEX: Optional[str] = None
    CORS_HEADERS: Any = ["*"]

    # Michelin configuration
    LLM_TYPE: str = "OpenAPI"
    RETRIEVER_TYPE: str = "Elasticsearch"

    MODEL_SOURCE: str = "openai"

    # OpenAI configuration
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o"
    MODEL_TEMPERATURE: float = 0.9

    # DeepSeek configuration
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"
    DEEPSEEK_MODEL_TEMPERATURE: float = 0.9

    # Elasticsearch configuration
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_USER: str = "admin"
    ELASTICSEARCH_PASSWORD: str = "admin"
    ELASTICSEARCH_INDEX: str = "company-data"

    # Internal services
    SEARCH_SERVICE_URL: str = "http://localhost:9011"
    SEARCH_SERVICE_TIMEOUT: int = 30
    # Entity extraction modes: fast (no LLM), llm (always LLM), hybrid (auto choose)
    ENTITY_EXTRACTOR_MODE: str = "llm"  # options: fast|llm|hybrid
    FAST_ENTITY_FIELD: str = "company_name"
    HYBRID_LENGTH_THRESHOLD: int = 80  # characters


SETTINGS = ExternalConfig()  # pyright: ignore
APP_CONFIGS: dict[str, Any] = {
    "title": "Company Recommendation",
    "root_path": SETTINGS.ROOT_PATH,
}
