# src/data_access/loans_repository.py

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.loan_entity import LoanEntity
from src.constants import LoanStatus, DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class LoansRepository(BaseRepository[LoanEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=LoanEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="loans") 
    def _entity_from_row(self, row: Dict[str, Any]) -> LoanEntity:
        if row is None:
            raise ValueError("Input row cannot be None for LoanEntity")
        try:
            # Assuming start_date and end_date are NOT NULL
            start_date_obj = datetime.strptime(row['start_date'], DATE_FORMAT).date()
            end_date_obj = datetime.strptime(row['end_date'], DATE_FORMAT).date()

            # Note: The 'installments' list is not populated here from the DB row.
            # It will be handled by the LoanManager using LoanInstallmentsRepository.
            return LoanEntity(
                id=row['id'],
                person_id=row['person_id'],
                loan_amount=float(row['loan_amount']),
                interest_rate=float(row['interest_rate']),
                start_date=start_date_obj,
                end_date=end_date_obj,
                installment_amount=float(row['installment_amount']),
                status=LoanStatus(row['status']),
                description=row.get('description'),
                fiscal_year_id=row.get('fiscal_year_id')
                # installments list is intentionally empty here
            )
        except KeyError as e:
            logger.error(f"KeyError when creating LoanEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For Enum, date or float conversion
            logger.error(f"ValueError when creating LoanEntity: {e}. Row: {row}")
            raise

    def get_by_person_id(self, person_id: int) -> List[LoanEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE person_id = ? ORDER BY start_date DESC"
        rows = self.db_manager.fetch_all(query, (person_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_status(self, status: LoanStatus) -> List[LoanEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE status = ? ORDER BY start_date DESC"
        rows = self.db_manager.fetch_all(query, (status.value,))
        return [self._entity_from_row(dict(row)) for row in rows if row]