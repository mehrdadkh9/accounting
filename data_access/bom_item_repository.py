# src/data_access/bom_item_repository.py
from typing import List, Optional, Dict, Any
from src.data_access.base_repository import BaseRepository
from src.business_logic.entities.bom_item_entity import BomItemEntity 
from src.data_access.database_manager import DatabaseManager
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class BomItemRepository(BaseRepository[BomItemEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, BomItemEntity, "bom_items")

    def _entity_from_row(self, row: Dict[str, Any]) -> BomItemEntity:
        if row is None:
            raise ValueError("Input row cannot be None for BomItemEntity")
        try:
            return BomItemEntity(
                id=row.get('id'),
                bom_id=row.get('bom_id'),
                component_product_id=row.get('component_product_id'),
                quantity_required=Decimal(str(row.get('quantity_required', '0.0'))),
                notes=row.get('notes')
            )
        except Exception as e:
            logger.error(f"Error creating BomItemEntity from row: {row}. Error: {e}", exc_info=True)
            raise

    def get_by_bom_id(self, bom_id: int) -> List[BomItemEntity]:
        logger.debug(f"Fetching BOM items for BOM ID: {bom_id}")
        return self.find_by_criteria({"bom_id": bom_id})

    def delete_by_bom_id(self, bom_id: int) -> bool:
        query = f"DELETE FROM {self._table_name} WHERE bom_id = ?"
        try:
            self.db_manager.execute_query(query, (bom_id,))
            logger.info(f"Deleted BOM items for BOM ID: {bom_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting BOM items for BOM ID {bom_id}: {e}", exc_info=True)
            return False