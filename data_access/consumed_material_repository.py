# src/data_access/consumed_material_repository.py
from typing import List, Optional, Dict, Any
from decimal import Decimal
from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.consumed_material_entity import ConsumedMaterialEntity # مسیر صحیح به Entity
import logging

logger = logging.getLogger(__name__)

class ConsumedMaterialRepository(BaseRepository[ConsumedMaterialEntity]):
    def __init__(self, db_manager: DatabaseManager):
        # لیست دقیق ستون‌های جدول consumed_materials در دیتابیس
        db_columns = [
            "manual_production_id", 
            "component_product_id", 
            "quantity_consumed", 
            "notes"
            # "unit_cost_at_consumption" # اگر این ستون را اضافه کردید
        ]
        super().__init__(db_manager, ConsumedMaterialEntity, "consumed_materials", db_columns=db_columns)

    def _entity_from_row(self, row: Dict[str, Any]) -> ConsumedMaterialEntity:
        return ConsumedMaterialEntity(
            id=row.get('id'),
            manual_production_id=row.get('manual_production_id'),
            component_product_id=row.get('component_product_id'),
            quantity_consumed=Decimal(str(row.get('quantity_consumed', '0.0'))),
            notes=row.get('notes')
            # unit_cost_at_consumption=Decimal(str(row.get('unit_cost_at_consumption', '0.0'))) # اگر دارید
        )

    def get_by_manual_production_id(self, manual_production_id: int) -> List[ConsumedMaterialEntity]:
        """تمام اقلام مصرفی مربوط به یک تولید دستی خاص را برمی‌گرداند."""
        if not manual_production_id:
            return []
        query = f"SELECT * FROM {self._table_name} WHERE manual_production_id = ?"
        rows = self.db_manager.fetch_all(query, (manual_production_id,))
        return [self._entity_from_row(dict(r)) for r in rows if r] if rows else []

    def delete_by_manual_production_id(self, manual_production_id: int) -> bool:
        """تمام اقلام مصرفی مربوط به یک تولید دستی خاص را حذف می‌کند."""
        if not manual_production_id:
            return False
        logger.info(f"Attempting to delete consumed materials for Manual Production ID: {manual_production_id}")
        query = f"DELETE FROM {self._table_name} WHERE manual_production_id = ?"
        try:
            self.db_manager.execute_query(query, (manual_production_id,))
            logger.info(f"Deleted consumed materials for Manual Production ID: {manual_production_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting consumed materials for Manual Production ID {manual_production_id}: {e}", exc_info=True)
            return False

    # می‌توانید متدهای دیگری مانند update_item یا add_multiple_items را در صورت نیاز اضافه کنید.