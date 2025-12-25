# Elasticsearch benchmark (search / msearch / get / mget)

- Timestamp (UTC): `2025-12-23T16:11:48Z`
- Index: `company-data-20240329`
- Query version (DSL): `v1`
- Runs: `10`, warmup: `5`
- search batch size: `0`
- msearch batch size: `0`
- mget batch size: `10`
- mget docs: `50`

## Summary

| method | ops/run | requests/run | wall mean (ms) | QPS mean | ES took mean (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| search_dsl | 3 | 3 | 16.375 | 187.262 | 3.167 |
| msearch_dsl | 3 | 1 | 8.761 | 366.568 | 4.300 |
| get | 50 | 50 | 37.263 | 1342.388 | — |
| mget | 50 | 5 | 16.663 | 3003.311 | — |
