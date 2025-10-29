import json
import os

def read_json_files(file_paths):
    """Đọc nhiều file JSON và trả về danh sách dữ liệu"""
    all_data = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Nếu dữ liệu là danh sách, thêm tất cả phần tử vào all_data
                if isinstance(data, list):
                    all_data.extend(data)
                # Nếu dữ liệu là dictionary, thêm trực tiếp vào all_data
                elif isinstance(data, dict):
                    all_data.append(data)
                else:
                    print(f"Cảnh báo: File {file_path} chứa dữ liệu không phải list hoặc dict, đã bỏ qua.")
        except Exception as e:
            print(f"Lỗi khi đọc file {file_path}: {str(e)}")
    return all_data

def save_to_json(data, output_file):
    """Lưu dữ liệu vào file JSON"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Đã lưu dữ liệu vào file: {os.path.abspath(output_file)}")
    except Exception as e:
        print(f"Lỗi khi lưu file {output_file}: {str(e)}")

def main():
    # Danh sách các file JSON cần hợp nhất (thay đổi đường dẫn theo file của bạn)
    json_files = [
        '/Users/Tienbruse/tmdt/Chatbot-test/Crawl/companies_data.json',
        '/Users/Tienbruse/tmdt/Chatbot-test/Crawl/company_info.json',
        '/Users/Tienbruse/tmdt/Chatbot-test/Crawl/product_info.json',
        '/Users/Tienbruse/tmdt/Chatbot-test/Crawl/companies_data_dnm.json',
        # Thêm các file khác nếu cần
    ]
    
    # Đọc tất cả file JSON
    print("Đang đọc các file JSON...")
    merged_data = read_json_files(json_files)
    
    # Lưu dữ liệu hợp nhất vào file mới
    output_file = 'data_latest1.json'
    print(f"Đang hợp nhất và lưu vào file {output_file}...")
    save_to_json(merged_data, output_file)
    
    print(f"Đã hoàn thành! Tổng số bản ghi: {len(merged_data)}")

if __name__ == "__main__":
    main()