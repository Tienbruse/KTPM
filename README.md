This is a project about to find information of company.

## Microservice architecture

The monolith has been split into independent services:

- `chatbot/` exposes the conversational API and forwards structured queries to the
  `company-search-service` via REST.
- `services/company_search_service/` owns Elasticsearch query composition and provides a reusable
  search API. Both services emit metrics at `/metrics` and propagate `X-Request-ID` headers for
  distributed tracing.
- Container images and orchestration manifests live in `docker-compose.yml` and `k8s/`.

The repo also contains architecture documentation in `docs/` and a CI workflow under
`.github/workflows/ci.yml` that builds the services and validates the codebase.

## Latest platform additions

- **Circuit breaker:** Elasticsearch calls are guarded by `aiobreaker`. See
  `docs/breaker-ambassador.md` for tuning and testing details.
- **Ambassador gateway:** Emissary manifests under `k8s/emissary/` expose the
  chatbot/search APIs through an authenticated, rate-limited edge layer. Setup
  instructions live in `docs/emissary.md`.

# Structure

```bash
.
└── company-llm/
    ├── chatbot/
    │   └── run.py <-- Main file to run Chatbot service.
    ├── data <-- Folder contains data./
    │   ├── mst.csv
    │   └── thongtindoanhnghiep.xlsx
    ├── elk/
    │   └── docker-compose.yml <-- Main file to build ElasticSearch.
    ├── indexer/
    │   ├── mst/
    │   │   └── script.py <-- Main script to index data mst.csv
    │   └── thongtindoanhnghiep/
    │       └── script.py <-- Main script to index data thongtindoanhnghiep.xlsx
    ├── ui <-- Chatbot UI/
    │   └── run.py <-- Main file to run Chatbot UI
    ├── Makefile <-- This is file which manage command line.
    ├── pyproject.yoml <-- This is file which manages all versions of necessary libraies.
    └── uv.lock <-- This is a file which saves all versions of above libraries and their dependencies.
```
# Guideline
## Step 1. The first step is installing Makefile.

For Linux:
```bash
sudo apt-get update &&
sudo apt-get install make
```

For MacOS:
```bash
brew install make
```

# Step 2. Run `make menu` and choose your options.

```bash
make menu
```

- Xoá index cũ: curl -X DELETE "http://localhost:9200/company-data-20240329"
- chạy index: uv run indexer/data_20250329/script.py    # KTPM
