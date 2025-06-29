# src/business_logic/entities/payment_header_entity.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date
from .base_entity import BaseEntity
from .payment_line_item_entity import PaymentLineItemEntity # وارد کردن قلم پرداخت
from decimal import Decimal
from src.constants  import PaymentType
# PaymentDirection را می‌توانیم به constants.py منتقل کنیم اگر در جای دیگری هم لازم است
# from enum import Enum
# class PaymentDirection(Enum):
#     RECEIPT = "دریافت"  # دریافت از مشتری یا سایر درآمدها
#     DISBURSEMENT = "پرداخت" # پرداخت به تامین‌کننده یا سایر هزینه‌ها

@dataclass
class PaymentHeaderEntity(BaseEntity):
    payment_date: date
    person_id: Optional[int] = None
    total_amount: Decimal = field(default_factory=lambda: Decimal("0.0"))
    description: Optional[str] = None
    invoice_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    fiscal_year_id: Optional[int] = None
    is_direct_posting: bool = False # <<< این فیلد اضافه شود

    # <<< ADD THIS LINE
    payment_type: PaymentType = PaymentType.PAYMENT 

    # This field is for holding related items, not for the database
    line_items: List[PaymentLineItemEntity] = field(default_factory=list, init=False, compare=False)
    person_name: Optional[str] = field(default=None, init=False, compare=False, repr=False) # <<< این فیلد اضافه شود
