import json
from collections import OrderedDict

# Đường dẫn tới file JSON đầu vào
input_file = '/Users/Tienbruse/tmdt/Backend/company-llm/data/data_20250329.json'
# Đường dẫn tới file JSON đầu ra sau khi loại bỏ trùng lặp và filter thêm
output_file = '/Users/Tienbruse/tmdt/Backend/company-llm/data/data_20250329_clean_1.json'

# Đọc dữ liệu từ file JSON
with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

cleaned_data = []
total_products_before = 0
total_products_after = 0
removed_companies = 0

for company in data:
    # Lọc bỏ công ty có tên chứa "THCS" (case-insensitive)
    company_name = company.get('name', '')
    if 'thcs' in company_name.lower():
        removed_companies += 1
        continue

    if 'ubnd' in company_name.lower():
        removed_companies += 1
        continue

    # Đếm info_count
    info_count = 0
    if company.get('tax_code'):
        info_count += 1
    if company.get('address'):
        info_count += 1
    if company.get('email'):
        info_count += 1
    if company.get('phone'):
        info_count += 1
    if company.get('employees'):
        info_count += 1
    if company.get('business_fields'):
        info_count += 1
    if company.get('url'):
        info_count += 1
    if company.get('introduction'):
        info_count += 3
    if company.get('products'):
        info_count += 4
    if company.get('product_name'):
        info_count += 1
    if company.get('product_link'):
        info_count += 1
    if company.get('product_description'):
        info_count += 1
    
    if info_count < 4:
        removed_companies += 1
        continue


    # Lấy danh sách sản phẩm của công ty
    products = company.get('products', [])
    total_products_before += len(products)

    # Sử dụng OrderedDict để loại bỏ trùng lặp dựa trên product_name và product_description
    unique_products = OrderedDict()
    for product in products:
        product_name = product.get('product_name', '')
        product_desc = product.get('product_description', None)
        key = (product_name, str(product_desc))
        if key not in unique_products:
            unique_products[key] = product

    unique_product_list = list(unique_products.values())
    total_products_after += len(unique_product_list)

    company['products'] = unique_product_list
    cleaned_data.append(company)

# Ghi dữ liệu đã làm sạch vào file mới
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

# In kết quả
print(f"Tổng số công ty ban đầu: {len(data)}")
print(f"Số công ty bị loại (tên chứa 'THCS'): {removed_companies}")
print(f"Số công ty sau khi loại bỏ: {len(cleaned_data)}")
print(f"Tổng số sản phẩm ban đầu: {total_products_before}")
print(f"Tổng số sản phẩm sau khi loại bỏ trùng lặp: {total_products_after}")
