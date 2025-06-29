# src/presentation/manual_production_dialogs.py (یا فایل دیگر)

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox, 
    QLineEdit, QLabel, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt
from typing import Optional, List, Dict, Any
from decimal import Decimal, InvalidOperation
from src.utils import date_converter
from .custom_widgets import ShamsiDateEdit # <<< ویجت جدید تاریخ شمسی
from src.business_logic.entities.product_entity import ProductEntity # برای type hint
from src.business_logic.product_manager import ProductManager
from src.constants import ProductType # برای فیلتر کردن محصولات
# from src.business_logic.entities.consumed_material_entity import ConsumedMaterialEntity # اگر برای item_to_edit استفاده می‌شود

import logging
logger = logging.getLogger(__name__)

class ConsumedMaterialDialog(QDialog):
    def __init__(self, 
                 product_manager: ProductManager,
                 # item_to_edit می‌تواند دیکشنری از داده‌های قلم برای ویرایش باشد
                 # یا یک آبجکت ConsumedMaterialEntity
                 item_to_edit: Optional[Dict[str, Any]] = None, 
                 parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.item_to_edit = item_to_edit # دیکشنری با کلیدهای: component_product_id, quantity_consumed, notes
        self.is_edit_mode = self.item_to_edit is not None
        self.products_cache: List[ProductEntity] = [] # برای نگهداری لیست محصولات واکشی شده

        title = "افزودن ماده اولیه/جزء مصرفی"
        if self.is_edit_mode:
            # اگر نام محصول در item_to_edit موجود باشد، می‌توانیم آن را در عنوان نمایش دهیم
            # این نیاز دارد که ManualProductionDialog هنگام فراخوانی برای ویرایش، نام را هم پاس دهد
            title = f"ویرایش ماده مصرفی" 
            if self.item_to_edit and self.item_to_edit.get('component_product_name'):
                 title = f"ویرایش: {self.item_to_edit.get('component_product_name')}"


        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui_elements()
        self._setup_ui_layout() # این باید پس از _setup_ui_elements فراخوانی شود
        
        self._populate_component_product_combo() # محصولات باید قبل از _load_item_for_editing بارگذاری شوند

        if self.is_edit_mode and self.item_to_edit:
            self._load_item_for_editing()
        else: # حالت افزودن جدید
            self.quantity_consumed_spinbox.setValue(1.0) # مقدار پیش‌فرض ۱.۰
            if self.component_product_combo.count() > 1: # اگر محصولی برای انتخاب وجود دارد
                 self.component_product_combo.setCurrentIndex(1) # انتخاب اولین محصول واقعی در لیست
                 # _update_unit_of_measure_label به طور خودکار با تغییر index فراخوانی می‌شود

        # اتصال سیگنال‌ها
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        self.setLayout(self.form_layout) # اطمینان از اینکه layout اصلی تنظیم شده

    def _setup_ui_elements(self):
        self.component_product_combo = QComboBox(self)
        self.quantity_consumed_spinbox = QDoubleSpinBox(self)
        self.unit_of_measure_label = QLabel("-") 
        self.notes_edit = QLineEdit(self)
        
        self.quantity_consumed_spinbox.setDecimals(1)  # <<< تعداد ارقام اعشار ۱
        self.quantity_consumed_spinbox.setMinimum(0.1) # <<< حداقل مقدار مثبت
        self.quantity_consumed_spinbox.setMaximum(99999.9) # یک مقدار حداکثر مناسب
        self.quantity_consumed_spinbox.setGroupSeparatorShown(False) # برای اعداد اعشاری معمولاً لازم نیست

        # تنظیم Locale برای پذیرش نقطه از کیبورد (اگر لازم شد، فعلاً این را اضافه نمی‌کنیم)
        # from PyQt5.QtCore import QLocale
        # english_locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        # self.quantity_consumed_spinbox.setLocale(english_locale)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("تایید قلم")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")

    def _setup_ui_layout(self):
        self.form_layout = QFormLayout(self)
        self.form_layout.addRow("ماده اولیه/جزء مصرفی:*", self.component_product_combo)
        
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(self.quantity_consumed_spinbox)
        qty_layout.addWidget(QLabel("واحد:"))
        qty_layout.addWidget(self.unit_of_measure_label)
        qty_layout.addStretch()
        self.form_layout.addRow("مقدار مصرفی:*", qty_layout)
        
        self.form_layout.addRow("ملاحظات (اختیاری):", self.notes_edit)
        self.form_layout.addRow(self.button_box)
        
        # اتصال سیگنال بعد از ایجاد ویجت‌ها
        self.component_product_combo.currentIndexChanged.connect(self._update_unit_of_measure_label)

    def _populate_component_product_combo(self):
        self.component_product_combo.clear()
        self.component_product_combo.addItem("-- انتخاب ماده اولیه --", None) # Placeholder
        if self.product_manager:
            self.products_cache = self.product_manager.get_all_products(active_only=True)
            eligible_components = [
                p for p in self.products_cache 
                if p.id is not None and p.product_type in [ProductType.RAW_MATERIAL, ProductType.SEMI_FINISHED_GOOD]
            ]
            
            if not eligible_components:
                self.component_product_combo.addItem("ماده اولیه‌ای یافت نشد", None)
                self.component_product_combo.setEnabled(False)
                self.quantity_consumed_spinbox.setEnabled(False)
            else:
                self.component_product_combo.setEnabled(True)
                self.quantity_consumed_spinbox.setEnabled(True)
                for product in eligible_components:
                    # نمایش نام و کد کالا برای انتخاب بهتر
                    display_text = f"{product.name} (کد: {product.sku or 'N/A'})"
                    self.component_product_combo.addItem(display_text, int(product.id))
        else:
            logger.error("ConsumedMaterialDialog: ProductManager is not available.")
            self.component_product_combo.addItem("خطا در بارگذاری محصولات", None)
            self.component_product_combo.setEnabled(False)
        
        self._update_unit_of_measure_label() # برای تنظیم اولیه واحد اگر آیتمی انتخاب شده

    def _update_unit_of_measure_label(self):
        product_id_data = self.component_product_combo.currentData()
        if product_id_data is not None and self.product_manager:
            try:
                product = next((p for p in self.products_cache if p.id == int(product_id_data)), None)
                if product and product.unit_of_measure:
                    self.unit_of_measure_label.setText(product.unit_of_measure)
                    return
            except (ValueError, TypeError) as e:
                 logger.error(f"Error finding product or unit for ID {product_id_data}: {e}")
        self.unit_of_measure_label.setText("-")

    def _load_item_for_editing(self):
        if not self.item_to_edit: return

        comp_id = self.item_to_edit.get("component_product_id")
        if comp_id is not None:
            try:
                idx = self.component_product_combo.findData(int(comp_id))
                if idx != -1: 
                    self.component_product_combo.setCurrentIndex(idx) 
                    # _update_unit_of_measure_label به طور خودکار با تغییر index فراخوانی می‌شود
                else:
                    logger.warning(f"ConsumedMaterialDialog: Component product ID {comp_id} not found in combo during edit.")
            except (ValueError, TypeError):
                logger.error(f"ConsumedMaterialDialog: Invalid component_product_id '{comp_id}' for editing.")
        
        try:
            qty_consumed = self.item_to_edit.get("quantity_consumed", 1.0)
            self.quantity_consumed_spinbox.setValue(float(qty_consumed)) # QDoubleSpinBox مقدار float می‌گیرد
        except (TypeError, ValueError):
            logger.warning(f"Invalid quantity_consumed value during edit: {self.item_to_edit.get('quantity_consumed')}. Defaulting to 1.0.")
            self.quantity_consumed_spinbox.setValue(1.0)

        self.notes_edit.setText(self.item_to_edit.get("notes", ""))

    def get_consumed_material_data(self) -> Optional[Dict[str, Any]]:
        """داده‌های وارد شده برای قلم ماده مصرفی را به صورت دیکشنری برمی‌گرداند."""
        component_id_data = self.component_product_combo.currentData()
        if component_id_data is None: # یعنی placeholder "-- انتخاب ماده اولیه --" انتخاب شده
            QMessageBox.warning(self, "خطای ورودی", "لطفاً یک ماده اولیه/جزء مصرفی انتخاب کنید.")
            self.component_product_combo.setFocus()
            return None
        
        try:
            component_product_id = int(component_id_data)
        except (ValueError, TypeError):
            QMessageBox.warning(self, "خطای داخلی", "شناسه ماده اولیه انتخاب شده نامعتبر است.")
            return None

        quantity_value = self.quantity_consumed_spinbox.value() # مقدار را به صورت float می‌گیرد

        if quantity_value < self.quantity_consumed_spinbox.minimum(): # بررسی حداقل مقدار
            QMessageBox.warning(self, "خطای ورودی", f"مقدار مصرفی باید حداقل {self.quantity_consumed_spinbox.minimum()} باشد.")
            self.quantity_consumed_spinbox.setFocus()
            return None
            
        try:
            quantity_decimal = Decimal(str(quantity_value)) # تبدیل به Decimal
        except InvalidOperation:
            QMessageBox.warning(self, "خطای ورودی", "مقدار وارد شده برای 'مقدار مصرفی' نامعتبر است.")
            self.quantity_consumed_spinbox.setFocus()
            return None
            
        # برای نمایش نام در پیام‌ها یا لاگ‌ها (اختیاری)
        selected_product_name = self.component_product_combo.currentText().split(" (کد:")[0]
        
        data_to_return = {
            "component_product_id": component_product_id,
            "quantity_consumed": quantity_decimal, 
            "notes": self.notes_edit.text().strip() or None, # اگر خالی است None برگردان
            "component_product_name": selected_product_name, # برای نمایش در جدول والد (اختیاری)
            "component_unit_of_measure": self.unit_of_measure_label.text() # برای نمایش در جدول والد (اختیاری)
        }
        # اگر در حالت ویرایش هستیم و شناسه قلم اصلی (از دیتابیس) را داریم، آن را هم برمی‌گردانیم
        if self.is_edit_mode and self.item_to_edit and self.item_to_edit.get("id"):
            data_to_return["id"] = self.item_to_edit.get("id")
        
        logger.debug(f"ConsumedMaterialDialog.get_consumed_material_data returning: {data_to_return}")
        return data_to_return
        # src/presentation/manual_production_models.py (یا فایل دیگر)
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant
from typing import List, Optional, Dict, Any
from decimal import Decimal
# از src.business_logic.entities.consumed_material_entity import ConsumedMaterialEntity # اگر از Entity استفاده می‌کنید
# فعلاً با دیکشنری کار می‌کنیم چون get_consumed_material_data از ConsumedMaterialDialog دیکشنری برمی‌گرداند

import logging
logger = logging.getLogger(__name__)

class ConsumedMaterialTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        # داده‌ها لیستی از دیکشنری‌ها هستند، هر دیکشنری یک قلم ماده مصرفی است
        # کلیدهای مورد انتظار: "component_product_id", "component_product_name", 
        #                     "quantity_consumed", "component_unit_of_measure", "notes"
        self._items_data: List[Dict[str, Any]] = data if data is not None else []
        self._headers = ["کد ماده", "نام ماده", "مقدار مصرفی", "واحد", "ملاحظات"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items_data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._items_data)):
            return QVariant()
        
        item_data = self._items_data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(item_data.get("component_product_code", item_data.get("component_product_id", "")))
            elif col == 1: return str(item_data.get("component_product_name", "نامشخص"))
            elif col == 2: 
                qty = item_data.get("quantity_consumed", Decimal("0.0"))
                return f"{float(qty):.1f}" # نمایش با یک رقم اعشار
            elif col == 3: return str(item_data.get("component_unit_of_measure", "-"))
            elif col == 4: return str(item_data.get("notes", ""))
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 2: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        logger.debug(f"ConsumedMaterialTableModel: Updating with {len(new_data)} items.")
        self.beginResetModel()
        self._items_data = new_data if new_data is not None else []
        self.endResetModel()

    def get_item_data_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._items_data):
            return self._items_data[row]
        return None
        
    def add_item_data(self, item_data: Dict[str, Any]):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._items_data.append(item_data)
        self.endInsertRows()
        logger.debug(f"ConsumedMaterialTableModel: Item added: {item_data}")

    def update_item_data(self, row: int, item_data: Dict[str, Any]):
        if 0 <= row < self.rowCount():
            self._items_data[row] = item_data
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() -1))
            logger.debug(f"ConsumedMaterialTableModel: Item updated at row {row}: {item_data}")
            return True
        return False

    def remove_item_data(self, row: int):
         if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            removed_item = self._items_data.pop(row)
            self.endRemoveRows()
            logger.debug(f"ConsumedMaterialTableModel: Item removed: {removed_item}")
            return True
         return False
         
    def get_all_items_data(self) -> List[Dict[str, Any]]:
        # فقط داده‌های لازم برای ارسال به ProductionManager را برمی‌گرداند
        return [
            {
                "component_product_id": item.get("component_product_id"),
                "quantity_consumed": item.get("quantity_consumed"), # باید Decimal باشد
                "notes": item.get("notes")
            } 
            for item in self._items_data 
            if item.get("component_product_id") is not None and item.get("quantity_consumed") is not None
        ]
    # src/presentation/manual_production_dialogs.py (یا فایل دیگر)
