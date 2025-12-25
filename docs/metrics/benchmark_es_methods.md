
  - Chạy benchmark baseline (prewarm, warmup=5, batch mget=10):

  uv run scripts/benchmark_es_methods.py \
    --index company-data-20240329 \
    --queries-file docs/metrics/sample_queries.json \
    --runs 10 --warmup 5 \
    --search-batch-size 0 --msearch-batch-size 0 \
    --mget-batch-size 10 --mget-docs 50 \
    --ids-file docs/metrics/sample_ids.json \
    --prewarm \
    --output docs/metrics/methods_before.json \
    --markdown docs/metrics/methods_before2137.md

  - Áp dụng cấu hình tối ưu:

  uv run scripts/configure_es.py \
    --index company-data-20240329 \
    --refresh-interval 5s \
    --flush-threshold 512mb \
    --request-cache

  - Chạy lại benchmark:

  uv run scripts/benchmark_es_methods.py \
    --index company-data-20240329 \
    --queries-file docs/metrics/sample_queries.json \
    --runs 10 --warmup 5 \
    --search-batch-size 0 --msearch-batch-size 0 \
    --mget-batch-size 10 --mget-docs 50 \
    --ids-file docs/metrics/sample_ids.json \
    --prewarm \
    --output docs/metrics/methods_after.json \
    --markdown docs/metrics/methods_after.md

  - So sánh kết quả

  uv run scripts/compare_methods_report.py \
    --baseline docs/metrics/methods_before.json \
    --candidate docs/metrics/methods_after.json \
    --output docs/metrics/so_sanh_methods.md

  uv run scripts/md_table_to_csv.py --input docs/metrics/so_sanh_methods.md --output docs/metrics/so_sanh_methods.csv


  - Reset cấu hình về baseline:

  uv run scripts/configure_es.py \
    --index company-data-20240329 \
    --refresh-interval 1s \
    --flush-threshold 512mb \
    --no-request-cache
