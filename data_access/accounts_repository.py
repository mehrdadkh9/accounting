# src/data_access/accounts_repository.py

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from decimal import Decimal # <<< اضافه کردن import برای Decimal

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.constants import AccountType
import logging

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.business_logic.entities.account_entity import AccountEntity

class AccountsRepository(BaseRepository['AccountEntity']): 
    def __init__(self, db_manager: DatabaseManager):
        # برای پاس دادن خود کلاس AccountEntity به BaseRepository، نیاز به import آن داریم.
        # اگر import در سطح ماژول باعث circular import می‌شود، این import را اینجا انجام می‌دهیم.
        from src.business_logic.entities.account_entity import AccountEntity 
        super().__init__(db_manager=db_manager, 
                         model_type=AccountEntity, 
                         table_name="accounts") 

    def _entity_from_row(self, row: Dict[str, Any]) -> 'AccountEntity':
        from src.business_logic.entities.account_entity import AccountEntity 

        if row is None:
            raise ValueError("Input row cannot be None for AccountEntity")
        try:
            account_type_value = row.get('type')
            account_type_enum = None
            if account_type_value is not None:
                try:
                    account_type_enum = AccountType(account_type_value)
                except ValueError:
                    logger.error(f"Invalid AccountType value '{account_type_value}' from database for account ID {row.get('id')}. Setting type to None or a default.")
                    # می‌توانید یک مقدار پیش‌فرض یا None برای type در نظر بگیرید یا خطا را raise کنید
                    # account_type_enum = None # یا AccountType.UNKNOWN اگر چنین عضوی دارید

            return AccountEntity(
                id=row.get('id'), # بهتر است از .get برای جلوگیری از KeyError استفاده شود
                name=row.get('name', ''), # مقدار پیش‌فرض اگر name وجود ندارد
                type=account_type_enum, # مقدار تبدیل شده یا None
                parent_id=row.get('parent_id'),
                balance=Decimal(str(row.get('balance', '0.0'))) # تبدیل به Decimal
            )
        except KeyError as e: # این خطا کمتر محتمل است اگر از .get استفاده کنیم
            logger.error(f"KeyError when creating AccountEntity from row: {e}. Row: {row}", exc_info=True)
            raise
        except Exception as e: # گرفتن خطاهای عمومی‌تر هنگام ساخت Entity
            logger.error(f"Unexpected error creating AccountEntity from row: {e}. Row: {row}", exc_info=True)
            raise


    def get_by_name(self, name: str) -> Optional['AccountEntity']:
        query = f"SELECT * FROM {self._table_name} WHERE name = ?"
        row = self.db_manager.fetch_one(query, (name,))
        return self._entity_from_row(dict(row)) if row else None

    def get_by_type(self, account_type: AccountType) -> List['AccountEntity']:
        query = f"SELECT * FROM {self._table_name} WHERE type = ?"
        rows = self.db_manager.fetch_all(query, (account_type.value,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_child_accounts(self, parent_id: Optional[int]) -> List['AccountEntity']:
        if parent_id is None:
            query = f"SELECT * FROM {self._table_name} WHERE parent_id IS NULL ORDER BY name ASC"
            params = ()
        else:
            if not isinstance(parent_id, int) or parent_id <= 0:
                logger.warning(f"Invalid parent_id for get_child_accounts: {parent_id}. Returning empty list.")
                return []
            query = f"SELECT * FROM {self._table_name} WHERE parent_id = ? ORDER BY name ASC"
            params = (parent_id,)
        
        rows = self.db_manager.fetch_all(query, params)
        return [self._entity_from_row(dict(row)) for row in rows if row]