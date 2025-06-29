# src/business_logic/entities/material_receipt_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import date # یا from datetime import date, datetime اگر هر دو لازم است
from .base_entity import BaseEntity

@dataclass
class MaterialReceiptEntity(BaseEntity):
    receipt_date: date
    person_id: int # Foreign Key to PersonEntity (Supplier)
    product_id: int # Foreign Key to ProductEntity
    quantity_received: float
    fiscal_year_id: Optional[int] = field(default=None) # Foreign Key to FiscalYearEntity

    purchase_order_id: Optional[int] = field(default=None) # Optional FK to PurchaseOrderEntity
    purchase_order_item_id: Optional[int] = field(default=None) # Optional FK to link to a specific PO line item
    unit_price: Optional[float] = field(default=None) # Actual price at receipt, can be from PO or entered
    description: Optional[str] = field(default=None)
    # 'id' از BaseEntity به ارث برده می‌شود و باید به صورت keyword argument پاس داده شود