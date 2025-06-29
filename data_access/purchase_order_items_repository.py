# src/data_access/purchase_order_items_repository.py

from typing import Dict, Any, List

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.purchase_order_item_entity import PurchaseOrderItemEntity
import logging

logger = logging.getLogger(__name__)

class PurchaseOrderItemsRepository(BaseRepository[PurchaseOrderItemEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                        model_type=PurchaseOrderItemEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="purchase_order_items") 
    def _entity_from_row(self, row: Dict[str, Any]) -> 'PurchaseOrderItemEntity':
        # وارد کردن محلی برای ساخت نمونه
        from src.business_logic.entities.purchase_order_item_entity import PurchaseOrderItemEntity

        if row is None:
            raise ValueError("Input row cannot be None for PurchaseOrderItemEntity")
        try:
            return PurchaseOrderItemEntity(
                id=row['id'],
                purchase_order_id=row['purchase_order_id'],
                product_id=row['product_id'],
                ordered_quantity=float(row['ordered_quantity']),
                unit_price=float(row['unit_price']),
                total_item_amount=float(row['total_item_amount']) # <<< این خط اضافه/اصلاح شد
            )
        except KeyError as e:
            logger.error(f"KeyError when creating PurchaseOrderItemEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: 
            logger.error(f"ValueError when creating PurchaseOrderItemEntity: {e}. Row: {row}")
            raise

    def get_by_purchase_order_id(self, purchase_order_id: int) -> List[PurchaseOrderItemEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE purchase_order_id = ?"
        rows = self.db_manager.fetch_all(query, (purchase_order_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def delete_by_purchase_order_id(self, purchase_order_id: int) -> None:
        query = f"DELETE FROM {self._table_name} WHERE purchase_order_id = ?"
        self.db_manager.execute_query(query, (purchase_order_id,))