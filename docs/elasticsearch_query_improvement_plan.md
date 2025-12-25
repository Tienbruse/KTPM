# Kế hoạch cải tiến truy vấn Elasticsearch

## 1. Bối cảnh
Chức năng `QueryCreator` hiện tạo truy vấn dạng `function_score` với các điều kiện `must`, `should`, `filter` và cộng điểm thưởng dựa trên sự hiện diện của một số trường (url, introduction, sản phẩm...). Truy vấn này đã đáp ứng các yêu cầu gần đây (ưu tiên website, loại bỏ domain không mong muốn). Tuy nhiên, phản hồi thực tế cho thấy vẫn có nhiều kết quả bị đánh giá thấp về mức độ liên quan hoặc thiếu dữ liệu cần thiết. Trước khi chỉnh sửa thêm vào codebase, tài liệu này ghi nhận các vấn đề và đề xuất cụ thể để đội ngũ đánh giá.

## 2. Hạn chế hiện tại
- **Relevance hạn chế**: Các điều kiện `should` chưa ràng buộc mức độ bắt buộc (không dùng `minimum_should_match`), dẫn tới nhiều công ty chỉ khớp lỏng lẻo theo tên hoặc phần giới thiệu.
- **Điểm ưu tiên cứng**: Việc cộng điểm dựa trên `exists` chỉ phân bổ điểm cố định, chưa phản ánh “mức độ giàu thông tin” (ví dụ số lượng sản phẩm, độ dài giới thiệu, số kênh liên hệ).
- **Không xét chất lượng domain**: Ngoài `doanhnghiepmoi.vn`, các domain yếu khác vẫn được tính điểm như nhau với domain chính thống.
- **Thiếu điều kiện đa thực thể**: Người dùng có thể cung cấp nhiều sản phẩm hoặc nhiều địa danh nhưng truy vấn hiện tại chỉ kết hợp đơn giản, dễ bỏ sót.
- **Không có logging chuyên sâu**: Chưa lưu lại thông tin điểm số chi tiết để phân tích sau.

## 3. Định hướng cải tiến

### 3.1. Tăng độ chính xác truy vấn
1. **Ràng buộc `minimum_should_match`** cho khối `bool.should`. Điều này đảm bảo kết quả phải khớp ít nhất một tiêu chí tự do (ngành nghề, sản phẩm) thay vì chỉ dựa vào `must`.
2. **`multi_match` với trọng số linh hoạt** cho các sản phẩm hoặc ngành nghề: thay vì `match_phrase_prefix` duy nhất, có thể kết hợp `best_fields`/`most_fields` để tận dụng nhiều trường (ví dụ `introduction`, `products.product_name`, `products.product_description`).
3. **Chuẩn hóa accent toàn cục**: Hiện có helper `_create_accents_query` cho địa chỉ. Có thể tạo phiên bản tương tự cho `company_name` và `products` để tăng tỷ lệ khớp tiếng Việt không dấu.

### 3.2. Ưu tiên công ty giàu thông tin
1. **Tính toán số lượng thông tin**: Sử dụng `script_score` hoặc `weight` dựa trên `params` để cộng điểm theo số lượng trường tồn tại, ví dụ:
   - `doc['products.product_name'].length` (số sản phẩm)
   - `doc['introduction'].size()` hoặc độ dài chuỗi
   - `params.contact_fields_count`
2. **Phân nhóm điểm “chất lượng liên hệ”**: Tăng trọng số nếu công ty có cả `email`, `phone`, `url`. Có thể tạo `weight` dựa trên `must` condition `bool` => `doc['phone'].size()>0 && doc['email'].size()>0`.
3. **Ưu tiên domain đáng tin**: thêm `should`/`functions` boost cho domain có trong whitelist (ví dụ `.gov.vn`, `.org.vn`, trang thương mại điện tử phổ biến). Có thể khai báo trong settings để dễ chỉnh sửa.

### 3.3. Loại bỏ hoặc phạt các domain không mong muốn
1. **Blacklist mở rộng**: sử dụng mảng cấu hình (ví dụ `SETTINGS.URL_BLACKLIST`) và sinh ra `must_not` tương ứng thay vì hard-code.
2. **Giảm điểm thay vì loại bỏ tuyệt đối**: Với domain chưa chắc chắn, có thể dùng `function_score` với `weight` âm hoặc `boost_mode: multiply` để giảm thứ hạng mà không loại khỏi kết quả.

### 3.4. Hỗ trợ truy vấn nhiều thực thể
1. **`bool.should` cho nhiều sản phẩm**: Khi người dùng nhập danh sách sản phẩm, thay vì gộp bằng `filter`, có thể dùng `should` với `minimum_should_match` để tìm công ty nào khớp ít nhất một sản phẩm.
2. **Địa lý theo nhiều cấp**: Nếu NLP trả về `tỉnh` và `quận`, thêm `should` cho mỗi cấp để ưu tiên công ty khớp đầy đủ vị trí.

