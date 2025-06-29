# src/data_access/payment_line_item_repository.py

from typing import Dict, Any, Optional, List, TYPE_CHECKING

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.constants import PaymentMethod # برای تبدیل نوع از رشته به Enum
import logging
from src.business_logic.entities.payment_line_item_entity import PaymentLineItemEntity

if TYPE_CHECKING:
    from src.business_logic.entities.payment_line_item_entity import PaymentLineItemEntity

logger = logging.getLogger(__name__)

class PaymentLineItemRepository(BaseRepository['PaymentLineItemEntity']):
    def __init__(self, db_manager: DatabaseManager):
        
        super().__init__(db_manager=db_manager, 
                         model_type=PaymentLineItemEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="payment_line_items") 
    def _entity_from_row(self, row: Dict[str, Any]) -> 'PaymentLineItemEntity':
        from src.business_logic.entities.payment_line_item_entity import PaymentLineItemEntity

        if row is None:
            raise ValueError("Input row cannot be None for PaymentLineItemEntity")
        try:
            payment_method_str = row.get('payment_method')
            pm_enum: Optional[PaymentMethod] = None
            if payment_method_str:
                try:
                    pm_enum = PaymentMethod(payment_method_str)
                except ValueError:
                    logger.error(f"Invalid payment_method value '{payment_method_str}' from DB for item ID {row.get('id')}")
                    # می‌توانید یک مقدار پیش‌فرض یا خطا برگردانید
                    # فعلاً خطا ایجاد می‌کنیم تا مشکل داده مشخص شود
                    raise ValueError(f"مقدار نامعتبر برای روش پرداخت از پایگاه داده: {payment_method_str}")


            return PaymentLineItemEntity(
                id=row['id'],
                payment_header_id=row['payment_header_id'],
                payment_method=pm_enum, # type: ignore # اطمینان از اینکه pm_enum مقداردهی شده
                amount=float(row['amount']),
                account_id=row.get('account_id'), # می‌تواند None باشد
                check_id=row.get('check_id'),     # می‌تواند None باشد
                description=row.get('description'),
                target_account_id=row.get('target_account_id') # <<< خواندن فیلد جدید
            )
        except KeyError as e:
            logger.error(f"KeyError when creating PaymentLineItemEntity from row: {e}. Row: {row}")
            raise
        # ValueError برای PaymentMethod قبلا گرفته شده

    def get_by_payment_header_id(self, payment_header_id: int) -> List['PaymentLineItemEntity']:
        query = f"SELECT * FROM {self._table_name} WHERE payment_header_id = ?"
        rows = self.db_manager.fetch_all(query, (payment_header_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def delete_by_payment_header_id(self, payment_header_id: int) -> None:
        query = f"DELETE FROM {self._table_name} WHERE payment_header_id = ?"
        self.db_manager.execute_query(query, (payment_header_id,))
        logger.info(f"Deleted payment line items for header ID: {payment_header_id}")