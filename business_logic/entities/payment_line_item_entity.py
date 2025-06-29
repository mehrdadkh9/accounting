# src/business_logic/entities/payment_line_item_entity.py
from dataclasses import dataclass, field
from typing import Optional
from .base_entity import BaseEntity
from src.constants import PaymentMethod, AccountType # AccountType برای حساب بانک/صندوق
from decimal import Decimal
@dataclass
class PaymentLineItemEntity(BaseEntity):
    payment_header_id: int
    payment_method: PaymentMethod
    amount: Decimal # Use Decimal for financial amounts
    account_id: Optional[int] = field(default=None)  # Our bank/cash account for cash/card/transfer, or bank for check
    check_id: Optional[int] = field(default=None)    # Link to CheckEntity if method is CHECK or ENDORSE_CHECK
    description: Optional[str] = field(default=None)
    target_account_id: Optional[int] = field(default=None)

    # --- Add this new field ---
    target_account_id: Optional[int] = field(default=None) # For direct Dr/Cr to Expense/Income accounts
    # --- End of new field ---
    