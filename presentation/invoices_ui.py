# src/presentation/invoices_ui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QPushButton, QHBoxLayout,
    QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout,QGroupBox,
    QDialogButtonBox, QAbstractItemView, QDoubleSpinBox, QTextEdit,
    QHeaderView, QDateEdit, QSpinBox, QApplication, QFileDialog,QCheckBox # QSpinBox برای سال مالی
)

from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate, pyqtSignal, QTimer, QSortFilterProxyModel
from PyQt5.QtGui import QColor, QFont, QTextDocument, QPainter
from decimal import Decimal
from typing import List, Optional, Any, Dict, Union
from datetime import date, datetime
from weasyprint import HTML, CSS # <<< وارد کردن WeasyPrint
#from weasyprint.fonts import FontConfiguration # برای تنظیمات فونت پیشرفته (اختیاری)
import logging # اطمینان از وجود logger
# Entities, Enums, Managers
from src.business_logic.entities.invoice_entity import InvoiceEntity
from src.business_logic.entities.invoice_item_entity import InvoiceItemEntity
from src.business_logic.entities.person_entity import PersonEntity
from src.business_logic.entities.product_entity import ProductEntity
from src.business_logic.entities.payment_header_entity import PaymentHeaderEntity

from src.constants import InvoiceType, PersonType, ProductType, DATE_FORMAT # و سایر ثابت‌های لازم
from src.business_logic.account_manager import AccountManager
from src.business_logic.invoice_manager import InvoiceManager
from src.business_logic.person_manager import PersonManager
from src.business_logic.product_manager import ProductManager
from src.business_logic.payment_manager import PaymentManager
# FinancialTransactionManager و AccountManager به طور غیرمستقیم توسط InvoiceManager استفاده 
import os
from src.constants import InvoiceStatus,PaymentMethod, PersonType, ProductType, DATE_FORMAT
from src.utils import date_converter
from .custom_widgets import ShamsiDateEdit # <<< ویجت جدید اضافه شد

import logging
logger = logging.getLogger(__name__)
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint library found and imported successfully.")
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML, CSS = None, None # Define them as None if import fails to prevent later errors
    logger.warning("WeasyPrint library not found. PDF export with WeasyPrint will be disabled.")
# --- End WeasyPrint Imports ---
class JalaliDateEdit(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        # فرمت نمایش شمسی است
        self.setDisplayFormat("yyyy/MM/dd")

    def textFromDate(self, date: QDate) -> str:
        """تبدیل تاریخ میلادی داخلی به رشته شمسی برای نمایش."""
        gregorian_date = date_converter.from_qdate(date)
        return date_converter.to_shamsi_str(gregorian_date)

    def dateFromText(self, text: str) -> QDate:
        """تبدیل رشته تاریخ شمسی از ورودی کاربر به تاریخ میلادی داخلی."""
        gregorian_date = date_converter.to_gregorian_date(text)
        if gregorian_date:
            return date_converter.to_qdate(gregorian_date)
        return QDate.currentDate() # در صورت خطا، تاریخ امروز را برگردان

    def gregorianDate(self) -> date:
        """تاریخ میلادی استاندارد پایتون را برمی‌گرداند."""
        return self.date().toPyDate()

# --- Table Model for the main list of Invoices ---
class InvoiceTableModel(QAbstractTableModel):
    def __init__(self, 
                 person_manager: Optional[PersonManager] = None, 
                 data: Optional[List[InvoiceEntity]] = None,
                 parent=None):
        super().__init__(parent)
        self._invoices: List[InvoiceEntity] = data if data is not None else []
        self._person_manager = person_manager
        
        self._headers = ["شماره فاکتور", "نوع", "تاریخ", "مشتری/تامین‌کننده", 
                         "مبلغ کل", "پرداخت شده", "مانده", "وضعیت کلی", "وضعیت پرداخت"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._invoices)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid(): return QVariant()
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._invoices)): return QVariant()
        
        invoice: InvoiceEntity = self._invoices[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return invoice.invoice_number
            elif col == 1: return invoice.invoice_type.value if isinstance(invoice.invoice_type, InvoiceType) else str(invoice.invoice_type)
            elif col == 2: 
                inv_date = invoice.invoice_date
                return date_converter.to_shamsi_str(invoice.invoice_date)
            
            elif col == 3: 
                if self._person_manager and invoice.person_id is not None:
                    try:
                        person = self._person_manager.get_person_by_id(int(invoice.person_id))
                        return person.name if person else f"ID: {invoice.person_id}"
                    except (ValueError, TypeError): 
                        logger.warning(f"Invalid person_id '{invoice.person_id}' in InvoiceTableModel for invoice ID {invoice.id}")
                        return str(invoice.person_id)
                return str(invoice.person_id) if invoice.person_id is not None else "-"
            elif col == 4: return f"{invoice.total_amount:,.2f}"
            elif col == 5: return f"{invoice.paid_amount:,.2f}"
            elif col == 6: return f"{invoice.remaining_amount:,.2f}"
            elif col == 7: 
                return invoice.status.value if hasattr(invoice, 'status') and isinstance(invoice.status, InvoiceStatus) else "نامشخص"
            elif col == 8: return "پرداخت شده" if invoice.is_paid else "پرداخت نشده"
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0,1,2,7,8]: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            if col in [4,5,6]: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ForegroundRole:
            if hasattr(invoice, 'status') and invoice.status == InvoiceStatus.CANCELED:
                return QColor(Qt.GlobalColor.gray)
            elif not invoice.is_paid and invoice.invoice_type == InvoiceType.SALE:
                if invoice.due_date and isinstance(invoice.due_date, date) and invoice.due_date < date.today():
                    return QColor("red")
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[InvoiceEntity]):
        self.beginResetModel()
        self._invoices = new_data if new_data is not None else []
        self.endResetModel()
        logger.debug(f"InvoiceTableModel updated with {len(self._invoices)} invoices.")

    def get_invoice_at_row(self, row: int) -> Optional[InvoiceEntity]:
        if 0 <= row < len(self._invoices): return self._invoices[row]
        return None
# ### پایان کد کلاس InvoiceTableModel ###
class InvoiceItemTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, 
                 product_manager: Optional[ProductManager] = None, 
                 parent=None):
        super().__init__(parent)
        self._items_data: List[Dict[str, Any]] = data if data is not None else []
        self._product_manager = product_manager
        self._headers = ["کد کالا", "نام کالا/خدمت", "تعداد", "واحد", "قیمت واحد", "مبلغ کل", "توضیحات قلم"] 

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid(): return QVariant()
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._items_data)): return QVariant()
        
        item_data = self._items_data[row] 

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(item_data.get("product_id", "")) # کد کالا
            elif col == 1: # نام کالا/خدمت
                return item_data.get("product_name_display", "نامشخص")
            elif col == 2: return str(item_data.get("quantity", 0)) # تعداد
            elif col == 3: return str(item_data.get("unit_of_measure", "-")) # واحد
            elif col == 4: return f"{Decimal(str(item_data.get('unit_price', '0.0'))):,.2f}" # قیمت واحد
            elif col == 5: # مبلغ کل (قبلاً توضیحات بود)
                try:
                    quantity = Decimal(str(item_data.get("quantity", 0)))
                    unit_price = Decimal(str(item_data.get("unit_price", 0.0)))
                    return f"{(quantity * unit_price):,.2f}"
                except: return "0.00"
            elif col == 6: return str(item_data.get("description", "")) # <<< ستون جدید توضیحات در انتها
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 2, 3]: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            # مبلغ کل و قیمت واحد راست‌چین
            if col in [4, 5]: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter 
            # توضیحات می‌تواند راست‌چین یا بر اساس محتوا باشد
            # اگر توضیحات طولانی است، AlignTop هم می‌تواند مناسب باشد
            if col == 6: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter 
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._items_data = new_data if new_data is not None else []
        self.endResetModel()
        logger.debug(f"InvoiceItemTableModel updated with {len(self._items_data)} items.")


    def get_item_data_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._items_data): return self._items_data[row]
        return None
    
    def add_item(self, item_data: Dict[str, Any]):
        self.beginInsertRows(QModelIndex(), len(self._items_data), len(self._items_data))
        self._items_data.append(item_data)
        self.endInsertRows()
        logger.debug(f"Item added to InvoiceItemTableModel: {item_data}")

    def remove_item(self, row: int):
        if 0 <= row < len(self._items_data):
            self.beginRemoveRows(QModelIndex(), row, row)
            removed_item = self._items_data.pop(row)
            self.endRemoveRows()
            logger.debug(f"Item removed from InvoiceItemTableModel: {removed_item}")
            return True
        return False
        
    def update_item(self, row: int, item_data: Dict[str, Any]):
        if 0 <= row < len(self._items_data):
            self._items_data[row] = item_data
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount(QModelIndex()) - 1))
            logger.debug(f"Item updated in InvoiceItemTableModel at row {row}: {item_data}")
            return True
        return False
