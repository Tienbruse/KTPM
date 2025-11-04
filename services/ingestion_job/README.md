# Ingestion Job

This module will evolve into a standalone ingestion microservice. Today it provides a CLI skeleton
that normalizes CSV/XLSX records from `data/` and publishes JSON documents to the
`company-search-service` indexing endpoint (to be implemented). The job can be executed via:

```bash
uv run services/ingestion_job/main.py --file data/mst.csv
```

The CLI shares the same telemetry conventions as the online services so that batch executions can be
observed centrally.
