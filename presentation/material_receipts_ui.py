# src/presentation/material_receipts_ui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QPushButton, QHBoxLayout,
    QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout,
    QDialogButtonBox, QAbstractItemView, QDoubleSpinBox, QTextEdit,QApplication,
    QHeaderView, QDateEdit, QSpinBox
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate
from PyQt5.QtGui import QColor

from typing import List, Optional, Any, Dict, Union
from datetime import date, datetime

# Import entities, enums, and managers
from src.business_logic.entities.material_receipt_entity import MaterialReceiptEntity
from src.business_logic.entities.purchase_order_entity import PurchaseOrderEntity
from src.business_logic.entities.purchase_order_item_entity import PurchaseOrderItemEntity # <<< اضافه شد
from src.business_logic.entities.product_entity import ProductEntity
from src.business_logic.entities.person_entity import PersonEntity


from src.constants import ( # <<< Enum های لازم اضافه شدند
    DATE_FORMAT, PurchaseOrderStatus, PersonType, ProductType, 
    InventoryMovementType, ReferenceType
)

from src.business_logic.material_receipt_manager import MaterialReceiptManager
from src.business_logic.purchase_order_manager import PurchaseOrderManager
from src.business_logic.product_manager import ProductManager
from src.business_logic.person_manager import PersonManager
from src.utils import date_converter
from .custom_widgets import ShamsiDateEdit # <<< ویجت جدید تاریخ شمسی
import logging
logger = logging.getLogger(__name__)


# --- Table Model for Material Receipts ---
class MaterialReceiptTableModel(QAbstractTableModel):
    def __init__(self, 
                 data: Optional[List[MaterialReceiptEntity]] = None, 
                 person_manager: Optional[PersonManager] = None,
                 product_manager: Optional[ProductManager] = None,
                 po_manager: Optional[PurchaseOrderManager] = None, # برای گرفتن شماره سفارش
                 parent=None):
        super().__init__(parent)
        self._data: List[MaterialReceiptEntity] = data if data is not None else []
        self._person_manager = person_manager
        self._product_manager = product_manager
        self._po_manager = po_manager
        self._headers = ["شناسه رسید", "تاریخ رسید", "تامین‌کننده", "کالا", 
                         "تعداد دریافتی", "قیمت واحد", "سفارش خرید"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid(): return QVariant()
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._data)): return QVariant()
        
        receipt = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(receipt.id)
            elif col == 1: 
                return date_converter.to_shamsi_str(receipt.receipt_date)
            elif col == 2: # Supplier Name
                if self._person_manager and receipt.person_id:
                    supplier = self._person_manager.get_person_by_id(receipt.person_id)
                    return supplier.name if supplier else f"ID: {receipt.person_id}"
                return str(receipt.person_id)
            elif col == 3: # Product Name
                if self._product_manager and receipt.product_id:
                    product = self._product_manager.get_product_by_id(receipt.product_id)
                    return product.name if product else f"ID: {receipt.product_id}"
                return str(receipt.product_id)
            elif col == 4: return str(receipt.quantity_received)
            elif col == 5: return f"{receipt.unit_price:,.2f}" if receipt.unit_price is not None else ""
            elif col == 6: # Purchase Order Number
                if self._po_manager and receipt.purchase_order_id:
                    po = self._po_manager.get_purchase_order_with_items(receipt.purchase_order_id) # یا متد ساده‌تر برای گرفتن فقط هدر
                    return po.order_number if po else f"PO ID: {receipt.purchase_order_id}"
                return str(receipt.purchase_order_id) if receipt.purchase_order_id else "مستقیم"
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0,1,6]: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if col in [4,5]: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[MaterialReceiptEntity]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_receipt_at_row(self, row: int) -> Optional[MaterialReceiptEntity]:
        if 0 <= row < len(self._data): return self._data[row]
        return None

# src/presentation/material_receipts_ui.py
# ... (import‌ها و کلاس MaterialReceiptTableModel مانند قبل) ...

