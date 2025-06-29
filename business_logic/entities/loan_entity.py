# src/business_logic/entities/loan_entity.py
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import date
from .base_entity import BaseEntity
from src.constants import LoanStatus, LoanDirectionType # Added LoanDirectionType
from .loan_installment_entity import LoanInstallmentEntity # Assuming this is already defined

@dataclass
class LoanEntity(BaseEntity):
    person_id: int 
    loan_direction: LoanDirectionType # <<< NEW FIELD: Is it a loan we GAVE or RECEIVED?
    loan_amount: float
    interest_rate: float # Annual interest rate (e.g., 0.05 for 5%)
    start_date: date
    end_date: date # Maturity date
    installment_amount: float # Regular payment amount
    number_of_installments: int # <<< NEW FIELD: Total number of installments
    status: LoanStatus 
    fiscal_year_id: Optional[int] = field(default=None)
    
    description: Optional[str] = field(default=None)
    # Account involved in initial disbursement/receipt
    # For GIVEN loan, this is the account from which we paid (e.g. our bank)
    # For RECEIVED loan, this is the account into which we received funds (e.g. our bank)
    related_account_id: Optional[int] = field(default=None) 
    
    installments: List[LoanInstallmentEntity] = field(default_factory=list) # Populated by LoanManager