# src/business_logic/entities/bom_item_entity.py (فرض می‌کنیم در این فایل است)
from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal
from src.business_logic.entities.base_entity import BaseEntity

@dataclass
class BomItemEntity(BaseEntity): # نام کلاس با حروف بزرگ اول هر کلمه
    id: Optional[int] = None
    bom_id: Optional[int] = None
    component_product_id: Optional[int] = None  # <<< این نام مورد انتظار است
    quantity_required: Decimal = Decimal("0.0") # <<< این نام مورد انتظار است
    notes: Optional[str] = None                 # <<< این نام مورد انتظار است
    
    # فیلدهای اضافی برای نمایش که مستقیماً از دیتابیس خوانده نمی‌شوند
    component_product_name: Optional[str] = field(default=None, compare=False, repr=False)
    component_product_code: Optional[str] = field(default=None, compare=False, repr=False)
    component_unit_of_measure: Optional[str] = field(default=None, compare=False, repr=False)