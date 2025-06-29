# src/business_logic/production_manager.py
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# --- Import Entity ها ---
from src.business_logic.entities.manual_production_entity import ManualProductionEntity
from src.business_logic.entities.consumed_material_entity import ConsumedMaterialEntity
# از ProductionOrderEntity دیگر استفاده نمی‌شود

# --- Import Repository ها ---
from src.data_access.manual_production_repository import ManualProductionRepository
from src.data_access.consumed_material_repository import ConsumedMaterialRepository
# از ProductionOrderRepository دیگر استفاده نمی‌شود

# --- Import سایر Manager ها ---
from src.business_logic.product_manager import ProductManager
from src.business_logic.financial_transaction_manager import FinancialTransactionManager # برای آثار مالی (اختیاری)
from src.business_logic.account_manager import AccountManager # برای آثار مالی (اختیاری)

# --- Import Constants ---
from src.constants import (
    InventoryMovementType, 
    ReferenceType, 
    FinancialTransactionType, # اگر آثار مالی ثبت می‌کنید
    ProductType 
)
import logging
logger = logging.getLogger(__name__)

# مثال برای accounts_config اگر بخواهید آثار مالی را ثبت کنید
# DEFAULT_ACCOUNTS_CONFIG_FOR_MANUAL_PRODUCTION = {
#     "work_in_progress_account_id": 15, 
#     "finished_goods_inventory_account_id_default": 13,
#     "raw_materials_inventory_account_id_default": 12,
# }

