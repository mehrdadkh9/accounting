# src/business_logic/product_manager.py
from typing import Optional, List, Any, Dict, Tuple,TYPE_CHECKING
from decimal import Decimal,InvalidOperation
from datetime import datetime

from src.business_logic.entities.product_entity import ProductEntity
from src.constants import ProductType, InventoryMovementType, ReferenceType 
# اگر InventoryManager و InventoryMovementEntity دارید، آنها را نیز import کنید
# from src.business_logic.inventory_manager import InventoryManager 
from .entities.inventory_movement_entity import InventoryMovementEntity
if TYPE_CHECKING:
    from ..data_access.products_repository import ProductsRepository
    from ..data_access.inventory_movements_repository import InventoryMovementsRepository

import logging

logger = logging.getLogger(__name__)

class ProductManager:
    def __init__(self, product_repository: 'ProductsRepository', inventory_movements_repository: 'InventoryMovementsRepository'):

        if product_repository is None:
            raise ValueError("product_repository cannot be None")
        self.product_repo = product_repository
        # self.inventory_manager = inventory_manager 
        self.inventory_movements_repo = inventory_movements_repository

    def get_product_by_id(self, product_id: int) -> Optional[ProductEntity]:
        """یک محصول را با شناسه آن واکشی می‌کند."""
        logger.debug(f"Fetching product by ID: {product_id}")
        product = self.product_repo.get_by_id(product_id)
        if not product:
            logger.warning(f"Product with ID {product_id} not found.")
            return None
        return product

    def get_product_by_sku(self, sku: str) -> Optional[ProductEntity]:
        """یک محصول را با SKU آن واکشی می‌کند."""
        logger.debug(f"Fetching product by SKU: {sku}")
        if not sku: # SKU خالی را جستجو نکن
            return None
        # فرض بر اینکه BaseRepository.find_by_criteria پارامتر limit را می‌پذیرد
        products = self.product_repo.find_by_criteria({"sku": sku}, limit=1) 
        if products:
            return products[0]
        logger.warning(f"Product with SKU {sku} not found.")
        return None

    def get_all_products(self, 
                         active_only: bool = True, 
                         product_type_filter: Optional[ProductType] = None
                         ) -> List[ProductEntity]:
        """لیستی از محصولات را برمی‌گرداند، با قابلیت فیلتر بر اساس فعال بودن و نوع محصول."""
        logger.debug(f"Fetching products. Active only: {active_only}, Type filter: {product_type_filter}")
        criteria: Dict[str, Any] = {}
        if active_only:
            criteria["is_active"] = True
        if product_type_filter:
            criteria["product_type"] = product_type_filter.value # فرض اینکه Enum value ذخیره می‌شود

        if criteria:
            return self.product_repo.find_by_criteria(criteria, order_by="name ASC")
        else:
            return self.product_repo.get_all(order_by="name ASC")

    def create_product(self, 
                       name: str, 
                       product_type: ProductType, 
                       unit_price: Decimal, 
                       stock_quantity: Optional[Decimal] = Decimal("0.0"), 
                       unit_of_measure: str = "", 
                       sku: Optional[str] = None, 
                       description: Optional[str] = None, 
                       is_active: bool = True,
                       ) -> Optional[ProductEntity]:
        if not name:
            raise ValueError("نام محصول نمی‌تواند خالی باشد.")
        
        try:
            # Ensure unit_price is Decimal
            unit_price_dec = unit_price if isinstance(unit_price, Decimal) else Decimal(str(unit_price or "0.0"))
            
            # Ensure stock_quantity is Decimal, defaulting to 0.0 if None or invalid
            if stock_quantity is None:
                stock_quantity_dec = Decimal("0.0")
            elif isinstance(stock_quantity, Decimal):
                stock_quantity_dec = stock_quantity
            else:
                stock_quantity_dec = Decimal(str(stock_quantity)) # Convert if not None and not Decimal
                
        except InvalidOperation:
            logger.error(f"Invalid numeric value for unit_price or stock_quantity. Price: {unit_price}, Stock: {stock_quantity}", exc_info=True)
            raise ValueError("قیمت واحد یا موجودی اولیه نامعتبر است.")

        if unit_price_dec < Decimal("0"):
            raise ValueError("قیمت واحد نمی‌تواند منفی باشد.")
        
        # Now stock_quantity_dec is guaranteed to be a Decimal
        if product_type != ProductType.SERVICE and stock_quantity_dec < Decimal("0.0"):
            raise ValueError("موجودی اولیه برای کالاها نمی‌تواند منفی باشد.")

        if sku:
            existing_by_sku = self.get_product_by_sku(sku)
            if existing_by_sku:
                raise ValueError(f"محصولی با SKU '{sku}' از قبل موجود است (شناسه: {existing_by_sku.id}).")

        product_entity = ProductEntity(
            name=name,
            product_type=product_type,
            sku=sku,
            unit_price=unit_price, # باید Decimal باشد
            stock_quantity=stock_quantity_dec if product_type != ProductType.SERVICE else Decimal("0.0"),
            unit_of_measure=unit_of_measure,
            description=description,
            is_active=is_active,
           
        )
        
        created_product = self.product_repo.add(product_entity)
        if created_product:
            logger.info(f"Product '{created_product.name}' (ID: {created_product.id}) created successfully.")
        else:
            logger.error(f"Failed to create product: {name}")
        return created_product

    def update_product(self, product_id: int, update_data: Dict[str, Any]) -> Optional[ProductEntity]:
        """یک محصول موجود را به‌روزرسانی می‌کند."""
        logger.info(f"Attempting to update product ID: {product_id} with data: {update_data}")
        product_to_update = self.get_product_by_id(product_id)
        if not product_to_update:
            # خطا قبلاً در get_product_by_id لاگ شده است
            return None

        # بررسی یکتا بودن SKU اگر در حال تغییر است
        new_sku = update_data.get("sku")
        if new_sku is not None and new_sku != product_to_update.sku:
            existing_by_sku = self.get_product_by_sku(new_sku)
            if existing_by_sku and existing_by_sku.id != product_id:
                raise ValueError(f"محصول دیگری با SKU '{new_sku}' از قبل موجود است (شناسه: {existing_by_sku.id}).")

        changed = False
        for key, value in update_data.items():
            if key == "stock_quantity": # Prevent direct stock update here
                logger.warning(f"Attempt to update 'stock_quantity' via update_product for product ID {product_id} was ignored. Use adjust_stock.")
                continue

            if hasattr(product_to_update, key):
                processed_value = value
                # Type conversions (similar to create_product or as needed)
                if key == "unit_price" and value is not None:
                    try: processed_value = Decimal(str(value))
                    except InvalidOperation: logger.warning(f"Invalid decimal value for {key}: {value}. Skipping."); continue
                elif key == "product_type" and isinstance(value, ProductType):
                     processed_value = value
                elif key == "product_type" and isinstance(value, str):
                    try: processed_value = ProductType(value)
                    except ValueError: logger.warning(f"Invalid product_type value: {value}. Skipping."); continue

                if getattr(product_to_update, key) != processed_value:
                    setattr(product_to_update, key, processed_value)
                    changed = True
            else:
                logger.warning(f"Field '{key}' not found in ProductEntity during update of product ID {product_id}.")

        if changed:
            if self.product_repo.update(product_to_update):
                logger.info(f"Product ID {product_id} updated successfully.")
                return product_to_update
            else:
                logger.error(f"Failed to update product ID {product_id} in repository.")
                return None 
        else:
            logger.info(f"No changes detected for product ID {product_id}. Update not performed.")
            return product_to_update


    def delete_product(self, product_id: int) -> bool:
        """یک محصول را حذف می‌کند."""
        logger.warning(f"Attempting to delete product ID: {product_id}. This is a sensitive operation.")
        product_to_delete = self.get_product_by_id(product_id)
        if not product_to_delete:
            return False # خطا قبلاً لاگ شده

        # TODO: بررسی وابستگی‌ها قبل از حذف (مثلاً آیا در BOM ها، فاکتورها، یا حرکات انبار استفاده شده؟)
        # if self.is_product_in_use(product_id):
        #     raise ValueError(f"محصول با شناسه {product_id} قابل حذف نیست زیرا در سیستم استفاده شده است.")
        
        if self.product_repo.delete(product_id):
            logger.info(f"Product ID {product_id} deleted successfully.")
            return True
        else:
            logger.error(f"Failed to delete product ID {product_id} from repository.")
            return False

    def adjust_stock(self, 
                     product_id: int, 
                     quantity_change: Decimal, 
                     movement_type: InventoryMovementType, 
                     movement_date: datetime, # باید datetime باشد برای ثبت دقیق‌تر
                     reference_id: Optional[int] = None, 
                     reference_type: Optional[ReferenceType] = None,
                     description: Optional[str] = None,
                     unit_cost_for_movement: Optional[Decimal] = None # برای ثبت ارزش حرکت انبار
                     ) -> bool:
        """موجودی یک کالا را تعدیل کرده و حرکت انبار را ثبت می‌کند."""
        logger.debug(f"Adjusting stock for product ID {product_id} by {quantity_change}, type: {movement_type.value}")
        product = self.get_product_by_id(product_id)
        
        if not product: # <<< بررسی مهم برای رفع خطای Pylance
            logger.error(f"Cannot adjust stock: Product with ID {product_id} not found.")
            return False
        
        if product.product_type == ProductType.SERVICE:
            logger.warning(f"Stock adjustment not applicable for service product ID {product_id} ('{product.name}').")
            # برای خدمات، معمولاً تعدیل موجودی معنی ندارد.
            return True # یا False بسته به اینکه آیا این یک خطای عملیاتی محسوب می‌شود یا خیر

        # اطمینان از Decimal بودن مقادیر
        current_stock = product.stock_quantity if product.stock_quantity is not None else Decimal("0.0")
        change = Decimal(str(quantity_change)) # اطمینان از Decimal بودن ورودی

        new_stock = current_stock + change
        
        # جلوگیری از منفی شدن موجودی (بسته به سیاست شرکت)
        # if new_stock < Decimal("0.0"):
        #     logger.error(f"Stock for product {product.name} (ID: {product.id}) cannot become negative ({new_stock}). Adjustment by {change} failed.")
        #     return False

        product.stock_quantity = new_stock
        if not self.product_repo.update(product):
            logger.error(f"Failed to update stock quantity for product ID {product_id} in products table.")
            # TODO: Rollback? یا حداقل یک هشدار جدی
            return False
        
        logger.info(f"Stock for product '{product.name}' (ID: {product.id}) adjusted by {change}. Old: {current_stock}, New: {new_stock}. Movement Type: {movement_type.value}.")
        self.product_repo.update(product)
        
        # ۲. سپس یک رکورد برای حرکت انبار ایجاد می‌کنیم
        movement = InventoryMovementEntity(
            product_id=product_id,
            movement_date=movement_date or datetime.now(),
            quantity_change=quantity_change,
            movement_type=movement_type,
            reference_id=reference_id,
            reference_type=reference_type,
            description=description
        )
        saved_movement = self.inventory_movements_repo.add(movement)
        
        # --- لاگ کلیدی برای دیباگ ---
        if saved_movement and saved_movement.id:
            logger.info(f"SUCCESSFULLY SAVED INVENTORY MOVEMENT: ID={saved_movement.id}, ProductID={product_id}, Change={quantity_change}, RefType={reference_type}, RefID={reference_id}")
        else:
            logger.error(f"FAILED TO SAVE INVENTORY MOVEMENT for Product ID {product_id}")
        # --- پایان لاگ کلیدی ---

        logger.info(f"Stock for product '{product.name}' (ID: {product.id}) adjusted by {quantity_change}. Old: {current_stock}, New: {new_stock}.")
        return product

    def get_product_display_details(self, product_id: Optional[int]) -> Tuple[str, str, str]:
        """ نام، کد و واحد اندازه‌گیری محصول را برای نمایش برمی‌گرداند. """
        if product_id is None:
            return "نامشخص", "-", ""
        
        product = self.get_product_by_id(product_id)
        if product:
            product_name_display = product.name or "نامشخص"
            product_code_display = product.sku or (str(product.id) if product.id else "-")
            product_unit_measure = product.unit_of_measure or ""
            return product_name_display, product_code_display, product_unit_measure
        return f"ID:{product_id} یافت نشد", "-", ""
    def set_product_activity(self, product_id: int, is_active: bool) -> Optional[ProductEntity]:
        """
        Sets the active status of a product.
        """
        logger.debug(f"Setting active status for Product ID {product_id} to {is_active}")
        product_to_update = self.get_product_by_id(product_id)
        if not product_to_update:
            logger.warning(f"Product with ID {product_id} not found. Cannot set activity.")
            return None

        if product_to_update.is_active == is_active:
            logger.info(f"Product ID {product_id} is already in the desired active state ({is_active}). No update needed.")
            return product_to_update # Return the product as no change was made

        product_to_update.is_active = is_active

        updated = self.product_repo.update(product_to_update)
        if updated:
            logger.info(f"Active status for Product ID {product_id} successfully set to {is_active}.")
            return product_to_update
        else:
            logger.error(f"Failed to update active status for Product ID {product_id} in repository.")
            return None