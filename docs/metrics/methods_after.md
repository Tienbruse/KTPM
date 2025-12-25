# Elasticsearch benchmark (search / msearch / get / mget)

- Timestamp (UTC): `2025-12-23T16:12:27Z`
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
| search_dsl | 3 | 3 | 18.473 | 163.900 | 3.833 |
| msearch_dsl | 3 | 1 | 9.312 | 346.472 | 5.700 |
| get | 50 | 50 | 37.633 | 1331.950 | — |
| mget | 50 | 5 | 16.114 | 3109.548 | — |