# --- Dialog for recording a new Material Receipt ---
class MaterialReceiptDialog(QDialog):
    def __init__(self,
                 purchase_order_manager: PurchaseOrderManager,
                 product_manager: ProductManager,
                 person_manager: PersonManager,
                 receipt_to_edit: Optional[MaterialReceiptEntity] = None, # تغییر نام پارامتر برای وضوح
                 parent=None):
        super().__init__(parent)
        self.po_manager = purchase_order_manager
        self._current_selected_po_item_entity: Optional[PurchaseOrderItemEntity] = None
        self.product_manager = product_manager
        self.person_manager = person_manager
        self.receipt_to_edit = receipt_to_edit # ذخیره رسید برای ویرایش
        self.is_edit_mode = self.receipt_to_edit is not None

        self._selected_po: Optional[PurchaseOrderEntity] = None
        self._selected_po_item_data: Optional[Union[PurchaseOrderItemEntity, Dict[str, Any]]] = None
        self._current_selected_po_item_entity: Optional[PurchaseOrderItemEntity] = None 

        title = "ثبت رسید جدید"
        if self.is_edit_mode and self.receipt_to_edit:
            title = f"ویرایش رسید شناسه: {self.receipt_to_edit.id}"
        self.setWindowTitle(title)
        self.setMinimumSize(550, 450)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui() # _setup_ui باید self.is_edit_mode و self.receipt_to_edit را بشناسد

        if self.is_edit_mode and self.receipt_to_edit:
            self._load_receipt_data_for_editing() # متد جدید برای بارگذاری داده‌ها
        else: 
            self._on_po_selected() 
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        form_layout = QFormLayout()

        self.receipt_date_edit = ShamsiDateEdit(self)


        self.po_combo = QComboBox(self)
        self.po_combo.addItem("-- رسید مستقیم (بدون سفارش خرید) --", None)
        self._populate_po_combo() # این متد باید در نظر بگیرد که در حالت ویرایش هستیم یا خیر
        self.po_combo.currentIndexChanged.connect(self._on_po_selected)

        self.supplier_combo = QComboBox(self)
        self._populate_supplier_combo()

        self.po_item_combo = QComboBox(self)
        self.po_item_combo.addItem("-- انتخاب قلم از سفارش --", None)
        self.po_item_combo.currentIndexChanged.connect(self._on_po_item_selected)

        self.product_combo = QComboBox(self)
        self._populate_product_combo()

        self.quantity_received_spinbox = QDoubleSpinBox(self)
        self.quantity_received_spinbox.setDecimals(2)
        self.quantity_received_spinbox.setMinimum(0.01)
        self.quantity_received_spinbox.setMaximum(999999.99)

        self.unit_price_spinbox = QDoubleSpinBox(self)
        self.unit_price_spinbox.setDecimals(2)
        self.unit_price_spinbox.setMinimum(0.00)
        self.unit_price_spinbox.setMaximum(99999999.99)
        self.unit_price_spinbox.setGroupSeparatorShown(True)

        self.fiscal_year_id_spinbox = QSpinBox(self)
        self.fiscal_year_id_spinbox.setRange(0, 9999)

        self.description_edit = QTextEdit(self)
        self.description_edit.setFixedHeight(60)

        form_layout.addRow("تاریخ رسید:", self.receipt_date_edit)
        form_layout.addRow("سفارش خرید مرتبط:", self.po_combo)
        form_layout.addRow("تامین‌کننده:", self.supplier_combo)
        form_layout.addRow("قلم سفارش خرید:", self.po_item_combo)
        form_layout.addRow("کالا (برای رسید مستقیم):", self.product_combo)
        form_layout.addRow("تعداد دریافتی:", self.quantity_received_spinbox)
        form_layout.addRow("قیمت واحد واقعی:", self.unit_price_spinbox)
        form_layout.addRow("شناسه سال مالی:", self.fiscal_year_id_spinbox)
        form_layout.addRow("توضیحات:", self.description_edit)
        
        main_layout.addLayout(form_layout)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons, Qt.Orientation.Horizontal, self) # type: ignore
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: 
            ok_button.setText("ثبت رسید" if not self.is_edit_mode else "ذخیره تغییرات")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        
        
        main_layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.setLayout(main_layout)

    def _populate_po_combo(self):
        self.po_combo.clear()
        self.po_combo.addItem("-- رسید مستقیم (بدون سفارش خرید) --", None)
        try:
            # Get POs that are not fully received or cancelled
            open_pos = [
                po for po in self.po_manager.get_all_purchase_orders_summary()
                if po.status not in [PurchaseOrderStatus.FULLY_RECEIVED, PurchaseOrderStatus.COMPLETED, PurchaseOrderStatus.CANCELED]
            ]
            if not open_pos:
                self.po_combo.addItem("سفارش خرید بازی یافت نشد.", -1) # Placeholder for no POs
                return
            
            for po in open_pos:
                if po.id is not None:
                    supplier = self.person_manager.get_person_by_id(po.person_id)
                    supplier_name = supplier.name if supplier else "ناشناس"
                    self.po_combo.addItem(f"{po.order_number} (تامین‌کننده: {supplier_name})", po.id)
        except Exception as e:
            logger.error(f"Error populating PO combo: {e}", exc_info=True)

    def _populate_supplier_combo(self):
        self.supplier_combo.clear()
        try:
            suppliers = self.person_manager.get_persons_by_type(PersonType.SUPPLIER)
            if not suppliers:
                self.supplier_combo.addItem("تامین‌کننده‌ای یافت نشد", -1)
                self.supplier_combo.setEnabled(False)
                return
            self.supplier_combo.setEnabled(True)
            for supplier in suppliers:
                if supplier.id is not None:
                    self.supplier_combo.addItem(f"{supplier.name} (ID: {supplier.id})", supplier.id)
        except Exception as e:
            logger.error(f"Error populating suppliers for direct receipt: {e}", exc_info=True)

    def _populate_product_combo(self):
        self.product_combo.clear()
        try:
            products = self.product_manager.get_all_products(active_only=True)
            # Filter for non-service items that can be received
            eligible_products = [p for p in products if p.product_type != ProductType.SERVICE and p.id is not None]
            if not eligible_products:
                self.product_combo.addItem("کالایی (غیرخدماتی) یافت نشد", -1)
                self.product_combo.setEnabled(False)
                return
            self.product_combo.setEnabled(True)
            for product in eligible_products:
                self.product_combo.addItem(f"{product.name} (SKU: {product.sku or 'N/A'})", product.id)
        except Exception as e:
            logger.error(f"Error populating products for direct receipt: {e}", exc_info=True)

    def _on_po_selected(self):
        selected_po_id = self.po_combo.currentData() # این شناسه PO است یا None
        logger.debug(f"MaterialReceiptDialog._on_po_selected: Selected PO ID: {selected_po_id}")

        self._selected_po = None
        self._current_selected_po_item_entity = None # ریست کردن قلم انتخاب شده قبلی
        self.po_item_combo.clear()
        self.po_item_combo.addItem("-- انتخاب قلم از سفارش --", None) # None به عنوان داده برای آیتم پیش‌فرض

        if selected_po_id is not None and selected_po_id != -1: # یک PO معتبر انتخاب شده
            fetched_po = self.po_manager.get_purchase_order_with_items(selected_po_id)
            if fetched_po:
                self._selected_po = fetched_po # ذخیره PO واکشی شده
                logger.debug(f"  Fetched PO: {self._selected_po.order_number}, Items count: {len(self._selected_po.items) if self._selected_po.items else 0}")

                if self._selected_po.items:
                    supplier_idx = self.supplier_combo.findData(self._selected_po.person_id)
                    if supplier_idx != -1:
                        self.supplier_combo.setCurrentIndex(supplier_idx)
                    self.supplier_combo.setEnabled(False)
                    
                    for item_entity in self._selected_po.items: # item_entity آبجکت PurchaseOrderItemEntity است
                        product = self.product_manager.get_product_by_id(item_entity.product_id)
                        product_name = product.name if product else "کالای نامشخص"
                        # ذخیره کل آبجکت PurchaseOrderItemEntity به عنوان داده
                        self.po_item_combo.addItem(
                            f"{product_name} (سفارش: {item_entity.ordered_quantity})", 
                            item_entity 
                        )
                    self.po_item_combo.setEnabled(True)
                    self.product_combo.setEnabled(False)
                    self.product_combo.setCurrentIndex(-1)
                    
                    # خودکار اولین آیتم واقعی را انتخاب کن (اگر وجود دارد)
                    if self.po_item_combo.count() > 1: # چون آیتم اول placeholder است
                        self.po_item_combo.setCurrentIndex(1) # این باعث فراخوانی _on_po_item_selected می‌شود
                    else: # PO آیتم ندارد یا مشکلی در پر کردن کمبو بوده
                        self._on_po_item_selected() # برای ریست کردن صحیح UI مربوط به کالا
                    return # از متد خارج شو چون یک PO پردازش شده است
                else: # PO آیتم نداشت
                    logger.debug(f"  PO ID {selected_po_id} found but has no items.")
            else: # PO یافت نشد
                logger.warning(f"  PO ID {selected_po_id} not found by manager.")
        
        # اگر به اینجا رسیدیم، یعنی یا PO انتخاب نشده، یا PO یافت نشده، یا PO آیتم نداشته
        self._handle_direct_receipt_state()

    def _on_po_item_selected(self):
        # currentData باید PurchaseOrderItemEntity یا None (برای placeholder) باشد
        selected_item_entity_candidate = self.po_item_combo.currentData()
        
        logger.debug(f"MaterialReceiptDialog._on_po_item_selected: currentData from po_item_combo is type: {type(selected_item_entity_candidate)}")
        if isinstance(selected_item_entity_candidate, PurchaseOrderItemEntity):
            logger.debug(f"  Selected PO Item Entity: Product ID {selected_item_entity_candidate.product_id}, Ordered Qty: {selected_item_entity_candidate.ordered_quantity}")
            self._current_selected_po_item_entity = selected_item_entity_candidate
            
            product = self.product_manager.get_product_by_id(self._current_selected_po_item_entity.product_id)
            if product and product.id is not None:
                prod_idx = self.product_combo.findData(product.id)
                if prod_idx != -1:
                    self.product_combo.setCurrentIndex(prod_idx)
                self.product_combo.setEnabled(False) # چون از آیتم PO انتخاب شده
                
                self.unit_price_spinbox.setValue(self._current_selected_po_item_entity.unit_price)
                # TODO: Prefill quantity_received based on ordered - already_received
                self.quantity_received_spinbox.setValue(self._current_selected_po_item_entity.ordered_quantity)
                self.quantity_received_spinbox.setMaximum(self._current_selected_po_item_entity.ordered_quantity)
            else:
                logger.warning(f"  Product not found for product_id {self._current_selected_po_item_entity.product_id} from selected PO item.")
                self._handle_direct_receipt_state_for_product_fields() # ریست کردن فیلدهای کالا و فعال کردن انتخاب مستقیم
        else: # اگر آیتم معتبری از PO انتخاب نشده (مثلاً "-- انتخاب قلم --" انتخاب شده)
            logger.debug("  No valid PO Item entity selected (likely placeholder).")
            self._current_selected_po_item_entity = None
            self._handle_direct_receipt_state_for_product_fields()

    def _handle_direct_receipt_state_for_product_fields(self):
        """Resets product related fields and enables product_combo for direct selection."""
        self.product_combo.setEnabled(True)
        if self.product_combo.count() > 0 : self.product_combo.setCurrentIndex(-1) # پاک کردن انتخاب قبلی
        self.unit_price_spinbox.setValue(0)
        self.quantity_received_spinbox.setValue(0) # ریست کردن تعداد
        self.quantity_received_spinbox.setMaximum(999999.99)

    def _handle_direct_receipt_state(self):
        """Sets UI elements for direct receipt mode (no PO selected)."""
        logger.debug("Setting UI to direct receipt state.")
        self._selected_po = None
        self._current_selected_po_item_entity = None

        self.supplier_combo.setEnabled(True)
        if self.supplier_combo.count() > 0: self.supplier_combo.setCurrentIndex(0) # یا -1 برای خالی بودن

        self.po_item_combo.clear()
        self.po_item_combo.addItem("-- انتخاب قلم از سفارش --", None)
        self.po_item_combo.setEnabled(False)
        
        self._handle_direct_receipt_state_for_product_fields() # ریست کردن فیلدهای کالا


    def get_receipt_data(self) -> Optional[Dict[str, Any]]:
        logger.debug("MaterialReceiptDialog.get_receipt_data called.")
        logger.debug(f"  _selected_po: {self._selected_po.order_number if self._selected_po else 'None'}")
        if isinstance(self._current_selected_po_item_entity, PurchaseOrderItemEntity):
            logger.debug(f"  _current_selected_po_item_entity: Product ID {self._current_selected_po_item_entity.product_id}, Item ID {self._current_selected_po_item_entity.id}")
        else:
            logger.debug(f"  _current_selected_po_item_entity is: {self._current_selected_po_item_entity}")

        # ... (بقیه متد get_receipt_data با استفاده از self._current_selected_po_item_entity برای استخراج
        # final_product_id و final_po_item_id مانند قبل، با اطمینان از بررسی None بودن) ...
        quantity = self.quantity_received_spinbox.value()
        unit_price = self.unit_price_spinbox.value()
        
        if quantity <= 0:
            QMessageBox.warning(self, "ورودی نامعتبر", "تعداد دریافتی باید مثبت باشد.")
            return None
        if unit_price < 0:
            QMessageBox.warning(self, "ورودی نامعتبر", "قیمت واحد نمی‌تواند منفی باشد.")
            return None

        selected_po_id_val = self.po_combo.currentData() # این همان po.id است یا None
        final_supplier_id: Optional[int] = None
        final_product_id: Optional[int] = None
        final_po_item_id: Optional[int] = None

        if self._selected_po: # اگر یک PO انتخاب شده است (نه گزینه "-- رسید مستقیم --")
            logger.debug(f"  Processing as PO-linked receipt for PO ID: {self._selected_po.id}")
            final_supplier_id = self._selected_po.person_id
            
            if isinstance(self._current_selected_po_item_entity, PurchaseOrderItemEntity) and \
               self._current_selected_po_item_entity.id is not None and \
               self._current_selected_po_item_entity.product_id is not None:
                
                final_po_item_id = self._current_selected_po_item_entity.id
                final_product_id = self._current_selected_po_item_entity.product_id
                logger.debug(f"    Derived from selected PO Item Entity: product_id={final_product_id}, po_item_id={final_po_item_id}")
            else:
                logger.warning("  PO selected, but _current_selected_po_item_entity is not a valid selected PO item.")
                QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک قلم معتبر از سفارش خرید انتخاب کنید.")
                return None
        else: # رسید مستقیم
            logger.debug("  Processing as Direct Receipt.")
            final_supplier_id = self.supplier_combo.currentData()
            final_product_id = self.product_combo.currentData()
            if not final_supplier_id or final_supplier_id == -1:
                QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک تامین‌کننده برای رسید مستقیم انتخاب کنید.")
                return None
        
        if not final_product_id or final_product_id == -1: 
            logger.error(f"  Final product_id is invalid or -1. Final product ID: {final_product_id}")
            QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک کالا انتخاب کنید (از لیست مستقیم یا از قلم سفارش).")
            return None
        if not final_supplier_id or final_supplier_id == -1 : 
             logger.error(f"  Final supplier_id is not set or invalid.")
             QMessageBox.warning(self, "ورودی نامعتبر", "تامین کننده مشخص نشده است.")
             return None
        receipt_date_val = self.receipt_date_edit.date()

        data_to_return = {
            "receipt_date": receipt_date_val,
            "product_id": final_product_id,
            "quantity_received": quantity,
            "supplier_person_id": final_supplier_id, 
            "purchase_order_id": self._selected_po.id if self._selected_po else None,
            "purchase_order_item_id": final_po_item_id,
            "unit_price_override": unit_price, 
            "description": self.description_edit.toPlainText().strip(),
            "fiscal_year_id": self.fiscal_year_id_spinbox.value() if self.fiscal_year_id_spinbox.value() > 0 else None,
        }
        if self.is_edit_mode and self.receipt_to_edit and self.receipt_to_edit.id:
            data_to_return["receipt_id"] = self.receipt_to_edit.id
            
        logger.debug(f"  get_receipt_data returning: {data_to_return}")
        return data_to_return
    
    def _load_receipt_data_for_editing(self):
        if not self.receipt_to_edit:
            return

        receipt = self.receipt_to_edit
        logger.debug(f"Loading receipt data for editing. Receipt ID: {receipt.id}")

        if isinstance(receipt.receipt_date, date):
            self.receipt_date_edit.setDate(self.receipt_to_edit.receipt_date)
        
        current_po_id = receipt.purchase_order_id
        current_supplier_id = receipt.person_id
        current_product_id = receipt.product_id
        current_po_item_id = receipt.purchase_order_item_id

        if current_po_id:
            po_index = self.po_combo.findData(current_po_id)
            if po_index != -1:
                self.po_combo.setCurrentIndex(po_index) 
                # _on_po_selected فراخوانی و supplier و po_item_combo را تنظیم می‌کند
                # و product_combo را غیرفعال می‌کند.
                # سپس باید قلم سفارش صحیح را انتخاب کنیم
                QApplication.processEvents() # اجازه پردازش سیگنال تغییر po_combo
                self._try_select_po_item(current_po_item_id)
            else: 
                logger.warning(f"PO ID {current_po_id} from receipt not found in combo.")
                self.po_combo.setCurrentIndex(0) # انتخاب "-- رسید مستقیم --"
                self._select_direct_supplier_and_product(receipt) # این متد supplier و product را تنظیم می‌کند
        else: 
            self.po_combo.setCurrentIndex(0) 
            self._select_direct_supplier_and_product(receipt)

        self.quantity_received_spinbox.setValue(receipt.quantity_received)
        self.unit_price_spinbox.setValue(receipt.unit_price if receipt.unit_price is not None else 0.0)
        self.fiscal_year_id_spinbox.setValue(receipt.fiscal_year_id or 0)
        self.description_edit.setText(receipt.description or "")

        # --- غیرفعال کردن فیلدهای کلیدی در حالت ویرایش ---
        self.po_combo.setEnabled(False)
        self.supplier_combo.setEnabled(False)
        self.po_item_combo.setEnabled(False)
        self.product_combo.setEnabled(False)
        # اگر می‌خواهید تعداد و قیمت هم غیرقابل ویرایش باشند، آنها را هم disable کنید:
        # self.quantity_received_spinbox.setEnabled(False)
        # self.unit_price_spinbox.setEnabled(False)
        # فعلاً اجازه ویرایش تعداد و قیمت را می‌دهیم.

        logger.info(f"Receipt data loaded for editing ID: {receipt.id}. Key fields disabled.")


    def _select_direct_supplier_and_product(self, receipt: MaterialReceiptEntity):
        """Helper to select supplier and product for direct receipt in edit mode."""
        if receipt.person_id:
            supplier_idx = self.supplier_combo.findData(receipt.person_id)
            if supplier_idx != -1: self.supplier_combo.setCurrentIndex(supplier_idx)
        
        if receipt.product_id:
            prod_idx = self.product_combo.findData(receipt.product_id)
            if prod_idx != -1: self.product_combo.setCurrentIndex(prod_idx)
        
        self.supplier_combo.setEnabled(True) # اطمینان از فعال بودن
        self.product_combo.setEnabled(True) # اطمینان از فعال بودن
        self.po_item_combo.setEnabled(False)


    def _try_select_po_item(self, po_item_id_to_select: Optional[int]):
        """Attempts to select a PO item in the po_item_combo if it's populated."""
        if po_item_id_to_select is None:
            return
        
        # po_item_combo داده‌اش خود آبجکت PurchaseOrderItemEntity است
        for i in range(self.po_item_combo.count()):
            item_data = self.po_item_combo.itemData(i)
            if isinstance(item_data, PurchaseOrderItemEntity) and item_data.id == po_item_id_to_select:
                self.po_item_combo.setCurrentIndex(i)
                # _on_po_item_selected باید فراخوانی شود
                return
        logger.warning(f"Could not find/select PO Item ID {po_item_id_to_select} in po_item_combo during edit load.")

    
