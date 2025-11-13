## Circuit Breaker & Emissary Integration Overview

This document summarizes the changes introduced when the company-search service
added an application-level circuit breaker and the platform gained an
Emissary/Ambassador edge gateway.

### Circuit Breaker Highlights

- **Library & scope:** `aiobreaker` wraps every Elasticsearch call inside
  `ElasticsearchGateway`. Both search and bulk-index reuse the same breaker.
- **Configuration knobs:** exposed through `Settings` (see
  `SEARCH_SERVICE_BREAKER_*` variables). Tune failure-rate threshold, minimum
  calls, wait duration, timeout, retry count, and exponential backoff.
- **Observability:** `MetricsRecorder` now tracks dependency outcomes and breaker
  state transitions. `/metrics` emits `circuit_breaker_calls_total`,
  `circuit_breaker_state`, and `circuit_breaker_open_total`.
- **Error handling:** `CircuitBreakerError` is translated to HTTP 503 while other
  backend failures keep returning 502.
- **Testing:** run
  `PYTHONPATH=services/company_search_service/src uv run python -m unittest services.company_search_service.tests.test_circuit_breaker -v`
  to verify open/recover behaviour. Tests simulate repeated failures and
  recovery after the wait duration.

### Emissary (Ambassador) Gateway

- **Manifests:** Under `k8s/emissary/` you will find Helm values plus Listener,
  Host, Mapping, Filter, Rate-limit, and observability CRDs.
- **Docs:** `docs/emissary.md` contains the full installation and operations
  guide: prerequisites (TLS/OIDC secrets), Helm upgrade instructions, routing,
  security, observability, and change-management workflow.
- **Security & policies:** OAuth2 filter enforces IdP auth on `/api/*`, rate
  limiting is applied per-user and per-IP for mappings labeled
  `rate-limit-tier: standard`, and circuit-breaker settings on the gateway limit
  max connections/pending requests upstream.
- **Observability:** LogService forwards Envoy access logs to Fluent Bit,
  TracingService streams to Jaeger, and a Prometheus `ServiceMonitor` scrapes
  the ingress stats port.

### Post-Deployment Checklist

1. Ensure the gateway secrets exist (`emissary-gateway-tls`,
   `emissary/oidc-client-secret`).
2. Install CRDs and deploy Emissary via
   `helm upgrade --install ... -f k8s/emissary/values.yaml`.
3. Apply the manifests in `k8s/emissary/` (namespace → listeners → host →
   filters → mappings → observability).
4. Run smoke tests:
   - `curl https://<domain>/api/chatbot/health`
   - `curl https://<domain>/api/search/metrics`
   - Trigger rate-limit and confirm `x-envoy-ratelimited`.
5. Monitor metrics/traces/logs to verify circuit-breaker state and traffic
   through the gateway.

Keep this document updated as breaker thresholds or gateway topology changes.