# ### پایان کد کلاس InvoiceItemTableModel ###
# --- Dialog for adding/editing a single Invoice Item ---
class InvoiceItemDialog(QDialog):
    def __init__(self, product_manager: ProductManager, 
                 invoice_type: InvoiceType, # To determine which products are eligible
                 item_data: Optional[Dict[str, Any]] = None, 
                 parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.invoice_type = invoice_type
        self.item_data_to_edit = item_data
        self.products_cache: List[ProductEntity] = [] 

        self.setWindowTitle("افزودن/ویرایش قلم فاکتور")
        self.setMinimumWidth(400) # عرض بیشتر برای نمایش بهتر نام کالا
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QFormLayout(self)
        self.product_combo = QComboBox(self)
        self.quantity_spinbox = QDoubleSpinBox(self)
        self.unit_price_spinbox = QDoubleSpinBox(self) # Price for this transaction
        self.item_description_edit = QLineEdit(self) # <<< فیلد جدید برای توضیحات قلم
        self.item_description_edit.setPlaceholderText("توضیحات اختیاری برای این قلم")
        self._populate_products_combo() # محصولات قبل از تنظیم مقادیر اولیه باید بارگذاری شوند

        self.quantity_spinbox.setDecimals(2)
        self.quantity_spinbox.setMinimum(0.01) 
        self.quantity_spinbox.setMaximum(999999.99)
        self.quantity_spinbox.setGroupSeparatorShown(False) # معمولا برای تعداد لازم نیست
        
        self.unit_price_spinbox.setDecimals(2)
        self.unit_price_spinbox.setMinimum(0.00)
        self.unit_price_spinbox.setMaximum(999999999.99) # افزایش ماکزیمم قیمت
        self.unit_price_spinbox.setGroupSeparatorShown(True)
        
        if self.item_data_to_edit: 
            product_id_to_select = self.item_data_to_edit.get("product_id")
            if product_id_to_select is not None:
                try:
                    idx = self.product_combo.findData(int(product_id_to_select))
                    if idx != -1: self.product_combo.setCurrentIndex(idx)
                    else: logger.warning(f"InvoiceItemDialog: Product ID {product_id_to_select} not found in combo for editing.")
                except (ValueError, TypeError):
                    logger.error(f"InvoiceItemDialog: Invalid product_id '{product_id_to_select}' for editing.")

            self.quantity_spinbox.setValue(self.item_data_to_edit.get("quantity", 1.0))
            self.unit_price_spinbox.setValue(self.item_data_to_edit.get("unit_price", 0.0))
            self.item_description_edit.setText(self.item_data_to_edit.get("description", "")) # <<< پر کردن توضیحات

        # اتصال سیگنال بعد از تمام تنظیمات اولیه و بارگذاری داده‌های ویرایش
        self.product_combo.currentIndexChanged.connect(self._on_product_selected)
        
        # اگر در حالت افزودن هستیم و آیتمی در کمبو انتخاب شده، _on_product_selected را دستی فراخوانی می‌کنیم
        # تا قیمت و موجودی اولیه تنظیم شود.
        if not self.item_data_to_edit and self.product_combo.currentIndex() != -1 : 
            self._on_product_selected(self.product_combo.currentIndex())


        layout.addRow("کالا/خدمت:", self.product_combo)
        layout.addRow("تعداد/مقدار:", self.quantity_spinbox)
        layout.addRow("قیمت واحد:", self.unit_price_spinbox)
        layout.addRow("توضیحات قلم:", self.item_description_edit) # <<< اضافه کردن به layout

        buttons_flags = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons_flags, Qt.Orientation.Horizontal, self) # type: ignore
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("تایید")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
    def _populate_products_combo(self):
        self.products_cache = self.product_manager.get_all_products(active_only=True)
        eligible_products: List[ProductEntity] = []
        if self.invoice_type == InvoiceType.SALE:
            eligible_products = [p for p in self.products_cache if p.product_type != ProductType.RAW_MATERIAL and p.id is not None]
        elif self.invoice_type == InvoiceType.PURCHASE:
            eligible_products = [p for p in self.products_cache if p.id is not None] 
        
        self.product_combo.clear()
        if not eligible_products:
            self.product_combo.addItem("موردی یافت نشد", -1)
            self.product_combo.setEnabled(False)
            self.quantity_spinbox.setEnabled(False) # غیرفعال کردن سایر فیلدها
            self.unit_price_spinbox.setEnabled(False)
            return
            
        self.product_combo.setEnabled(True)
        self.quantity_spinbox.setEnabled(True)
        self.unit_price_spinbox.setEnabled(True)

        for product in eligible_products:
            if product.id is not None: # اطمینان از اینکه شناسه None نیست
                 # اطمینان از اینکه موجودی اگر None است به 'N/A' تبدیل شود
                stock_display = product.stock_quantity if product.stock_quantity is not None and product.product_type != ProductType.SERVICE else 'N/A'
                self.product_combo.addItem(f"{product.name} (موجودی: {stock_display})", int(product.id))


    def _on_product_selected(self, index: int):
        if index == -1 : # اگر آیتمی انتخاب نشده یا آیتم "موردی یافت نشد" انتخاب شده
            self.unit_price_spinbox.setValue(0)
            self.quantity_spinbox.setValue(0.01) # مقدار کم برای جلوگیری از صفر بودن
            self.quantity_spinbox.setMaximum(0.01) # در این حالت اجازه تغییر ندهیم
            return

        product_id_data = self.product_combo.itemData(index) 
        
        # فقط در حالت افزودن، قیمت و موجودی را بر اساس انتخاب جدید تغییر می‌دهیم
        if product_id_data is not None and product_id_data != -1 and not self.item_data_to_edit: 
            try:
                product_id = int(product_id_data)
                selected_product = next((p for p in self.products_cache if p.id == product_id), None)
                
                if selected_product:
                    self.unit_price_spinbox.setValue(float(selected_product.unit_price)) # اطمینان از float
                    
                    if self.invoice_type == InvoiceType.SALE and selected_product.product_type != ProductType.SERVICE:
                        current_stock = selected_product.stock_quantity if selected_product.stock_quantity is not None else 0
                        if current_stock <= 0:
                            QMessageBox.warning(self, "موجودی ناکافی", f"کالای '{selected_product.name}' موجودی انبار ندارد.")
                            self.quantity_spinbox.setValue(0)
                            self.quantity_spinbox.setMaximum(0) # کاربر نتواند بیشتر از صفر وارد کند
                            self.quantity_spinbox.setEnabled(False)
                        else:
                            self.quantity_spinbox.setEnabled(True)
                            self.quantity_spinbox.setMaximum(float(current_stock)) # اطمینان از float
                            self.quantity_spinbox.setValue(1) # Default to 1
                    else: # Purchase or service
                        self.quantity_spinbox.setEnabled(True)
                        self.quantity_spinbox.setMaximum(999999.99) # Reset max for purchase/service
                        self.quantity_spinbox.setValue(1)
                else: # اگر محصول در کش پیدا نشد (نباید اتفاق بیفتد)
                    self.unit_price_spinbox.setValue(0)
                    self.quantity_spinbox.setValue(0.01)
                    self.quantity_spinbox.setMaximum(0.01)
            except (ValueError, TypeError) as e:
                logger.error(f"Error in _on_product_selected: {e}, product_id_data: {product_id_data}", exc_info=True)
                self.unit_price_spinbox.setValue(0)
                self.quantity_spinbox.setValue(0.01)
                self.quantity_spinbox.setMaximum(0.01)

    def get_item_data(self) -> Optional[Dict[str, Any]]:
        product_id_data = self.product_combo.currentData()
        final_product_id: Optional[int] = None

        if product_id_data is not None and product_id_data != -1:
            try:
                final_product_id = int(product_id_data)
            except (ValueError, TypeError):
                QMessageBox.warning(self, "ورودی نامعتبر", "شناسه کالا/خدمت انتخاب شده نامعتبر است.")
                return None
        
        if final_product_id is None:
            QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک کالا/خدمت انتخاب کنید.")
            return None
            
        quantity = self.quantity_spinbox.value()
        if quantity <= 0: 
            QMessageBox.warning(self, "ورودی نامعتبر", "تعداد/مقدار باید مثبت باشد.")
            return None
            
        unit_price = self.unit_price_spinbox.value()
        # قیمت واحد می‌تواند صفر باشد (مثلاً برای آیتم‌های هدیه یا نمونه)
        if unit_price < 0: 
            QMessageBox.warning(self, "ورودی نامعتبر", "قیمت واحد نمی‌تواند منفی باشد.")
            return None
        
        selected_product_text_parts = self.product_combo.currentText().split(" (موجودی:")
        selected_product_name = selected_product_text_parts[0] if selected_product_text_parts else "نامشخص"

        # اعتبارسنجی مجدد موجودی در زمان تایید، به خصوص برای فاکتور فروش
        if self.invoice_type == InvoiceType.SALE:
            product = self.product_manager.get_product_by_id(final_product_id) # این باید ProductEntity برگرداند
            if product and product.product_type != ProductType.SERVICE:
                current_stock = product.stock_quantity if product.stock_quantity is not None else 0
                if quantity > current_stock:
                    QMessageBox.warning(self, "موجودی ناکافی", 
                                        f"تعداد درخواستی ({quantity}) برای کالای '{product.name}' "
                                        f"بیشتر از موجودی انبار ({current_stock}) است.")
                    return None
        
        item_data_result = {
            "product_id": final_product_id,
            "product_name_display": selected_product_name, 
            "quantity": quantity,
            "unit_price": unit_price,
            "description": self.item_description_edit.text().strip() or None, # <<< گرفتن مقدار توضیحات
            # and is typically handled by the parent InvoiceDialog when loading.
        }
        if self.item_data_to_edit and "item_id_db" in self.item_data_to_edit:
             item_data_result["item_id_db"] = self.item_data_to_edit["item_id_db"]

        logger.debug(f"InvoiceItemDialog.get_item_data returning: {item_data_result}")
        return item_data_result