class MaterialReceiptsUI(QWidget):
    def __init__(self, 
                 receipt_manager: MaterialReceiptManager, 
                 po_manager: PurchaseOrderManager, 
                 product_manager: ProductManager, 
                 person_manager: PersonManager, 
                 parent=None):
        super().__init__(parent)
        self.receipt_manager = receipt_manager
        self.po_manager = po_manager        # برای پاس دادن به دیالوگ و مدل جدول
        self.product_manager = product_manager  # برای پاس دادن به دیالوگ و مدل جدول
        self.person_manager = person_manager    # برای پاس دادن به دیالوگ و مدل جدول

        # ارسال مدیران لازم به مدل جدول
        self.table_model = MaterialReceiptTableModel(
            person_manager=self.person_manager,
            product_manager=self.product_manager,
            po_manager=self.po_manager
        )
        
        self._init_ui()
        self.load_receipts_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # TODO: Add filters for receipts (e.g., by date range, supplier, PO) later if needed
        self.receipt_table_view = QTableView()
        self.receipt_table_view.setModel(self.table_model)
        self.receipt_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.receipt_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.receipt_table_view.setSortingEnabled(True)
        self.receipt_table_view.setAlternatingRowColors(True)

        header = self.receipt_table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            # می‌توانید عرض ستون‌های خاصی را Stretch کنید
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # تامین‌کننده
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # کالا
        
        # مرتب‌سازی پیش‌فرض بر اساس تاریخ رسید به صورت نزولی
        self.receipt_table_view.sortByColumn(1, Qt.SortOrder.DescendingOrder) 
        main_layout.addWidget(self.receipt_table_view)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("ثبت رسید جدید")
        self.edit_button = QPushButton("ویرایش رسید") 
        self.delete_button = QPushButton("حذف رسید")
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_receipt_dialog)
        self.edit_button.clicked.connect(self._open_edit_receipt_dialog) 
        self.delete_button.clicked.connect(self._delete_selected_receipt) 
        self.refresh_button.clicked.connect(self.load_receipts_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button) 
        button_layout.addWidget(self.delete_button) 
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("MaterialReceiptsUI initialized.")

    def load_receipts_data(self):
        logger.debug("Loading material receipts data...")
        try:
            receipts = self.receipt_manager.get_all_receipts()
            self.table_model.update_data(receipts)
            logger.info(f"{len(receipts)} material receipts loaded into table.")
        except Exception as e:
            logger.error(f"Error loading material receipts: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا در بارگذاری", f"خطا در بارگذاری لیست رسیدها: {e}")

    def _open_add_receipt_dialog(self):
        logger.debug("Opening Add Material Receipt dialog.")
        # پاس دادن مدیران لازم به دیالوگ
        dialog = MaterialReceiptDialog(
            purchase_order_manager=self.po_manager,
            product_manager=self.product_manager,
            person_manager=self.person_manager,
            # material_receipt_manager is not directly needed by the dialog itself for data entry
            parent=self
        )
        
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_receipt_data()
            if data:
                try:
                    # MaterialReceiptManager.record_material_receipt expects individual args
                    created_receipt = self.receipt_manager.record_material_receipt(
                        receipt_date=data["receipt_date"],
                        product_id=data["product_id"],
                        quantity_received=data["quantity_received"],
                        supplier_person_id=data["supplier_person_id"],
                        purchase_order_id=data.get("purchase_order_id"),
                        purchase_order_item_id=data.get("purchase_order_item_id"),
                        unit_price_override=data.get("unit_price_override"), # این همان unit_price از دیالوگ است
                        description=data.get("description"),
                        fiscal_year_id=data.get("fiscal_year_id")
                    )
                    if created_receipt:
                        QMessageBox.information(self, "موفقیت", f"رسید کالا با شناسه {created_receipt.id} با موفقیت ثبت شد.")
                        self.load_receipts_data() # Refresh table
                    else:
                        QMessageBox.warning(self, "خطا", "ثبت رسید کالا ناموفق بود.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error recording material receipt: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ثبت رسید کالا: {e}")
            else:
                logger.debug("Add material receipt dialog returned no data (or validation failed in dialog).")
        else:
            logger.debug("Add Material Receipt dialog cancelled.")
   
    def _open_edit_receipt_dialog(self):
        """Opens the MaterialReceiptDialog for editing the selected receipt."""
        selection_model = self.receipt_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک رسید را برای ویرایش انتخاب کنید.")
            return

        selected_row_index = selection_model.selectedRows()[0].row()
        receipt_to_edit = self.table_model.get_receipt_at_row(selected_row_index)

        if not receipt_to_edit or receipt_to_edit.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات رسید برای ویرایش.")
            return

        logger.debug(f"Opening Edit Material Receipt dialog for Receipt ID: {receipt_to_edit.id}")
        dialog = MaterialReceiptDialog(
            purchase_order_manager=self.po_manager,
            product_manager=self.product_manager,
            person_manager=self.person_manager,
            receipt_to_edit=receipt_to_edit, # Pass existing receipt data
            parent=self
        )

        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_receipt_data()
            # data باید شامل receipt_id باشد که از receipt_to_edit در دیالوگ مقداردهی شده
            if data and data.get("receipt_id") is not None: 
                try:
                    updated_receipt = self.receipt_manager.update_material_receipt(
                        receipt_id=data["receipt_id"],
                        receipt_date=data.get("receipt_date"),
                        # product_id, supplier_person_id, po_id, po_item_id از data خوانده نمی‌شوند
                        # چون در نسخه ساده شده update، اینها تغییر نمی‌کنند.
                        # اگر بخواهیم تغییر کنند، باید از data خوانده شوند.
                        # فعلاً فقط تعداد، قیمت، توضیحات و سال مالی را پاس می‌دهیم.
                        quantity_received=data.get("quantity_received"),
                        unit_price_override=data.get("unit_price_override"),
                        description=data.get("description"),
                        fiscal_year_id=data.get("fiscal_year_id")
                    )
                    if updated_receipt:
                        QMessageBox.information(self, "موفقیت", f"رسید کالا با شناسه {updated_receipt.id} با موفقیت ویرایش شد.")
                        self.load_receipts_data()
                    else:
                        QMessageBox.warning(self, "عدم تغییر", "تغییری در رسید اعمال نشد یا ویرایش ناموفق بود.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error updating material receipt: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ویرایش رسید کالا: {e}")
            else:
                logger.warning("Edit receipt dialog returned no data or receipt_id was missing.")
        else:
            logger.debug("Edit Material Receipt dialog cancelled.")


    def _delete_selected_receipt(self):
        """Deletes the selected material receipt after confirmation."""
        selection_model = self.receipt_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک رسید را برای حذف انتخاب کنید.")
            return

        selected_row_index = selection_model.selectedRows()[0].row()
        receipt_to_delete = self.table_model.get_receipt_at_row(selected_row_index)

        if not receipt_to_delete or receipt_to_delete.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات رسید برای حذف.")
            return

        reply = QMessageBox.question(self, "تایید حذف", 
                                     f"آیا از حذف رسید شناسه {receipt_to_delete.id} مطمئن هستید؟\n"
                                     "این عملیات، آثار انباری و سفارش خرید مرتبط را نیز برمی‌گرداند.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, # type: ignore
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            logger.debug(f"Attempting to delete Material Receipt ID: {receipt_to_delete.id}")
            try:
                success = self.receipt_manager.delete_material_receipt(receipt_to_delete.id) # type: ignore
                if success:
                    QMessageBox.information(self, "موفقیت", f"رسید شناسه {receipt_to_delete.id} با موفقیت حذف شد.")
                    self.load_receipts_data()
                else:
                    QMessageBox.warning(self, "ناموفق", f"رسید شناسه {receipt_to_delete.id} حذف نشد. (بررسی لاگ‌ها)")
            except ValueError as ve: 
                 QMessageBox.critical(self, "خطا در حذف", str(ve))
            except Exception as e:
                logger.error(f"Error deleting material receipt: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"خطا در حذف رسید: {e}")

