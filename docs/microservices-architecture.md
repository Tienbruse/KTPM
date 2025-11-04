# Microservices Architecture

## Service Topology

| Service | Bounded Context | Responsibilities | Interface |
|---------|-----------------|------------------|-----------|
| **company-search-service** | Catalog Indexing & Search | Construct Elasticsearch queries from structured entity payloads, execute searches, expose ranking metadata. | REST (`POST /v1/search/companies`) |
| **ingestion-job** | Data Acquisition & Processing | Convert CSV/XLSX from `data/` into normalized JSON and push to search index through `company-search-service` (future queue integration). | Batch job (CLI + async task queue placeholder) |
| **chatbot-service** | Conversational Experience | Orchestrate LLM interactions, call `company-search-service`, format answers, expose `/v1/chat/completions`. | REST & Server-Sent Events |
| **ui-gateway** | Presentation | Streamlit UI consuming chatbot APIs. | HTTP |
| **observability-stack** | Observability Platform | Central log shipping (Elastic), metrics scraping (Prometheus), trace collector (OTLP stubs). | HTTP/OTLP |

## Communication Protocols
* **Internal service-to-service:** REST over HTTP using JSON. Services publish OpenAPI documents.
* **Async data ingestion:** Initial implementation triggers indexing by invoking REST endpoint. Design
  leaves room for future message queue (e.g., Kafka) to decouple ingestion cadence.
* **Observability:** Services emit structured logs (JSON) and expose `/metrics` in Prometheus format.
  Request/response traces include `X-Request-ID` header propagated across calls.

## API Contracts

### company-search-service
* `POST /v1/search/companies`
  * Request body:
    ```json
    {
      "entities": {
        "company_name": "string?",
        "business_field": "string?",
        "product_names": "string?",
        "address": "string?",
        "num_employees": 0,
        "num_employees_operator": "gte|lte"
      },
      "top_k": 5
    }
    ```
  * Response body:
    ```json
    {
      "results": [
        {
          "id": "...",
          "company_name": "...",
          "phone": "...",
          "products": [
            {"product_name": "...", "product_description": "..."}
          ]
        }
      ],
      "meta": {
        "total": 3,
        "took_ms": 25
      }
    }
    ```
* `GET /health`, `GET /metrics` for observability.

### chatbot-service
* `POST /v1/chat/completions`
  * Request body: `{ "message": "user prompt", "session_id": "optional" }`
  * Response: `{"response": "...", "sources": []}`
* Propagates `X-Request-ID` to outbound search calls and attaches metadata for tracing.
* Additional `POST /v1/chat/reset` to clear session memory.

### ingestion-job
* CLI entry point `uv run services/ingestion_job/main.py --file data/mst.csv` pushes batches via
  search API.

## Data Requirements & Ownership
* **company-search-service** owns the denormalized Elasticsearch index schema. Accepts sanitized
  entity payloads; rejects invalid structures with `422` responses. Maintains configuration for index
  name and credentials via environment variables.
* **ingestion-job** owns mapping from raw files to canonical document schema. Writes through search
  API and may later publish domain events.
* **chatbot-service** owns conversational memory, entity extraction prompts, and answer formatting.
* Shared `common/telemetry` helpers provide middleware for logging, metrics counters, and trace
  propagation.

## Deployment Considerations
* Each service ships with dedicated Dockerfile. `docker-compose.yml` orchestrates services locally
  along with Elasticsearch and Jaeger (stub). Kubernetes manifests under `k8s/` define Deployments,
  Services, and ConfigMaps for production.
* GitHub Actions pipeline builds containers, runs unit tests, and performs linting before pushing
  images to registry (placeholder commands).

