from constants import ACCENT_FIELDS, NESTED_FIELDS, NUM_FIELDS, TEXT_FIELDS


def get_properties():
    properties = {}
    properties["info_count"] = {
        "type": "integer"
    }
    for field_name in TEXT_FIELDS:
        properties.update({field_name: {"type": "text"}})
    for field_name in NUM_FIELDS:
        properties.update({field_name: {"type": "integer"}})
    for field_name in ACCENT_FIELDS:
        properties.update(
            {
                field_name: {
                    "type": "text",
                    "fields": {
                        "with_accent_normalized_analyzer": {
                            "type": "text",
                            "analyzer": "with_accent_normalized_analyzer",
                            "search_analyzer": "with_accent_normalized_analyzer",
                        },
                        "without_accent_normalized_analyzer": {
                            "type": "text",
                            "analyzer": "without_accent_normalized_analyzer",
                            "search_analyzer": "without_accent_normalized_analyzer",
                        },
                    },
                    "analyzer": "standard",
                    "search_analyzer": "standard",
                }
            }
        )
    for field in NESTED_FIELDS:
        properties.update(
            {
                field["key"]: {
                    "type": "nested",
                    "properties": {
                        sub_key["name"]: sub_key["value"]
                        for sub_key in field["sub_keys"]
                    },
                },
            }
        )
    return properties


def get_settings():
    settings = {
        "analysis": {
            # "filter": {
            #     # Synonym filter chỉ mở rộng 1 chiều từ 'đặc sản' thành các sản phẩm cụ thể
            #     "specialty_synonym_filter": {
            #         "type": "synonym",
            #         "synonyms_path": "analysis/semantic.txt",
            #         "expand": False,
            #     }
            # },
            "analyzer": {
                "with_accent_normalized_analyzer": {
                    "filter": ["lowercase", "trim"],
                    "tokenizer": "standard",
                },
                "without_accent_normalized_analyzer": {
                    "filter": ["lowercase", "trim", "asciifolding"],
                    "tokenizer": "standard",
                },
            }
        }
    }
    return settings