# src/data_access/fiscal_years_repository.py

from typing import Dict, Any, Optional
from datetime import datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.fiscal_year_entity import FiscalYearEntity
from src.constants import FiscalYearStatus, DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class FiscalYearsRepository(BaseRepository[FiscalYearEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=FiscalYearEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="fiscal_years") 

    def _entity_from_row(self, row: Dict[str, Any]) -> FiscalYearEntity:
        if row is None:
            raise ValueError("Input row cannot be None for FiscalYearEntity")
        try:
            # Assuming start_date and end_date are NOT NULL in the DB as per schema
            return FiscalYearEntity(
                id=row['id'],
                name=row['name'],
                start_date=datetime.strptime(row['start_date'], DATE_FORMAT).date(),
                end_date=datetime.strptime(row['end_date'], DATE_FORMAT).date(),
                status=FiscalYearStatus(row['status'])
            )
        except KeyError as e:
            logger.error(f"KeyError when creating FiscalYearEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # Handles issues with FiscalYearStatus conversion or date parsing
            logger.error(f"ValueError when creating FiscalYearEntity: {e}. Row: {row}")
            raise

    def get_by_name(self, name: str) -> Optional[FiscalYearEntity]:
        query = f"SELECT * FROM {self.table_name} WHERE name = ?"
        row = self.db_manager.fetch_one(query, (name,))
        return self._entity_from_row(dict(row)) if row else None

    def get_open_fiscal_year(self) -> Optional[FiscalYearEntity]:
        """Retrieves the currently open fiscal year, if any."""
        query = f"SELECT * FROM {self.table_name} WHERE status = ? LIMIT 1"
        row = self.db_manager.fetch_one(query, (FiscalYearStatus.OPEN.value,))
        return self._entity_from_row(dict(row)) if row else None