import json

def group_by_company(data):
    grouped_data = {}
    for item in data:
        company_name = item.get("name")
        if company_name not in grouped_data:
            grouped_data[company_name] = {
                "name": company_name,
                "tax_code": item.get("tax_code"),
                "address": item.get("address"),
                "email": item.get("email"),
                "phone": item.get("phone"),
                "employees": item.get("employees"),
                "business_field": item.get("business_fields"),
                "url": item.get("url"),
                "introduction": item.get("introduction"),
                "products": []
            }
        product = {
            "product_name": item.get("product_name"),
            "product_link": item.get("product_link"),
            "product_description": item.get("product_description")
        }
        if product["product_name"]:  # Chỉ thêm nếu có product_name
            grouped_data[company_name]["products"].append(product)
    
    return list(grouped_data.values())

# Đọc file JSON
with open('/Users/Tienbruse/tmdt/Backend/company-llm/Crawl/data_latest1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Nhóm dữ liệu
grouped_data = []
grouped_data = group_by_company(data)

# Lưu lại file mới
with open('data_latest_3.json', 'w', encoding='utf-8') as f:
    json.dump(grouped_data, f, ensure_ascii=False, indent=4)