# src/business_logic/entities/fiscal_year_entity.py
from dataclasses import dataclass
from typing import Optional
from datetime import date
from .base_entity import BaseEntity
from src.constants import FiscalYearStatus

@dataclass
class FiscalYearEntity(BaseEntity):
    name: str
    start_date: date
    end_date: date
    status: FiscalYearStatus # Enum: Open, Closed