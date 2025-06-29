# src/business_logic/entities/employee_entity.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import date
from .base_entity import BaseEntity # Employee specific ID, or can use person_id as PK if 1-to-1 is strict.
                                    # Using own ID for flexibility if Employee might have other non-Person aspects.

@dataclass
class EmployeeEntity(BaseEntity):
    person_id: int # Foreign Key to PersonEntity
    national_id: Optional[str] = field(default=None)
    position: Optional[str] = field(default=None)
    base_salary: float = field(default=0.0)
    hire_date: Optional[date] = field(default=None)
    is_active: bool = field(default=True)
    # Name and contact_info are in the associated PersonEntity