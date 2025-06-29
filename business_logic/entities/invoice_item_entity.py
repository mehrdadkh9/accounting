from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal
from .base_entity import BaseEntity

@dataclass
class InvoiceItemEntity(BaseEntity):
    # --- فیلدهایی که در دیتابیس ذخیره می‌شوند ---
    invoice_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: Decimal = field(default_factory=lambda: Decimal("0.0"))
    unit_price: Decimal = field(default_factory=lambda: Decimal("0.0"))
    description: Optional[str] = None
    
    # --- فیلدهای نمایشی (از دیتابیس خوانده نمی‌شوند) ---
    product_name: Optional[str] = field(default=None, compare=False, repr=False, init=False)
    product_code: Optional[str] = field(default=None, compare=False, repr=False, init=False)
    unit_of_measure: Optional[str] = field(default=None, compare=False, repr=False, init=False)
    
    # --- تعریف مبلغ کل به عنوان یک property محاسباتی ---
    @property
    def total_item_amount(self) -> Decimal:
        """مبلغ کل این قلم را محاسبه و برمی‌گرداند."""
        qty = self.quantity if self.quantity is not None else Decimal("0.0")
        price = self.unit_price if self.unit_price is not None else Decimal("0.0")
        return qty * price
