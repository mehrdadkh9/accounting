# src/data_access/material_receipts_repository.py

from typing import Dict, Any, Optional, List
from datetime import date, datetime # Ensure date is imported

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.material_receipt_entity import MaterialReceiptEntity
from src.constants import DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class MaterialReceiptsRepository(BaseRepository[MaterialReceiptEntity]):
    def __init__(self, db_manager: DatabaseManager):
      
        super().__init__(db_manager=db_manager, 
                         model_type=MaterialReceiptEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="material_receipts") 
    def _entity_from_row(self, row: Dict[str, Any]) -> MaterialReceiptEntity:
        if row is None:
            raise ValueError("Input row cannot be None for MaterialReceiptEntity")
        try:
            # Assuming receipt_date is NOT NULL
            receipt_date_obj = datetime.strptime(row['receipt_date'], DATE_FORMAT).date()
            
            unit_price_val = row.get('unit_price')

            return MaterialReceiptEntity(
                id=row['id'],
                receipt_date=receipt_date_obj,
                person_id=row['person_id'], # Supplier ID
                product_id=row['product_id'],
                quantity_received=float(row['quantity_received']),
                unit_price=float(unit_price_val) if unit_price_val is not None else None,
                purchase_order_id=row.get('purchase_order_id'),
                purchase_order_item_id=row.get('purchase_order_item_id'),
                description=row.get('description'),
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except KeyError as e:
            logger.error(f"KeyError when creating MaterialReceiptEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For date or float conversion
            logger.error(f"ValueError when creating MaterialReceiptEntity: {e}. Row: {row}")
            raise

    def get_by_purchase_order_id(self, purchase_order_id: int) -> List[MaterialReceiptEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE purchase_order_id = ? ORDER BY receipt_date DESC"
        rows = self.db_manager.fetch_all(query, (purchase_order_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_product_id(self, product_id: int) -> List[MaterialReceiptEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE product_id = ? ORDER BY receipt_date DESC"
        rows = self.db_manager.fetch_all(query, (product_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]