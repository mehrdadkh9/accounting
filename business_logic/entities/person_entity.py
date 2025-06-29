# src/business_logic/entities/person_entity.py
from dataclasses import dataclass, field
from typing import Optional
from .base_entity import BaseEntity
from src.constants import PersonType

@dataclass
class PersonEntity(BaseEntity):
    name: str
    person_type: PersonType # Enum: Customer, Supplier, Employee
    contact_info: Optional[str] = field(default=None)