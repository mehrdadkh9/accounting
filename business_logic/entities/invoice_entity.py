# src/business_logic/entities/invoice_entity.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date
from .base_entity import BaseEntity
from src.constants import InvoiceType,InvoiceStatus
from .invoice_item_entity import InvoiceItemEntity
from decimal import Decimal
@dataclass
class InvoiceEntity(BaseEntity):
    invoice_number: str
    invoice_date: date
    person_id: int # Foreign Key to PersonEntity (Customer for Sale, Supplier for Purchase)
    invoice_type: InvoiceType # Enum: Sale, Purchase
    
    # ADD is_paid as a regular field
    is_paid: bool = field(default=False) # Matches DB column
    status: InvoiceStatus = field(default=InvoiceStatus.ISSUED)
    fiscal_year_id: Optional[int] = field(default=None) # Foreign Key to FiscalYearEntity
    due_date: Optional[date] = field(default=None)
    total_amount: Decimal = field(default_factory=lambda: Decimal("0.0"))
    paid_amount: Decimal = field(default_factory=lambda: Decimal("0.0"))
    description: Optional[str] = field(default=None)
    items: List[InvoiceItemEntity] = field(default_factory=list)

    @property
    def remaining_amount(self) -> Decimal:
        # Ensure total_amount is positive to avoid issues with zero-amount invoices
        # if self.total_amount <= 0:
        #     return 0.0
        return self.total_amount - self.paid_amount

    # The original @property is_paid is removed.
    # The InvoiceManager will be responsible for updating the is_paid field
    # based on remaining_amount.
    # Alternatively, if you want is_paid to ALWAYS be calculated, then the DB column
    # for is_paid is redundant and should not be set from _entity_from_row.
    # For now, making it a settable field is more consistent with having a DB column.