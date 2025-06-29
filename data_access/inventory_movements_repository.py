# src/data_access/inventory_movements_repository.py

from typing import Dict, Any, List
from datetime import datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.inventory_movement_entity import InventoryMovementEntity
from src.constants import InventoryMovementType, ReferenceType, DATETIME_FORMAT
import logging

logger = logging.getLogger(__name__)

class InventoryMovementsRepository(BaseRepository[InventoryMovementEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=InventoryMovementEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="inventory_movements") 
    def _entity_from_row(self, row: Dict[str, Any]) -> 'InventoryMovementEntity':
        # ...
        movement_date_str = row.get('movement_date')
        parsed_movement_date = None
        if movement_date_str:
            try:
                parsed_movement_date = datetime.fromisoformat(movement_date_str)
            except ValueError as e_iso:
                logger.error(f"Failed to parse movement_date '{movement_date_str}' with fromisoformat for IM ID {row.get('id')}: {e_iso}")
                raise ValueError(f"فرمت تاریخ حرکت انبار نامعتبر است: {movement_date_str}") from e_iso
        # ...
        return InventoryMovementEntity(
            # ...
            movement_date=parsed_movement_date, # type: ignore # Pylance might not know parsed_movement_date is datetime here
            # ...
        )
    
    # ... (other methods remain the same) ...
    def get_by_product_id(self, product_id: int) -> List[InventoryMovementEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE product_id = ? ORDER BY movement_date DESC"
        rows = self.db_manager.fetch_all(query, (product_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_reference(self, reference_id: int, reference_type: ReferenceType) -> List[InventoryMovementEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE reference_id = ? AND reference_type = ?"
        rows = self.db_manager.fetch_all(query, (reference_id, reference_type.value))
        return [self._entity_from_row(dict(row)) for row in rows if row]
    
    def find_by_product_id(self, product_id: int) -> List[InventoryMovementEntity]:
        """
        تمام حرکات انبار مربوط به یک کالای خاص را برمی‌گرداند.
        """
        return self.find_by_criteria({"product_id": product_id}, order_by="movement_date ASC, id ASC")