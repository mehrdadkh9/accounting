# src/data_access/settings_repository.py

from typing import Dict, Any, Optional, List
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.setting_entity import SettingEntity
import logging

logger = logging.getLogger(__name__)

class SettingsRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.table_name = "settings"

    def _entity_from_row(self, row: Dict[str, Any]) -> SettingEntity:
        if row is None:
            raise ValueError("Input row cannot be None for SettingEntity")
        try:
            return SettingEntity(
                key=row['key'],
                value=row['value'] 
            )
        except KeyError as e:
            logger.error(f"KeyError when creating SettingEntity from row: {e}. Row: {row}")
            raise

    def get_setting(self, key: str) -> Optional[SettingEntity]:
        query = f"SELECT * FROM {self.table_name} WHERE key = ?"
        row = self.db_manager.fetch_one(query, (key,))
        return self._entity_from_row(dict(row)) if row else None

    def get_all_settings(self) -> List[SettingEntity]:
        query = f"SELECT * FROM {self.table_name}"
        rows = self.db_manager.fetch_all(query)
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def set_setting(self, setting: SettingEntity) -> SettingEntity:
        # Using INSERT OR REPLACE (UPSERT behavior)
        query = f"INSERT OR REPLACE INTO {self.table_name} (key, value) VALUES (?, ?)"
        self.db_manager.execute_query(query, (setting.key, setting.value))
        return setting # The entity itself is returned as SQLite UPSERT doesn't return an ID in this case

    def delete_setting(self, key: str) -> None:
        query = f"DELETE FROM {self.table_name} WHERE key = ?"
        self.db_manager.execute_query(query, (key,))