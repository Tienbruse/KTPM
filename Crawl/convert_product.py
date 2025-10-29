import pandas as pd
import json
import os

def read_excel_files(file_paths):
    """Đọc nhiều file Excel và trả về list các DataFrame"""
    dataframes = []
    for file_path in file_paths:
        df = pd.read_excel(file_path)
        dataframes.append(df)
    return dataframes

def merge_dataframes(dataframes):
    """Hợp nhất các DataFrame và xử lý dữ liệu"""
    # Hợp nhất tất cả DataFrame
    merged_df = pd.concat(dataframes, ignore_index=True)
    
    # Chuyển đổi NaN thành None
    merged_df = merged_df.where(pd.notna(merged_df), None)
    
    # Chuyển DataFrame thành list of dictionaries
    result = merged_df.to_dict('records')
    return result

def normalize_data(data):
    """Chuẩn hóa dữ liệu theo schema mong muốn với tên cột tiếng Anh"""
    normalized_data = []
    
    # Ánh xạ các cột tiếng Việt sang tiếng Anh
    field_mapping = {
        'Tên sản phẩm': 'product_name',
        'Đơn vị sản xuất': 'name',
        'Địa chỉ': 'address',
        'SĐT': 'phone',
        'Mô tả': 'product_description',
        'Link chi tiết': 'product_link',
    }
    
    for item in data:
        # Tạo một dictionary trống cho mỗi mục
        normalized_item = {}
        
        # Cập nhật các giá trị từ dữ liệu gốc
        for key, value in item.items():
            # Ánh xạ tên cột sang tiếng Anh nếu có trong field_mapping
            normalized_key = field_mapping.get(key, key.lower().replace(' ', '_'))
            normalized_item[normalized_key] = value
        
        normalized_data.append(normalized_item)
    
    return normalized_data

def save_to_json(data, output_file):
    """Lưu dữ liệu vào file JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    # Danh sách các file Excel (thay đổi đường dẫn theo file của bạn)
    excel_files = [
        '/Users/Tienbruse/tmdt/Chatbot-test/Crawl/merged_hatiplaza.xlsx',
    ]
    
    # Đọc các file Excel
    print("Đang đọc các file Excel...")
    dataframes = read_excel_files(excel_files)
    
    # Hợp nhất dữ liệu
    print("Đang hợp nhất dữ liệu...")
    merged_data = merge_dataframes(dataframes)
    
    # Chuẩn hóa dữ liệu theo schema
    print("Đang chuẩn hóa dữ liệu...")
    normalized_data = normalize_data(merged_data)
    
    # Lưu vào file JSON
    output_file = 'product_info.json'
    print(f"Đang lưu vào file {output_file}...")
    save_to_json(normalized_data, output_file)
    
    print(f"Đã hoàn thành! File JSON đã được tạo tại: {os.path.abspath(output_file)}")
    print(f"Tổng số công ty: {len(normalized_data)}")

if __name__ == "__main__":
    main()