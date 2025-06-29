# src/data_access/financial_transactions_repository.py

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.financial_transaction_entity import FinancialTransactionEntity
from src.constants import FinancialTransactionType, ReferenceType, DATETIME_FORMAT
import logging
from decimal import Decimal
logger = logging.getLogger(__name__)

class FinancialTransactionsRepository(BaseRepository[FinancialTransactionEntity]):
    def __init__(self, db_manager: DatabaseManager):
        
        super().__init__(db_manager=db_manager, 
                         model_type=FinancialTransactionEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="financial_transactions") 
    def _entity_from_row(self, row: Dict[str, Any]) -> 'FinancialTransactionEntity':
        from src.business_logic.entities.financial_transaction_entity import FinancialTransactionEntity # وارد کردن محلی

        if row is None:
            raise ValueError("Input row cannot be None for FinancialTransactionEntity")
        try:
            transaction_date_str = row.get('transaction_date')
            reference_type_str = row.get('reference_type')

            # استفاده از fromisoformat برای خواندن تاریخ و زمان با فرمت ISO (شامل T)
            parsed_transaction_date = None
            if transaction_date_str:
                try:
                    # fromisoformat می‌تواند فرمت‌های مختلف ISO شامل 'T' را مدیریت کند
                    parsed_transaction_date = datetime.fromisoformat(transaction_date_str)
                except ValueError:
                    # اگر fromisoformat شکست خورد، به عنوان fallback سعی می‌کنیم با فرمت قبلی بخوانیم
                    # این حالت نباید رخ دهد اگر همه تاریخ‌ها با isoformat ذخیره شده باشند
                    logger.warning(f"Could not parse date '{transaction_date_str}' with fromisoformat, trying DATETIME_FORMAT for FT ID {row.get('id')}")
                    try:
                        parsed_transaction_date = datetime.strptime(transaction_date_str, DATETIME_FORMAT)
                    except ValueError as e_strptime:
                        logger.error(f"Failed to parse transaction_date '{transaction_date_str}' with all known formats for FT ID {row.get('id')}: {e_strptime}")
                        # می‌توانید خطا ایجاد کنید یا None برگردانید یا تاریخ پیش‌فرض بگذارید
                        raise ValueError(f"فرمت تاریخ تراکنش نامعتبر است: {transaction_date_str}") from e_strptime


            return FinancialTransactionEntity(
                id=row['id'],
                transaction_date=parsed_transaction_date, # <<< استفاده از تاریخ تجزیه شده # type: ignore
                account_id=row['account_id'],
                transaction_type=FinancialTransactionType(row['transaction_type']),
                amount=Decimal(str(row.get('amount', '0.0'))),
                description=row.get('description'),
                category=row.get('category'),
                reference_id=row.get('reference_id'),
                reference_type=ReferenceType(reference_type_str) if reference_type_str else None,
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except KeyError as e:
            logger.error(f"KeyError when creating FinancialTransactionEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: 
            logger.error(f"ValueError when creating FinancialTransactionEntity: {e}. Row: {row}")
            raise

    # ... (other methods remain the same) ...
    def get_by_account_id(self, account_id: int) -> List[FinancialTransactionEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE account_id = ? ORDER BY transaction_date DESC"
        rows = self.db_manager.fetch_all(query, (account_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_reference(self, reference_id: int, reference_type: ReferenceType) -> List[FinancialTransactionEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE reference_id = ? AND reference_type = ?"
        rows = self.db_manager.fetch_all(query, (reference_id, reference_type.value))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_fiscal_year_id(self, fiscal_year_id: int) -> List[FinancialTransactionEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE fiscal_year_id = ? ORDER BY transaction_date DESC"
        rows = self.db_manager.fetch_all(query, (fiscal_year_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]