# ### پایان کد کلاس InvoiceItemDialog ###
class InvoiceDialog(QDialog):
    def __init__(self,
                 invoice_type: InvoiceType,
                 person_manager: PersonManager,
                 product_manager: ProductManager,
                 invoice_entity_data: Optional[InvoiceEntity] = None, # برای ویرایش
                 parent=None):
        super().__init__(parent)
        self.invoice_type = invoice_type
        self.person_manager = person_manager
        self.product_manager = product_manager
        self.invoice_to_edit_data = invoice_entity_data
        self.is_edit_mode = self.invoice_to_edit_data is not None

        # این لیست، دیکشنری‌هایی از داده‌های اقلام فاکتور را در این دیالوگ نگه می‌دارد
        # و به عنوان منبع داده برای items_table_model استفاده می‌شود.
        self.current_invoice_items_data: List[Dict[str, Any]] = [] 

        title = "ایجاد فاکتور فروش جدید" if invoice_type == InvoiceType.SALE else "ایجاد فاکتور خرید جدید"
        if self.is_edit_mode and self.invoice_to_edit_data:
            type_str = "فروش" if self.invoice_to_edit_data.invoice_type == InvoiceType.SALE else "خرید"
            title = f"ویرایش فاکتور {type_str}: {self.invoice_to_edit_data.invoice_number}"
        
        self.setWindowTitle(title)
        self.setMinimumSize(750, 600) 
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self._setup_ui()

        if  self.is_edit_mode and self.invoice_to_edit_data:
            self._load_invoice_data_for_editing()
        else:
            self.invoice_date_edit.setDate(date.today())
            self.due_date_edit.setDate(date.today())
            # TODO: دریافت سال مالی فعال پیش‌فرض از FiscalYearManager
            # active_fy = fiscal_year_manager.get_active_fiscal_year()
            # if active_fy: self.fiscal_year_id_spinbox.setValue(active_fy.id or 0)

        self._calculate_and_display_totals() # محاسبه اولیه جمع کل

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Header Group ---
        header_groupbox_title = "اطلاعات فاکتور فروش" if self.invoice_type == InvoiceType.SALE else "اطلاعات فاکتور خرید"
        header_groupbox = QGroupBox(header_groupbox_title)
        header_groupbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        form_layout = QFormLayout(header_groupbox)

        self.invoice_number_edit = QLineEdit(self)
        if self.is_edit_mode and self.invoice_to_edit_data: # شماره فاکتور در حالت ویرایش معمولاً قابل تغییر نیست
            self.invoice_number_edit.setReadOnly(True)
        
        self.person_label_text = "مشتری:" if self.invoice_type == InvoiceType.SALE else "تامین‌کننده:"
        self.person_combo = QComboBox(self)
        self._populate_person_combo()

        self.invoice_date_edit = ShamsiDateEdit(self)
        self.due_date_edit = ShamsiDateEdit(self)
        self.fiscal_year_id_spinbox = QSpinBox(self) 
        self.fiscal_year_id_spinbox.setRange(0, 9999) # 0 یعنی انتخاب نشده یا پیش‌فرض سیستم
        
        self.description_edit = QTextEdit(self)
        self.description_edit.setFixedHeight(60)
      
        form_layout.addRow("شماره فاکتور (اختیاری):", self.invoice_number_edit)
        form_layout.addRow(self.person_label_text, self.person_combo)
        form_layout.addRow("تاریخ فاکتور:", self.invoice_date_edit)
        if self.invoice_type == InvoiceType.SALE:
            form_layout.addRow("تاریخ سررسید:", self.due_date_edit)
        form_layout.addRow("شناسه سال مالی:", self.fiscal_year_id_spinbox)
        form_layout.addRow("توضیحات:", self.description_edit)
        
        if self.is_edit_mode and self.invoice_to_edit_data:
            self.status_display_label = QLabel() # برای نمایش وضعیت کلی و وضعیت پرداخت
            form_layout.addRow("وضعیت فاکتور:", self.status_display_label)
        main_layout.addWidget(header_groupbox)

        # --- Items Group ---
        items_groupbox = QGroupBox("اقلام فاکتور")
        items_groupbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        items_layout = QVBoxLayout(items_groupbox)

        self.items_table_view = QTableView()
        self.items_table_model = InvoiceItemTableModel(product_manager=self.product_manager) 
        self.items_table_view.setModel(self.items_table_model)
        self.items_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        items_header = self.items_table_view.horizontalHeader()
        if items_header:
            # "نام کالا/خدمت" (اندیس 1) و "توضیحات قلم" (اندیس 6) می‌توانند Stretch باشند
            items_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) 
            items_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch) 
            for col in [0, 2, 3, 4, 5]: # سایر ستون‌ها بر اساس محتوا
                items_header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        items_button_layout = QHBoxLayout()
        self.add_item_button = QPushButton("افزودن آیتم")
        self.edit_item_button = QPushButton("ویرایش آیتم")
        self.remove_item_button = QPushButton("حذف آیتم")

        self.add_item_button.clicked.connect(self._add_item_clicked)
        self.edit_item_button.clicked.connect(self._edit_item_clicked)
        self.remove_item_button.clicked.connect(self._remove_item_clicked)

        items_button_layout.addWidget(self.add_item_button)
        items_button_layout.addWidget(self.edit_item_button)
        items_button_layout.addWidget(self.remove_item_button)
        items_button_layout.addStretch()

        items_layout.addLayout(items_button_layout)
        items_layout.addWidget(self.items_table_view)
        main_layout.addWidget(items_groupbox)

        # --- Footer ---
        footer_layout = QVBoxLayout()
        totals_group_layout = QFormLayout() # برای نمایش مرتب‌تر جمع‌ها

        self.total_amount_label = QLabel("0.00")
        self.total_amount_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.paid_amount_display_label = QLabel("0.00")
        self.remaining_amount_display_label = QLabel("0.00")
        
        totals_group_layout.addRow("جمع کل فاکتور:", self.total_amount_label)
        totals_group_layout.addRow("پرداخت شده:", self.paid_amount_display_label)
        totals_group_layout.addRow("مانده:", self.remaining_amount_display_label)
        
        self.paid_amount_display_label.setVisible(self.is_edit_mode) # فقط در ویرایش نمایش داده شود
        self.remaining_amount_display_label.setVisible(self.is_edit_mode)

        footer_layout.addLayout(totals_group_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,  # type: ignore
                                           Qt.Orientation.Horizontal, self) # type: ignore
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("ذخیره فاکتور")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        
        footer_layout.addWidget(self.button_box)
        main_layout.addLayout(footer_layout)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.setLayout(main_layout)

    def _populate_person_combo(self):
        current_person_id = None
        if self.is_edit_mode and self.invoice_to_edit_data:
            current_person_id = self.invoice_to_edit_data.person_id
        
        self.person_combo.clear()
        self.person_combo.addItem(f"-- {self.person_label_text.replace(':', '')} --", None) # Placeholder
        person_type_to_fetch = PersonType.CUSTOMER if self.invoice_type == InvoiceType.SALE else PersonType.SUPPLIER
        try:
            persons = self.person_manager.get_persons_by_type(person_type_to_fetch)
            if not persons:
                self.person_combo.addItem("موردی یافت نشد", None)
                self.person_combo.setEnabled(False)
            else:
                self.person_combo.setEnabled(True)
                for person in persons:
                    if person.id is not None:
                        self.person_combo.addItem(f"{person.name} (ID: {person.id})", int(person.id)) # اطمینان از int
                if current_person_id is not None:
                    idx = self.person_combo.findData(current_person_id)
                    if idx != -1: self.person_combo.setCurrentIndex(idx)
                    else: self.person_combo.setCurrentIndex(0)
                else:
                     self.person_combo.setCurrentIndex(0) # انتخاب placeholder اگر در حالت افزودن هستیم
        except Exception as e:
            logger.error(f"Error populating persons combo for invoice: {e}", exc_info=True)
            self.person_combo.addItem("خطا در بارگذاری", None)
            self.person_combo.setEnabled(False)
            self.person_combo.setCurrentIndex(0)


    def _load_invoice_data_for_editing(self):
        if not self.invoice_to_edit_data: return
        inv = self.invoice_to_edit_data
        
        self.invoice_number_edit.setText(inv.invoice_number)
        
        # شخص قبلاً در _populate_person_combo (اگر is_edit_mode) انتخاب شده
        # person_idx = self.person_combo.findData(inv.person_id) 
        # if person_idx != -1: self.person_combo.setCurrentIndex(person_idx)
        
        if isinstance(inv.invoice_date, date):
            self.invoice_date_edit.setDate(inv.invoice_date)
        if inv.due_date:
            self.due_date_edit.setDate(inv.due_date)
        self.description_edit.setText(inv.description or "")
        self.fiscal_year_id_spinbox.setValue(inv.fiscal_year_id or 0)
        
        status_text = f"وضعیت کلی: {inv.status.value if hasattr(inv, 'status') and inv.status else 'نامشخص'}"
        status_text += f" | پرداخت: {'کامل' if inv.is_paid else 'نشده/ناقص'}"
        if hasattr(self, 'status_display_label'): # اطمینان از وجود ویجت
            self.status_display_label.setText(status_text)

        self.current_invoice_items_data = []
        if inv.items:
            for item_entity in inv.items:
                product_name = "کالای نامشخص"
                if self.product_manager and item_entity.product_id is not None:
                     product = self.product_manager.get_product_by_id(item_entity.product_id)
                     if product: product_name = product.name
                item_description_value = getattr(item_entity, 'description', None) # بگیرید، می‌تواند None باشد
     
                self.current_invoice_items_data.append({
                    "item_id_db": item_entity.id, 
                    "product_id": item_entity.product_id,
                    "product_name_display": product_name,
                    "quantity": item_entity.quantity,
                    "unit_price": item_entity.unit_price,
                    "description": item_description_value # <<< از متغیر استفاده کنید
                })
        self.items_table_model.update_data(self.current_invoice_items_data)
        # _calculate_and_display_totals در انتهای سازنده فراخوانی می‌شود

    def _add_item_clicked(self):
        item_dialog = InvoiceItemDialog(self.product_manager, self.invoice_type, parent=self)
        if item_dialog.exec_() == QDialog.DialogCode.Accepted:
            new_item_data = item_dialog.get_item_data()
            if new_item_data:
                self.current_invoice_items_data.append(new_item_data)
                self.items_table_model.update_data(self.current_invoice_items_data) # یا add_item اگر مدل پشتیبانی می‌کند
                self._calculate_and_display_totals()

    def _edit_item_clicked(self):
        # ... (بدنه این متد مانند قبل، با استفاده از self.items_table_model.update_item یا مدیریت مستقیم self.current_invoice_items_data و سپس update_data)
        selection_model = self.items_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection(): QMessageBox.information(self, "انتخاب نشده", "یک قلم را انتخاب کنید."); return
        selected_indexes = selection_model.selectedRows()
        if not selected_indexes: return
        row_to_edit = selected_indexes[0].row()
        item_data_to_edit = dict(self.current_invoice_items_data[row_to_edit])
        item_dialog = InvoiceItemDialog(self.product_manager, self.invoice_type, item_data=item_data_to_edit, parent=self)
        if item_dialog.exec_() == QDialog.DialogCode.Accepted:
            updated_item_data = item_dialog.get_item_data()
            if updated_item_data:
                if "item_id_db" in item_data_to_edit: updated_item_data["item_id_db"] = item_data_to_edit["item_id_db"]
                self.current_invoice_items_data[row_to_edit] = updated_item_data
                self.items_table_model.update_data(self.current_invoice_items_data)
                self._calculate_and_display_totals()


    def _remove_item_clicked(self):
        # ... (بدنه این متد مانند قبل، با استفاده از self.items_table_model.remove_item یا مدیریت مستقیم self.current_invoice_items_data و سپس update_data)
        selection_model = self.items_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection(): QMessageBox.information(self, "انتخاب نشده", "یک قلم را انتخاب کنید."); return
        selected_indexes = selection_model.selectedRows()
        if not selected_indexes: return
        row_to_remove = selected_indexes[0].row()
        item_to_remove = self.current_invoice_items_data[row_to_remove]
        reply = QMessageBox.question(self, "تایید حذف قلم", f"حذف قلم '{item_to_remove.get('product_name_display', '')}'؟", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) # type: ignore
        if reply == QMessageBox.StandardButton.Yes:
            del self.current_invoice_items_data[row_to_remove]
            self.items_table_model.update_data(self.current_invoice_items_data)
            self._calculate_and_display_totals()


    def _calculate_and_display_totals(self) -> float: 
        total = sum(Decimal(str(item.get("quantity", 0))) * Decimal(str(item.get("unit_price", 0.0))) for item in self.current_invoice_items_data)
        total_float = float(total)
        self.total_amount_label.setText(f"{total_float:,.2f}")
        
        if self.is_edit_mode and self.invoice_to_edit_data:
            paid = self.invoice_to_edit_data.paid_amount
            remaining = total_float - paid
            self.paid_amount_display_label.setText(f"{paid:,.2f}")
            self.remaining_amount_display_label.setText(f"{remaining:,.2f}")
        else: 
            self.paid_amount_display_label.setText("0.00")
            self.remaining_amount_display_label.setText(f"{total_float:,.2f}")
        return total_float

    def get_invoice_data(self) -> Optional[Dict[str, Any]]:
        person_id_data = self.person_combo.currentData()
        final_person_id: Optional[int] = None
        if person_id_data is not None:
            try: final_person_id = int(person_id_data)
            except (ValueError, TypeError): pass
        
        if final_person_id is None:
            QMessageBox.warning(self, "ورودی نامعتبر", f"لطفاً یک {self.person_label_text.replace(':', '')} انتخاب کنید.")
            return None
        
        if not self.current_invoice_items_data:
            QMessageBox.warning(self, "ورودی نامعتبر", "فاکتور باید حداقل یک قلم کالا/خدمت داشته باشد.")
            return None
            
        invoice_date_val = self.invoice_date_edit.date()
        due_date_val = self.due_date_edit.date()

        fiscal_year_id_val = self.fiscal_year_id_spinbox.value()

        # اطمینان از وجود سال مالی برای فاکتور جدید یا ویرایش شده
        if fiscal_year_id_val <= 0:
            # TODO: در آینده، سال مالی فعال پیش‌فرض را اینجا تنظیم کنید اگر کاربر وارد نکرده
            QMessageBox.warning(self, "ورودی نامعتبر", "شناسه سال مالی باید یک عدد مثبت معتبر باشد.")
            return None


        items_data_list = []
        for item in self.current_invoice_items_data:
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            unit_price = item.get("unit_price")
            item_description = item.get("description") # This should be from the item's description field

            # Default to 0 if None, before converting to float/int
            product_id_int = int(product_id) if product_id is not None else None
            quantity_float = float(quantity) if quantity is not None else 0.0
            unit_price_float = float(unit_price) if unit_price is not None else 0.0

            if product_id_int is None:
                QMessageBox.warning(self, "خطای آیتم", "یکی از اقلام شناسه کالای معتبر ندارد.")
                return None
            if quantity_float <= 0:
                QMessageBox.warning(self, "خطای آیتم", f"تعداد برای کالای ID {product_id_int} باید مثبت باشد.")
                return None
            if unit_price_float < 0:
                QMessageBox.warning(self, "خطای آیتم", f"قیمت واحد برای کالای ID {product_id_int} نمی‌تواند منفی باشد.")
                return None

            items_data_list.append({
                "product_id": product_id_int,
                "quantity": quantity_float,
                "unit_price": unit_price_float,
                "item_id_db": item.get("item_id_db") ,
                "description": item.get("description"), # <<< اضافه کردن توضیحات

            })
        invoice_date_val = self.invoice_date_edit.date()
        due_date_val = self.due_date_edit.date()
        # ### پایان اصلاح پیشنهادی برای items_data ###
       
        data_dict = {
            "person_id": final_person_id,
            "invoice_date": invoice_date_val,
            "invoice_type": self.invoice_type,
            "due_date": due_date_val,
            "invoice_number_override": self.invoice_number_edit.text().strip() or None,
            "description": self.description_edit.toPlainText().strip(),
            "fiscal_year_id": fiscal_year_id_val,
            "items_data": items_data_list, # <<< استفاده از لیست اصلاح شده
        }
        if self.is_edit_mode and self.invoice_to_edit_data and self.invoice_to_edit_data.id:
            data_dict["invoice_id"] = self.invoice_to_edit_data.id
            
        logger.debug(f"InvoiceDialog.get_invoice_data returning: {data_dict}")
        return data_dict

