# src/business_logic/entities/inventory_movement_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from decimal import Decimal
from .base_entity import BaseEntity
from ...constants import InventoryMovementType, ReferenceType

@dataclass
class InventoryMovementEntity(BaseEntity):
    # این فیلدها همیشه باید مقدار داشته باشند
    product_id: int
    movement_date: datetime
    # FIX: تغییر نوع داده به Decimal برای هماهنگی با کل برنامه
    quantity_change: Decimal
    movement_type: InventoryMovementType
    
    # این فیلدها می‌توانند در دیتابیس NULL باشند
    reference_id: Optional[int] = field(default=None)
    reference_type: Optional[ReferenceType] = field(default=None)
    description: Optional[str] = field(default=None)
