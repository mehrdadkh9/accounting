# src/data_access/checks_repository.py

from typing import Dict, Any, Optional, List
from datetime import date, datetime
from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.check_entity import CheckEntity
from src.constants import CheckType, CheckStatus, DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class ChecksRepository(BaseRepository[CheckEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=CheckEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="checks") 

    def _entity_from_row(self, row: Dict[str, Any]) -> CheckEntity:
        if row is None:
            raise ValueError("Input row cannot be None for CheckEntity")
        try:
            # Assuming issue_date and due_date are NOT NULL in the DB
            issue_date_obj = datetime.strptime(row['issue_date'], DATE_FORMAT).date()
            due_date_obj = datetime.strptime(row['due_date'], DATE_FORMAT).date()

            return CheckEntity(
                id=row['id'],
                check_number=row['check_number'],
                amount=float(row['amount']),
                issue_date=issue_date_obj,
                due_date=due_date_obj,
                person_id=row['person_id'],
                account_id=row['account_id'],
                check_type=CheckType(row['check_type']),
                status=CheckStatus(row['status']),
                description=row.get('description'),
                invoice_id=row.get('invoice_id'),
                purchase_order_id=row.get('purchase_order_id'),
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except KeyError as e:
            logger.error(f"KeyError when creating CheckEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For Enum, date, or float conversion
            logger.error(f"ValueError when creating CheckEntity: {e}. Row: {row}")
            raise

    def get_by_check_number(self, check_number: str, account_id: Optional[int] = None) -> List[CheckEntity]:
        """
        Retrieves checks by check number.
        Optionally filters by account_id if provided (useful for issued checks).
        """
        if account_id:
            query = f"SELECT * FROM {self._table_name} WHERE check_number = ? AND account_id = ?"
            params = (check_number, account_id)
        else:
            query = f"SELECT * FROM {self._table_name} WHERE check_number = ?"
            params = (check_number,)
        
        rows = self.db_manager.fetch_all(query, params)
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_status(self, status: CheckStatus) -> List[CheckEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE status = ? ORDER BY due_date ASC"
        rows = self.db_manager.fetch_all(query, (status.value,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_person_id(self, person_id: int) -> List[CheckEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE person_id = ? ORDER BY due_date ASC"
        rows = self.db_manager.fetch_all(query, (person_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_due_date_range(self, start_date: date, end_date: date) -> List[CheckEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE due_date BETWEEN ? AND ? ORDER BY due_date ASC"
        # The strftime calls are correct for date objects
        rows = self.db_manager.fetch_all(query, (start_date.strftime(DATE_FORMAT), end_date.strftime(DATE_FORMAT)))
        return [self._entity_from_row(dict(row)) for row in rows if row]