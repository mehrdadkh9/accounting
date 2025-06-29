# src/data_access/invoices_repository.py

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.invoice_entity import InvoiceEntity
from src.constants import InvoiceType, DATE_FORMAT,InvoiceStatus
import logging

logger = logging.getLogger(__name__)

class InvoicesRepository(BaseRepository[InvoiceEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=InvoiceEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="invoices") 

    def _entity_from_row(self, row: Dict[str, Any]) -> InvoiceEntity:
        if row is None:
            raise ValueError("Input row cannot be None for InvoiceEntity")
        try:
            # Assuming invoice_date is NOT NULL in DB
            invoice_date_obj = datetime.strptime(row['invoice_date'], DATE_FORMAT).date()
            
            due_date_str = row.get('due_date')
            due_date_obj = datetime.strptime(due_date_str, DATE_FORMAT).date() if due_date_str else None
            
            return InvoiceEntity(
                id=row['id'],
                invoice_number=row['invoice_number'],
                invoice_date=invoice_date_obj, # Directly assign non-optional
                due_date=due_date_obj,         # Assign optional
                person_id=row['person_id'],
                total_amount=float(row['total_amount']),
                paid_amount=float(row['paid_amount']),
                description=row.get('description'),
                is_paid=bool(row['is_paid']), # Now a direct field
                invoice_type=InvoiceType(row['invoice_type']),
                status=InvoiceStatus(row['status']),
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except KeyError as e:
            logger.error(f"KeyError when creating InvoiceEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: 
            logger.error(f"ValueError when creating InvoiceEntity: {e}. Row: {row}")
            raise


    def get_by_invoice_number(self, invoice_number: str) -> Optional[InvoiceEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE invoice_number = ?"
        row = self.db_manager.fetch_one(query, (invoice_number,))
        return self._entity_from_row(dict(row)) if row else None

    def get_by_person_id(self, person_id: int) -> List[InvoiceEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE person_id = ?"
        rows = self.db_manager.fetch_all(query, (person_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_fiscal_year_id(self, fiscal_year_id: int) -> List[InvoiceEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE fiscal_year_id = ?"
        rows = self.db_manager.fetch_all(query, (fiscal_year_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]