# src/business_logic/entities/consumed_material_entity.py
from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal
from .base_entity import BaseEntity

@dataclass
class ConsumedMaterialEntity(BaseEntity):
    manual_production_id: Optional[int] = None  # شناسه رکورد تولید دستی والد
    component_product_id: Optional[int] = None  # شناسه ماده اولیه/جزء مصرف شده
    quantity_consumed: Decimal = field(default_factory=lambda: Decimal("0.0"))
    notes: Optional[str] = None
    
    # فیلدهای نمایشی (از دیتابیس خوانده نمی‌شوند، توسط Manager پر می‌شوند)
    component_product_name: Optional[str] = field(default=None, compare=False, repr=False, init=False)
    component_product_code: Optional[str] = field(default=None, compare=False, repr=False, init=False)
    component_unit_of_measure: Optional[str] = field(default=None, compare=False, repr=False, init=False)
    # می‌توانید هزینه واحد این ماده در زمان مصرف را هم اینجا اضافه کنید اگر لازم است
    # unit_cost_at_consumption: Optional[Decimal] = field(default=None, compare=False, repr=False, init=False)