import json

def calculate_average_metrics(data):
    """Tính trung bình các chỉ số phụ (rouge1, rouge2, rougeL, meteor, bertscore)."""
    metrics = ['rouge1', 'rouge2', 'rougeL', 'meteor', 'bertscore']
    total = 0
    count = 0
    for metric in metrics:
        if metric in data:
            total += data[metric]
            count += 1
    return total / count if count > 0 else 0

def filter_and_reindex_results(input_filename="/Users/Tienbruse/tmdt/Backend/company-llm/test/results_evaluation-3.json", output_filename="/Users/Tienbruse/tmdt/Backend/company-llm/test/last_result.json"):
    """
    Đọc file JSON, lọc kết quả dựa trên deepseek_score và các chỉ số phụ,
    sau đó đánh lại index và lưu vào file mới.
    """
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            # Giả sử file JSON chứa một danh sách các đối tượng
            # Nếu file chỉ chứa một đối tượng như ví dụ, cần đặt nó vào list
            # Ví dụ: data = [json.load(f)]
            # Hoặc nếu file chắc chắn là một list:
            data = json.load(f)
            # Đảm bảo data là một list để xử lý nhất quán
            if not isinstance(data, list):
                 data = [data] # Nếu file chỉ chứa 1 object, biến nó thành list 1 phần tử

    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file '{input_filename}'")
        return
    except json.JSONDecodeError:
        print(f"Lỗi: File '{input_filename}' không phải là định dạng JSON hợp lệ.")
        return
    except Exception as e:
        print(f"Đã xảy ra lỗi không mong muốn khi đọc file: {e}")
        return

    filtered_data = []
    print(f"Đã tải {len(data)} bản ghi từ '{input_filename}'. Bắt đầu lọc...")

    for item in data:
        # Kiểm tra xem các key cần thiết có tồn tại không
        if not all(k in item for k in ['RAG', 'Deepseek']) or \
           not all(score_key in item['RAG'] for score_key in ['deepseek_score']) or \
           not all(score_key in item['Deepseek'] for score_key in ['deepseek_score']):
            print(f"Cảnh báo: Bỏ qua bản ghi với index gốc {item.get('index', 'N/A')} do thiếu cấu trúc RAG/Deepseek hoặc deepseek_score.")
            continue

        rag_score = item['RAG']['deepseek_score']
        deepseek_score = item['Deepseek']['deepseek_score']
        keep_item = False

        if rag_score > deepseek_score:
            keep_item = True
        elif rag_score == deepseek_score:
            # Tính trung bình các chỉ số khác để quyết định
            avg_rag_metrics = calculate_average_metrics(item['RAG'])
            avg_deepseek_metrics = calculate_average_metrics(item['Deepseek'])
            if avg_rag_metrics >= avg_deepseek_metrics: # Giữ lại RAG nếu bằng hoặc tốt hơn
                keep_item = True

        if keep_item:
            filtered_data.append(item)

    print(f"Đã lọc xong. Giữ lại {len(filtered_data)} bản ghi.")

    # Đánh lại số index bắt đầu từ 1
    for i, item in enumerate(filtered_data, start=1):
        item['index'] = i

    # Lưu kết quả vào file mới
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=4)
        print(f"Đã lưu kết quả đã lọc và đánh lại index vào file '{output_filename}'.")
    except Exception as e:
        print(f"Đã xảy ra lỗi khi ghi file '{output_filename}': {e}")

# Chạy hàm xử lý
filter_and_reindex_results()