### 3.5. Quan sát & kiểm thử
1. **Ghi log điểm `function_score`**: Bật `track_scores` trong truy vấn và log top N score để đánh giá sau.
2. **Thêm test dataset**: Tạo tập truy vấn chuẩn (ví dụ 10 câu) chạy tự động sau mỗi thay đổi để so sánh thứ hạng kết quả.

## 4. Lợi ích kỳ vọng
- Kết quả đầu ra ưu tiên doanh nghiệp có website chính thống, nhiều thông tin sản phẩm, thông tin liên hệ đầy đủ.
- Tính linh hoạt cao hơn nhờ cấu hình domain whitelist/blacklist và trọng số qua settings.
- Quy trình cải tiến có kiểm thử/logging giúp đánh giá rõ tác động.

## 5. Các bước tiếp theo
1. Thống nhất bộ domain whitelist/blacklist và trọng số mới với nhóm vận hành dữ liệu.
2. Cập nhật `settings` để đọc các cấu hình trên (tránh hard-code).
3. Refactor `QueryCreator` theo hướng modular: chia nhỏ phần xây dựng `query`, `function_score`, `filters` để dễ unit test.
4. Viết test integration (ví dụ `tests/test_es_query_builder.py`) mô phỏng các tổ hợp entity khác nhau.
5. Sau khi các thay đổi được duyệt trong tài liệu này, tiến hành chỉnh sửa code và triển khai.

## 6. So sánh và lưu thông số cho hai phiên bản
Để theo dõi tác động của từng đợt cải tiến, giữ nguyên mô hình “phiên bản truy vấn”:

| Thông số chính | Phiên bản hiện tại (v1 - sau yêu cầu ưu tiên URL) | Phiên bản đề xuất (v2 - sau cải tiến bổ sung) |
| --- | --- | --- |
| `bool.must` | Tên công ty (`match_phrase_prefix`), địa chỉ (multi_match chuẩn hóa) | Giữ nguyên, bổ sung variances (accent-insensitive cho tên, địa lý đa cấp) |
| `bool.should` | Ngành nghề (`match` introduction), sản phẩm (`nested match_phrase_prefix`) | Thêm nhiều thực thể, đặt `minimum_should_match >= 1`, dùng `multi_match` mode `best_fields` |
| `bool.must_not` | Loại bỏ domain `doanhnghiepmoi.vn` | Cho phép cấu hình mảng blacklist/penalty cho nhiều domain |
| `function_score.functions` | Các `exists`-boost: URL (6), introduction (4), sản phẩm (3), liên hệ (1.5), tax_code, address | Thêm `script_score` tính số trường thông tin, điểm thưởng theo domain whitelist, giảm điểm domain rủi ro |
| `score_mode` / `boost_mode` | `sum` / `sum` | Có thể chuyển sang `sum`/`multiply` hoặc `avg` tùy tests |
| Logging | Log payload JSON trong `QueryCreator` | Bổ sung `track_scores`, log top-hit metadata + metrics file |

### 6.1. Quy trình lưu thông số
1. **Chạy server với `ES_QUERY_VERSION=v1`** (baseline). Gửi bộ truy vấn mẫu (ít nhất 10 câu thường gặp). Thu thập:
   - `total_hits`, `max_score`, `avg_score`.
   - Số kết quả có URL, có >=3 sản phẩm, có đủ thông tin liên hệ.
   - Danh sách domain top-5 xuất hiện.
   Ghi vào file `docs/metrics/v1_<ngày>.jsonl`.
2. **Triển khai cải tiến (v2)** theo kế hoạch.
3. **Lặp lại bộ truy vấn** với `ES_QUERY_VERSION=v2`, lưu vào `docs/metrics/v2_<ngày>.jsonl`.
4. **So sánh** bằng script/Notebook (có thể dùng `pandas`) để tạo bảng:

| Truy vấn | v1 max_score | v2 max_score | % kết quả có URL | Ghi chú |
| --- | --- | --- | --- | --- |
| “công ty sản xuất gạch” | … | … | … | … |

5. **Báo cáo** các khác biệt nổi bật (ví dụ: tăng tỷ lệ kết quả có URL từ 40% lên 85%).

### 6.2. Công cụ hỗ trợ đề xuất
- Tạo script `scripts/collect_es_metrics.py` (chạy bằng `uv run`) để tự động gửi bộ truy vấn mẫu và lưu JSONL kèm version.
- Bổ sung biến môi trường `ES_QUERY_VERSION`/`ES_QUERY_STRATEGY` trong settings để dễ chuyển đổi khi test A/B.
- Dựng dashboard tạm thời (ví dụ trong notebook `analysis/es_query_comparison.ipynb`) để trực quan hóa các thông số giữa v1 và v2.
