import json

MAX_QA_PAIRS = 2000
# Các trường bạn muốn hiển thị về công ty:
COMPANY_FIELDS = [
    ("Tên công ty", "name"),
    ("Mã số thuế", "tax_code"),
    ("Địa chỉ", "address"),
    ("Email", "email"),
    ("Số điện thoại", "phone"),
    ("Quy mô nhân sự", "employees"),
    ("Website", "url"),
    ("Giới thiệu", "introduction"),
]
# Các trường bạn muốn hiển thị về sản phẩm:
PRODUCT_FIELDS = [
    ("Tên sản phẩm", "product_name"),
    ("Mô tả sản phẩm", "product_description"),
    ("Đường dẫn sản phẩm", "product_link"),
]

def load_data(json_file_path):
    """Đọc file JSON, trả về list các doanh nghiệp."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = [data]
    return data

def build_company_answer(company):
    """
    Tạo câu trả lời bằng cách ghép các trường không rỗng,
    trả về (answer_string, count_non_empty).
    """
    lines = []
    count_non_empty = 0
    for label, key in COMPANY_FIELDS:
        val = company.get(key, "")
        if not val:
            # val là None hoặc chuỗi rỗng
            continue
        # Bước 1: ép về chuỗi
        val_str = str(val).strip()
        # Bước 2: lọc bỏ các giá trị "không ý nghĩa"
        # ví dụ: "./."
        if val_str == "./.":
            continue
        # Nếu là "Quy mô nhân sự" mà val_str = "0 người" => bỏ qua
        if label == "Quy mô nhân sự":
            # Giả sử ta coi "0 người" là không có giá trị
            if val_str.startswith("0"):
                # ví dụ "0 người" hay "0" => skip
                continue
        # Nếu còn là chuỗi hợp lệ, ta thêm vào lines
        lines.append(f"{label}: {val_str}")
        count_non_empty += 1
    answer = "\n".join(lines)
    return answer, count_non_empty

def build_product_answer(product):
    """
    Tạo câu trả lời cho sản phẩm,
    trả về (answer_string, count_non_empty).
    """
    lines = []
    count_non_empty = 0
    for label, key in PRODUCT_FIELDS:
        val = product.get(key, "")
        if val and isinstance(val, str) and val.strip():
            lines.append(f"{label}: {val.strip()}")
            count_non_empty += 1
        elif val and not isinstance(val, str):
            lines.append(f"{label}: {val}")
            count_non_empty += 1
    answer = "\n".join(lines)
    return answer, count_non_empty

def remove_duplicate_questions(qa_pairs):
    """
    Loại bỏ các câu hỏi trùng lặp, giữ lại cặp có info_count cao nhất.
    """
    # Sử dụng dictionary để lưu câu hỏi và info_count cao nhất
    unique_questions = {}
    
    for qa in qa_pairs:
        question = qa["question"]
        info_count = qa["info_count"]
        
        # Nếu câu hỏi chưa có trong dictionary hoặc có info_count cao hơn
        if question not in unique_questions or info_count > unique_questions[question]["info_count"]:
            unique_questions[question] = qa
    
    # Chuyển dictionary thành list các cặp Q&A duy nhất
    return list(unique_questions.values())

def main():
    json_file_path = "/Users/Tienbruse/tmdt/Backend/company-llm/data/data_20250329.json"  # Thay đường dẫn file thực tế
    data = load_data(json_file_path)
    
    # Danh sách Q&A (mỗi item gồm: question, answer, info_count)
    qa_pairs = []
    
    # 1. Tạo Q&A cho từng công ty
    for company in data:
        company_name = str(company.get("name", "")).strip()
        if not company_name:
            # Nếu công ty không có name thì bỏ qua
            continue
        
        # Câu hỏi
        question = f"Bạn hãy giới thiệu về công ty {company_name}?"
        
        # Câu trả lời
        answer, info_count = build_company_answer(company)
        if info_count > 0:
            # Chỉ thêm Q&A nếu có ít nhất 1 trường không rỗng
            qa_pairs.append({
                "question": question,
                "answer": answer,
                "info_count": info_count
            })
        
        # 2. Tạo Q&A cho từng sản phẩm của công ty
        products = company.get("products", [])
        for product in products:
            product_name = product.get("product_name", "").strip()
            if not product_name:
                continue  # Bỏ qua sản phẩm không có tên
            
            p_answer, p_count = build_product_answer(product)
            if p_count == 0:
                # Không có info thì bỏ qua
                continue
            
            p_question = f"Bạn hãy giới thiệu về sản phẩm {product_name}?"
            # Thêm cặp
            qa_pairs.append({
                "question": p_question,
                "answer": p_answer,
                "info_count": p_count
            })
    
    # 3. Loại bỏ các câu hỏi trùng lặp
    print(f"Tổng số Q&A trước khi loại bỏ trùng lặp: {len(qa_pairs)}")
    qa_pairs = remove_duplicate_questions(qa_pairs)
    print(f"Tổng số Q&A sau khi loại bỏ trùng lặp: {len(qa_pairs)}")
    
    # 4. Ưu tiên cặp Q&A có info_count cao (nhiều thông tin)
    # Sắp xếp giảm dần theo info_count
    qa_pairs.sort(key=lambda x: x["info_count"], reverse=True)
    
    # 5. Giới hạn số lượng cặp Q&A
    final_qa = qa_pairs[:MAX_QA_PAIRS]
    print(f"Lấy {len(final_qa)} cặp Q&A ưu tiên thông tin đầy đủ.")
    
    # 6. Ghi ra file JSON
    output_file = "/Users/Tienbruse/tmdt/Backend/company-llm/test/demo_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_qa, f, ensure_ascii=False, indent=2)
    
    # 7. In thử 5 cặp Q&A
    print("=== 5 CẶP Q&A MẪU ===")
    for i in range(min(5, len(final_qa))):
        print("Q:", final_qa[i]["question"])
        print("A:", final_qa[i]["answer"])
        print("(info_count =", final_qa[i]["info_count"], ")")
        print("---")

if __name__ == "__main__":
    main()