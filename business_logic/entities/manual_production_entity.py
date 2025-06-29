# src/business_logic/entities/manual_production_entity.py
from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal
from datetime import date
from .base_entity import BaseEntity
from .consumed_material_entity import ConsumedMaterialEntity # <<< وارد کردن موجودیت اقلام مصرفی

@dataclass
class ManualProductionEntity(BaseEntity):
    production_date: date = field(default_factory=date.today)
    finished_product_id: Optional[int] = None      # شناسه محصول نهایی تولید شده
    quantity_produced: Decimal = field(default_factory=lambda: Decimal("0.0"))
    description: Optional[str] = None
    # fiscal_year_id: Optional[int] = None # اگر نیاز به اتصال به سال مالی دارید

    # این لیست در خود جدول ManualProduction ذخیره نمی‌شود، بلکه برای کار با آبجکت در برنامه است.
    # اقلام مصرفی به صورت جداگانه در جدول ConsumedMaterial با manual_production_id ذخیره می‌شوند.
    consumed_items: List[ConsumedMaterialEntity] = field(default_factory=list, compare=False, repr=False, init=False)
    
    # فیلدهای نمایشی
    finished_product_name: Optional[str] = field(default=None, compare=False, repr=False, init=False)
    finished_product_sku: Optional[str] = field(default=None, compare=False, repr=False, init=False)