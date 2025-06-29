# src/business_logic/entities/payroll_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import date
from .base_entity import BaseEntity

@dataclass
class PayrollEntity(BaseEntity):
    employee_id: int # Foreign Key to EmployeeEntity
    pay_period_start: date
    pay_period_end: date
    gross_salary: float
    deductions: float = field(default=0.0)
    # net_salary is a @property
    payment_date: Optional[date] = field(default=None)
    paid_by_account_id: Optional[int] = field(default=None) # FK to AccountEntity
    is_paid: bool = field(default=False)
    description: Optional[str] = field(default=None)
    transaction_id: Optional[int] = field(default=None) # FK to FinancialTransaction if payment recorded
    fiscal_year_id: Optional[int] = field(default=None) # Foreign Key to FiscalYearEntity

    @property
    def net_salary(self) -> float:
        return self.gross_salary - self.deductions