# src/data_access/production_order_repository.py
from typing import Dict, Any, Optional
from src.data_access.base_repository import BaseRepository
from src.business_logic.entities.production_order_entity import ProductionOrderEntity # مسیر صحیح
from src.data_access.database_manager import DatabaseManager
from src.constants import ProductionOrderStatus, DATE_FORMAT # و سایر Enum های لازم
from decimal import Decimal
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

class ProductionOrderRepository(BaseRepository[ProductionOrderEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, ProductionOrderEntity, "production_orders") # نام جدول شما

    def _entity_from_row(self, row: Dict[str, Any]) -> ProductionOrderEntity:
        if row is None:
            raise ValueError("Input row cannot be None for ProductionOrderEntity")
        try:
            order_date_val = row.get('order_date')
            order_date_obj = None
            if isinstance(order_date_val, str):
                try: order_date_obj = datetime.strptime(order_date_val, DATE_FORMAT).date()
                except ValueError: 
                    try: order_date_obj = date.fromisoformat(order_date_val)
                    except ValueError: logger.error(f"Invalid date format for order_date: {order_date_val}")
            elif isinstance(order_date_val, date):
                order_date_obj = order_date_val

            start_date_val = row.get('start_date')
            start_date_obj = None
            if isinstance(start_date_val, str):
                try: start_date_obj = datetime.fromisoformat(start_date_val)
                except ValueError: logger.error(f"Invalid datetime format for start_date: {start_date_val}")
            elif isinstance(start_date_val, datetime):
                start_date_obj = start_date_val
            
            completion_date_val = row.get('completion_date')
            completion_date_obj = None
            if isinstance(completion_date_val, str):
                try: completion_date_obj = datetime.fromisoformat(completion_date_val)
                except ValueError: logger.error(f"Invalid datetime format for completion_date: {completion_date_val}")
            elif isinstance(completion_date_val, datetime):
                completion_date_obj = completion_date_val

            return ProductionOrderEntity(
                id=row.get('id'),
                order_number=row.get('order_number'),
                product_id=row.get('product_id'),
                bom_id=row.get('bom_id'),
                quantity_to_produce=Decimal(str(row.get('quantity_to_produce', '0.0'))),
                quantity_produced=Decimal(str(row.get('quantity_produced', '0.0'))),
                order_date=order_date_obj or date.today(),
                start_date=start_date_obj,
                completion_date=completion_date_obj,
                status=ProductionOrderStatus(row['status']) if row.get('status') else ProductionOrderStatus.PENDING,
                description=row.get('description'),
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except Exception as e:
            logger.error(f"Error creating ProductionOrderEntity from row: {row}. Error: {e}", exc_info=True)
            raise