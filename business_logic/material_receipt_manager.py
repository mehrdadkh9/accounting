# src/business_logic/material_receipt_manager.py

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from src.business_logic.entities.material_receipt_entity import MaterialReceiptEntity
from src.data_access.material_receipts_repository import MaterialReceiptsRepository
from src.business_logic.product_manager import ProductManager
from src.business_logic.purchase_order_manager import PurchaseOrderManager
from src.data_access.purchase_order_items_repository import PurchaseOrderItemsRepository
from src.business_logic.person_manager import PersonManager

from src.constants import InventoryMovementType, ReferenceType, PersonType, ProductType
import logging

logger = logging.getLogger(__name__)

class MaterialReceiptManager:
    def __init__(self,
                 receipts_repository: MaterialReceiptsRepository,
                 product_manager: ProductManager,
                 po_manager: PurchaseOrderManager,
                 po_items_repository: PurchaseOrderItemsRepository, # Used to get PO item details like price
                 person_manager: PersonManager):

        if receipts_repository is None: raise ValueError("receipts_repository cannot be None")
        if product_manager is None: raise ValueError("product_manager cannot be None")
        if po_manager is None: raise ValueError("po_manager cannot be None")
        if po_items_repository is None: raise ValueError("po_items_repository cannot be None")
        if person_manager is None: raise ValueError("person_manager cannot be None")

        self.receipts_repository = receipts_repository
        self.product_manager = product_manager
        self.po_manager = po_manager
        self.po_items_repository = po_items_repository
        self.person_manager = person_manager

    def record_material_receipt(self,
                                receipt_date: date,
                                product_id: int,
                                quantity_received: float,
                                supplier_person_id: int, # This is the person_id of the supplier
                                purchase_order_id: Optional[int] = None,
                                purchase_order_item_id: Optional[int] = None, 
                                unit_price_override: Optional[float] = None, 
                                description: Optional[str] = None,
                                fiscal_year_id: Optional[int] = None
                                ) -> Optional[MaterialReceiptEntity]:
        if not isinstance(receipt_date, date): raise ValueError("تاریخ رسید نامعتبر است.")
        if not isinstance(product_id, int): raise ValueError("شناسه کالا نامعتبر است.")
        if not isinstance(quantity_received, (int, float)) or quantity_received <= 0:
            raise ValueError("تعداد دریافت شده باید مثبت باشد.")
        if not isinstance(supplier_person_id, int): raise ValueError("شناسه تامین‌کننده نامعتبر است.")

        supplier = self.person_manager.get_person_by_id(supplier_person_id)
        if not supplier:
            raise ValueError(f"تامین‌کننده‌ای با شناسه {supplier_person_id} یافت نشد.")
        if supplier.person_type != PersonType.SUPPLIER:
            raise ValueError(f"شخص با شناسه {supplier_person_id} یک تامین‌کننده معتبر نیست.")

        product = self.product_manager.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"کالایی با شناسه {product_id} یافت نشد.")

        actual_unit_price_for_receipt = unit_price_override

        if purchase_order_id:
            po = self.po_manager.get_purchase_order_with_items(purchase_order_id) # Fetches PO with its items
            if not po:
                raise ValueError(f"سفارش خرید با شناسه {purchase_order_id} یافت نشد.")
            if po.person_id != supplier_person_id: # Validate supplier consistency
                raise ValueError("تامین‌کننده مشخص شده در رسید با تامین‌کننده سفارش خرید مغایرت دارد.")

            if purchase_order_item_id:
                po_item = self.po_items_repository.get_by_id(purchase_order_item_id) # Get specific PO item
                if not po_item or po_item.purchase_order_id != purchase_order_id or po_item.product_id != product_id:
                    raise ValueError(f"قلم سفارش خرید با شناسه {purchase_order_item_id} برای این سفارش/کالا معتبر نیست.")
                
                if actual_unit_price_for_receipt is None: # Default to PO item price if not overridden
                    actual_unit_price_for_receipt = po_item.unit_price
                
            elif actual_unit_price_for_receipt is None and po.items: # PO linked, no specific item, try to find price
                matching_po_items = [item for item in po.items if item.product_id == product_id]
                if matching_po_items:
                    actual_unit_price_for_receipt = matching_po_items[0].unit_price
                else:
                    raise ValueError(f"قیمت واحد برای کالا {product_id} در رسید مشخص نشده و در سفارش خرید مرتبط نیز یافت نشد.")
        
        if actual_unit_price_for_receipt is None: 
             raise ValueError(f"قیمت واحد برای کالا {product_id} در رسید مشخص نشده است (و از سفارش خرید نیز قابل استخراج نیست).")
        if not isinstance(actual_unit_price_for_receipt, (int, float)) or actual_unit_price_for_receipt < 0:
            raise ValueError("قیمت واحد نامعتبر است.")

        receipt_entity = MaterialReceiptEntity(
            receipt_date=receipt_date,
            person_id=supplier_person_id, # Use person_id as per entity definition
            product_id=product_id,
            quantity_received=quantity_received,
            unit_price=actual_unit_price_for_receipt,
            purchase_order_id=purchase_order_id,
            purchase_order_item_id=purchase_order_item_id,
            description=description,
            fiscal_year_id=fiscal_year_id
        )
        
        try:
            created_receipt = self.receipts_repository.add(receipt_entity)
            if not created_receipt or not created_receipt.id:
                raise Exception("خطا در ذخیره رسید مواد.")
            
            logger.info(f"Material Receipt ID {created_receipt.id} recorded for product ID {product_id}, quantity {quantity_received}.")

            # ۱. تعدیل موجودی انبار
            self.product_manager.adjust_stock(
                product_id=product_id,
                quantity_change=quantity_received,
                movement_type=InventoryMovementType.RECEIPT,
                movement_date=datetime.combine(receipt_date, datetime.min.time()),
                reference_id=created_receipt.id,
                reference_type=ReferenceType.MATERIAL_RECEIPT,
                description=f"Receipt from Supplier ID {supplier_person_id}" + (f" (PO: {purchase_order_id})" if purchase_order_id else "")
            )

            # ۲. به‌روزرسانی سفارش خرید در صورت ارتباط
            # این بلوک if/elif/else باید تورفتگی صحیح داشته باشد
            if purchase_order_id and unit_price_override is not None:
                value_of_this_receipt = quantity_received * unit_price_override
                logger.info(f"Attempting to update PO. Calling po_manager.update_received_value for PO ID {purchase_order_id} with change {value_of_this_receipt}")
                try:
                    updated_po = self.po_manager.update_received_value(
                        po_id=purchase_order_id,
                        value_of_goods_received_change=value_of_this_receipt
                    )
                    if updated_po:
                        logger.info(f"PO ID {purchase_order_id} update_received_value call returned. New PO received_amount: {updated_po.received_amount}, Status: {updated_po.status.value}")
                    else:
                        logger.warning(f"PO ID {purchase_order_id} update_received_value call returned None or PO not found by manager.")
                except Exception as e_po_update:
                    logger.error(f"Error calling po_manager.update_received_value for PO ID {purchase_order_id}: {e_po_update}", exc_info=True)
            elif not purchase_order_id: # اگر سفارش خریدی وجود ندارد
                logger.info("No purchase_order_id provided for this receipt, skipping PO update.")
            elif unit_price_override is None: # اگر سفارش خرید وجود دارد اما قیمت واحد برای محاسبه ارزش رسید در دسترس نیست
                # این شرط زمانی برقرار می‌شود که purchase_order_id مقدار دارد اما unit_price_override مقدار None دارد
                logger.warning(f"unit_price_override is None for PO ID {purchase_order_id}, cannot calculate value_of_this_receipt. Skipping PO update.")
            
            return created_receipt

        except Exception as e:
            logger.error(f"Error recording material receipt: {e}", exc_info=True)
            # در اینجا منطق rollback (حذف رسید ایجاد شده، برگرداندن تعدیل انبار) می‌تواند پیچیده‌تر باشد
            raise
            return created_receipt
        
    def get_all_receipts(self) -> List[MaterialReceiptEntity]:
        """Retrieves all material receipts."""
        logger.debug("Fetching all material receipts.")
        return self.receipts_repository.get_all()
    def get_material_receipt_by_id(self, receipt_id: int) -> Optional[MaterialReceiptEntity]:
        return self.receipts_repository.get_by_id(receipt_id)

    def get_receipts_for_po(self, purchase_order_id: int) -> List[MaterialReceiptEntity]:
        return self.receipts_repository.find_by_criteria({"purchase_order_id": purchase_order_id})

    def get_receipts_for_product(self, product_id: int) -> List[MaterialReceiptEntity]:
        return self.receipts_repository.find_by_criteria({"product_id": product_id})
        
    def get_receipts_by_supplier(self, supplier_person_id: int) -> List[MaterialReceiptEntity]:
        # MaterialReceiptEntity uses 'person_id' for supplier
        return self.receipts_repository.find_by_criteria({"person_id": supplier_person_id})

    def delete_material_receipt(self, receipt_id: int) -> bool:
        logger.warning(f"Attempting to delete Material Receipt ID {receipt_id}. This is a destructive operation.")
        receipt_to_delete = self.receipts_repository.get_by_id(receipt_id)

        if not receipt_to_delete or not receipt_to_delete.id:
            logger.warning(f"Material Receipt ID {receipt_id} not found for deletion.")
            return False
        
        # Ensure unit_price is not None for reversal calculation, though it should be set if receipt exists.
        if receipt_to_delete.unit_price is None:
            logger.error(f"Cannot reverse impact for Material Receipt ID {receipt_id} as unit_price is missing.")
            # This indicates a data integrity issue with the receipt itself.
            return False 

        try:
            self.product_manager.adjust_stock(
                product_id=receipt_to_delete.product_id,
                quantity_change= -receipt_to_delete.quantity_received,
                movement_type=InventoryMovementType.ADJUSTMENT_OUT,
                movement_date=datetime.now(),
                reference_id=receipt_to_delete.id,
                reference_type=ReferenceType.MATERIAL_RECEIPT,
                description=f"Reversal for deleted Material Receipt ID {receipt_id}"
            )

            if receipt_to_delete.purchase_order_id:
                value_of_this_receipt = receipt_to_delete.quantity_received * receipt_to_delete.unit_price
                self.po_manager.update_received_value(
                    po_id=receipt_to_delete.purchase_order_id,
                    value_of_goods_received_change= -value_of_this_receipt
                )
                logger.info(f"Purchase Order ID {receipt_to_delete.purchase_order_id} received value reversed by {value_of_this_receipt}.")

            self.receipts_repository.delete(receipt_id)
            logger.info(f"Material Receipt ID {receipt_id} deleted successfully after reversals.")
            return True
        except Exception as e:
            logger.error(f"Error during deletion of Material Receipt ID {receipt_id}: {e}", exc_info=True)
            return False
    def update_material_receipt(self,
                                receipt_id: int,
                                receipt_date: Optional[date] = None,
                                quantity_received: Optional[float] = None,
                                unit_price_override: Optional[float] = None,
                                description: Optional[str] = None,
                                fiscal_year_id: Optional[int] = None
                                # توجه: تغییر product_id, supplier_person_id, purchase_order_id, 
                                # و purchase_order_item_id در این نسخه پشتیبانی نمی‌شود.
                                ) -> Optional[MaterialReceiptEntity]:
        logger.info(f"Attempting to update Material Receipt ID: {receipt_id}")
        
        receipt_to_update = self.receipts_repository.get_by_id(receipt_id)
        if not receipt_to_update or not receipt_to_update.id:
            raise ValueError(f"رسید کالا با شناسه {receipt_id} برای ویرایش یافت نشد.")

        # --- ذخیره مقادیر قدیمی برای مقایسه و برگرداندن آثار ---
        old_product_id = receipt_to_update.product_id
        old_quantity = receipt_to_update.quantity_received
        old_unit_price = receipt_to_update.unit_price if receipt_to_update.unit_price is not None else 0.0
        old_po_id = receipt_to_update.purchase_order_id
        
        # برای مقایسه فیلدهای توصیفی
        old_receipt_date_for_comparison = receipt_to_update.receipt_date
        old_description_for_comparison = receipt_to_update.description
        old_fy_id_for_comparison = receipt_to_update.fiscal_year_id


        fields_changed_affecting_value_or_stock = False
        descriptive_fields_changed = False

        # به‌روزرسانی فیلدهای قابل ویرایش
        if receipt_date is not None and receipt_to_update.receipt_date != receipt_date:
            receipt_to_update.receipt_date = receipt_date
            descriptive_fields_changed = True
        if description is not None and receipt_to_update.description != description:
            receipt_to_update.description = description
            descriptive_fields_changed = True
        if fiscal_year_id is not None and receipt_to_update.fiscal_year_id != fiscal_year_id:
            receipt_to_update.fiscal_year_id = fiscal_year_id
            descriptive_fields_changed = True
        
        if quantity_received is not None and abs(receipt_to_update.quantity_received - quantity_received) > 0.001:
            if quantity_received <=0 : raise ValueError("تعداد دریافتی جدید باید مثبت باشد.")
            receipt_to_update.quantity_received = quantity_received
            fields_changed_affecting_value_or_stock = True
        
        if unit_price_override is not None and abs((receipt_to_update.unit_price or 0.0) - unit_price_override) > 0.001:
            if unit_price_override <0 : raise ValueError("قیمت واحد جدید نمی‌تواند منفی باشد.")
            receipt_to_update.unit_price = unit_price_override
            fields_changed_affecting_value_or_stock = True
        

        if not descriptive_fields_changed and not fields_changed_affecting_value_or_stock:
            logger.info(f"No effective changes detected for Material Receipt ID {receipt_id}.")
            return receipt_to_update

        # --- شروع بلاک مفهومی تراکنش ---
        try:
            if fields_changed_affecting_value_or_stock: # اگر تعداد یا قیمت تغییر کرده، آثار قبلی را برمی‌گردانیم
                logger.info(f"Reversing old stock & PO value for Receipt ID {receipt_id} due to value/qty change.")
                # ۱. برگرداندن آثار انبار قدیمی
                old_product_entity_for_reversal = self.product_manager.get_product_by_id(old_product_id) # old_product_id تعریف شده
                if old_product_entity_for_reversal and old_product_entity_for_reversal.product_type != ProductType.SERVICE:
                     self.product_manager.adjust_stock(
                        product_id=old_product_id, # old_product_id تعریف شده
                        quantity_change= -old_quantity, # old_quantity تعریف شده
                        movement_type=InventoryMovementType.ADJUSTMENT_OUT,
                        movement_date=datetime.now(), 
                        reference_id=receipt_id,
                        reference_type=ReferenceType.MATERIAL_RECEIPT,
                        description=f"Stock reversal for edited Receipt ID {receipt_id}"
                    )
                
                # ۲. برگرداندن آثار سفارش خرید قدیمی (اگر لینک بوده)
                if old_po_id: # old_po_id تعریف شده
                    old_value_for_po = Decimal(str(old_quantity)) * Decimal(str(old_unit_price)) # old_quantity و old_unit_price تعریف شده‌اند
                    if old_value_for_po > 0:
                        logger.info(f"Reversing old PO value for Receipt ID {receipt_id} on PO ID {old_po_id} by {-float(old_value_for_po)}")
                        self.po_manager.update_received_value(
                            po_id=old_po_id,
                            value_of_goods_received_change= -float(old_value_for_po)
                        )

            # ۳. ذخیره تغییرات در خود رسید (با مقادیر جدید)
            updated_receipt_in_db = self.receipts_repository.update(receipt_to_update) # type: ignore
            logger.info(f"Material Receipt ID {receipt_id} base data updated in repository.")

            if fields_changed_affecting_value_or_stock: # اگر تعداد یا قیمت تغییر کرده، آثار جدید را اعمال می‌کنیم
                # ۴. اعمال آثار انبار جدید
                logger.info(f"Applying new stock movement for updated Receipt ID {receipt_id} (Product: {updated_receipt_in_db.product_id}, Qty: {updated_receipt_in_db.quantity_received})") # type: ignore
                new_product_entity_for_apply = self.product_manager.get_product_by_id(updated_receipt_in_db.product_id) # type: ignore
                if new_product_entity_for_apply and new_product_entity_for_apply.product_type != ProductType.SERVICE:
                    self.product_manager.adjust_stock(
                        product_id=updated_receipt_in_db.product_id, # type: ignore
                        quantity_change=updated_receipt_in_db.quantity_received, # type: ignore
                        movement_type=InventoryMovementType.RECEIPT,
                        movement_date=datetime.combine(updated_receipt_in_db.receipt_date, datetime.min.time()), # type: ignore
                        reference_id=updated_receipt_in_db.id, # type: ignore
                        reference_type=ReferenceType.MATERIAL_RECEIPT,
                        description=f"Stock adjustment for edited Receipt ID {updated_receipt_in_db.id}" # type: ignore
                    )
                
                # ۵. اعمال آثار سفارش خرید جدید (اگر لینک است)
                if updated_receipt_in_db.purchase_order_id and updated_receipt_in_db.unit_price is not None: # type: ignore
                    new_value_for_po = Decimal(str(updated_receipt_in_db.quantity_received)) * Decimal(str(updated_receipt_in_db.unit_price)) # type: ignore
                    logger.info(f"Applying new PO value for Receipt ID {receipt_id} on PO ID {updated_receipt_in_db.purchase_order_id} by {float(new_value_for_po)}") # type: ignore
                    self.po_manager.update_received_value(
                        po_id=updated_receipt_in_db.purchase_order_id, # type: ignore
                        value_of_goods_received_change= float(new_value_for_po)
                    )
            
            logger.info(f"Material Receipt ID {receipt_id} fully updated.")
            return self.receipts_repository.get_by_id(receipt_id)

        except Exception as e:
            logger.error(f"Error during update of Material Receipt ID {receipt_id}: {e}", exc_info=True)
            raise