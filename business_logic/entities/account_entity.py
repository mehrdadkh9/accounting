# src/business_logic/entities/account_entity.py
from dataclasses import dataclass, field
from typing import Optional,List
from .base_entity import BaseEntity
from src.constants import AccountType
from decimal import Decimal

@dataclass
class AccountEntity(BaseEntity):
    name: str                       # نام حساب
    type: AccountType               # نوع اصلی حساب (دارایی، بدهی و...)

    parent_id: Optional[int] = field(default=None) # شناسه حساب والد
    balance: Decimal = field(default_factory=lambda: Decimal("0.0"))
    # 'id' از BaseEntity به ارث برده می‌شود
    children: List['AccountEntity'] = field(default_factory=list, init=False, compare=False, repr=False)
