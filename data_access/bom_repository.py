# src/data_access/bom_repository.py
from typing import List, Optional, Dict, Any
from src.data_access.base_repository import BaseRepository
from src.business_logic.entities.bom_entity import BOMEntity # مسیر صحیح را بررسی کنید
from src.data_access.database_manager import DatabaseManager
from decimal import Decimal
from datetime import date, datetime # برای تبدیل تاریخ
from src.constants import DATE_FORMAT # اگر برای تبدیل تاریخ لازم است
import logging

logger = logging.getLogger(__name__)

class BOMsRepository(BaseRepository[BOMEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, BOMEntity, "boms")

    def _entity_to_dict_for_db(self, entity: BOMEntity) -> Dict[str, Any]:
        data = super()._entity_to_dict_for_db(entity)
        data.pop('product_name', None) # Remove product_name if it exists
        data.pop('items', None) # Also ensure 'items' (list of BomItemEntity) is removed
        return data
    def _entity_from_row(self, row: Dict[str, Any]) -> BOMEntity:
        if row is None:
            raise ValueError("Input row cannot be None for BOMEntity")
        try:
            creation_date_val = row.get('creation_date')
            creation_date_obj: Optional[date] = None
            if isinstance(creation_date_val, str):
                try: creation_date_obj = datetime.strptime(creation_date_val, DATE_FORMAT).date()
                except ValueError: 
                    try: creation_date_obj = date.fromisoformat(creation_date_val)
                    except ValueError: logger.error(f"Invalid date format for creation_date: {creation_date_val}")
            elif isinstance(creation_date_val, date):
                creation_date_obj = creation_date_val

            last_modified_date_val = row.get('last_modified_date')
            last_modified_date_obj: Optional[date] = None
            if isinstance(last_modified_date_val, str):
                try: last_modified_date_obj = datetime.strptime(last_modified_date_val, DATE_FORMAT).date()
                except ValueError: 
                    try: last_modified_date_obj = date.fromisoformat(last_modified_date_val)
                    except ValueError: logger.error(f"Invalid date format for last_modified_date: {last_modified_date_val}")
            elif isinstance(last_modified_date_val, date):
                last_modified_date_obj = last_modified_date_val

            return BOMEntity(
                id=row.get('id'),
                name=row.get('name', ''),
                product_id=row.get('product_id'),
                quantity_produced=Decimal(str(row.get('quantity_produced', '1.0'))),
                description=row.get('description'),
                is_active=bool(row.get('is_active', True)),
                creation_date=creation_date_obj or date.today(), # پیش‌فرض اگر تبدیل ناموفق بود
                last_modified_date=last_modified_date_obj
                # items در اینجا پر نمی‌شود، توسط Manager مدیریت می‌شود
            )
        except Exception as e:
            logger.error(f"Error creating BomEntity from row: {row}. Error: {e}", exc_info=True)
            raise

    def get_active_bom_for_product(self, product_id: int) -> Optional[BOMEntity]:
        """ یک BOM فعال برای محصول مشخص شده برمی‌گرداند (فرض بر اینکه فقط یک BOM فعال برای هر محصول داریم) """
        boms = self.find_by_criteria({"product_id": product_id, "is_active": True}, limit=1)
        return boms[0] if boms else None