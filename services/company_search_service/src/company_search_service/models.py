from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntityPayload(BaseModel):
    company_name: Optional[str] = Field(default=None)
    business_field: Optional[str] = Field(default=None)
    product_names: Optional[str] = Field(default=None)
    address: Optional[str] = Field(default=None)
    num_employees: Optional[int] = Field(default=None, ge=0)
    num_employees_operator: Optional[str] = Field(default=None, pattern="^(gte|lte)$")


class SearchRequest(BaseModel):
    entities: EntityPayload
    top_k: int = Field(default=5, ge=1, le=50)


class Product(BaseModel):
    product_name: Optional[str] = None
    product_description: Optional[str] = None


class CompanyResult(BaseModel):
    id: str
    company_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    tax_code: Optional[str] = None
    address: Optional[str] = None
    url: Optional[str] = None
    information: Optional[str] = None
    num_employees: Optional[int] = None
    products: List[Product] = Field(default_factory=list)


class SearchMeta(BaseModel):
    total: int
    took_ms: float


class SearchResponse(BaseModel):
    results: List[CompanyResult]
    meta: SearchMeta
    raw_hits: Optional[List[Dict[str, Any]]] = None


class IndexRequest(BaseModel):
    documents: List[Dict[str, Any]]
