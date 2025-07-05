# src/data_access/base_repository.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, List, Optional, Dict, Any, Tuple, TYPE_CHECKING, Union

from datetime import date, datetime
from src.data_access.database_manager import DatabaseManager
import logging # <<< این خط را اضافه کنید یا مطمئن شوید وجود دارد

from typing import List, Optional, TypeVar, Generic, Any, Dict, TYPE_CHECKING, Type # <<< Add Type here
from decimal import Decimal # <<< IMPORT DECIMAL HERE
from enum import Enum
from dataclasses import fields, is_dataclass, MISSING
# برای TypeVar، از "forward reference" به صورت رشته استفاده می‌کنیم
# تا در زمان اجرا نیازی به import مستقیم BaseEntity در سطح ماژول نباشد.
if TYPE_CHECKING:
    from ..business_logic.entities.base_entity import BaseEntity
# --- پایان اصلاح ---

logger = logging.getLogger(__name__)

# --- شروع اصلاح ---
# برای اینکه برنامه در زمان اجرا BaseEntity را بشناسد، از یک رشته استفاده می‌کنیم
# این تکنیک به عنوان "Forward Reference" شناخته می‌شود.
T = TypeVar('T', bound='BaseEntity')
# --- پایان اصلاح ---

class BaseRepository(Generic[T]):
    def __init__(self, db_manager: DatabaseManager, model_type: Type[T], table_name: str):
        self.db_manager = db_manager
        self.model_type = model_type
        self._table_name = table_name
        self._db_columns = [f.name for f in fields(model_type) if f.init]
        logger.debug(f"BaseRepository for {self._table_name} initialized. Columns: {self._db_columns}")

    def get_by_id(self, entity_id: int) -> Optional[T]:
        query = f"SELECT * FROM {self._table_name} WHERE id = ?"
        with self.db_manager as conn:
            cursor = conn.execute(query, (entity_id,))
            row = cursor.fetchone()
            if row:
                row_dict = {k[0]: v for k, v in zip(cursor.description, row)}
                return self._entity_from_row(row_dict)
        return None

    def get_all(self, order_by: Optional[str] = None) -> List[T]:
        query = f"SELECT * FROM {self._table_name}"
        if order_by:
            query += f" ORDER BY {order_by}"
        
        with self.db_manager as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            return [self._entity_from_row({k[0]: v for k, v in zip(cursor.description, row)}) for row in rows]

    def _get_table_name_from_entity(self) -> str:
        class_name = self._entity_type.__name__.replace("Entity", "")
        s1 = class_name[0].lower()
        for char_idx, char in enumerate(class_name[1:]):
            if char.isupper() and class_name[char_idx].islower(): s1 += '_' + char.lower()
            else: s1 += char.lower()
        if s1.endswith('y') and not s1.endswith('ey'): return s1[:-1] + "ies"
        elif s1.endswith('s') or s1.endswith('x') or s1.endswith('z') or s1.endswith('ch') or s1.endswith('sh'): return s1 + "es"
        else: return s1 + "s"

    @abstractmethod
    


    def _entity_to_dict_for_db(self, entity: T) -> Dict[str, Any]:
        """
        فیلدهای entity را به دیکشنری برای ذخیره در دیتابیس تبدیل می‌کند،
        فقط فیلدهایی که در self._db_columns تعریف شده‌اند را شامل می‌شود.
        """
        data_to_persist = {}
        if not self._db_columns:
            # اگر ستون‌ها به طور خودکار تشخیص داده نشده‌اند، از __dict__ استفاده می‌کنیم اما با ریسک
            # این حالت باید با پاس دادن db_columns به سازنده BaseRepository یا override این متد در فرزند، مدیریت شود.
            logger.warning(f"DB columns for {self._table_name} not explicitly defined. Using entity.__dict__ which might include non-DB fields.")
            entity_data = entity.__dict__
        else:
            entity_data = {col: getattr(entity, col, None) for col in self._db_columns if hasattr(entity, col)}


        for k, v in entity_data.items():
            # فقط فیلدهایی که در self._db_columns هستند (اگر تعریف شده) یا تمام فیلدها (اگر تعریف نشده)
            if self._db_columns and k not in self._db_columns:
                if k not in ['id', 'items', 'product_name']: # فیلدهای شناخته شده غیر پایدار
                     logger.debug(f"Skipping field '{k}' as it's not in defined DB columns for {self._table_name}.")
                continue
            
            if isinstance(v, list) and k.endswith("items"): 
                logger.debug(f"Skipping list field '{k}' (likely related items).")
                continue

            processed_v = v
            if isinstance(v, Decimal): processed_v = float(v)
            elif isinstance(v, Enum): processed_v = v.value
            elif isinstance(v, bool): processed_v = 1 if v else 0
            elif isinstance(v, (datetime, date)): processed_v = v.isoformat()
            
            data_to_persist[k] = processed_v
        return data_to_persist

    def add(self, entity: T) -> Optional[T]:
        logger.debug(f"BaseRepository.add: Type {type(entity).__name__} to table '{self._table_name}'.")
        
        fields_to_insert = self._entity_to_dict_for_db(entity)
        # 'id' نباید در INSERT باشد اگر اتوماتیک است
        fields_to_insert.pop('id', None) # حذف id اگر وجود دارد

        if not fields_to_insert:
            logger.error(f"BaseRepository.add: No valid fields to insert for entity {type(entity)}.")
            # raise ValueError(f"No columns to insert for entity {type(entity)}.") # شاید بهتر باشد None برگردانیم
            return None

        columns = ', '.join(fields_to_insert.keys())
        placeholders = ', '.join(['?'] * len(fields_to_insert))
        values_tuple = tuple(fields_to_insert.values())

        logger.debug(f"BaseRepository.add: Columns for INSERT: {columns}")
        logger.debug(f"BaseRepository.add: Values for INSERT: {values_tuple}")
        
        query = f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})"
        
        try:
            cursor = self.db_manager.execute_query(query, values_tuple)
            if hasattr(entity, 'id') and cursor and cursor.lastrowid is not None:
                entity.id = cursor.lastrowid
                logger.debug(f"BaseRepository.add: Entity ID set to {entity.id} after insert.")
                return entity
            else:
                logger.warning(f"BaseRepository.add: Could not retrieve lastrowid or entity has no 'id'. Table: {self._table_name}.")
                if cursor and cursor.lastrowid is None and not hasattr(entity, 'id'): # اگر جدول PK ندارد (بعید)
                    return entity # باز هم entity را برمی‌گردانیم
                return None # اگر id قابل تنظیم نبود
        except Exception as e:
            logger.error(f"Error during INSERT into {self._table_name}: {e}", exc_info=True)
            # می‌توان خطا را دوباره raise کرد یا None برگرداند
            # raise e 
            return None


    def update(self, entity: T) -> Optional[T]: # Optional[E] برای اینکه اگر آپدیت نشد None برگرداند
        if not hasattr(entity, 'id') or entity.id is None:
            logger.error(f"Entity of type {type(entity).__name__} must have an ID to be updated.")
            # raise ValueError(f"Entity of type {type(entity).__name__} must have an ID to be updated.")
            return None # یا خطا را raise کنید

        entity_id = entity.id
        logger.debug(f"BaseRepository.update: Preparing to update entity ID {entity_id} in table '{self._table_name}'.")
        
        fields_to_update = self._entity_to_dict_for_db(entity)
        fields_to_update.pop('id', None) # id در WHERE clause می‌آید، نه SET

        if not fields_to_update:
            logger.warning(f"BaseRepository.update: No fields to update for entity ID {entity_id}. Returning original entity.")
            return entity # یا None

        set_clause = ', '.join([f"{key} = ?" for key in fields_to_update.keys()])
        values_list = list(fields_to_update.values())
        values_list.append(entity_id) 
        values_tuple = tuple(values_list)

        query = f"UPDATE {self._table_name} SET {set_clause} WHERE id = ?"
        
        logger.debug(f"BaseRepository.update: Query: {query}")
        logger.debug(f"BaseRepository.update: Values: {values_tuple}")
        
        try:
            self.db_manager.execute_query(query, values_tuple)
            logger.info(f"BaseRepository.update: Entity ID {entity_id} in table {self._table_name} updated.")
            return entity
        except Exception as e:
            logger.error(f"Error during UPDATE for entity ID {entity_id} in table {self._table_name}: {e}", exc_info=True)
            # raise e
            return None

    
    def find_by_criteria(self, criteria: Dict[str, Any], order_by: Optional[str] = None) -> List[T]:
        """
        موجودیت‌ها را بر اساس دیکشنری از معیارها با پشتیبانی از عملگرهای پیچیده پیدا می‌کند.
        """
        if not criteria:
            return self.get_all(order_by=order_by)

        base_query = f"SELECT * FROM {self._table_name} WHERE "
        conditions = []
        params = []
        
        for key, value in criteria.items():
            if isinstance(value, tuple) and len(value) == 2:
                operator, val = value
                if str(operator).upper() == 'BETWEEN' and isinstance(val, (list, tuple)) and len(val) == 2:
                    conditions.append(f"{key} BETWEEN ? AND ?")
                    params.extend(val)
                else:
                    conditions.append(f"{key} {operator} ?")
                    params.append(val)
            else:
                conditions.append(f"{key} = ?")
                params.append(value)
        
        query = base_query + " AND ".join(conditions)
        if order_by:
            query += f" ORDER BY {order_by}"

        logger.debug(f"BaseRepository.find_by_criteria: Query: {query}, Values: {tuple(params)}")
        
        with self.db_manager as conn:
            cursor = conn.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._entity_from_row({k[0]: v for k, v in zip(cursor.description, row)}) for row in rows]

    def _entity_from_row(self, row: Dict[str, Any]) -> T:
        """
        یک دیکشنری از داده‌های ردیف دیتابیس را به یک آبجکت دیتاکلاس تبدیل می‌کند.
        این نسخه بسیار قوی‌تر است و انواع داده و مقادیر None را مدیریت می‌کند.
        """
        entity_data = {}
        
        for f in fields(self.model_type):
            if not f.init:
                continue

            field_name = f.name
            field_type = f.type
            value_from_db = row.get(field_name)

            if value_from_db is None:
                if f.default is MISSING and f.default_factory is MISSING:
                    is_optional = getattr(field_type, '__origin__', None) is Union and type(None) in getattr(field_type, '__args__', [])
                    if not is_optional:
                        raise ValueError(
                            f"Database integrity error: NULL value found for required field '{field_name}' "
                            f"in table '{self._table_name}' for row: {row}"
                        )
                continue

            try:
                actual_type = field_type
                if getattr(field_type, '__origin__', None) is Union:
                    possible_types = [arg for arg in getattr(field_type, '__args__', []) if arg is not type(None)]
                    if possible_types:
                        actual_type = possible_types[0]
                
                is_enum = isinstance(actual_type, type) and issubclass(actual_type, Enum)

                if is_enum:
                    entity_data[field_name] = actual_type(value_from_db)
                elif actual_type == Decimal:
                    entity_data[field_name] = Decimal(str(value_from_db))
                elif actual_type == datetime and isinstance(value_from_db, str):
                    entity_data[field_name] = datetime.fromisoformat(value_from_db)
                elif actual_type == date and isinstance(value_from_db, str):
                    entity_data[field_name] = date.fromisoformat(value_from_db.split(" ")[0])
                elif actual_type == bool and isinstance(value_from_db, int):
                    entity_data[field_name] = bool(value_from_db)
                else:
                    entity_data[field_name] = value_from_db
            except (ValueError, TypeError) as e:
                logger.warning(f"Type conversion failed for field '{field_name}' with value '{value_from_db}'. Setting to None. Error: {e}")
                entity_data[field_name] = None

        try:
            return self.model_type(**entity_data)
        except TypeError as e:
            logger.error(f"Failed to instantiate {self.model_type.__name__}. Error: {e}. Data passed: {entity_data}")
            missing_fields = [f.name for f in fields(self.model_type) if f.init and f.name not in entity_data and f.default is MISSING and f.default_factory is MISSING]
            raise TypeError(f"Missing required arguments for {self.model_type.__name__}: {missing_fields}. Original error: {e}") from e
