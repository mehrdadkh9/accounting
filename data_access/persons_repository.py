# src/data_access/persons_repository.py

from typing import Dict, Any, Optional, List

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.person_entity import PersonEntity
from src.constants import PersonType
import logging

logger = logging.getLogger(__name__)

class PersonsRepository(BaseRepository[PersonEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=PersonEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="persons") 

    def _entity_from_row(self, row: Dict[str, Any]) -> PersonEntity:
        if row is None:
            raise ValueError("Input row cannot be None for PersonEntity")
        try:
            return PersonEntity(
                id=row['id'],
                name=row['name'],
                person_type=PersonType(row['person_type']),
                contact_info=row.get('contact_info') # .get() handles if column might be missing, though schema defines it
            )
        except KeyError as e:
            logger.error(f"KeyError when creating PersonEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For PersonType conversion
            logger.error(f"ValueError when creating PersonEntity: {e}. Row: {row}")
            raise

    def get_by_name(self, name: str, exact: bool = True) -> List[PersonEntity]:
        if exact:
            query = f"SELECT * FROM {self._table_name} WHERE name = ?"
            params = (name,)
        else:
            query = f"SELECT * FROM {self._table_name} WHERE name LIKE ?"
            params = (f"%{name}%",)
        
        rows = self.db_manager.fetch_all(query, params)
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_type(self, person_type: PersonType) -> List[PersonEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE person_type = ?"
        rows = self.db_manager.fetch_all(query, (person_type.value,))
        return [self._entity_from_row(dict(row)) for row in rows if row]