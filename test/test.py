import json
import pandas as pd

# Thay đổi đường dẫn này thành đường dẫn file JSON của bạn
results_file = "/Users/Tienbruse/tmdt/Backend/company-llm/test/last_result.json"

# Đọc dữ liệu từ file JSON
with open(results_file, "r", encoding="utf-8") as f:
    results = json.load(f)

# Khởi tạo DataFrame để lưu các giá trị
rag_scores = []
deepseek_scores = []

# Thu thập các chỉ số
for item in results:
    rag_scores.append(item["RAG"])
    deepseek_scores.append(item["Deepseek"])

# Chuyển sang DataFrame để dễ tính toán
rag_df = pd.DataFrame(rag_scores)
deepseek_df = pd.DataFrame(deepseek_scores)

# Tính trung bình các chỉ số
rag_means = rag_df[["rouge1", "rouge2", "rougeL", "meteor", "bertscore", "deepseek_score"]].mean()
deepseek_means = deepseek_df[["rouge1", "rouge2", "rougeL", "meteor", "bertscore", "deepseek_score"]].mean()

# Hiển thị rõ ràng các chỉ số
print("Trung bình các chỉ số đánh giá:")
print("\nRAG:")
print(rag_means)

print("\nDeepseek:")
print(deepseek_means)
