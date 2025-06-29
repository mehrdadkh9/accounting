# src/business_logic/entities/setting_entity.py
from dataclasses import dataclass
from typing import Any

@dataclass
class SettingEntity: # No BaseEntity as key is the primary identifier and not necessarily int
    key: str  # The primary key for settings
    value: Any