# src/business_logic/entities/purchase_order_item_entity.py
from dataclasses import dataclass
from .base_entity import BaseEntity

@dataclass
class PurchaseOrderItemEntity(BaseEntity):
    purchase_order_id: int # Foreign Key to PurchaseOrderEntity
    product_id: int # Foreign Key to ProductEntity (Raw Material or other product)
    ordered_quantity: float
    unit_price: float # Expected price
    total_item_amount: float
   