class ProductionManager:
    def __init__(self, 
                 product_manager: ProductManager,
                 manual_production_repository: ManualProductionRepository,
                 consumed_material_repository: ConsumedMaterialRepository,
                 ft_manager: Optional[FinancialTransactionManager] = None, 
                 account_manager: Optional[AccountManager] = None, 
                 accounts_config: Optional[Dict[str, Any]] = None 
                 ):
        
        if product_manager is None: raise ValueError("product_manager cannot be None")
        if manual_production_repository is None: raise ValueError("manual_production_repository cannot be None")
        if consumed_material_repository is None: raise ValueError("consumed_material_repository cannot be None")
        
        self.product_manager = product_manager
        self.manual_production_repo = manual_production_repository
        self.consumed_material_repo = consumed_material_repository
        self.ft_manager = ft_manager
        self.account_manager = account_manager # برای آثار مالی لازم است
        self.accounts_config = accounts_config if accounts_config is not None else {}

    def _get_active_fiscal_year_id(self) -> Optional[int]: # متد کمکی موقت
        # TODO: این متد باید سال مالی فعال واقعی را از FiscalYearManager دریافت کند
        logger.warning("ProductionManager: Using hardcoded fiscal year ID 1. Needs proper implementation with FiscalYearManager.")
        return 1 

    def record_manual_production(self, 
                                 production_date: date,
                                 finished_product_id: int,
                                 quantity_produced: Decimal,
                                 consumed_items_data: List[Dict[str, Any]], 
                                 description: Optional[str] = None
                                 ) -> Optional[ManualProductionEntity]:
        logger.info(f"Attempting to record manual production for Product ID {finished_product_id}, Quantity: {quantity_produced}")

        if not isinstance(quantity_produced, Decimal) or quantity_produced <= Decimal("0"):
            raise ValueError("مقدار تولید شده باید یک عدد Decimal مثبت باشد.")
        if not finished_product_id:
            raise ValueError("محصول نهایی برای تولید باید مشخص شود.")
        
        finished_product = self.product_manager.get_product_by_id(finished_product_id)
        if not finished_product:
            raise ValueError(f"محصول نهایی با شناسه {finished_product_id} یافت نشد.")
        if finished_product.product_type == ProductType.SERVICE:
            raise ValueError("نمی‌توان برای محصول خدماتی، تولید ثبت کرد.")

        # اعتبارسنجی مواد اولیه مصرفی (اگر خالی باشد، می‌توان اجازه داد یا خطا داد)
        # if not consumed_items_data:
        #     raise ValueError("حداقل یک ماده اولیه مصرفی باید برای تولید مشخص شود.") 
        
        valid_consumed_entities: List[ConsumedMaterialEntity] = []
        if consumed_items_data: # فقط اگر آیتمی وجود دارد پردازش کن
            for item_data in consumed_items_data:
                comp_id = item_data.get("component_product_id")
                qty_consumed_val = item_data.get("quantity_consumed")

                if comp_id is None or qty_consumed_val is None:
                    raise ValueError("هر ماده اولیه مصرفی باید شناسه محصول و مقدار مصرفی داشته باشد.")
                
                try:
                    qty_consumed_dec = Decimal(str(qty_consumed_val))
                    if qty_consumed_dec <= Decimal("0"):
                        raise ValueError(f"مقدار مصرفی برای جزء ID {comp_id} باید مثبت باشد.")
                except InvalidOperation:
                    raise ValueError(f"مقدار مصرفی نامعتبر (باید عددی باشد) برای جزء ID {comp_id}.")

                component = self.product_manager.get_product_by_id(comp_id)
                if not component:
                    raise ValueError(f"ماده اولیه با شناسه {comp_id} یافت نشد.")
                if component.id == finished_product_id:
                    raise ValueError(f"محصول '{finished_product.name}' نمی‌تواند به عنوان ماده اولیه خودش مصرف شود.")
                
                valid_consumed_entities.append(ConsumedMaterialEntity(
                    component_product_id=comp_id,
                    quantity_consumed=qty_consumed_dec,
                    notes=item_data.get("notes")
                ))
        
        created_header: Optional[ManualProductionEntity] = None
        # --- مدیریت تراکنش دیتابیس (نیاز به پیاده‌سازی در DatabaseManager یا استفاده از ORM دارد) ---
        # self.manual_production_repo.db_manager.begin_transaction() 
        try:
            mp_header_entity = ManualProductionEntity(
                production_date=production_date,
                finished_product_id=finished_product_id,
                quantity_produced=quantity_produced,
                description=description
            )
            created_header = self.manual_production_repo.add(mp_header_entity)
            if not created_header or not created_header.id:
                # self.manual_production_repo.db_manager.rollback_transaction()
                raise Exception("خطا در ایجاد هدر تولید دستی.") # جزئیات بیشتر می‌تواند از repo بیاید
            
            saved_consumed_item_entities: List[ConsumedMaterialEntity] = []
            if valid_consumed_entities:
                for item_entity_to_save in valid_consumed_entities:
                    item_entity_to_save.manual_production_id = created_header.id
                    saved_item = self.consumed_material_repo.add(item_entity_to_save)
                    if not saved_item:
                        raise Exception(f"خطا در ذخیره ماده مصرفی ID: {item_entity_to_save.component_product_id}.")
                    saved_consumed_item_entities.append(saved_item)
            
            created_header.consumed_items = saved_consumed_item_entities
            logger.info(f"Manual Production Header ID {created_header.id} and {len(saved_consumed_item_entities)} items saved.")

            movement_datetime = datetime.combine(production_date, datetime.min.time())
            
            # تعدیل موجودی محصول نهایی (افزایش)
            if not self.product_manager.adjust_stock(
                product_id=finished_product_id, quantity_change=quantity_produced,
                movement_type=InventoryMovementType.MANUAL_PRODUCTION_RECEIPT, 
                movement_date=movement_datetime, reference_id=created_header.id,
                reference_type=ReferenceType.MANUAL_PRODUCTION,
                description=f"تولید دستی: {finished_product.name} - {description or ''}"
            ):
                raise Exception(f"خطا در تعدیل موجودی محصول نهایی ID {finished_product_id}.")
            
            # تعدیل موجودی مواد اولیه مصرفی (کاهش)
            for consumed_item_entity in saved_consumed_item_entities:
                comp_prod_info = self.product_manager.get_product_by_id(consumed_item_entity.component_product_id) # type: ignore
                comp_prod_name = comp_prod_info.name if comp_prod_info else f"ID {consumed_item_entity.component_product_id}"
                if not self.product_manager.adjust_stock(
                    product_id=consumed_item_entity.component_product_id, # type: ignore
                    quantity_change= -consumed_item_entity.quantity_consumed, # type: ignore
                    movement_type=InventoryMovementType.MANUAL_PRODUCTION_ISSUE,
                    movement_date=movement_datetime, reference_id=created_header.id,
                    reference_type=ReferenceType.MANUAL_PRODUCTION,
                    description=f"مصرف ماده اولیه: {comp_prod_name} برای MP ID {created_header.id}"
                ):
                    raise Exception(f"خطا در تعدیل موجودی ماده اولیه ID {consumed_item_entity.component_product_id}.")

            # (اختیاری) ثبت آثار مالی
            # if self.ft_manager and self.account_manager:
            #     self._record_manual_production_financials(created_header)

            # self.manual_production_repo.db_manager.commit_transaction()
            logger.info(f"Manual production MP ID {created_header.id} recorded and stock adjusted successfully.")
            return created_header

        except Exception as e:
            logger.error(f"Error in record_manual_production for product ID {finished_product_id}: {e}", exc_info=True)
            # self.manual_production_repo.db_manager.rollback_transaction()
            # اگر هدر ایجاد شده اما عملیات کامل نشده، آن را حذف کنید
            if created_header and created_header.id:
                 # ابتدا اقلام مصرفی مرتبط را پاک کنید
                self.consumed_material_repo.delete_by_manual_production_id(created_header.id)
                self.manual_production_repo.delete(created_header.id)
                logger.info(f"Rolled back Manual Production Header ID {created_header.id} due to error.")
            raise # خطا را برای نمایش در UI دوباره raise کنید
    
    def get_all_manual_productions_summary(self) -> List[ManualProductionEntity]:
        logger.debug("Fetching all manual production summaries.")
        headers = self.manual_production_repo.get_all(order_by="production_date DESC, id DESC")
        for header in headers:
            if header.finished_product_id and self.product_manager:
                product = self.product_manager.get_product_by_id(header.finished_product_id)
                if product:
                    header.finished_product_name = product.name
        return headers

    def get_manual_production_with_details(self, manual_production_id: int) -> Optional[ManualProductionEntity]:
        logger.debug(f"Fetching details for manual production ID: {manual_production_id}")
        header = self.manual_production_repo.get_by_id(manual_production_id)
        if not header: return None
        
        consumed_items = self.consumed_material_repo.get_by_manual_production_id(manual_production_id)
        for item in consumed_items:
            if item.component_product_id and self.product_manager:
                product_details = self.product_manager.get_product_by_id(item.component_product_id)
                if product_details:
                    item.component_product_name = product_details.name
                    item.component_product_code = product_details.sku
                    item.component_unit_of_measure = product_details.unit_of_measure
        header.consumed_items = consumed_items

        if header.finished_product_id and self.product_manager:
            finished_product_details = self.product_manager.get_product_by_id(header.finished_product_id)
            if finished_product_details:
                header.finished_product_name = finished_product_details.name
        return header

    def update_manual_production(self, production_id: int, update_data: Dict[str, Any]) -> Optional[ManualProductionEntity]:
        """
        یک رکورد تولید دستی موجود را به‌روزرسانی می‌کند.
        update_data باید شامل کلیدهای: 
        "production_date", "finished_product_id", "quantity_produced", "description", 
        و "consumed_items_data" (لیستی از دیکشنری‌های اقلام مصرفی) باشد.
        """
        logger.info(f"Attempting to update manual production ID: {production_id}")
        
        # ۱. هدر تولید دستی موجود را واکشی کنید
        original_production_header = self.get_manual_production_with_details(production_id)
        if not original_production_header:
            raise ValueError(f"رکورد تولید دستی با شناسه {production_id} یافت نشد.")

        # --- مدیریت تراکنش دیتابیس ---
        # self.manual_production_repo.db_manager.begin_transaction()
        try:
            # ۲. داده‌های هدر را به‌روز کنید
            original_production_header.production_date = update_data.get("production_date", original_production_header.production_date)
            original_production_header.finished_product_id = update_data.get("finished_product_id", original_production_header.finished_product_id)
            original_production_header.quantity_produced = Decimal(str(update_data.get("quantity_produced", original_production_header.quantity_produced)))
            original_production_header.description = update_data.get("description", original_production_header.description)
            
            updated_header = self.manual_production_repo.update(original_production_header)
            if not updated_header:
                raise Exception("خطا در به‌روزرسانی هدر تولید دستی.")
            
            # ۳. اقلام مصرفی قدیمی را حذف کنید
            self.consumed_material_repo.delete_by_manual_production_id(production_id)
            
            # ۴. اقلام مصرفی جدید را اضافه کنید
            new_consumed_items_data = update_data.get("consumed_items_data", [])
            saved_consumed_items: List[ConsumedMaterialEntity] = []
            for item_data in new_consumed_items_data:
                comp_id = item_data.get("component_product_id")
                qty_consumed_val = item_data.get("quantity_consumed")
                if comp_id is None or qty_consumed_val is None: continue # یا خطا
                
                qty_consumed_dec = Decimal(str(qty_consumed_val))
                if qty_consumed_dec <= Decimal("0"): continue # یا خطا

                item_entity = ConsumedMaterialEntity(
                    manual_production_id=production_id,
                    component_product_id=comp_id,
                    quantity_consumed=qty_consumed_dec,
                    notes=item_data.get("notes")
                )
                saved_item = self.consumed_material_repo.add(item_entity)
                if not saved_item:
                    raise Exception("خطا در ذخیره اقلام مصرفی جدید هنگام ویرایش.")
                saved_consumed_items.append(saved_item)
            
            updated_header.consumed_items = saved_consumed_items

            # ۵. تعدیل موجودی‌ها بر اساس *تفاوت* (این بخش پیچیده است و نیاز به منطق دقیق دارد)
            # برای سادگی، فعلاً فرض می‌کنیم که کاربر مسئول اطمینان از صحت مقادیر است
            # و ما فقط موجودی‌ها را بر اساس مقادیر جدید تعدیل می‌کنیم.
            # این به معنی این است که ابتدا باید آثار تعدیلات قبلی را خنثی کنیم و سپس تعدیلات جدید را اعمال نماییم.
            # یک راه ساده‌تر (اما نه کاملاً دقیق از نظر حسابداری انبار در برخی سناریوها) این است که:
            # ابتدا موجودی‌های قبلی را برگردانیم و سپس موجودی‌های جدید را اعمال کنیم.

            # الف) برگرداندن تعدیلات موجودی قبلی:
            # افزایش موجودی مواد اولیه قبلی
            if original_production_header.consumed_items:
                for old_item in original_production_header.consumed_items:
                    self.product_manager.adjust_stock(old_item.component_product_id, # type: ignore
                                                      old_item.quantity_consumed, # type: ignore
                                                      InventoryMovementType.MANUAL_PRODUCTION_ADJUST_RETURN, # نوع جدید
                                                      datetime.combine(updated_header.production_date, datetime.min.time()),
                                                      reference_id=production_id, reference_type=ReferenceType.MANUAL_PRODUCTION,
                                                      description=f"بازگشت مصرف برای ویرایش تولید دستی ID {production_id}")
            # کاهش موجودی محصول نهایی قبلی
            if original_production_header.finished_product_id is not None and original_production_header.quantity_produced > Decimal("0"):
                self.product_manager.adjust_stock(original_production_header.finished_product_id,
                                                  -original_production_header.quantity_produced,
                                                  InventoryMovementType.MANUAL_PRODUCTION_ADJUST_REVERSE, # نوع جدید
                                                  datetime.combine(updated_header.production_date, datetime.min.time()),
                                                  reference_id=production_id, reference_type=ReferenceType.MANUAL_PRODUCTION,
                                                  description=f"بازگشت تولید برای ویرایش تولید دستی ID {production_id}")
            
            # ب) اعمال تعدیلات موجودی جدید:
            movement_datetime_updated = datetime.combine(updated_header.production_date, datetime.min.time())
            finished_product_new = self.product_manager.get_product_by_id(updated_header.finished_product_id) # type: ignore
            if not self.product_manager.adjust_stock(
                product_id=updated_header.finished_product_id, quantity_change=updated_header.quantity_produced, # type: ignore
                movement_type=InventoryMovementType.MANUAL_PRODUCTION_RECEIPT, movement_date=movement_datetime_updated,
                reference_id=production_id, reference_type=ReferenceType.MANUAL_PRODUCTION,
                description=f"تولید دستی (ویرایش شده): {finished_product_new.name if finished_product_new else ''}" # type: ignore
            ):
                raise Exception("خطا در تعدیل موجودی محصول نهایی (ویرایش).")

            for new_item in saved_consumed_items:
                comp_prod_info_new = self.product_manager.get_product_by_id(new_item.component_product_id) # type: ignore
                comp_prod_name_new = comp_prod_info_new.name if comp_prod_info_new else f"ID {new_item.component_product_id}"
                if not self.product_manager.adjust_stock(
                    product_id=new_item.component_product_id, quantity_change= -new_item.quantity_consumed, # type: ignore
                    movement_type=InventoryMovementType.MANUAL_PRODUCTION_ISSUE, movement_date=movement_datetime_updated,
                    reference_id=production_id, reference_type=ReferenceType.MANUAL_PRODUCTION,
                    description=f"مصرف ماده (ویرایش شده): {comp_prod_name_new} برای MP ID {production_id}"
                ):
                    raise Exception(f"خطا در تعدیل موجودی ماده اولیه (ویرایش) ID {new_item.component_product_id}.")

            # ۶. (اختیاری) اصلاح یا ایجاد مجدد آثار مالی
            # self.manual_production_repo.db_manager.commit_transaction()
            logger.info(f"Manual production MP ID {production_id} updated successfully.")
            return updated_header
            
        except Exception as e:
            logger.error(f"Error in update_manual_production for ID {production_id}: {e}", exc_info=True)
            # self.manual_production_repo.db_manager.rollback_transaction()
            raise

    def delete_manual_production(self, production_id: int) -> bool:
        logger.warning(f"Attempting to delete manual production ID: {production_id}. This action might require reversing stock adjustments manually or through a separate process.")
        
        # واکشی رکورد برای اطلاع از مقادیر جهت تعدیل معکوس موجودی (اگر لازم است)
        # production_to_delete = self.get_manual_production_with_details(production_id)
        # if not production_to_delete:
        #     logger.error(f"Manual production with ID {production_id} not found for deletion.")
        #     return False

        # self.manual_production_repo.db_manager.begin_transaction()
        try:
            # ابتدا اقلام مصرفی مرتبط را حذف کنید
            if not self.consumed_material_repo.delete_by_manual_production_id(production_id):
                # self.manual_production_repo.db_manager.rollback_transaction()
                logger.error(f"Failed to delete consumed items for manual production ID {production_id}.")
                return False
            
            # سپس هدر تولید دستی را حذف کنید
            if not self.manual_production_repo.delete(production_id):
                # self.manual_production_repo.db_manager.rollback_transaction()
                logger.error(f"Failed to delete manual production header for ID {production_id}.")
                return False

            # هشدار: حذف رکورد تولید، به طور خودکار موجودی انبار را برنمی‌گرداند.
            # این کار باید با یک عملیات تعدیل موجودی جداگانه انجام شود اگر لازم است.
            # یا اینکه منطق تعدیل معکوس در اینجا پیاده‌سازی شود (پیچیده‌تر).
            logger.info(f"Manual production record ID {production_id} and its items deleted successfully. Stock levels were NOT automatically reversed.")
            # self.manual_production_repo.db_manager.commit_transaction()
            return True
        except Exception as e:
            logger.error(f"Error deleting manual production ID {production_id}: {e}", exc_info=True)
            # self.manual_production_repo.db_manager.rollback_transaction()
            return False