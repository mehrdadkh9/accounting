# src/business_logic/entities/product_entity.py
from dataclasses import dataclass, field
from typing import Optional
from .base_entity import BaseEntity
from src.constants import ProductType
from decimal import Decimal
@dataclass
class ProductEntity(BaseEntity):
    name: str                       # فیلد بدون مقدار پیش‌فرض
    product_type: ProductType       # فیلد بدون مقدار پیش‌فرض
    
    # فیلدهای با مقدار پیش‌فرض
    sku: Optional[str] = field(default=None)
    unit_price: Decimal = field(default_factory=lambda: Decimal("0.0"))
    stock_quantity: Decimal = field(default_factory=lambda: Decimal("0.0")) 
    unit_of_measure: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    is_active: bool = field(default=True)
    inventory_account_id: Optional[int] = None
    