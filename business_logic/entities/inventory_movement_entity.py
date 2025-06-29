# src/business_logic/entities/inventory_movement_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from .base_entity import BaseEntity
from src.constants import InventoryMovementType, ReferenceType
from decimal import Decimal

@dataclass
class InventoryMovementEntity(BaseEntity):
    # این فیلدها همیشه باید مقدار داشته باشند
    product_id: int
    quantity_change: Decimal
    movement_type: InventoryMovementType
    
    # این فیلد یک مقدار پیش‌فرض دارد
    movement_date: datetime = field(default_factory=datetime.now)

    # این فیلدها می‌توانند در دیتابیس NULL باشند
    reference_id: Optional[int] = None
    reference_type: Optional[ReferenceType] = None
    description: Optional[str] = None
