# src/data_access/products_repository.py

from typing import Dict, Any, Optional, List

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.product_entity import ProductEntity
from src.constants import ProductType
import logging
from decimal import Decimal
logger = logging.getLogger(__name__)

class ProductsRepository(BaseRepository[ProductEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=ProductEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="products") 

    def _entity_from_row(self, row: Dict[str, Any]) -> ProductEntity:
        from src.business_logic.entities.product_entity import ProductEntity # باید ProductEntity باشد

        if row is None:
            raise ValueError("Input row cannot be None for ProductEntity")
        try:
            return ProductEntity(
            id=row['id'],
            name=row['name'],
            product_type=ProductType(row['product_type']), # <<< این خط را به بعد از name منتقل کردم تا با ترتیب جدید Entity سازگار باشد
            sku=row.get('sku'),
            unit_price=float(row['unit_price']),
            stock_quantity=Decimal(str(row.get('stock_quantity', '0.0'))),
            unit_of_measure=row.get('unit_of_measure'), # <<< خواندن فیلد جدید
            description=row.get('description'),
            is_active=bool(row['is_active'])
        )
        except KeyError as e:
            logger.error(f"KeyError when creating ProductEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For ProductType or float conversion
            logger.error(f"ValueError when creating ProductEntity: {e}. Row: {row}")
            raise

    def get_by_sku(self, sku: str) -> Optional[ProductEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE sku = ?"
        row = self.db_manager.fetch_one(query, (sku,))
        return self._entity_from_row(dict(row)) if row else None

    def search_by_name(self, name_query: str) -> List[ProductEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE name LIKE ?"
        rows = self.db_manager.fetch_all(query, (f"%{name_query}%",))
        return [self._entity_from_row(dict(row)) for row in rows if row]
    def get_by_exact_name(self, name: str) -> Optional['ProductEntity']: # نوع بازگشتی 'ProductEntity'
        """
        Retrieves a product by its exact name (case-sensitive).
        """
        # وارد کردن محلی برای استفاده از ProductEntity در صورت نیاز به ساخت نمونه
        # from src.business_logic.entities.product_entity import ProductEntity

        query = f"SELECT * FROM {self._table_name} WHERE name = ?"
        row = self.db_manager.fetch_one(query, (name,))
        return self._entity_from_row(dict(row)) if row else None
