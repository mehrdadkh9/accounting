# src/business_logic/bom_manager.py

from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal

from src.business_logic.entities.bom_entity import BOMEntity
from src.business_logic.entities.bom_item_entity import BomItemEntity # اطمینان از مسیر صحیح
from src.business_logic.entities.product_entity import ProductEntity

from src.data_access.bom_repository import BOMsRepository
from src.data_access.bom_item_repository import BomItemRepository
from src.business_logic.product_manager import ProductManager
from src.constants import ProductType 

import logging
logger = logging.getLogger(__name__)

class BomManager:
    def __init__(self, 
                 bom_repository: BOMsRepository, 
                 bom_item_repository: BomItemRepository,
                 product_manager: ProductManager):
        if bom_repository is None: raise ValueError("bom_repository cannot be None")
        if bom_item_repository is None: raise ValueError("bom_item_repository cannot be None")
        if product_manager is None: raise ValueError("product_manager cannot be None")
        
        self.bom_repo = bom_repository
        self.bom_item_repo = bom_item_repository
        self.product_manager = product_manager

    def _validate_bom_data(self, product_id: Optional[int], quantity_produced: Decimal, 
                           items_data: List[Dict[str, Any]], bom_id_to_exclude: Optional[int] = None, 
                           existing_bom_name: Optional[str] = None, new_bom_name: Optional[str] = None):
        if product_id is None:
            raise ValueError("محصول نهایی برای BOM باید مشخص شود.")
        finished_product = self.product_manager.get_product_by_id(product_id)
        if not finished_product:
            raise ValueError(f"محصول نهایی با شناسه {product_id} یافت نشد.")
        if finished_product.product_type == ProductType.SERVICE: # اطمینان از import ProductType
            raise ValueError(f"محصول '{finished_product.name}' از نوع خدمت است و نمی‌تواند BOM داشته باشد.")
        if quantity_produced <= Decimal("0"):
            raise ValueError("مقدار تولید شده توسط BOM باید مثبت باشد.")

        if new_bom_name is not None and new_bom_name.strip():
            if existing_bom_name is None or new_bom_name.strip() != existing_bom_name:
                criteria = {"name": new_bom_name.strip()}
                conflicting_boms = self.bom_repo.find_by_criteria(criteria)
                for bom_loop_var in conflicting_boms:
                    if bom_loop_var.id != bom_id_to_exclude:
                        raise ValueError(f"BOM دیگری با نام '{new_bom_name.strip()}' از قبل موجود است.")
        
        component_ids = set()
        # if not items_data and bom_id_to_exclude is None : 
        #     pass # BOM می‌تواند در ابتدا بدون آیتم باشد

        for idx, item_d_loop_validate in enumerate(items_data):
            comp_id = item_d_loop_validate.get("component_product_id")
            try:
                qty_req_str = str(item_d_loop_validate.get("quantity_required", "0"))
                if not qty_req_str.strip(): raise ValueError(f"مقدار برای قلم {idx+1} نامعتبر (رشته خالی).")
                qty_req = Decimal(qty_req_str)
            except Exception as e:
                raise ValueError(f"مقدار مورد نیاز برای قلم {idx+1} نامعتبر: '{item_d_loop_validate.get('quantity_required')}'. خطا: {e}")

            if comp_id is None: raise ValueError(f"شناسه جزء برای قلم {idx+1} مشخص نشده.")
            if not isinstance(comp_id, int): raise ValueError(f"شناسه جزء برای قلم {idx+1} باید عدد صحیح باشد.")
            component = self.product_manager.get_product_by_id(comp_id)
            if not component: raise ValueError(f"جزء با شناسه {comp_id} (قلم {idx+1}) یافت نشد.")
            
            if component.id is not None and component.id == product_id: # بررسی None بودن component.id
                raise ValueError(f"محصول نهایی '{finished_product.name}' نمی‌تواند جزء BOM خودش باشد.")
            if qty_req <= Decimal("0"): raise ValueError(f"مقدار جزء '{component.name}' (قلم {idx+1}) باید مثبت باشد.")
            if comp_id in component_ids: raise ValueError(f"جزء '{component.name}' (ID: {comp_id}) در BOM تکرار شده.")
            component_ids.add(comp_id)

    def create_bom(self, name: str, product_id: int, items_data: List[Dict[str, Any]],
                   quantity_produced: Decimal = Decimal("1.0"), description: Optional[str] = None,
                   is_active: bool = True) -> Optional[BOMEntity]:
        logger.info(f"Attempting to create BOM for Product ID: {product_id}, Name: {name}")
        if not name.strip(): raise ValueError("نام BOM نمی‌تواند خالی باشد.")
            
        self._validate_bom_data(product_id, quantity_produced, items_data, new_bom_name=name.strip())

        if is_active:
            active_boms = self.bom_repo.find_by_criteria({"product_id": product_id, "is_active": True})
            for abom in active_boms:
                if abom and abom.id is not None:
                    abom.is_active = False
                    self.bom_repo.update(abom)
                    logger.info(f"Deactivated existing active BOM ID {abom.id} for product ID {product_id}.")

        bom_entity = BOMEntity(
            name=name.strip(), product_id=product_id, quantity_produced=quantity_produced,
            description=description, is_active=is_active, creation_date=date.today(),
            last_modified_date=date.today()
        )
        
        created_bom_header = self.bom_repo.add(bom_entity)
        if not created_bom_header or not created_bom_header.id:
            logger.error("Failed to create BOM header.")
            return None

        logger.info(f"BOM Header ID {created_bom_header.id} created. Adding items...")
        saved_items: List[BomItemEntity] = []
        try:
            for item_data_loop in items_data:
                bom_item_instance = BomItemEntity(
                    bom_id=created_bom_header.id,
                    component_product_id=item_data_loop.get("component_product_id"), # استفاده از نام صحیح
                    quantity_required=Decimal(str(item_data_loop.get("quantity_required", "0.0"))), # استفاده از نام صحیح
                    notes=item_data_loop.get("notes") # استفاده از نام صحیح
                )
                saved_item = self.bom_item_repo.add(bom_item_instance)
                if not saved_item:
                    logger.error(f"Failed to add BOM item: {bom_item_instance}. Rolling back BOM header ID {created_bom_header.id}")
                    if created_bom_header and created_bom_header.id:
                        self.bom_item_repo.delete_by_bom_id(created_bom_header.id)
                        self.bom_repo.delete(created_bom_header.id)
                    return None
                saved_items.append(saved_item)
            
            created_bom_header.items = saved_items
            logger.info(f"Successfully created BOM ID {created_bom_header.id} with {len(saved_items)} items.")
            return self.get_bom_with_details(created_bom_header.id) # برگرداندن با جزئیات کالاها
        except Exception as e:
            logger.error(f"Error creating BOM items for BOM ID {created_bom_header.id}: {e}", exc_info=True)
            if created_bom_header and created_bom_header.id:
                self.bom_item_repo.delete_by_bom_id(created_bom_header.id)
                self.bom_repo.delete(created_bom_header.id)
            return None

    def get_bom_with_details(self, bom_id: int) -> Optional[BOMEntity]:
        logger.debug(f"Fetching BOM with details for ID: {bom_id}")
        bom = self.bom_repo.get_by_id(bom_id)
        if bom: 
            if bom.product_id:
                finished_product = self.product_manager.get_product_by_id(bom.product_id)
                if finished_product: bom.product_name = finished_product.name
                else: bom.product_name = f"محصول ID:{bom.product_id} یافت نشد"
            else: bom.product_name = "محصول نهایی مشخص نشده"
            
            items = self.bom_item_repo.get_by_bom_id(bom_id)
            detailed_items: List[BomItemEntity] = []
            for item_entity in items:
                if item_entity.component_product_id:
                    component = self.product_manager.get_product_by_id(item_entity.component_product_id)
                    if component:
                        item_entity.component_product_name = component.name
                        item_entity.component_product_code = component.sku or (str(component.id) if component.id else "-")
                        item_entity.component_unit_of_measure = component.unit_of_measure
                    else:
                        item_entity.component_product_name = f"جزء ID:{item_entity.component_product_id} یافت نشد"
                detailed_items.append(item_entity)
            bom.items = detailed_items
            logger.debug(f"Fetched BOM ID {bom.id if bom and bom.id else 'N/A'} with {len(detailed_items)} detailed items.")
        else: logger.warning(f"BOM with ID {bom_id} not found.")
        return bom

    def get_all_boms_with_product_names(self) -> List[BOMEntity]:
        logger.debug("Fetching all BOMs with product names.")
        all_boms = self.bom_repo.get_all(order_by="name ASC") 
        for bom_loop_var in all_boms: 
            if bom_loop_var.product_id:
                product = self.product_manager.get_product_by_id(bom_loop_var.product_id)
                if product: bom_loop_var.product_name = product.name
                else: bom_loop_var.product_name = f"محصول ID:{bom_loop_var.product_id} یافت نشد"
            else: bom_loop_var.product_name = "بدون محصول نهایی"
        return all_boms

    def update_bom(self, bom_id: int, name: Optional[str] = None, product_id: Optional[int] = None, 
                   items_data: Optional[List[Dict[str, Any]]] = None, 
                   quantity_produced: Optional[Decimal] = None, description: Optional[str] = None,
                   is_active: Optional[bool] = None) -> Optional[BOMEntity]:
        logger.info(f"Attempting to update BOM ID: {bom_id}")
        
        bom_to_update = self.bom_repo.get_by_id(bom_id)
        if not bom_to_update or bom_to_update.id is None:
            logger.error(f"BOM with ID {bom_id} not found for update.")
            return None

        original_name = bom_to_update.name
        new_name_to_validate = name.strip() if name is not None and name.strip() else None
        temp_product_id = product_id if product_id is not None else bom_to_update.product_id
        temp_qty_produced = quantity_produced if quantity_produced is not None else bom_to_update.quantity_produced
        
        items_for_validation = items_data if items_data is not None else [] 
        if items_data is not None or (name is not None and name.strip() != original_name) or \
           (product_id is not None and product_id != bom_to_update.product_id) or \
           (quantity_produced is not None and quantity_produced != bom_to_update.quantity_produced) :
             self._validate_bom_data(temp_product_id, temp_qty_produced, items_for_validation, 
                                   bom_id_to_exclude=bom_id, 
                                   existing_bom_name=original_name, 
                                   new_bom_name=new_name_to_validate)

        if is_active is True and not bom_to_update.is_active and temp_product_id is not None:
            active_boms = self.bom_repo.find_by_criteria({"product_id": temp_product_id, "is_active": True})
            for abom in active_boms:
                if abom.id != bom_id:
                    abom.is_active = False
                    self.bom_repo.update(abom)
                    logger.info(f"Deactivated existing active BOM ID {abom.id} for product ID {temp_product_id} during update of BOM ID {bom_id}.")

        if name is not None: bom_to_update.name = name.strip()
        if product_id is not None: bom_to_update.product_id = product_id
        if quantity_produced is not None: bom_to_update.quantity_produced = quantity_produced
        if description is not None: bom_to_update.description = description
        if is_active is not None: bom_to_update.is_active = is_active
        bom_to_update.last_modified_date = date.today()
            
        updated_bom_header = self.bom_repo.update(bom_to_update)
        if not updated_bom_header:
            logger.error(f"Failed to update BOM header ID: {bom_id}.")
            return None
        
        if items_data is not None: 
            logger.info(f"Updating items for BOM ID: {bom_id}. Deleting old items first.")
            self.bom_item_repo.delete_by_bom_id(bom_id)
            
            saved_new_items: List[BomItemEntity] = []
            for item_data_loop_var in items_data:
                new_bom_item = BomItemEntity(
                    bom_id=bom_id,
                    component_product_id=item_data_loop_var.get("component_product_id"),
                    quantity_required=Decimal(str(item_data_loop_var.get("quantity_required","0.0"))),
                    notes=item_data_loop_var.get("notes")
                )
                saved_item = self.bom_item_repo.add(new_bom_item)
                if not saved_item:
                    logger.error(f"Failed to add new BOM item during update: {new_bom_item}.")
                    return None
                saved_new_items.append(saved_item)
            logger.info(f"Successfully updated items for BOM ID {bom_id}. New item count: {len(saved_new_items)}")

        return self.get_bom_with_details(bom_id)

    def delete_bom(self, bom_id: int) -> bool:
        logger.warning(f"Attempting to delete BOM ID: {bom_id} and all its items.")
        
        if not self.bom_item_repo.delete_by_bom_id(bom_id):
            logger.error(f"Failed to delete items for BOM ID: {bom_id}, but will attempt to delete header.")
        
        if self.bom_repo.delete(bom_id): 
            logger.info(f"Successfully deleted BOM ID: {bom_id}.")
            return True
        else:
            logger.error(f"Failed to delete BOM header ID: {bom_id}.")
            return False

    def get_active_bom_for_product_with_details(self, product_id: int) -> Optional[BOMEntity]:
        logger.debug(f"Fetching active BOM with details for Product ID: {product_id}")
        active_bom_header = self.bom_repo.get_active_bom_for_product(product_id)
        if active_bom_header and active_bom_header.id:
            return self.get_bom_with_details(active_bom_header.id)
        logger.debug(f"No active BOM found for Product ID: {product_id}")
        return None

    # متد calculate_required_materials منطقاً به BomManager تعلق دارد
    def calculate_required_materials(self, product_id_to_produce: int, quantity_to_produce: Decimal, bom_id_override: Optional[int] = None) -> List[Dict[str, Any]]:
        """مواد اولیه مورد نیاز برای تولید تعداد مشخصی از محصول را محاسبه می‌کند."""
        bom = self._get_bom_for_production(product_id_to_produce, bom_id_override)
        
        if not bom:
            bom_identifier = f"ID {bom_id_override}" if bom_id_override else "فعال"
            raise ValueError(f"BOM {bom_identifier} برای محصول ID {product_id_to_produce} یافت نشد.")
        
        # --- اصلاح خطای ۲۳۹ ---
        bom_name_for_log = bom.name if bom and hasattr(bom, 'name') and bom.name else f"BOM ID {bom.id if bom and bom.id else 'N/A'}"
        if not bom.items:
            raise ValueError(f"اقلامی برای BOM '{bom_name_for_log}' (محصول ID {product_id_to_produce}) یافت نشد.")
        # --- پایان اصلاح ---

        required_materials = []
        for item_entity in bom.items: 
            item_qty_req = item_entity.quantity_required if item_entity.quantity_required is not None else Decimal("0")
            bom_qty_prod = bom.quantity_produced if bom.quantity_produced is not None else Decimal("1.0")
            if bom_qty_prod == Decimal("0"): bom_qty_prod = Decimal("1.0") # جلوگیری از تقسیم بر صفر

            # --- اصلاح خطاهای ۲۲۸، ۲۲۹، ۲۳۱ ---
            actual_quantity_needed = (item_qty_req / bom_qty_prod) * quantity_to_produce
            
            if item_entity.component_product_id is None:
                 logger.warning(f"Skipping BOM item without component_product_id for BOM ID {bom.id if bom and bom.id else 'N/A'}")
                 continue

            required_materials.append({
                "component_product_id": item_entity.component_product_id,
                "component_product_name": item_entity.component_product_name,
                "quantity_needed": actual_quantity_needed,
                "unit_of_measure": item_entity.component_unit_of_measure
            })
            # --- پایان اصلاحات ---
        return required_materials

    def _get_bom_for_production(self, product_id: int, bom_id_override: Optional[int] = None) -> Optional[BOMEntity]:
        """BOM مورد نیاز برای تولید را پیدا می‌کند. (متد کمکی)"""
        if bom_id_override:
            bom = self.get_bom_with_details(bom_id_override)
            if bom and bom.product_id != product_id:
                raise ValueError(f"BOM ID {bom_id_override} به محصول ID {product_id} تعلق ندارد.")
            return bom
        return self.get_active_bom_for_product_with_details(product_id)