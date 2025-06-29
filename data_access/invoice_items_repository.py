# src/data_access/invoice_items_repository.py

from typing import Dict, Any, List

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.invoice_item_entity import InvoiceItemEntity
import logging
from decimal import Decimal
logger = logging.getLogger(__name__)

class InvoiceItemsRepository(BaseRepository[InvoiceItemEntity]):
    def __init__(self, db_manager: DatabaseManager):
        db_item_columns = [
            "invoice_id", 
            "product_id", 
            "quantity", 
            "unit_price",
            "description" # <<< Ensure this is in the list
        ]

        super().__init__(db_manager=db_manager, 
                         model_type=InvoiceItemEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="invoice_items") 

    def _entity_from_row(self, row: Dict[str, Any]) -> 'InvoiceItemEntity':
        # وارد کردن محلی برای ساخت نمونه
        if row is None:
            raise ValueError("Input row cannot be None for InvoiceItemEntity")
        try:
            return InvoiceItemEntity(
            id=row.get('id'),
            invoice_id=row.get('invoice_id'),
            product_id=row.get('product_id'),
            quantity=Decimal(str(row.get('quantity', '0.0'))),
            unit_price=Decimal(str(row.get('unit_price', '0.0'))),
            description=row.get('description')
        )
        except KeyError as e:
            logger.error(f"KeyError when creating InvoiceItemEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: 
            logger.error(f"ValueError when creating InvoiceItemEntity: {e}. Row: {row}")
            raise
    def get_by_invoice_id(self, invoice_id: int) -> List[InvoiceItemEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE invoice_id = ?"
        rows = self.db_manager.fetch_all(query, (invoice_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def delete_by_invoice_id(self, invoice_id: int) -> None:
        query = f"DELETE FROM {self._table_name} WHERE invoice_id = ?"
        self.db_manager.execute_query(query, (invoice_id,))