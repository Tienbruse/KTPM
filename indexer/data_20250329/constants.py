TEXT_FIELDS = [
    "name",
    "tax_code",
    "email",
    "phone",
    "url",
    "introduction",
    "business_field"
]

ACCENT_FIELDS = [
    "address",
]
ID_FIELD = "no"

NUM_FIELDS = [
    "employees",
]

NESTED_FIELDS = [
    {
        "key": "products",
        "sub_keys": [
            {
                "name": "product_name",
                "value": {
                    "type": "text",
                },
            },
            {
                "name": "product_link",
                "value": {
                    "type": "text",
                },
            },
            {
                "name": "product_description",
                "value": {
                    "type": "text",
                },
            },
        ],
    },
]
