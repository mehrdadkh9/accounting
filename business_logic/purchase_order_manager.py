# src/business_logic/purchase_order_manager.py

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from src.business_logic.entities.purchase_order_entity import PurchaseOrderEntity
from src.business_logic.entities.purchase_order_item_entity import PurchaseOrderItemEntity

from src.data_access.purchase_orders_repository import PurchaseOrdersRepository
from src.data_access.purchase_order_items_repository import PurchaseOrderItemsRepository

from src.business_logic.person_manager import PersonManager
from src.business_logic.product_manager import ProductManager

from src.constants import PersonType, PurchaseOrderStatus, ProductType
import logging

logger = logging.getLogger(__name__)

class PurchaseOrderManager:
    def __init__(self,
                 po_repository: PurchaseOrdersRepository,
                 po_items_repository: PurchaseOrderItemsRepository,
                 person_manager: PersonManager,
                 product_manager: ProductManager):
        if po_repository is None: raise ValueError("po_repository cannot be None")
        if po_items_repository is None: raise ValueError("po_items_repository cannot be None")
        if person_manager is None: raise ValueError("person_manager cannot be None")
        if product_manager is None: raise ValueError("product_manager cannot be None")

        self.po_repository = po_repository
        self.po_items_repository = po_items_repository
        self.person_manager = person_manager
        self.product_manager = product_manager


    def _generate_po_number(self) -> str:
        return f"PO-{int(datetime.now().timestamp() * 1000)}"

    def create_purchase_order(self,
                              order_date: date,
                              supplier_person_id: int,
                              items_data: List[Dict[str, Any]], 
                              description: Optional[str] = None,
                              fiscal_year_id: Optional[int] = None,
                              order_number_override: Optional[str] = None
                              ) -> Optional[PurchaseOrderEntity]:
        logger.info(f"Attempting to create PO. Supplier: {supplier_person_id}, Items: {len(items_data)}")
        if not isinstance(order_date, date): raise ValueError("تاریخ سفارش نامعتبر است.")
        # ... (سایر اعتبارسنجی‌های اولیه برای supplier_person_id و items_data) ...
        supplier = self.person_manager.get_person_by_id(supplier_person_id)
        if not supplier or supplier.person_type != PersonType.SUPPLIER:
            raise ValueError(f"تامین‌کننده با شناسه {supplier_person_id} نامعتبر است.")

        order_number_to_use = order_number_override if order_number_override else self._generate_po_number()
        
        existing_po_check = self.po_repository.find_by_criteria({"order_number": order_number_to_use})
        if existing_po_check:
             raise ValueError(f"شماره سفارش خرید '{order_number_to_use}' تکراری است.")

        temp_item_entities_data_for_db: List[Dict[str, Any]] = []
        calculated_total_amount_expected = Decimal("0.0")

        for item_data_from_dialog in items_data:
            product_id = item_data_from_dialog.get('product_id')
            ordered_quantity_val = item_data_from_dialog.get('ordered_quantity')
            unit_price_val = item_data_from_dialog.get('unit_price')

            if not product_id or not isinstance(product_id, int):
                raise ValueError(f"شناسه کالا نامعتبر در اقلام سفارش: {item_data_from_dialog}")
            product = self.product_manager.get_product_by_id(product_id)
            if not product: raise ValueError(f"کالایی با شناسه {product_id} یافت نشد.")
            if ordered_quantity_val is None or not isinstance(ordered_quantity_val, (int, float)) or ordered_quantity_val <= 0:
                raise ValueError(f"تعداد سفارش نامعتبر برای کالا '{product.name}': {ordered_quantity_val}")
            if unit_price_val is None or not isinstance(unit_price_val, (int, float)) or unit_price_val < 0:
                raise ValueError(f"قیمت واحد نامعتبر برای کالا '{product.name}': {unit_price_val}")

            ordered_quantity_dec = Decimal(str(ordered_quantity_val))
            unit_price_dec = Decimal(str(unit_price_val))
            current_item_total_dec = ordered_quantity_dec * unit_price_dec
            calculated_total_amount_expected += current_item_total_dec
            
            temp_item_entities_data_for_db.append({
                "product_id": product_id,
                "ordered_quantity": float(ordered_quantity_dec),
                "unit_price": float(unit_price_dec),
                "total_item_amount": float(current_item_total_dec)
            })
        
        po_header_entity = PurchaseOrderEntity(
            order_number=order_number_to_use,
            person_id=supplier_person_id,
            order_date=order_date,
            total_amount_expected=float(calculated_total_amount_expected),
            status=PurchaseOrderStatus.PENDING,
            description=description,
            fiscal_year_id=fiscal_year_id
        )
        created_po_header_from_db: Optional[PurchaseOrderEntity] = None
        try:
            created_po_header_from_db = self.po_repository.add(po_header_entity)
            if not created_po_header_from_db or not created_po_header_from_db.id:
                raise Exception("خطا در ذخیره هدر سفارش خرید.")
            logger.info(f"PO Header ID {created_po_header_from_db.id} created.")

            saved_item_entities_list: List[PurchaseOrderItemEntity] = []
            for item_data_for_creation in temp_item_entities_data_for_db:
                item_entity_to_save = PurchaseOrderItemEntity(
                    purchase_order_id=created_po_header_from_db.id, # type: ignore
                    product_id=item_data_for_creation['product_id'],
                    ordered_quantity=item_data_for_creation['ordered_quantity'],
                    unit_price=item_data_for_creation['unit_price'],
                    total_item_amount=item_data_for_creation['total_item_amount']
                )
                saved_item = self.po_items_repository.add(item_entity_to_save)
                saved_item_entities_list.append(saved_item)
            
            created_po_header_from_db.items = saved_item_entities_list
            return created_po_header_from_db
        except Exception as e:
            # ... (منطق rollback که قبلا بود) ...
            log_order_num = order_number_to_use 
            if created_po_header_from_db and created_po_header_from_db.id: 
                logger.error(f"Error during item processing for PO {log_order_num} (ID: {created_po_header_from_db.id}). Attempting rollback.", exc_info=True)
                try:
                    self.po_items_repository.delete_by_purchase_order_id(created_po_header_from_db.id) # type: ignore
                    self.po_repository.delete(created_po_header_from_db.id) # type: ignore
                    logger.info(f"Rolled back PO Header ID {created_po_header_from_db.id}")
                except Exception as rb_e:
                    logger.critical(f"Failed to rollback PO Header ID {created_po_header_from_db.id}: {rb_e}")
            else: 
                 logger.error(f"Error during Purchase Order creation for {log_order_num}: {e}", exc_info=True)
            raise

    
    def update_purchase_order(self, 
                              po_id: int, 
                              order_date: Optional[date] = None,
                              supplier_person_id: Optional[int] = None,
                              items_data: Optional[List[Dict[str, Any]]] = None, # لیست جدید اقلام
                              description: Optional[str] = None,
                              fiscal_year_id: Optional[int] = None
                              # order_number معمولاً ویرایش نمی‌شود
                              # status توسط فرآیندهای دیگر تغییر می‌کند
                             ) -> Optional[PurchaseOrderEntity]:
        """
        Updates an existing purchase order.
        If items_data is provided, old items are deleted and new ones are added.
        """
        logger.info(f"Attempting to update Purchase Order ID: {po_id}")
        po_to_update = self.po_repository.get_by_id(po_id)
        if not po_to_update or not po_to_update.id:
            logger.warning(f"Purchase Order ID {po_id} not found for update.")
            raise ValueError(f"سفارش خرید با شناسه {po_id} یافت نشد.")

        header_changed = False
        if order_date is not None and po_to_update.order_date != order_date:
            po_to_update.order_date = order_date
            header_changed = True
        if supplier_person_id is not None and po_to_update.person_id != supplier_person_id:
            supplier = self.person_manager.get_person_by_id(supplier_person_id)
            if not supplier or supplier.person_type != PersonType.SUPPLIER:
                raise ValueError("تامین‌کننده جدید نامعتبر است.")
            po_to_update.person_id = supplier_person_id
            header_changed = True
        if description is not None and po_to_update.description != description:
            po_to_update.description = description
            header_changed = True
        if fiscal_year_id is not None and po_to_update.fiscal_year_id != fiscal_year_id:
            po_to_update.fiscal_year_id = fiscal_year_id
            header_changed = True
        
        # --- Transactional Block for Item Updates & Header Save ---
        try:
            if items_data is not None: # If new item list is provided, replace old items
                logger.info(f"Replacing items for PO ID {po_id}.")
                self.po_items_repository.delete_by_purchase_order_id(po_id) # Delete all existing items
                
                new_po_item_entities: List[PurchaseOrderItemEntity] = []
                new_calculated_total_amount = Decimal("0.0")
                for item_data_dict in items_data:
                    ordered_qty = Decimal(str(item_data_dict.get('ordered_quantity', 0.0)))
                    unit_p = Decimal(str(item_data_dict.get('unit_price', 0.0)))
                    item_total = ordered_qty * unit_p
                    new_calculated_total_amount += item_total

                    item_entity = PurchaseOrderItemEntity(
                        purchase_order_id=po_id,
                        product_id=item_data_dict['product_id'],
                        ordered_quantity=float(ordered_qty),
                        unit_price=float(unit_p),
                        total_item_amount=float(item_total)
                    )
                    saved_item = self.po_items_repository.add(item_entity)
                    new_po_item_entities.append(saved_item)
                
                po_to_update.items = new_po_item_entities # Update in-memory items list
                po_to_update.total_amount_expected = float(new_calculated_total_amount)
                header_changed = True # total_amount_expected in header changed

            if header_changed: # If any header field OR items (which affects total_amount) changed
                logger.info(f"Updating PO header for ID {po_id}. New total: {po_to_update.total_amount_expected}")
                self.po_repository.update(po_to_update)
            else:
                logger.info(f"No changes detected for PO ID {po_id} header or items.")

            # Re-fetch to ensure consistency and return the full updated object with potentially updated items
            return self.get_purchase_order_with_items(po_id)

        except Exception as e:
            logger.error(f"Error updating PO ID {po_id}: {e}", exc_info=True)
            # More complex rollback might be needed if DB is partially updated
            raise
        # --- End Transactional Block ---

    def get_purchase_order_with_items(self, po_id: int) -> Optional[PurchaseOrderEntity]:
        po = self.po_repository.get_by_id(po_id)
        if po and po.id: # اطمینان از وجود شناسه
            po.items = self.po_items_repository.get_by_purchase_order_id(po.id)
        return po

    def get_all_purchase_orders_summary(self) -> List[PurchaseOrderEntity]:
        """Fetches all PO headers without their items for summary display."""
        # BaseRepository.get_all() به طور پیش‌فرض items را بارگذاری نمی‌کند (چون لیست است و نادیده گرفته می‌شود)
        # PurchaseOrderEntity.items یک default_factory=list دارد.
        return self.po_repository.get_all()

    def get_purchase_orders_by_supplier(self, supplier_person_id: int, include_items: bool = False) -> List[PurchaseOrderEntity]:
        # Assuming repository has get_by_person_id or similar
        pos = self.po_repository.find_by_criteria({"person_id": supplier_person_id})
        if include_items:
            for po_header in pos:
                if po_header.id:
                    po_header.items = self.po_items_repository.get_by_purchase_order_id(po_header.id)
        return pos
        
    def get_purchase_orders_by_status(self, status: PurchaseOrderStatus, include_items: bool = False) -> List[PurchaseOrderEntity]:
        pos = self.po_repository.find_by_criteria({"status": status.value}) # Assuming find_by_criteria takes enum value
        if include_items:
            for po_header in pos:
                if po_header.id:
                    po_header.items = self.po_items_repository.get_by_purchase_order_id(po_header.id)
        return pos

     # update_paid_amount and update_received_value methods (مانند قبل، با اصلاحات جزئی در لاگ و وضعیت‌ها)
    def update_paid_amount(self, po_id: int, payment_amount_change: float) -> Optional[PurchaseOrderEntity]:
        po = self.po_repository.get_by_id(po_id)
        if not po: # type: ignore
            logger.warning(f"Purchase Order ID {po_id} not found for updating paid amount.")
            return None
        
        logger.info(f"Updating paid amount for PO ID {po_id}. Change: {payment_amount_change}. Current paid: {po.paid_amount}")
        po.paid_amount += payment_amount_change
        
        # Clamp paid_amount
        if po.paid_amount < 0: po.paid_amount = 0.0
        if po.paid_amount > po.total_amount_expected:
            logger.warning(f"PO ID {po_id} paid amount {po.paid_amount} exceeds total expected {po.total_amount_expected}. Clamping.")
            po.paid_amount = po.total_amount_expected

        # Update status based on paid_amount and received_amount
        # This status logic can become complex.
        current_status = po.status
        if po.status == PurchaseOrderStatus.CANCELED:
            logger.warning(f"Payment recorded for a CANCELED PO ID {po_id}. Status not changed from CANCELED.")
        elif abs(po.paid_amount - po.total_amount_expected) < 0.001 : # Fully Paid
            if abs(po.received_amount - po.total_amount_expected) < 0.001 : # And Fully Received
                po.status = PurchaseOrderStatus.COMPLETED
            else:
                po.status = PurchaseOrderStatus.FULLY_PAID
        elif po.paid_amount > 0:
            po.status = PurchaseOrderStatus.PARTIALLY_PAID
        elif po.paid_amount <= 0: # No payment or payment reversed fully
            if abs(po.received_amount - po.total_amount_expected) < 0.001 :
                 po.status = PurchaseOrderStatus.FULLY_RECEIVED
            elif po.received_amount > 0:
                 po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
            else: # No payments and no receipts
                 po.status = PurchaseOrderStatus.PENDING
        
        if current_status != po.status:
             logger.info(f"PO ID {po_id} status changed from {current_status.value} to {po.status.value} due to payment update.")


        try:
            updated_po = self.po_repository.update(po)
            logger.info(f"Paid amount for PO ID {po_id} updated. New Paid: {updated_po.paid_amount}, New Status: {updated_po.status.value}")
            return updated_po
        except Exception as e:
            logger.error(f"Error updating paid amount for PO ID {po_id}: {e}", exc_info=True)
            raise

    def update_received_value(self, po_id: int, value_of_goods_received_change: float) -> Optional[PurchaseOrderEntity]:
        po = self.po_repository.get_by_id(po_id)
        if not po: # type: ignore
            logger.warning(f"Purchase Order ID {po_id} not found for updating received amount.")
            return None

        logger.info(f"Updating received value for PO ID {po_id}. Change: {value_of_goods_received_change}. Current received: {po.received_amount}")
        po.received_amount += value_of_goods_received_change

        if po.received_amount < 0: po.received_amount = 0.0
        if po.received_amount > po.total_amount_expected:
            logger.warning(f"PO ID {po_id} received amount {po.received_amount} exceeds total expected {po.total_amount_expected}. Clamping.")
            po.received_amount = po.total_amount_expected

        current_status = po.status
        if po.status == PurchaseOrderStatus.CANCELED:
             logger.warning(f"Goods received for a CANCELED PO ID {po_id}. Status not changed from CANCELED.")
        elif abs(po.received_amount - po.total_amount_expected) < 0.001: # Fully Received
            if abs(po.paid_amount - po.total_amount_expected) < 0.001 : # And Fully Paid
                po.status = PurchaseOrderStatus.COMPLETED
            else:
                po.status = PurchaseOrderStatus.FULLY_RECEIVED
        elif po.received_amount > 0:
            po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
        elif po.received_amount <= 0: # No receipts or receipts reversed fully
            if abs(po.paid_amount - po.total_amount_expected) < 0.001 :
                 po.status = PurchaseOrderStatus.FULLY_PAID
            elif po.paid_amount > 0:
                 po.status = PurchaseOrderStatus.PARTIALLY_PAID
            else: # No payments and no receipts
                 po.status = PurchaseOrderStatus.PENDING
        
        if current_status != po.status:
             logger.info(f"PO ID {po_id} status changed from {current_status.value} to {po.status.value} due to receipt update.")

        try:
            updated_po = self.po_repository.update(po)
            logger.info(f"Received amount for PO ID {po_id} updated. New Received Value: {updated_po.received_amount}, New Status: {updated_po.status.value}")
            return updated_po
        except Exception as e:
            logger.error(f"Error updating received amount for PO ID {po_id}: {e}", exc_info=True)
            raise
            

    def cancel_purchase_order(self, po_id: int) -> Optional[PurchaseOrderEntity]:
        logger.info(f"Attempting to cancel Purchase Order ID: {po_id}")
        po = self.po_repository.get_by_id(po_id)
        if not po:
            logger.warning(f"Purchase Order ID {po_id} not found for cancellation.")
            raise ValueError(f"سفارش خرید با شناسه {po_id} یافت نشد.")

        if po.status in [PurchaseOrderStatus.COMPLETED, PurchaseOrderStatus.CANCELED]: # Already completed or cancelled
            logger.warning(f"PO ID {po_id} is already in status {po.status.value}, cannot cancel.")
            return po # Or raise error: raise ValueError(...)
        
        # Business rule: Can a PO with partial receipts/payments be cancelled?
        # If so, what are the implications? Reversals needed?
        # For now, we allow cancellation if not fully completed.
        if po.received_amount > 0:
            logger.warning(f"PO ID {po_id} has received goods (value: {po.received_amount}). Cancellation might require further actions.")
        if po.paid_amount > 0:
            logger.warning(f"PO ID {po_id} has payments made (amount: {po.paid_amount}). Cancellation might require refund processing.")

        po.status = PurchaseOrderStatus.CANCELED
        try:
            updated_po = self.po_repository.update(po)
            logger.info(f"Purchase Order ID {po_id} status set to CANCELLED.")
            return updated_po
        except Exception as e:
            logger.error(f"Error cancelling PO ID {po_id}: {e}", exc_info=True)
            raise
    def delete_purchase_order(self, po_id: int) -> bool:
        # ... (کد قبلی این متد با بررسی‌های بیشتر)
        logger.warning(f"Attempting physical delete of Purchase Order ID: {po_id}.")
        po_to_delete = self.get_purchase_order_with_items(po_id)
        if not po_to_delete or not po_to_delete.id:
            logger.warning(f"PO ID {po_id} not found for deletion.")
            raise ValueError(f"سفارش خرید با شناسه {po_id} یافت نشد.")

        if po_to_delete.paid_amount > 0 or po_to_delete.received_amount > 0 or \
           po_to_delete.status not in [PurchaseOrderStatus.PENDING, PurchaseOrderStatus.CANCELED]:
            logger.error(f"Cannot delete PO ID {po_id} due to activity or state (Status: {po_to_delete.status.value}).")
            raise ValueError("سفارش خرید دارای پرداخت، رسید یا در وضعیت غیرقابل حذف است.")

        try:
            self.po_items_repository.delete_by_purchase_order_id(po_to_delete.id) # type: ignore
            self.po_repository.delete(po_to_delete.id) # type: ignore
            logger.info(f"Purchase Order ID {po_id} (Number: {po_to_delete.order_number}) and its items physically deleted.")
            return True
        except Exception as e:
            logger.error(f"Error physically deleting PO ID {po_id}: {e}", exc_info=True)
            raise # Re-raise for UI to catch specific error
    def get_open_purchase_orders_by_supplier(self, supplier_id: int) -> List[PurchaseOrderEntity]:
        logger.debug(f"Fetching open purchase orders for supplier ID: {supplier_id}")
        
        # واکشی تمام سفارش‌های خرید مربوط به این تامین‌کننده
        all_supplier_pos = self.po_repository.find_by_criteria(
            {"person_id": supplier_id},
            order_by="order_date DESC, id DESC" 
        )

        open_pos: List[PurchaseOrderEntity] = []
        if all_supplier_pos:
            for po in all_supplier_pos:
                # فیلتر وضعیت‌های باز و بررسی مبلغ باقی‌مانده
                if po.status not in [PurchaseOrderStatus.COMPLETED, PurchaseOrderStatus.CANCELED] and \
                   (Decimal(str(po.total_amount_expected)) - Decimal(str(po.paid_amount))).copy_abs() > Decimal("0.001"):
                    open_pos.append(po)
            logger.debug(f"Found {len(open_pos)} open POs after filtering statuses and amounts.")
        else:
            logger.debug("No purchase orders found for this supplier initially.")
            
        return open_pos