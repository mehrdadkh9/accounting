# src/business_logic/entities/purchase_order_entity.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date
from .base_entity import BaseEntity
from src.constants import PurchaseOrderStatus # مطمئن شوید PurchaseOrderStatus در constants.py تعریف شده
from .purchase_order_item_entity import PurchaseOrderItemEntity

@dataclass
class PurchaseOrderEntity(BaseEntity):
    order_number: str
    person_id: int # کلید خارجی به PersonEntity (تامین‌کننده)
    order_date: date
    status: PurchaseOrderStatus # Enum
    
    # فیلدهای با مقدار پیش‌فرض
    total_amount_expected: float = field(default=0.0)
    paid_amount: float = field(default=0.0)
    received_amount: float = field(default=0.0) # ارزش ریالی کالاهای دریافت شده

    description: Optional[str] = field(default=None)
    fiscal_year_id: Optional[int] = field(default=None) # کلید خارجی به FiscalYearEntity
    
    items: List[PurchaseOrderItemEntity] = field(default_factory=list) # این لیست برای راحتی است و مستقیماً در ستون دیتابیس ذخیره نمی‌شود
    # 'id' از BaseEntity به ارث برده می‌شود و چون kw_only=True است، ترتیبش نسبت به اینها مهم نیست.