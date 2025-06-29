# src/business_logic/entities/loan_installment_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import date
from .base_entity import BaseEntity
from src.constants import PaymentMethod

@dataclass
class LoanInstallmentEntity(BaseEntity):
    loan_id: int # Foreign Key to LoanEntity
    due_date: date
    installment_amount: float # Total amount for this installment
    fiscal_year_id: Optional[int] = field(default=None) # Foreign Key to FiscalYearEntity
    
    paid_date: Optional[date] = field(default=None)
    principal_amount: float = field(default=0.0) # Portion of installment that is principal
    interest_amount: float = field(default=0.0) # Portion of installment that is interest
    payment_method: Optional[PaymentMethod] = field(default=None) # Enum
    description: Optional[str] = field(default=None)
    # transaction_id: Optional[int] = field(default=None) # FK to FinancialTransaction if payment recorded