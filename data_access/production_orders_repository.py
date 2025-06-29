# src/data_access/production_orders_repository.py

from typing import Dict, Any, Optional, List
from datetime import date, datetime # Ensure date is imported

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.production_order_entity import ProductionOrderEntity
from src.constants import ProductionOrderStatus, DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class ProductionOrdersRepository(BaseRepository[ProductionOrderEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=ProductionOrderEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="production_orders") 

    def _entity_from_row(self, row: Dict[str, Any]) -> ProductionOrderEntity:
        if row is None:
            raise ValueError("Input row cannot be None for ProductionOrderEntity")
        try:
            # Assuming order_date is NOT NULL
            order_date_obj = datetime.strptime(row['order_date'], DATE_FORMAT).date()
            
            completion_date_str = row.get('completion_date')
            completion_date_obj = datetime.strptime(completion_date_str, DATE_FORMAT).date() if completion_date_str else None

            return ProductionOrderEntity(
                id=row['id'],
                bom_id=row['bom_id'],
                order_date=order_date_obj,
                quantity_to_produce=float(row['quantity_to_produce']),
                status=ProductionOrderStatus(row['status']),
                completion_date=completion_date_obj,
                produced_quantity=float(row['produced_quantity']) if row.get('produced_quantity') is not None else None,
                description=row.get('description'),
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except KeyError as e:
            logger.error(f"KeyError when creating ProductionOrderEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For Enum, date, or float conversion
            logger.error(f"ValueError when creating ProductionOrderEntity: {e}. Row: {row}")
            raise

    def get_by_status(self, status: ProductionOrderStatus) -> List[ProductionOrderEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE status = ? ORDER BY order_date DESC"
        rows = self.db_manager.fetch_all(query, (status.value,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_bom_id(self, bom_id: int) -> List[ProductionOrderEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE bom_id = ? ORDER BY order_date DESC"
        rows = self.db_manager.fetch_all(query, (bom_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]