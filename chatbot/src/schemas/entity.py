from typing import Optional

from pydantic import BaseModel, Field

from src.constants.prompts import FUNCTION_ENTITES


class Entity(BaseModel):
    """Information about a restaurant."""

    company_name: Optional[str] = Field(
        default=None, description=FUNCTION_ENTITES["company_name"]
    )
    address: Optional[str] = Field(
        default=None,
        description=FUNCTION_ENTITES["address"],
    )
    business_field: Optional[str] = Field(
        default=None,
        description=FUNCTION_ENTITES["business_field"],
    )
    num_employees: Optional[int] = Field(
        default=None,
        description=FUNCTION_ENTITES["num_employees"],
        ge=0,
    )
    num_employees_operator: Optional[str] = Field(
        default=None,
        description=FUNCTION_ENTITES["num_employees_operator"],
        pattern="^(gte|lte)$",
    )
    product_names: Optional[str] = Field(
        default=None,
        description=FUNCTION_ENTITES["product_names"],
    )

    # @field_validator('product_names', mode='after')
    # @classmethod
    # def ensure_list(cls, value: str) -> List[str]:
    #     values = value.split(",")
    #     values = [v.strip() for v in values]
    #     return values
