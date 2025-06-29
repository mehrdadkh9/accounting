# src/data_access/employees_repository.py

from typing import Dict, Any, Optional
from datetime import datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.employee_entity import EmployeeEntity
from src.constants import DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class EmployeesRepository(BaseRepository[EmployeeEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=EmployeeEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="employees") 

    def _entity_from_row(self, row: Dict[str, Any]) -> EmployeeEntity:
        if row is None:
            raise ValueError("Input row cannot be None for EmployeeEntity")
        try:
            hire_date_str = row.get('hire_date')
            return EmployeeEntity(
                id=row['id'],
                person_id=row['person_id'],
                national_id=row.get('national_id'),
                position=row.get('position'),
                base_salary=float(row['base_salary']),
                hire_date=datetime.strptime(hire_date_str, DATE_FORMAT).date() if hire_date_str else None,
                is_active=bool(row['is_active']) # DB stores 0 or 1
            )
        except KeyError as e:
            logger.error(f"KeyError when creating EmployeeEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For date or bool conversion
            logger.error(f"ValueError when creating EmployeeEntity: {e}. Row: {row}")
            raise
            
    def get_by_person_id(self, person_id: int) -> Optional[EmployeeEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE person_id = ?"
        row = self.db_manager.fetch_one(query, (person_id,))
        return self._entity_from_row(dict(row)) if row else None

    def get_active_employees(self) -> list[EmployeeEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE is_active = 1"
        rows = self.db_manager.fetch_all(query)
        return [self._entity_from_row(dict(r)) for r in rows if r]