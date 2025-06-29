# src/data_access/purchase_orders_repository.py

from typing import Dict, Any, Optional, List
from datetime import date, datetime # Ensure date is imported

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.purchase_order_entity import PurchaseOrderEntity
from src.constants import PurchaseOrderStatus, DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class PurchaseOrdersRepository(BaseRepository[PurchaseOrderEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=PurchaseOrderEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="purchase_orders") 

    def _entity_from_row(self, row: Dict[str, Any]) -> PurchaseOrderEntity:
        if row is None:
            raise ValueError("Input row cannot be None for PurchaseOrderEntity")
        try:
            # Assuming order_date is NOT NULL
            order_date_obj = datetime.strptime(row['order_date'], DATE_FORMAT).date()

            # Note: The 'items' list (PurchaseOrderItemEntity) is not populated here.
            # It will be handled by the PurchaseOrderManager.
            return PurchaseOrderEntity(
                id=row['id'],
                order_number=row['order_number'],
                person_id=row['person_id'], # Supplier ID
                order_date=order_date_obj,
                total_amount_expected=float(row['total_amount_expected']),
                paid_amount=float(row['paid_amount']),
                received_amount=float(row.get('received_amount', 0.0)),
                status=PurchaseOrderStatus(row['status']),
                description=row.get('description'),
                fiscal_year_id=row.get('fiscal_year_id')
                # items list is intentionally empty here
            )
        except KeyError as e:
            logger.error(f"KeyError when creating PurchaseOrderEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For Enum, date or float conversion
            logger.error(f"ValueError when creating PurchaseOrderEntity: {e}. Row: {row}")
            raise

    def get_by_order_number(self, order_number: str) -> Optional[PurchaseOrderEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE order_number = ?"
        row = self.db_manager.fetch_one(query, (order_number,))
        return self._entity_from_row(dict(row)) if row else None

    def get_by_person_id(self, person_id: int) -> List[PurchaseOrderEntity]: # Supplier ID
        query = f"SELECT * FROM {self._table_name} WHERE person_id = ? ORDER BY order_date DESC"
        rows = self.db_manager.fetch_all(query, (person_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_status(self, status: PurchaseOrderStatus) -> List[PurchaseOrderEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE status = ? ORDER BY order_date DESC"
        rows = self.db_manager.fetch_all(query, (status.value,))
        return [self._entity_from_row(dict(row)) for row in rows if row]