# ... (import های ConsumedMaterialDialog و ConsumedMaterialTableModel) ...
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDoubleSpinBox, QTextEdit,
    QDateEdit, QGroupBox, QPushButton, QHBoxLayout, QTableView, 
    QDialogButtonBox, QMessageBox, QAbstractItemView, QHeaderView
)
from PyQt5.QtCore import Qt, QDate
from typing import Optional, List, Dict, Any
from decimal import Decimal

from src.business_logic.entities.manual_production_entity import ManualProductionEntity # اگر برای ویرایش استفاده می‌شود
from src.business_logic.product_manager import ProductManager
from src.constants import ProductType
# from .consumed_material_dialog import ConsumedMaterialDialog # اگر در فایل جداگانه است
# from .manual_production_models import ConsumedMaterialTableModel # اگر در فایل جداگانه است


import logging
logger = logging.getLogger(__name__)

class ManualProductionDialog(QDialog):
    def __init__(self, 
                 product_manager: ProductManager,
                 # production_manager: ProductionManager, # برای ویرایش و گرفتن جزئیات
                 production_to_edit: Optional[ManualProductionEntity] = None, 
                 parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        # self.production_manager = production_manager
        self.production_to_edit = production_to_edit
        self.is_edit_mode = self.production_to_edit is not None
        
        # این لیست دیکشنری‌هایی از داده‌های اقلام مصرفی را نگه می‌دارد
        # هر دیکشنری شامل component_product_id, component_product_name, quantity_consumed, component_unit_of_measure, notes است
        self.current_consumed_items: List[Dict[str, Any]] = [] 

        title = "ثبت تولید دستی جدید"
        if self.is_edit_mode and self.production_to_edit:
            # برای عنوان ویرایش، می‌توانیم نام محصول نهایی را از production_to_edit.finished_product_name بگیریم
            # این فیلد باید توسط ProductionManager.get_manual_production_with_details پر شده باشد.
            edit_title_suffix = f" (محصول: {getattr(self.production_to_edit, 'finished_product_name', 'نامشخص')})" if getattr(self.production_to_edit, 'finished_product_name', None) else ""
            title = f"ویرایش تولید دستی {edit_title_suffix}"

        self.setWindowTitle(title)
        self.setMinimumSize(700, 550)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui_elements()
        self._setup_ui_layout()

        self._populate_finished_product_combo()

        if self.is_edit_mode and self.production_to_edit:
            self._load_production_data_for_editing()
        else: # حالت افزودن
            self.production_date_edit.setDate(QDate.currentDate())
            if self.finished_product_combo.count() > 1 :
                self.finished_product_combo.setCurrentIndex(1) # انتخاب اولین محصول واقعی
            self.quantity_produced_spinbox.setValue(1.0)

        # اتصال سیگنال‌ها
        self.add_consumed_item_button.clicked.connect(self._add_consumed_item)
        self.edit_consumed_item_button.clicked.connect(self._edit_consumed_item)
        self.remove_consumed_item_button.clicked.connect(self._remove_consumed_item)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        self.setLayout(self.main_layout)


    def _setup_ui_elements(self):
        # --- سربرگ تولید دستی ---
        self.header_group = QGroupBox("اطلاعات تولید")
        self.header_group_layout = QFormLayout(self.header_group)
        self.production_date_edit = ShamsiDateEdit(self)

        

        self.finished_product_combo = QComboBox(self)
        
        self.quantity_produced_spinbox = QDoubleSpinBox(self)
        self.quantity_produced_spinbox.setDecimals(2) # تا دو رقم اعشار برای محصول نهایی
        self.quantity_produced_spinbox.setMinimum(0.01)
        self.quantity_produced_spinbox.setMaximum(999999.99)
        
        self.description_edit = QTextEdit(self)
        self.description_edit.setFixedHeight(60)

        self.header_group_layout.addRow("تاریخ تولید:*", self.production_date_edit)
        self.header_group_layout.addRow("محصول نهایی تولید شده:*", self.finished_product_combo)
        self.header_group_layout.addRow("مقدار تولید شده:*", self.quantity_produced_spinbox)
        self.header_group_layout.addRow("توضیحات:", self.description_edit)

        # --- اقلام مواد اولیه مصرفی ---
        self.consumed_items_group = QGroupBox("مواد اولیه/اجزاء مصرفی")
        self.consumed_items_layout = QVBoxLayout(self.consumed_items_group)

        self.consumed_items_table_view = QTableView(self)
        self.consumed_items_table_model = ConsumedMaterialTableModel() # مدل جدید
        self.consumed_items_table_view.setModel(self.consumed_items_table_model)
        self.consumed_items_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.consumed_items_table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.consumed_items_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # تنظیمات هدر جدول
        items_header = self.consumed_items_table_view.horizontalHeader()
        if items_header:
            items_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # نام ماده
            for col in [0, 2, 3, 4]: items_header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        item_buttons_layout = QHBoxLayout()
        self.add_consumed_item_button = QPushButton(" (+) افزودن ماده مصرفی")
        self.edit_consumed_item_button = QPushButton("ویرایش ماده مصرفی")
        self.remove_consumed_item_button = QPushButton("حذف ماده مصرفی")
        item_buttons_layout.addWidget(self.add_consumed_item_button)
        item_buttons_layout.addWidget(self.edit_consumed_item_button)
        item_buttons_layout.addWidget(self.remove_consumed_item_button)
        item_buttons_layout.addStretch()

        self.consumed_items_layout.addLayout(item_buttons_layout)
        self.consumed_items_layout.addWidget(self.consumed_items_table_view)

        # --- دکمه‌های تایید و انصراف ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn: ok_btn.setText("ذخیره تولید")
        cancel_btn = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn: cancel_btn.setText("انصراف")
        
    def _setup_ui_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.header_group)
        self.main_layout.addWidget(self.consumed_items_group)
        self.main_layout.addWidget(self.button_box)

    def _populate_finished_product_combo(self):
        self.finished_product_combo.clear()
        self.finished_product_combo.addItem("-- انتخاب محصول نهایی --", None)
        if self.product_manager:
            products = self.product_manager.get_all_products(active_only=True)
            finished_products = [p for p in products if p.id and p.product_type == ProductType.FINISHED_GOOD]
            
            if not finished_products:
                self.finished_product_combo.addItem("محصول نهایی فعالی یافت نشد", None)
                self.finished_product_combo.setEnabled(False)
            else:
                self.finished_product_combo.setEnabled(True)
                for p in finished_products:
                    self.finished_product_combo.addItem(f"{p.name} (کد: {p.sku or 'N/A'})", int(p.id))
        else:
            logger.error("ManualProductionDialog: ProductManager is not available.")
            self.finished_product_combo.addItem("خطا در بارگذاری محصولات", None)
            self.finished_product_combo.setEnabled(False)

    def _load_production_data_for_editing(self):
        if not self.production_to_edit: return # باید ManualProductionEntity باشد
        self.production_date_edit.setDate(self.production_to_edit.production_date)

        
        if self.production_to_edit.finished_product_id is not None:
            idx = self.finished_product_combo.findData(int(self.production_to_edit.finished_product_id))
            if idx != -1: self.finished_product_combo.setCurrentIndex(idx)
        
        self.quantity_produced_spinbox.setValue(float(self.production_to_edit.quantity_produced or 1.0))
        self.description_edit.setText(self.production_to_edit.description or "")
        
        # بارگذاری اقلام مصرفی
        self.current_consumed_items = []
        if hasattr(self.production_to_edit, 'consumed_items') and self.production_to_edit.consumed_items:
            for item_entity in self.production_to_edit.consumed_items: # item_entity باید ConsumedMaterialEntity باشد
                self.current_consumed_items.append({
                    "id": item_entity.id, # شناسه قلم مصرفی از دیتابیس (برای ویرایش/حذف)
                    "component_product_id": item_entity.component_product_id,
                    "component_product_name": getattr(item_entity, 'component_product_name', 'نامشخص'),
                    "component_product_code": getattr(item_entity, 'component_product_code', '-'),
                    "quantity_consumed": item_entity.quantity_consumed, # باید Decimal باشد
                    "component_unit_of_measure": getattr(item_entity, 'component_unit_of_measure', '-'),
                    "notes": item_entity.notes
                })
        self.consumed_items_table_model.update_data(self.current_consumed_items)


    def _add_consumed_item(self):
        logger.debug("ManualProductionDialog: Add consumed item clicked.")
        dialog = ConsumedMaterialDialog(product_manager=self.product_manager, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            item_data_dict = dialog.get_consumed_material_data()
            if item_data_dict:
                # item_data_dict شامل component_product_name و component_unit_of_measure هم هست
                self.current_consumed_items.append(item_data_dict)
                self.consumed_items_table_model.update_data(self.current_consumed_items)
                logger.info(f"New consumed item added to dialog list: {item_data_dict.get('component_product_name')}")

    def _edit_consumed_item(self):
        logger.debug("ManualProductionDialog: Edit consumed item clicked.")
        selection_model = self.consumed_items_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک ماده مصرفی را برای ویرایش انتخاب کنید.")
            return
        
        selected_row = selection_model.selectedRows()[0].row()
        if not (0 <= selected_row < len(self.current_consumed_items)):
            QMessageBox.warning(self, "خطا", "ردیف انتخاب شده نامعتبر است.")
            return
            
        item_to_edit_dict = dict(self.current_consumed_items[selected_row]) # کپی برای ویرایش

        dialog = ConsumedMaterialDialog(product_manager=self.product_manager, 
                                        item_to_edit=item_to_edit_dict, 
                                        parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            updated_item_data_dict = dialog.get_consumed_material_data()
            if updated_item_data_dict:
                self.current_consumed_items[selected_row] = updated_item_data_dict
                self.consumed_items_table_model.update_data(self.current_consumed_items)
                logger.info(f"Consumed item at row {selected_row} updated: {updated_item_data_dict.get('component_product_name')}")

    def _remove_consumed_item(self):
        logger.debug("ManualProductionDialog: Remove consumed item clicked.")
        selection_model = self.consumed_items_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک ماده مصرفی را برای حذف انتخاب کنید.")
            return
            
        selected_row = selection_model.selectedRows()[0].row()
        if not (0 <= selected_row < len(self.current_consumed_items)):
            QMessageBox.warning(self, "خطا", "ردیف انتخاب شده برای حذف نامعتبر است.")
            return
            
        item_to_remove = self.current_consumed_items[selected_row]
        reply = QMessageBox.question(self, "تایید حذف قلم",
                                     f"آیا از حذف ماده مصرفی '{item_to_remove.get('component_product_name', 'نامشخص')}' مطمئن هستید؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.current_consumed_items[selected_row]
            self.consumed_items_table_model.update_data(self.current_consumed_items)
            logger.info(f"Consumed item '{item_to_remove.get('component_product_name')}' removed from dialog list.")

    def get_manual_production_data(self) -> Optional[Dict[str, Any]]:
        finished_product_id_data = self.finished_product_combo.currentData()
        
        if finished_product_id_data is None:
            QMessageBox.warning(self, "خطای ورودی", "محصول نهایی تولید شده باید انتخاب شود.")
            self.finished_product_combo.setFocus()
            return None
        
        try:
            finished_product_id = int(finished_product_id_data)
        except (ValueError, TypeError):
            QMessageBox.warning(self, "خطای داخلی", "شناسه محصول نهایی نامعتبر است.")
            return None

        quantity_produced_val = self.quantity_produced_spinbox.value()
        if quantity_produced_val < self.quantity_produced_spinbox.minimum():
            QMessageBox.warning(self, "خطای ورودی", f"مقدار تولید شده باید حداقل {self.quantity_produced_spinbox.minimum()} باشد.")
            self.quantity_produced_spinbox.setFocus()
            return None
        try:
            quantity_produced_dec = Decimal(str(quantity_produced_val))
        except InvalidOperation:
            QMessageBox.warning(self, "خطای ورودی", "مقدار تولید شده نامعتبر است.")
            return None
        
        description = self.description_edit.toPlainText().strip() or None

        if not self.current_consumed_items:
            QMessageBox.warning(self, "خطای ورودی", "حداقل یک ماده اولیه مصرفی باید برای تولید ثبت شود.")
            return None
            
        # داده‌های اقلام مصرفی را برای ارسال به ProductionManager آماده می‌کنیم
        # get_all_items_data از ConsumedMaterialTableModel فقط کلیدهای لازم را برمی‌گرداند
        consumed_items_for_manager = self.consumed_items_table_model.get_all_items_data() 
        production_date_val = self.production_date_edit.date()

        return {
            "production_date": production_date_val,
            "finished_product_id": finished_product_id,
            "quantity_produced": quantity_produced_dec, # ارسال به صورت Decimal
            "description": description,
            "consumed_items_data": consumed_items_for_manager 
            # "fiscal_year_id": ... # اگر سال مالی را هم می‌گیرید
        }
    
    # src/presentation/manual_production_models.py (یا فایل دیگر)
# ... (import های قبلی) ...
from src.business_logic.entities.manual_production_entity import ManualProductionEntity
from src.constants import DATE_FORMAT # اطمینان از import

class ManualProductionTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[ManualProductionEntity]] = None, parent=None):
        super().__init__(parent)
        self._productions: List[ManualProductionEntity] = data if data is not None else []
        # ستون‌ها: شناسه، تاریخ تولید، نام محصول نهایی، مقدار تولید شده، توضیحات
        self._headers = ["شناسه تولید", "تاریخ تولید", "محصول نهایی", "مقدار تولید شده", "توضیحات"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._productions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._productions)):
            return QVariant()
        
        production_header = self._productions[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(production_header.id)
            elif col == 1: 
                return date_converter.to_shamsi_str(production_header.production_date)

            elif col == 2: 
                # finished_product_name باید توسط ProductionManager پر شده باشد
                return getattr(production_header, 'finished_product_name', f"ID: {production_header.finished_product_id}")
            elif col == 3: 
                qty = production_header.quantity_produced
                return f"{float(qty):.2f}" # نمایش با دو رقم اعشار (یا هر تعداد لازم)
            elif col == 4: return str(production_header.description or "")
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 3: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[ManualProductionEntity]):
        logger.debug(f"ManualProductionTableModel: Updating with {len(new_data)} production headers.")
        self.beginResetModel()
        self._productions = new_data if new_data is not None else []
        self.endResetModel()

    def get_production_header_at_row(self, row: int) -> Optional[ManualProductionEntity]:
        if 0 <= row < len(self._productions):
            return self._productions[row]
        return None