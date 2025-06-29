# src/business_logic/entities/financial_transaction_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime # Using datetime for more precision if needed, or just date
from .base_entity import BaseEntity
from src.constants import FinancialTransactionType, ReferenceType
from decimal import Decimal
@dataclass
class FinancialTransactionEntity(BaseEntity):
    transaction_date: datetime
    account_id: int # Foreign Key to AccountEntity
    transaction_type: FinancialTransactionType # Enum: Income, Expense, Transfer
    amount: Decimal = Decimal("0.0")
    fiscal_year_id: Optional[int] = field(default=None) # Foreign Key to FiscalYearEntity

    description: Optional[str] = field(default=None)
    category: Optional[str] = field(default=None) # e.g., 'Salary', 'Utilities'
    reference_id: Optional[int] = field(default=None) # FK to Invoice, Payment, Check etc.
    reference_type: Optional[ReferenceType] = field(default=None) # Enum: Invoice, Payment, etc.