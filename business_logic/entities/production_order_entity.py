# src/business_logic/entities/production_order_entity.py
from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
from src.business_logic.entities.base_entity import BaseEntity
from src.constants import ProductionOrderStatus # این Enum را باید در constants.py تعریف کنید

@dataclass
class ProductionOrderEntity(BaseEntity):
    id: Optional[int] = None
    order_number: Optional[str] = None # شماره دستور تولید (می‌تواند خودکار تولید شود)
    product_id: Optional[int] = None # شناسه محصول نهایی که باید تولید شود
    bom_id: Optional[int] = None # شناسه BOM ای که برای این تولید استفاده می‌شود
    quantity_to_produce: Decimal = Decimal("0.0") # مقدار برنامه‌ریزی شده برای تولید
    quantity_produced: Decimal = Decimal("0.0") # مقدار واقعی تولید شده تاکنون
    order_date: date = field(default_factory=date.today)
    start_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    status: ProductionOrderStatus = ProductionOrderStatus.PENDING # وضعیت (مثلاً: در انتظار، در حال تولید، تکمیل شده، لغو شده)
    description: Optional[str] = None
    fiscal_year_id: Optional[int] = None
    
    # فیلدهای نمایشی (از دیتابیس خوانده نمی‌شوند)
    product_name: Optional[str] = field(default=None, compare=False, repr=False)
    bom_name: Optional[str] = field(default=None, compare=False, repr=False)
    # اقلام مواد اولیه مصرفی واقعی می‌توانند در جدول جداگانه‌ای ذخیره شوند یا در اینجا به صورت لیست باشند
    # consumed_materials: List[Dict[str, Any]] = field(default_factory=list)