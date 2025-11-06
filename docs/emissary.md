## Emissary‑Ingress (Ambassador) Gateway Setup

This guide describes how to deploy Emissary‑Ingress, configure routing to the
chatbot microservices, and manage security/observability policies.

### 1. Install Emissary‑Ingress

1. Add the Helm repo and update it:

   ```bash
   helm repo add datawire https://app.getambassador.io
   helm repo update
   ```

2. Create the runtime namespaces:

   ```bash
   kubectl apply -f k8s/emissary/namespace.yaml
   kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
   ```

3. Install the CRDs (only once per cluster):

   ```bash
   kubectl apply -f https://app.getambassador.io/yaml/emissary/latest/emissary-crds.yaml
   ```

4. Install/upgrade Emissary with the curated settings:

   ```bash
   helm upgrade --install emissary-ingress datawire/emissary-ingress \
     --namespace emissary \
     --create-namespace \
     -f k8s/emissary/values.yaml
   ```

5. (Optional) Allocate a cloud LoadBalancer or configure an ingress/NLB that
   targets the `emissary-ingress` service. For bare metal environments expose a
   NodePort and front it with MetalLB or an external reverse proxy.

### 2. Bootstrap security prerequisites

* **TLS certificate:** create `emissary-gateway-tls` in the `emissary` namespace.
  Use cert‑manager, ACM, or manual `kubectl create secret tls`.
* **OIDC client secret:** store the OAuth client secret in
  `emissary/oidc-client-secret`.
* **Rate limiting storage:** the Helm values enable the bundled Redis instance.
  For production replace it with an external Redis (update `values.yaml`).

### 3. Apply routing and policy resources

After Helm finishes, apply the declarative configuration:

```bash
kubectl apply -f k8s/emissary/listeners.yaml
kubectl apply -f k8s/emissary/hosts.yaml
kubectl apply -f k8s/emissary/filters.yaml
kubectl apply -f k8s/emissary/mappings.yaml
kubectl apply -f k8s/emissary/observability.yaml
```

Adjust hostnames, callback URLs, and origin lists to match your domains. Each
Mapping targets the existing services (`chatbot-service`, `company-search-service`)
deployed in the `default` namespace.

### 4. Authentication & rate limiting

* `filters.yaml` defines an OAuth2 filter (`oidc-auth`) that uses an external
  identity provider. The `FilterPolicy` attaches the filter to all `/api/*`
  routes. Update the URLs and scopes for your IdP.
* `RateLimitService` points to the Envoy rate limit service that ships with the
  chart. The `RateLimitPolicy` applies per-user and per-IP quotas to every
  mapping labeled `rate-limit-tier: standard`. Tune the requests per minute to
  meet your needs.

### 5. Observability

* `observability.yaml` pipes access logs to Fluent Bit, sends traces to Jaeger,
  and exposes metrics via a `ServiceMonitor` for Prometheus. Modify the service
  names to match your logging/tracing stack.
* The Helm chart already annotates pods for scraping; ensure Prometheus is
  configured to read from the `emissary-ingress` service or the provided monitor.

### 6. Change management workflow

1. Edit YAML under `k8s/emissary/` and commit changes.
2. Validate manifests locally with `kubectl apply --dry-run=client`.
3. Deploy to staging:

   ```bash
   kubectl apply -f k8s/emissary/
   ```

4. Run smoke tests (curl to `/api/chatbot/health`, `/api/search/health`).
5. Confirm tracing/metrics/logs flow into observability stack.
6. Promote to production via GitOps (Argo CD/Flux) or a controlled Helm upgrade.
7. Rollback using `helm rollback emissary-ingress <revision>` if needed.

### 7. Post-deployment checklist

- External DNS/ingress entries resolve to the Emissary load balancer.
- TLS termination succeeds (`curl -I https://chat.example.com/api/chatbot/health`).
- OAuth login flow completes and injects `x-user-*` headers.
- Rate limiting headers (`x-envoy-ratelimited`) appear when exceeding limits.
- Prometheus scrapes `/metrics`, Jaeger shows traces, and logs land in Fluent Bit.

Update this document whenever routing, security posture, or observability
pipelines change. Include screenshots/runbooks in your team's knowledge base as
the platform evolves.
