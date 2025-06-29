# src/business_logic/entities/bom_entity.py
from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal
from datetime import date
from src.business_logic.entities.base_entity import BaseEntity
from src.business_logic.entities.product_entity import ProductEntity # برای نوع محصول نهایی و کامپوننت
from src.business_logic.entities.bom_item_entity import BomItemEntity

@dataclass
class BOMEntity(BaseEntity):
    id: Optional[int] = None
    name: str = ""  # نام یا کد BOM، مثلاً "BOM استاندارد برای محصول X"
    product_id: Optional[int] = None  # شناسه محصول نهایی که این BOM برای آن است
    quantity_produced: Decimal = Decimal("1.0") # این BOM برای تولید چه تعداد از محصول نهایی است (معمولاً ۱)
    description: Optional[str] = None
    is_active: bool = True # آیا این BOM فعال است؟ (ممکن است چندین نسخه BOM برای یک محصول وجود داشته باشد)
    creation_date: date = field(default_factory=date.today)
    last_modified_date: Optional[date] = None
    items: List[BomItemEntity] = field(default_factory=list, compare=False, repr=False) # لیست اقلام BOM
    
    # برای نمایش بهتر، می‌توان نام محصول نهایی را هم اضافه کرد
    product_name: Optional[str] = field(default=None, compare=False, repr=False)