# --- Main Invoices UI Widget ---
# ### شروع کد کلاس InvoicesUI ###
class InvoicesUI (QWidget):
    def __init__(self, 
                 invoice_manager: InvoiceManager, 
                 person_manager: PersonManager,
                 product_manager: ProductManager,
                 payment_manager: PaymentManager, # برای پاس دادن به دیالوگ‌ها اگر لازم باشد
                 company_details: Dict[str, Any],
                 parent=None):
        super().__init__(parent)
        self.invoice_manager = invoice_manager
        self.person_manager = person_manager
        self.product_manager = product_manager
        self.payment_manager = payment_manager        # self.fiscal_year_manager = fiscal_year_manager
        self.company_details = company_details 
        self.table_model = InvoiceTableModel(
            person_manager=self.person_manager
            # در آینده اگر نیاز به نمایش نام سال مالی در جدول بود، fiscal_year_manager هم پاس داده می‌شود
        )
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterKeyColumn(-1)  # جستجو در تمام ستون‌ها
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive) # جستجوی غیرحساس به حروف بزرگ و کوچک

        self._init_ui()
        self.load_invoices_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("جستجو در تمام ستون‌ها...")
        self.search_input.textChanged.connect(self.proxy_model.setFilterRegExp)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        # TODO: افزودن فیلترهای پیشرفته‌تر (تاریخ، نوع، شخص، وضعیت)

        self.invoice_table_view = QTableView(self)
        self.invoice_table_view.setModel(self.proxy_model) # اتصال جدول به پروکسی مدل
        self.invoice_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.invoice_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.invoice_table_view.setSortingEnabled(True)
        self.invoice_table_view.setAlternatingRowColors(True)
        self.invoice_table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.invoice_table_view.customContextMenuRequested.connect(self._show_context_menu)
        main_layout.addWidget(self.invoice_table_view)


        header = self.invoice_table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            # تنظیم عرض ستون‌های کلیدی
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # شماره فاکتور
            header.resizeSection(0, 150) 
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)   # مشتری/تامین‌کننده
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)   # مانده
        
        self.invoice_table_view.sortByColumn(2, Qt.SortOrder.DescendingOrder) # مرتب‌سازی پیش‌فرض بر اساس تاریخ فاکتور
        main_layout.addWidget(self.invoice_table_view)

        # دکمه‌ها
        button_layout = QHBoxLayout()
        self.add_sales_invoice_button = QPushButton(" (+) فاکتور فروش جدید")
        self.add_purchase_invoice_button = QPushButton(" (+) فاکتور خرید جدید")
        self.edit_button = QPushButton("ویرایش فاکتور")
        self.view_details_button = QPushButton("مشاهده جزئیات")
        self.cancel_invoice_button = QPushButton("ابطال فاکتور") 
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_sales_invoice_button.clicked.connect(lambda: self._open_invoice_dialog_for_add(InvoiceType.SALE))
        self.add_purchase_invoice_button.clicked.connect(lambda: self._open_invoice_dialog_for_add(InvoiceType.PURCHASE))
        self.edit_button.clicked.connect(self._open_edit_invoice_dialog)
        self.view_details_button.clicked.connect(self._view_invoice_details)
        self.cancel_invoice_button.clicked.connect(self._cancel_selected_invoice) 
        self.refresh_button.clicked.connect(self.load_invoices_data)

        button_layout.addWidget(self.add_sales_invoice_button)
        button_layout.addWidget(self.add_purchase_invoice_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.view_details_button)
        button_layout.addWidget(self.cancel_invoice_button) 
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("InvoicesUI initialized.")

    def _show_context_menu(self, position):
        # این متد برای نمایش منوی راست کلیک روی جدول است (اختیاری)
        # می‌توانید عملکردهای ویرایش، حذف، ابطال و مشاهده جزئیات را اینجا هم قرار دهید
        pass

    def load_invoices_data(self):
        logger.debug("Loading invoices data...")
        try:
            invoices = self.invoice_manager.get_all_invoices_summary()
            self.table_model.update_data(invoices)
            logger.info(f"{len(invoices)} invoices loaded into table model.")
        except Exception as e:
            logger.error(f"Error loading invoices: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری لیست فاکتورها: {e}")
    def _get_selected_invoice_header(self) -> Optional[InvoiceEntity]:
        selection_model = self.invoice_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک فاکتور را انتخاب کنید.")
            return None
        
        # تبدیل ایندکس پروکسی به ایندکس مدل اصلی
        proxy_index = selection_model.selectedRows()[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        
        return self.table_model.get_invoice_at_row(source_index.row())
    def _call_invoice_dialog(self, invoice_type: InvoiceType, invoice_to_edit: Optional[InvoiceEntity] = None):
        action_text = "افزودن" if not invoice_to_edit else "ویرایش"
        logger.debug(f"InvoicesUI: Calling InvoiceDialog for {action_text} - Type: {invoice_type.value}, Edit ID: {invoice_to_edit.id if invoice_to_edit else None}")
        
        dialog = InvoiceDialog(
            invoice_type=invoice_type,
            person_manager=self.person_manager,
            product_manager=self.product_manager,
            invoice_entity_data=invoice_to_edit,
            parent=self
        )
        
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_invoice_data()
            if data:
                try:
                    if invoice_to_edit and invoice_to_edit.id:
                        logger.info(f"Attempting to update invoice ID: {invoice_to_edit.id}")
                        # FIX: فراخوانی صحیح متد update_invoice با دو آرگومان
                        updated_invoice = self.invoice_manager.update_invoice(
                            invoice_id=invoice_to_edit.id,
                            update_data=data
                        )
                        if updated_invoice:
                            QMessageBox.information(self, "موفقیت", f"فاکتور شماره '{updated_invoice.invoice_number}' با موفقیت ویرایش شد.")
                        else:
                            QMessageBox.warning(self, "عدم تغییر", "تغییری در فاکتور اعمال نشد یا ویرایش ناموفق بود.")
                    else: # حالت افزودن
                        logger.info(f"Attempting to create a new invoice with data: {data}")
                        created_invoice = self.invoice_manager.create_invoice(
                            invoice_type=data["invoice_type"], 
                            person_id=data["person_id"],
                            invoice_date=data["invoice_date"],
                            items_data=data["items_data"],
                            due_date=data.get("due_date"),
                            description=data.get("description"),
                            fiscal_year_id=data.get("fiscal_year_id"),
                            invoice_number_override=data.get("invoice_number_override")
                        )
                        if created_invoice:
                            QMessageBox.information(self, "موفقیت", f"فاکتور شماره '{created_invoice.invoice_number}' با موفقیت ایجاد شد.")
                        else:
                            QMessageBox.warning(self, "خطا", "ایجاد فاکتور ناموفق بود.")
                    
                    self.load_invoices_data()
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error processing invoice: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در پردازش فاکتور: {e}")
            else:
                logger.debug(f"InvoiceDialog for {action_text} was cancelled or returned no data.")


    def _open_invoice_dialog_for_add(self, invoice_type: InvoiceType):
        self._call_invoice_dialog(invoice_type=invoice_type, invoice_to_edit=None)

    def _open_edit_invoice_dialog(self):
        selected_invoice_header = self._get_selected_invoice_header()
        if not selected_invoice_header or selected_invoice_header.id is None:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک فاکتور را برای ویرایش انتخاب کنید.")
            return

        # برای ویرایش، باید فاکتور کامل با اقلامش واکشی شود
        full_invoice_to_edit = self.invoice_manager.get_invoice_with_items(selected_invoice_header.id)
        if not full_invoice_to_edit:
            QMessageBox.critical(self, "خطا", f"اطلاعات کامل فاکتور با شناسه {selected_invoice_header.id} برای ویرایش یافت نشد.")
            self.load_invoices_data() # رفرش لیست در صورت بروز خطا
            return
        
        self._call_invoice_dialog(invoice_type=full_invoice_to_edit.invoice_type, invoice_to_edit=full_invoice_to_edit)

  
    def _view_invoice_details(self):
        logger.debug("InvoicesUI: _view_invoice_details called.") # <<< لاگ جدید
        selected_header = self._get_selected_invoice_header()
        if not selected_header or selected_header.id is None:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک فاکتور را برای مشاهده جزئیات انتخاب کنید.")
            logger.debug("InvoicesUI: No invoice selected for view details.") # <<< لاگ جدید
            return

        logger.debug(f"InvoicesUI: Selected invoice header ID: {selected_header.id}") # <<< لاگ جدید

        # برای نمایش جزئیات، فاکتور کامل با اقلامش لازم است
        full_invoice = self.invoice_manager.get_invoice_with_items(selected_header.id)
        if not full_invoice:
            QMessageBox.critical(self, "خطا", f"اطلاعات کامل فاکتور با شناسه {selected_header.id} یافت نشد.")
            logger.error(f"InvoicesUI: Full invoice not found for ID: {selected_header.id}") # <<< لاگ جدید
            return
        
        logger.debug(f"InvoicesUI: Full invoice with ID {full_invoice.id} fetched successfully.") # <<< لاگ جدید

        # company_details باید از self.company_details در InvoicesUI بیاید
        if not hasattr(self, 'company_details') or not self.company_details:
            logger.error("InvoicesUI: self.company_details is missing or None.") # <<< لاگ جدید
            QMessageBox.critical(self, "خطای داخلی", "اطلاعات شرکت برای نمایش فاکتور تنظیم نشده است.")
            return
        
        # payment_manager باید از self.payment_manager در InvoicesUI بیاید
        if not hasattr(self, 'payment_manager') or not self.payment_manager:
            logger.error("InvoicesUI: self.payment_manager is missing or None.") # <<< لاگ جدید
            QMessageBox.critical(self, "خطای داخلی", "مدیر پرداخت برای نمایش جزئیات فاکتور تنظیم نشده است.")
            return

        logger.debug("InvoicesUI: All managers and details seem to be ready. Instantiating InvoiceViewDialog...") # <<< لاگ جدید
          # اطلاعات شرکت را می‌توانید از یک فایل تنظیمات یا دیتابیس بخوانید
        # یا به صورت موقت هاردکد کنید
        company_info_dict = {
            "name": "", 
            "address": "آدرس شما", 
            "phone": "تلفن شما",
            "economic_code": "کد اقتصادی شما",
            "registration_number": "شماره ثبت شما"
        }
        view_dialog = InvoiceViewDialog(
            invoice=full_invoice,
            person_manager=self.person_manager, 
            product_manager=self.product_manager,
            payment_manager=self.payment_manager,
            company_details=self.company_details, 
            parent=self
        )
        logger.debug("InvoicesUI: InvoiceViewDialog instance created. Calling exec_()...") # <<< لاگ جدید
        result = view_dialog.exec_()
        logger.debug(f"InvoicesUI: InvoiceViewDialog exec_() finished with result: {result}") # <<< لاگ جدید
    def _cancel_selected_invoice(self):
        logger.debug("InvoicesUI: Cancel button clicked.")
        selected_header = self._get_selected_invoice_header() 
        if not selected_header or selected_header.id is None:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک فاکتور را برای ابطال انتخاب کنید.")
            return

        reply = QMessageBox.question(self, "تایید ابطال", 
                                     f"آیا از ابطال فاکتور شماره '{selected_header.invoice_number}' (ID: {selected_header.id}) مطمئن هستید؟\n"
                                     "این عملیات تمام آثار مالی و انباری فاکتور را برمی‌گرداند.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, # type: ignore
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # می‌توان یک تاریخ برای ابطال از کاربر گرفت یا از تاریخ فعلی استفاده کرد
                cancellation_date = date.today() 
                cancelled_invoice = self.invoice_manager.cancel_invoice(selected_header.id, cancellation_date)
                if cancelled_invoice:
                    QMessageBox.information(self, "موفقیت", f"فاکتور شماره '{cancelled_invoice.invoice_number}' با موفقیت باطل شد.")
                    self.load_invoices_data()
                else:
                    QMessageBox.warning(self, "ناموفق", "ابطال فاکتور انجام نشد (بررسی لاگ‌ها).")
            except ValueError as ve: 
                 QMessageBox.critical(self, "خطا در ابطال", str(ve))
            except Exception as e:
                logger.error(f"Error cancelling invoice ID {selected_header.id}: {e}", exc_info=True)
                QMessageBox.critical(self, "خطای سیستمی", f"خطا در ابطال فاکتور: {e}")
# ### پایان کد کلاس InvoicesUI ###
              
# ### شروع کد کلاس InvoiceViewDialog ###
from PyQt5.QtGui import QFontMetrics, QStandardItemModel, QStandardItem # برای محاسبه ارتفاع متن
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog # برای چاپ در آینده

class InvoiceViewDialog(QDialog):
    def __init__(self, 
                 invoice: InvoiceEntity, 
                 person_manager: PersonManager, 
                 product_manager: ProductManager,
                 payment_manager: Optional[PaymentManager], # <<< اطمینان از اینکه این پارامتر وجود دارد
                 company_details: Optional[Dict[str, Any]] = None,
                 parent=None):
        super().__init__(parent)
        self.invoice = invoice
        self.person_manager = person_manager
        self.product_manager = product_manager
        self.payment_manager = payment_manager # <<< و اینجا ذخیره می‌شود
        self.company_details = company_details if company_details else {
            "name": "نام شرکت پیش‌فرض", "logo_path": None, "app_name": "نرم‌افزار حسابداری"
        }
        self.setting_display_company_name_invoice_header = self.company_details.get('display_company_name_invoice_header', True)
        self.min_item_rows_on_invoice_print = self.company_details.get('min_item_rows_on_invoice_print', 7)

        self.setWindowTitle(f"مشاهده فاکتور: {self.invoice.invoice_number or 'جدید'}")
        self.setMinimumSize(800, 700) 
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui()
        self._populate_data() # این متد HTML اولیه را در QTextBrowser نمایش می‌دهد

        # اتصال سیگنال‌ها
        if hasattr(self, 'print_button'): self.print_button.clicked.connect(self._handle_print_weasyprint)
        if hasattr(self, 'pdf_button'): self.pdf_button.clicked.connect(self._handle_pdf_export_weasyprint)
        if hasattr(self, 'copy_text_button'): self.copy_text_button.clicked.connect(self._handle_copy_text)
        if hasattr(self, 'dialog_button_box'):
            self.dialog_button_box.rejected.connect(self.reject)
            close_btn = self.dialog_button_box.button(QDialogButtonBox.StandardButton.Close)
            if close_btn:
                close_btn.clicked.connect(self.reject)

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)

        top_controls_layout = QHBoxLayout()
        self.print_button = QPushButton("چاپ فاکتور")
        self.pdf_button = QPushButton("خروجی PDF")
        self.copy_text_button = QPushButton("کپی متن ساده")
        
        top_controls_layout.addWidget(self.print_button)
        top_controls_layout.addWidget(self.pdf_button)
        top_controls_layout.addWidget(self.copy_text_button)
        top_controls_layout.addStretch(1) 

        self.show_payments_checkbox = QCheckBox("نمایش پرداخت‌ها در PDF") # متن کوتاه‌تر
        self.show_payments_checkbox.setChecked(True) # پیش‌فرض فعال
        self.show_payments_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        top_controls_layout.addWidget(self.show_payments_checkbox)
        
        self.main_layout.addLayout(top_controls_layout)

        self.invoice_display_browser = QTextEdit() 
        self.invoice_display_browser.setReadOnly(True)
        # یک استایل پایه برای نمایش بهتر در QTextBrowser (اختیاری)
        # self.invoice_display_browser.document().setDefaultStyleSheet("body {font-family: Tahoma; direction:rtl; font-size:9pt;} table {border-collapse:collapse;} td,th {border:1px solid #ccc; padding:2px;} th {background-color:#f0f0f0;}")
        self.main_layout.addWidget(self.invoice_display_browser)
        
        self.dialog_button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = self.dialog_button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_button: close_button.setText("بستن")
        self.main_layout.addWidget(self.dialog_button_box)
        self.setLayout(self.main_layout)

    def _populate_data(self):
        logger.debug("InvoiceViewDialog: _populate_data called.") # <<< لاگ جدید
        if self.invoice and hasattr(self, 'invoice_display_browser'):
            show_payments = False
            if hasattr(self, 'show_payments_checkbox'):
                show_payments = self.show_payments_checkbox.isChecked()
            logger.debug(f"InvoiceViewDialog: _populate_data - show_payments_checkbox state: {show_payments}") # <<< لاگ جدید
            
            html_for_display = self._get_invoice_html_representation(show_payments_table=show_payments) 
            self.invoice_display_browser.setHtml(html_for_display)
            logger.debug("InvoiceViewDialog: HTML content set in invoice_display_browser.") # <<< لاگ جدید
        else:
            logger.warning("InvoiceViewDialog: _populate_data - Invoice or invoice_display_browser not available.") # <<< لاگ جدید


    def _handle_pdf_export_weasyprint(self):
        # ... (کد کامل این متد از پاسخ قبلی، شامل خواندن self.show_payments_checkbox.isChecked()) ...
        if not self.invoice: QMessageBox.warning(self, "خطا", "فاکتوری برای صدور PDF بارگذاری نشده است."); return
        invoice_number_for_file = (self.invoice.invoice_number or "UnknownInvoice").replace('/', '-').replace('\\', '-')
        default_filename = f"Invoice_WP_{invoice_number_for_file}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره فاکتور PDF", default_filename, "PDF Files (*.pdf)")
        if not file_path: return

        if not WEASYPRINT_AVAILABLE:
            QMessageBox.critical(self, "خطای WeasyPrint", "کتابخانه WeasyPrint یا وابستگی‌های آن نصب نشده‌اند.")
            return
        try:
            logger.info(f"Generating PDF at: {file_path} with show_payments: {self.show_payments_checkbox.isChecked()}")
            html_content = self._get_invoice_html_representation(show_payments_table=self.show_payments_checkbox.isChecked())
            if not html_content: QMessageBox.critical(self, "خطا", "محتوای HTML برای PDF خالی است."); return
            
            HTML(string=html_content).write_pdf(file_path)
            QMessageBox.information(self, "موفقیت", f"فاکتور PDF ذخیره شد:\n{file_path}")
        except Exception as e:
            logger.error(f"Error generating PDF with WeasyPrint: {e}", exc_info=True)
            QMessageBox.critical(self, "خطای تولید PDF", f"خطا در تولید PDF:\n{e}")

    def _handle_print_weasyprint(self): # برای چاپ مستقیم با WeasyPrint (نیاز به بررسی بیشتر دارد)
        if not self.invoice: return
        if not WEASYPRINT_AVAILABLE:
             QMessageBox.critical(self, "خطای WeasyPrint", "WeasyPrint برای چاپ در دسترس نیست.")
             return
        
        # چاپ مستقیم با WeasyPrint پیچیده‌تر است و معمولاً به یک فایل موقت PDF نیاز دارد
        # یا استفاده از API های سطح پایین‌تر آن.
        # ساده‌ترین راه، تولید PDF در یک فایل موقت و سپس ارسال آن به پرینتر پیش‌فرض سیستم است.
        # فعلاً این بخش را ساده نگه می‌داریم و به کاربر می‌گوییم PDF را ذخیره و چاپ کند.
        QMessageBox.information(self, "چاپ", "لطفاً ابتدا فاکتور را به صورت PDF ذخیره کرده و سپس فایل PDF را چاپ کنید.")
        # TODO: پیاده‌سازی چاپ مستقیم‌تر اگر لازم است و WeasyPrint از آن پشتیبانی می‌کند.


    def _handle_copy_text(self):
        # ... (متد شما برای کپی متن ساده فاکتور) ...
        text_to_copy = self._get_invoice_text_representation()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text_to_copy)
            QMessageBox.information(self, "کپی شد", "اطلاعات متنی فاکتور در کلیپ‌بورد کپی شد.")


    def _get_invoice_text_representation(self) -> str:
        # این متد باید یک نمایش متنی ساده از فاکتور برای کپی کردن برگرداند
        # (این کد از پاسخ‌های قبلی شماست و باید با ساختار فعلی فاکتور تطبیق داده شود)
        if not self.invoice: return "اطلاعات فاکتور موجود نیست."
        
        inv = self.invoice
        invoice_type_str = "فروش" if inv.invoice_type == InvoiceType.SALE else "خرید"
        header_title = f"فاکتور {invoice_type_str} شماره: {inv.invoice_number}"
        date_str = inv.invoice_date.strftime(DATE_FORMAT) if inv.invoice_date else "-"
        
        person_name = "نامشخص"
        if inv.person_id and self.person_manager:
            person = self.person_manager.get_person_by_id(inv.person_id)
            if person: person_name = person.name
        
        lines = [header_title, f"تاریخ: {date_str}", f"طرف حساب: {person_name}"]
        lines.append("-" * 30)
        lines.append("اقلام:")
        if inv.items:
            for i, item in enumerate(inv.items):
                item_name = getattr(item, 'product_name', item.description or f"کالا {item.product_id}")
                qty = item.quantity or 0
                price = item.unit_price or 0
                total = qty * price
                lines.append(f"  {i+1}. {item_name}: {qty} * {float(price):,.0f} = {float(total):,.0f}")
        else:
            lines.append("  (بدون قلم)")
        lines.append("-" * 30)
        lines.append(f"جمع کل: {float(inv.total_amount or 0):,.0f}")
        # (سایر اطلاعات جمع‌بندی)
        if inv.description:
            lines.append(f"توضیحات: {inv.description}")
        return "\n".join(lines)



    
    
    def _get_invoice_html_representation(self, show_payments_table: bool = False) -> str:
        inv = self.invoice 
        if not inv:
            logger.error("Invoice object is None in _get_invoice_html_representation.")
            return "<p>اطلاعات فاکتور برای نمایش موجود نیست.</p>"
        if not hasattr(self, 'company_details') or not self.company_details:
            logger.error("company_details not found or is None in InvoiceViewDialog.")
            return "<p>اطلاعات شرکت برای نمایش فاکتور موجود نیست.</p>"

        display_company_name_in_header = getattr(self, 'setting_display_company_name_invoice_header', True) 
        company_name_display = self.company_details.get('name', 'نام شرکت شما')
        logo_path = self.company_details.get('logo_path', None)
        
        invoice_type_enum_value = getattr(inv, 'invoice_type', InvoiceType.SALE.value)
        try:
            invoice_type_enum = InvoiceType(invoice_type_enum_value) if not isinstance(invoice_type_enum_value, InvoiceType) else invoice_type_enum_value
        except ValueError:
            invoice_type_enum = InvoiceType.SALE
        main_invoice_title_text = "فاکتور فروش کالا" if invoice_type_enum == InvoiceType.SALE else "فاکتور خرید کالا / خدمات"
        
        person_name_str = f"مشتری {inv.person_id}" if inv.person_id else "نامشخص"
        person_section_title_text = "مشخصات خریدار"
        person_phone_str = "ثبت نشده"

        if inv.person_id and hasattr(self, 'person_manager') and self.person_manager:
            try:
                person = self.person_manager.get_person_by_id(int(inv.person_id))
                if person: 
                    person_name_str = person.name or f"مشتری {inv.person_id}"
                    person_phone_str = getattr(person, 'contact_info', 'ثبت نشده') 
            except (ValueError,TypeError) as e:
                logger.error(f"Error fetching person details for person_id {inv.person_id} in invoice PDF: {e}")
        
        current_time_str = datetime.now().strftime('%H:%M:%S')
        current_date_formatted = date_converter.to_shamsi_str(inv.invoice_date)
        due_date_formatted = date_converter.to_shamsi_str(inv.due_date) if inv.due_date else "-"
        css_styles = self._get_invoice_css_styles()

        html_parts = [] # استفاده از لیست برای ساخت HTML
        html_parts.append(f"<html><head><meta charset='UTF-8'><style>{css_styles}</style></head><body><div class='page-container'>")

        # --- هدر ---
        html_parts.append(f"""
           <div class="invoice-header-wrapper">
                <div class="invoice-main-title-text">{main_invoice_title_text}</div>
                <div class="invoice-details-line">
                    <span>شماره: <b>{inv.invoice_number or '---'}</b></span>
                    <span>تاریخ: {current_date_formatted}</span>
                    <span>ساعت: {due_date_formatted}</span>
                </div>
            </div>
        """)

        # --- مشخصات خریدار ---
        html_parts.append(f"""
            <div class="buyer-details-box">
                <div class="buyer-details-title">{person_section_title_text}</div>
                 <table class="buyer-details-table">
                    <tr>
                        <td class="label">نام:</td><td class="value">{person_name_str}</td>
                    </tr>
                    <tr>
                        <td class="label">شماره تماس:</td><td class="value">{person_phone_str}</td>
                    </tr>
                </table>
            </div>
        """)

        # --- جدول اقلام ---
        html_parts.append(f"""
            <div class="items-table-title">مشخصات کالا یا خدمات مورد معامله</div>
            <table class="items-table" dir="rtl">
                <thead><tr>
                <th style="width: 5%;">#</th> 
                <th style="width: 25%;">شرح کالا</th>
                <th style="width: 8%;">مقدار</th>
                <th style="width: 8%;">واحد</th>
                <th style="width: 17%;">قیمت واحد (تومان)</th>
                <th style="width: 17%;">مبلغ کل (تومان)</th>
                <th style="width: 20%;">توضیحات قلم</th> 
            </tr></thead>
            <tbody>
        """)
        subtotal_invoice_items = Decimal("0.0")
        if inv.items:
            for i, item_entity in enumerate(inv.items):
                # ... (منطق واکشی و نمایش اقلام مانند قبل) ...
                product_name_display = getattr(item_entity, 'product_name', 'کالای نامشخص')
                product_unit_measure = getattr(item_entity, 'unit_of_measure', '')
                if not getattr(item_entity, 'product_name', None) and hasattr(self,'product_manager') and self.product_manager and item_entity.product_id:
                    try:
                        product = self.product_manager.get_product_by_id(int(item_entity.product_id))
                        if product: 
                            product_name_display = product.name
                            if not product_unit_measure: product_unit_measure = product.unit_of_measure or ''
                    except (ValueError, TypeError): pass
                quantity_val = Decimal(str(item_entity.quantity if item_entity.quantity is not None else '0'))
                unit_price_val = Decimal(str(item_entity.unit_price if item_entity.unit_price is not None else '0'))
                item_total_dec = quantity_val * unit_price_val
                subtotal_invoice_items += item_total_dec
                item_description = getattr(item_entity, 'description', '') or "" # <<< تعریف متغیر

                html_parts.append(f"""
                        <tr>
                            <td class="center">{i+1}</td>
                            <td>{product_name_display}</td>
                            <td class="center">{float(quantity_val):n}</td> 
                            <td class="center">{product_unit_measure}</td>
                            <td class="amount">{float(unit_price_val):,.0f}</td>
                            <td class="amount">{float(item_total_dec):,.0f}</td>
                            <td style="font-size: 7pt; text-align: right;">{item_description}</td> 
                        </tr>""")
        
        min_rows_for_items = getattr(self, 'min_item_rows_on_invoice_print', 7) 
        current_item_count = len(inv.items) if inv.items else 0
        if current_item_count < min_rows_for_items:
            for _ in range(min_rows_for_items - current_item_count):
                html_parts.append("<tr><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td></tr>")
        
        html_parts.append("</tbody></table>")

        # --- بخش جمع‌بندی و امضا ---
        current_total_amount = inv.total_amount if isinstance(inv.total_amount, Decimal) else Decimal(str(inv.total_amount or '0.0'))
        current_paid_amount = inv.paid_amount if isinstance(inv.paid_amount, Decimal) else Decimal(str(inv.paid_amount or '0.0'))
        final_payable_amount = current_total_amount
        current_remaining_amount = getattr(inv, 'remaining_amount', final_payable_amount - current_paid_amount)
        if not isinstance(current_remaining_amount, Decimal): current_remaining_amount = Decimal(str(current_remaining_amount or '0.0'))

        html_parts.append(f"""
            <div class="summary-and-signature-box">
                <div class="totals-section-container">
                    <div class="invoice-description-final"> 
                        {'<p><b>توضیحات:</b></p><p style="word-wrap: break-word; min-height:50px; border:1px solid #f0f0f0; padding:2px;">' + str(inv.description or "") + '</p>' if inv.description else "<p style='min-height:50px;'>&nbsp;</p>"}
                    </div>
                    <div class="totals-table-container"> 
                        <table class="totals-table-final">
                            <tr><td class="label">جمع کل اقلام (تومان):</td><td class="value">{float(subtotal_invoice_items):,.0f}</td></tr>
                            <tr><td class="label" style="background-color: #D0D0D0; font-weight:bold;">قابل پرداخت (تومان):</td><td class="value" style="background-color: #D0D0D0; font-weight:bold;">{float(final_payable_amount):,.0f}</td></tr>
                            <tr><td class="label">مبلغ پرداخت شده (تومان):</td><td class="value">{float(current_paid_amount):,.0f}</td></tr>
                            <tr><td class="label" style="background-color: #E0E0E0; font-weight:bold;">مبلغ باقیمانده (تومان):</td><td class="value" style="background-color: #E0E0E0; font-weight:bold;">{float(current_remaining_amount):,.0f}</td></tr>
                        </table>
                    </div>
                </div>
                <div class="clear"></div>
                <div class="footer-signature-area">مهر و امضاء فروشنده</div>
            </div>
        """)
        
        # --- شروع بخش اصلاح شده نمایش پرداخت‌های مرتبط ---
        if show_payments_table and hasattr(self, 'payment_manager') and self.payment_manager and inv and inv.id is not None:
            related_payments: List[PaymentHeaderEntity] = self.payment_manager.get_payments_for_invoice(inv.id)
            if related_payments:
                html_parts.append("""
                    <div class="related-payments-section">
                        <div class="related-payments-title">پرداخت‌های مرتبط</div>
                        <table class="related-payments-table" dir="rtl">
                            <thead><tr>
                                <th style="width: 20%;">تاریخ پرداخت</th>
                                <th style="width: 15%;">ش. سند</th>
                                <th style="width: 15%;">روش پرداخت</th>
                                <th style="width: 30%;">شرح/بانک/چک</th>
                                <th style="width: 20%;">مبلغ (تومان)</th>
                            </tr></thead>
                            <tbody>
                """)
                for payment_header in related_payments:
                    if not hasattr(payment_header, 'line_items') or not payment_header.line_items: continue

                    for line_item in payment_header.line_items:
                        payment_date_str = payment_header.payment_date.strftime(DATE_FORMAT) if payment_header.payment_date else '-'
                        payment_id_str = str(payment_header.id) if payment_header.id is not None else '-'
                        
                        method_value = "---"
                        method_details = ""
                        description_str = str(line_item.description or "")

                        if hasattr(line_item, 'payment_method'):
                            method_value = line_item.payment_method.value
                            # فقط جزئیات خاص روش پرداخت را در method_details قرار بده
                            if line_item.payment_method == PaymentMethod.CHECK and hasattr(line_item, 'check_details_display'):
                                method_details = f"چک: {getattr(line_item, 'check_details_display', '')}"
                            elif line_item.payment_method == PaymentMethod.BANK_TRANSFER and hasattr(line_item, 'account_name_display'):
                                method_details = f"واریز به: {getattr(line_item, 'account_name_display', '')}"
                        
                        line_amount_str = f"{float(line_item.amount or 0):,.0f}"

                        html_parts.append(f"""
                                    <tr>
                                        <td class="center">{payment_date_str}</td>
                                        <td class="center">{payment_id_str}</td>
                                        <td class="center">{method_value}</td>
                                        <td style="text-align:right;">{description_str} {method_details}</td> 
                                        <td class="amount">{line_amount_str}</td>
                                    </tr>
                        """)
                html_parts.append("</tbody></table></div>")
            else:
                 html_parts.append('<p style="font-size:8pt; text-align:center; margin-top:4mm;">پرداختی برای این فاکتور ثبت نشده است.</p>')
        # --- پایان بخش اصلاح شده نمایش پرداخت‌های مرتبط ---
        html_parts.append(f"""
        </body>
        </html>
        """)
        return "".join(html_parts)
    def _get_invoice_css_styles(self) -> str:
        # Fetch display settings if they are attributes of the class instance
        display_company_name_in_header = getattr(self, 'setting_display_company_name_invoice_header', True)
        
        return f"""
            body {{ 
                font-family: 'Tahoma', 'B Nazanin', Arial, sans-serif; 
                direction: rtl; 
                font-size: 9pt; 
                line-height: 1.35; /* Adjusted for potentially more content */
                margin: 0;
                background-color: #fff; /* Ensure white background */
            }}
            .page-container {{
                padding: 7mm; /* Minimal padding for more content space */
                width: 100%; 
                box-sizing: border-box;
            }}
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-bottom: 2mm; 
                box-sizing: border-box;
            }}
            th, td {{ 
                border: 1px solid #333; 
                padding: 2px 3px; 
                text-align: right; 
                vertical-align: middle;
                box-sizing: border-box;
            }}
            th {{ 
                background-color: #E0E0E0; 
                font-weight: bold; 
                text-align: center; 
                font-size: 8pt; /* Smaller font for headers to save space */
            }}

            /* Header Section */
             /* ===== شروع اصلاحات CSS برای هدر جدید ===== */
            .invoice-header-wrapper {{ /* کانتینر اصلی برای کل هدر */
                width: 100%;
                margin-bottom: 5mm; /* فاصله از بخش بعدی */
                padding-bottom: 2mm; /* فاصله داخلی پایین */
                border-bottom: 1.5px solid black; /* خط جداکننده زیر کل هدر */
            }}
            .company-name-title {{
                text-align: center;
                font-size: 11pt;
                font-weight: bold;
                margin-bottom: 1mm; /* فاصله نام شرکت از عنوان اصلی */
                display: {'block' if display_company_name_in_header else 'none'};
            }}
            .invoice-main-title-text {{
                font-size: 16pt; /* فونت بزرگ و بولد برای عنوان اصلی */
                font-weight: bold;
                text-align: center;
                margin-bottom: 3mm; /* فاصله عنوان از اطلاعات شماره/تاریخ */
            }}
            .invoice-details-line {{ /* برای شماره، تاریخ، ساعت در یک خط */
                text-align: center; /* چینش کل خط به راست */
                font-size: 8.5pt;
                line-height: 1.5;
            }}
            .invoice-details-line span {{ 
                margin-left: 15px; /* فاصله بین هر بخش از اطلاعات */
                white-space: nowrap; /* جلوگیری از شکستن هر بخش */
            }}
            .invoice-details-line span:last-child {{ 
                margin-left: 0; /* حذف مارجین از آخرین آیتم */
            }}
            .invoice-details-line b {{ 
                font-weight: normal; /* اگر نمی‌خواهید مقادیر بولد باشند */
            }}
            /* ===== پایان اصلاحات CSS هدر ===== */


            .buyer-details-box {{ border: 1px solid black; margin-bottom: 3mm; }}
            .buyer-details-title {{ font-weight: bold; text-align: center; background-color: #E0E0E0; padding: 2px; border-bottom: 1px solid black; font-size: 9.5pt; }}
            .buyer-details-table {{ width: 100%; margin:0; border:none;}}
            .buyer-details-table td {{ border: none; padding: 1mm 1mm; font-size: 9pt; text-align: right !important; }}
            .buyer-details-table td.label {{ font-weight:bold; width: auto; white-space: nowrap; padding-left: 30px;}} /* برچسب سمت راست */
            .buyer-details-table td.value {{ width: 75%; text-align: right !important; }} /* مقدار سمت راست */
            
            
              
            /* Items Table */
            .items-table-title {{ 
                text-align: center; 
                font-weight: bold; 
                font-size: 10pt; 
                padding: 2.5px; 
                background-color: #E0E0E0; 
                border: 1px solid black; 
                border-bottom: none;
            }}
            .items-table {{ 
                direction: rtl; 
                border: 1px solid black !important; 
                width:100% !important;
                table-layout: fixed; 
            }} 
            .items-table th, .items-table td {{
                padding: 2.5px;
                word-wrap: break-word;
            }}
            .items-table th {{ 
                font-size: 9pt;
                background-color: #D8D8D8;
            }}
            .items-table td {{ 
                font-size: 9pt;
            }}
            .items-table td.center {{ text-align: center !important; }}
            .items-table td.amount {{ text-align: right !important; font-family: 'Tahoma', Arial, sans-serif; }}

             .summary-and-signature-box {{ 
                    border: 1px solid black; 
                    margin-top: 1.5mm; /* کمی فاصله از جدول اقلام */
                    overflow: auto; 
                    padding: 1.5mm; /* کاهش پدینگ داخلی کادر اصلی */
                }}
                .totals-section-container {{ 
                    width: 100%; 
                    margin-bottom: 1mm; 
                }}
                .invoice-description-final {{ /* توضیحات در سمت راست */
                    width: 50%; 
                    float: right; 
                    font-size: 8pt; 
                    padding-left: 1%; 
                    min-height: 45px; /* کاهش ارتفاع حداقلی */
                    box-sizing: border-box;
                }}
                .totals-table-container {{ /* جدول جمع مبالغ در سمت چپ */
                    width: 48%; /* افزایش جزئی عرض */
                    float: left; 
                    box-sizing: border-box;
                }}
                .totals-table-final {{ 
                    width: 100%; 
                    font-size: 8.5pt; 
                    border:none !important; 
                    margin:0; 
                }}
                .totals-table-final td {{ 
                    padding: 2.5px 3.5px; /* پدینگ مناسب */
                    border: 1px solid #999;
                    line-height: 1.3; /* کمی کاهش فاصله خطوط داخلی سلول */
                }}
                .totals-table-final td.label {{ 
                    font-weight: bold; 
                    background-color: #E8E8E8; 
                    text-align: right;
                    white-space: nowrap; 
                }}
                .totals-table-final td.value {{ 
                    text-align: right; /* اعداد راست‌چین */
                    font-weight: bold; 
                    font-family: 'Tahoma', Arial, sans-serif;
                    background-color: #FDFDFD; 
                }}
                /* رنگ پس‌زمینه برای ردیف‌های قابل پرداخت و باقیمانده */
                .totals-table-final tr:nth-child(2) td.label, /* قابل پرداخت - لیبل */
                .totals-table-final tr:nth-child(4) td.label  {{ /* باقیمانده - لیبل */
                     background-color: #DCDCDC !important; 
                }}
                .totals-table-final tr:nth-child(2) td.value, /* قابل پرداخت - مقدار */
                .totals-table-final tr:nth-child(4) td.value  {{ /* باقیمانده - مقدار */
                     background-color: #DCDCDC !important; 
                }}

                .clear {{ clear: both; height:0; line-height:0; font-size:0;}}
                
                .footer-signature-area {{ 
                    text-align: left; 
                    padding: 2mm 2mm 1mm 2mm; 
                    font-size:9pt; 
                    border-top: 1px dashed #777; 
                    margin-top:1.5mm; 
                }}
                .footer-app-note {{ 
                    text-align:center; 
                    font-size:7pt; 
                    margin-top:2mm; 
                    color:#555; 
                }}
                /* ===== پایان اصلاحات CSS بخش جمع‌بندی و امضا ===== */

            /* Styles for Related Payments Table (if shown) */
            .related-payments-section {{ margin-top: 4mm; page-break-inside: avoid; }}
            .related-payments-title {{ text-align: center; font-weight: bold; font-size: 10pt; padding: 2px; background-color: #E0E0E0; border: 1px solid black; border-bottom: 1px solid black; margin-bottom:0;}}
            .related-payments-table {{ direction: rtl; border: 1px solid black !important; border-top:none !important; width:100% !important; table-layout: fixed; font-size: 8pt; margin-top:0;}}
            .related-payments-table th {{ background-color: #D8D8D8; padding: 1.5px; font-size:12pt; }}
            .related-payments-table td {{ padding: 1.5px 2.5px; border-color: #666;}}
        </style>
        """