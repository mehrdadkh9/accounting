# src/data_access/manual_production_repository.py
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import date,datetime
from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.manual_production_entity import ManualProductionEntity # مسیر صحیح به Entity
from src.constants import DATE_FORMAT # اگر برای تبدیل تاریخ استفاده می‌کنید
import logging

logger = logging.getLogger(__name__)

class ManualProductionRepository(BaseRepository[ManualProductionEntity]):
    def __init__(self, db_manager: DatabaseManager):
        # لیست دقیق ستون‌های جدول manual_productions در دیتابیس
        db_columns = [
            "production_date", 
            "finished_product_id", 
            "quantity_produced", 
            "description"
            # "fiscal_year_id" # اگر دارید
        ]
        super().__init__(db_manager, ManualProductionEntity, "manual_productions", db_columns=db_columns)

    def _entity_from_row(self, row: Dict[str, Any]) -> ManualProductionEntity:
        production_date_val = row.get('production_date')
        production_date_obj = None
        if isinstance(production_date_val, str):
            try:
                production_date_obj = date.fromisoformat(production_date_val)
            except ValueError:
                try: # برای سازگاری با فرمت‌های دیگر احتمالی
                    production_date_obj = datetime.strptime(production_date_val, DATE_FORMAT).date() # DATE_FORMAT را از constants وارد کنید
                except ValueError:
                    logger.error(f"Invalid date format for production_date: {production_date_val} in ManualProduction ID {row.get('id')}")
        elif isinstance(production_date_val, date):
            production_date_obj = production_date_val
        
        entity = ManualProductionEntity(
            id=row.get('id'),
            production_date=production_date_obj or date.today(), # پیش‌فرض اگر تاریخ نامعتبر بود
            finished_product_id=row.get('finished_product_id'),
            quantity_produced=Decimal(str(row.get('quantity_produced', '0.0'))),
            description=row.get('description')
            # fiscal_year_id=row.get('fiscal_year_id')
        )
        # فیلدهای نمایشی مانند finished_product_name توسط Manager پر می‌شوند
        return entity

    # می‌توانید متدهای جستجوی خاص دیگری (مثلاً بر اساس تاریخ یا محصول) در اینجا اضافه کنید
    # def get_all_productions_summary(self) -> List[ManualProductionEntity]:
    #     """ یک خلاصه از تمام تولیدات دستی را برمی‌گرداند (بدون اقلام مصرفی). """
    #     return self.get_all(order_by="production_date DESC, id DESC")