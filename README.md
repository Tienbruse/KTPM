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
