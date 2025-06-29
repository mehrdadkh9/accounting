# src/business_logic/entities/check_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import date
from .base_entity import BaseEntity
from src.constants import CheckType, CheckStatus

@dataclass
class CheckEntity(BaseEntity):
    check_number: str
    amount: float
    issue_date: date
    due_date: date
    person_id: int # Foreign Key to PersonEntity (drawer for issued, beneficiary for received)
    account_id: int # Foreign Key to AccountEntity (bank account for issued checks, or target for received)
    check_type: CheckType # Enum: Received, Issued
    status: CheckStatus # Enum
    fiscal_year_id: Optional[int] = field(default=None) # Foreign Key to FiscalYearEntity

    description: Optional[str] = field(default=None)
    invoice_id: Optional[int] = field(default=None) # Optional link to an invoice
    purchase_order_id: Optional[int] = field(default=None) # Optional link to a PO
    person_name: Optional[str] = field(default=None, init=False, compare=False, repr=False)
    bank_account_name: Optional[str] = field(default=None, init=False, compare=False, repr=False)