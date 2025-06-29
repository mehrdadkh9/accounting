# src/business_logic/entities/base_entity.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class BaseEntity:
    id: Optional[int] = field(default=None, kw_only=True) # kw_only=True makes it a keyword-only argument