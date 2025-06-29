# src/presentation/boms_ui.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QPushButton, QHBoxLayout,
    QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout, QGroupBox,
    QDialogButtonBox, QAbstractItemView, QDoubleSpinBox, QTextEdit,
    QHeaderView, QDateEdit, QSpinBox, QCheckBox, QAbstractSpinBox # اضافه کردن QCheckBox
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate, QTimer
from PyQt5.QtGui import QColor

from typing import List, Optional, Any, Dict
from datetime import date
from decimal import Decimal,InvalidOperation
from src.business_logic.entities.bom_item_entity import BomItemEntity # اطمینان از مسیر صحیح
from src.business_logic.entities.bom_entity import BOMEntity # مسیر صحیح را بررسی کنید
from src.business_logic.bom_manager import BomManager
from src.business_logic.product_manager import ProductManager # برای نمایش نام محصول
from src.constants import DATE_FORMAT,ProductType

import logging
logger = logging.getLogger(__name__)

class BomTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[BOMEntity]] = None, parent=None):
        super().__init__(parent)
        self._boms: List[BOMEntity] = data if data is not None else []
        # product_manager برای این مدل لازم نیست چون نام محصول از قبل در BOMEntity توسط BomManager پر شده است
        
        self._headers = [
            "شناسه BOM", "نام/کد BOM", "محصول نهایی", 
            "مقدار تولیدی", "فعال", "تاریخ ایجاد", "توضیحات"
        ]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._boms)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._boms)):
            return QVariant()
        
        bom = self._boms[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(bom.id)
            elif col == 1: return bom.name
            elif col == 2: return bom.product_name or (f"ID محصول: {bom.product_id}" if bom.product_id else "نامشخص")
            elif col == 3: return str(bom.quantity_produced)
            elif col == 4: return "بله" if bom.is_active else "خیر"
            elif col == 5: 
                return bom.creation_date.strftime(DATE_FORMAT) if bom.creation_date else "-"
            elif col == 6: return bom.description or ""
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 3, 4, 5]: # شناسه، مقدار، فعال، تاریخ
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[BOMEntity]):
        logger.debug(f"BomTableModel: Updating with {len(new_data)} BOMs.")
        self.beginResetModel()
        self._boms = new_data if new_data is not None else []
        self.endResetModel()
        logger.debug("BomTableModel: Update complete.")

    def get_bom_at_row(self, row: int) -> Optional[BOMEntity]:
        if 0 <= row < len(self._boms):
            return self._boms[row]
        return None
    # src/presentation/boms_ui.py
# ... (import‌ها و BomTableModel از بالا) ...
class BomItemTableModel(QAbstractTableModel):
    def __init__(self, 
                 data: Optional[List[BomItemEntity]] = None, 
                 product_manager: Optional[ProductManager] = None, # برای نمایش نام و کد کامپوننت
                 parent=None):
        super().__init__(parent)
        self._bom_items: List[BomItemEntity] = data if data is not None else []
        self.product_manager = product_manager

        self._headers = [
            "ردیف", "کد جزء", "نام جزء/ماده اولیه", 
            "مقدار لازم", "واحد", "ملاحظات"
        ]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._bom_items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._bom_items)):
            return QVariant()

        item = self._bom_items[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(index.row() + 1) # ردیف از ۱ شروع شود
            elif col == 1: # کد جزء
                return item.component_product_code or (str(item.component_product_id) if item.component_product_id else "-")
            elif col == 2: # نام جزء
                return item.component_product_name or (f"ID جزء: {item.component_product_id}" if item.component_product_id else "نامشخص")
            elif col == 3: # مقدار لازم
                return str(item.quantity_required)
            elif col == 4: # واحد
                return item.component_unit_of_measure or "-"
            elif col == 5: # ملاحظات
                return item.notes or ""

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 3]: # ردیف، مقدار
                return Qt.AlignmentFlag.AlignCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[BomItemEntity]):
        logger.debug(f"BomItemTableModel: Updating with {len(new_data)} BOM items.")
        self.beginResetModel()
        self._bom_items = new_data if new_data is not None else []
        self.endResetModel()

    def get_item_at_row(self, row: int) -> Optional[BomItemEntity]:
        if 0 <= row < len(self._bom_items):
            return self._bom_items[row]
        return None

    def add_item_data(self, item_data: BomItemEntity): # برای افزودن یک آیتم جدید
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._bom_items.append(item_data)
        self.endInsertRows()

    def update_item_data(self, row: int, item_data: BomItemEntity): # برای ویرایش یک آیتم
        if 0 <= row < self.rowCount():
            self._bom_items[row] = item_data
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() -1))
            return True
        return False

    def remove_item_data(self, row: int): # برای حذف یک آیتم
         if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._bom_items[row]
            self.endRemoveRows()
            return True
         return False

    def get_all_items(self) -> List[BomItemEntity]: # برای گرفتن تمام آیتم‌ها جهت ذخیره‌سازی
        return self._bom_items
class BomDialog(QDialog):
    def __init__(self, 
                 bom_manager: BomManager, 
                 product_manager: ProductManager, 
                 bom_to_edit: Optional[BOMEntity] = None, # برای حالت ویرایش
                 parent=None):
        super().__init__(parent)
        self.bom_manager = bom_manager
        self.product_manager = product_manager
        self.bom_to_edit = bom_to_edit
        self.is_edit_mode = self.bom_to_edit is not None

        self.current_bom_items: List[BomItemEntity] = [] # برای نگهداری اقلام BOM در UI

        title = "ایجاد صورت مواد اولیه (BOM) جدید"
        if self.is_edit_mode and self.bom_to_edit:
            title = f"ویرایش BOM: {self.bom_to_edit.name}"
        self.setWindowTitle(title)
        self.setMinimumSize(800, 600)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui_elements()
        self._setup_ui_layout()

        self._populate_finished_product_combo()

        if self.is_edit_mode and self.bom_to_edit:
            self._load_bom_for_editing()
        else: # حالت افزودن
            self.creation_date_edit.setDate(QDate.currentDate())
            self.active_checkbox.setChecked(True)
            self.quantity_produced_spinbox.setValue(1.0)

        # اتصال سیگنال‌ها
        self.add_item_button.clicked.connect(self._add_bom_item)
        self.edit_item_button.clicked.connect(self._edit_bom_item)
        self.remove_item_button.clicked.connect(self._remove_bom_item)
        self.button_box.accepted.connect(self._accept_dialog)
        self.button_box.rejected.connect(self.reject)

        self.setLayout(self.main_layout)

    def _setup_ui_elements(self):
        # --- سربرگ BOM ---
        self.header_group = QGroupBox("اطلاعات سربرگ BOM")
        self.header_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        header_form_layout = QFormLayout(self.header_group)

        self.name_edit = QLineEdit()
        self.finished_product_combo = QComboBox() # برای انتخاب محصول نهایی
        self.quantity_produced_spinbox = QDoubleSpinBox()
        self.quantity_produced_spinbox.setDecimals(2)
        self.quantity_produced_spinbox.setMinimum(0.01)
        
        self.quantity_produced_spinbox.setMaximum(999999.99)
        self.quantity_produced_spinbox.setValue(1.0) # <<< مقدار پیش‌فرض اولیه

        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(60)
        self.active_checkbox = QCheckBox("BOM فعال است")
        self.creation_date_edit = QDateEdit() # فقط برای نمایش در حالت ویرایش
        self.creation_date_edit.setReadOnly(True)
        self.creation_date_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.last_modified_date_edit = QDateEdit() # فقط برای نمایش در حالت ویرایش
        self.last_modified_date_edit.setReadOnly(True)
        self.last_modified_date_edit.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        header_form_layout.addRow("نام/کد BOM:*", self.name_edit)
        header_form_layout.addRow("محصول نهایی:*", self.finished_product_combo)
        header_form_layout.addRow("مقدار تولیدی با این BOM:*", self.quantity_produced_spinbox)
        header_form_layout.addRow("توضیحات:", self.description_edit)
        header_form_layout.addRow(self.active_checkbox)
        header_form_layout.addRow("تاریخ ایجاد:", self.creation_date_edit)
        header_form_layout.addRow("آخرین ویرایش:", self.last_modified_date_edit)

        # --- اقلام BOM ---
        self.items_group = QGroupBox("اقلام و مواد اولیه مورد نیاز")
        self.items_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        items_layout = QVBoxLayout(self.items_group)

        self.items_table_view = QTableView()
        self.bom_items_table_model = BomItemTableModel(product_manager=self.product_manager) # مدل جدید
        self.items_table_view.setModel(self.bom_items_table_model)
        self.items_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.items_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # (تنظیمات هدر جدول اقلام در اینجا یا _setup_ui_layout)

        item_buttons_layout = QHBoxLayout()
        self.add_item_button = QPushButton(" (+) افزودن ماده اولیه")
        self.edit_item_button = QPushButton("ویرایش ماده اولیه")
        self.remove_item_button = QPushButton("حذف ماده اولیه")
        item_buttons_layout.addWidget(self.add_item_button)
        item_buttons_layout.addWidget(self.edit_item_button)
        item_buttons_layout.addWidget(self.remove_item_button)
        item_buttons_layout.addStretch()

        items_layout.addLayout(item_buttons_layout)
        items_layout.addWidget(self.items_table_view)

        # --- دکمه‌های تایید و انصراف ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel) # type: ignore
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("ذخیره BOM") # type: ignore
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("انصراف") # type: ignore

    def _setup_ui_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.header_group)
        self.main_layout.addWidget(self.items_group)
        self.main_layout.addWidget(self.button_box)

    def _populate_finished_product_combo(self):
        self.finished_product_combo.clear()
        self.finished_product_combo.addItem("-- انتخاب محصول نهایی --", None)
        if self.product_manager:
            # فقط محصولاتی که از نوع "محصول نهایی" یا "کالای نیمه ساخته" هستند را نمایش بده
            # و خدماتی نیستند
            products = self.product_manager.get_all_products(active_only=True)
            for p in products:
                if p.id and p.product_type in [ProductType.FINISHED_GOOD, ProductType.SEMI_FINISHED_GOOD]:
                    self.finished_product_combo.addItem(f"{p.name} (کد: {p.sku or p.id})", p.id)
        if self.finished_product_combo.count() <= 1:
             self.finished_product_combo.addItem("محصول قابل ساختی یافت نشد", None)
             self.finished_product_combo.setEnabled(False)


    def _load_bom_for_editing(self):
        if not self.bom_to_edit or not self.bom_to_edit.id : return # باید bom_to_edit.id هم وجود داشته باشد

        logger.debug(f"Loading BOM ID {self.bom_to_edit.id} for editing.")
        # واکشی BOM کامل با جزئیات اقلام و نام محصولات
        full_bom = self.bom_manager.get_bom_with_details(self.bom_to_edit.id)
        if not full_bom:
            QMessageBox.critical(self, "خطا", f"اطلاعات کامل BOM با شناسه {self.bom_to_edit.id} یافت نشد.")
            self.reject() # یا self.close()
            return

        self.bom_to_edit = full_bom # جایگزینی با آبجکت کامل

        self.name_edit.setText(self.bom_to_edit.name)
        if self.bom_to_edit.product_id:
            idx = self.finished_product_combo.findData(self.bom_to_edit.product_id)
            if idx != -1: self.finished_product_combo.setCurrentIndex(idx)
        self.quantity_produced_spinbox.setValue(float(self.bom_to_edit.quantity_produced or 1.0))
        self.description_edit.setText(self.bom_to_edit.description or "")
        self.active_checkbox.setChecked(self.bom_to_edit.is_active)
        if self.bom_to_edit.creation_date and isinstance(self.bom_to_edit.creation_date, date):
            self.creation_date_edit.setDate(QDate(self.bom_to_edit.creation_date))
        if self.bom_to_edit.last_modified_date and isinstance(self.bom_to_edit.last_modified_date, date):
            self.last_modified_date_edit.setDate(QDate(self.bom_to_edit.last_modified_date))

        self.current_bom_items = list(self.bom_to_edit.items) if self.bom_to_edit.items else []
        self.bom_items_table_model.update_data(self.current_bom_items)


    def _add_bom_item(self):
        logger.debug("BomDialog: Add BOM item clicked.")
        # اطمینان از اینکه ProductManager به BomItemDialog پاس داده می‌شود
        if not self.product_manager:
            QMessageBox.critical(self, "خطای داخلی", "ProductManager مقداردهی نشده است.")
            return

        dialog = BomItemDialog(product_manager=self.product_manager, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            item_data_dict = dialog.get_item_data() 
            if item_data_dict and item_data_dict.get("component_product_id") is not None:
                # برای نمایش در جدول، نیاز به واکشی نام و کد محصول داریم
                component_product = self.product_manager.get_product_by_id(item_data_dict["component_product_id"])
                
                new_item_entity = BomItemEntity(
                    # id و bom_id در زمان ذخیره‌سازی نهایی توسط BomManager تنظیم می‌شوند
                    component_product_id=item_data_dict["component_product_id"],
                    quantity_required=item_data_dict["quantity_required"], # از قبل Decimal است
                    notes=item_data_dict.get("notes"),
                    # پر کردن فیلدهای نمایشی
                    component_product_name=component_product.name if component_product else "جزء نامشخص",
                    component_product_code=component_product.sku if component_product and component_product.sku else (str(component_product.id) if component_product and component_product.id else "-"),
                    component_unit_of_measure=component_product.unit_of_measure if component_product else "-"
                )
                self.current_bom_items.append(new_item_entity)
                self.bom_items_table_model.update_data(self.current_bom_items)
                logger.info(f"New BOM item added to dialog list: {new_item_entity.component_product_name}")
            elif item_data_dict is None:
                 logger.debug("BomItemDialog was accepted but returned no data (likely validation error inside).")
            else:
                 logger.warning("BomItemDialog returned data without component_product_id.")


    def _edit_bom_item(self):
        logger.debug("BomDialog: Edit BOM item clicked.")
        selection_model = self.items_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک قلم ماده اولیه را برای ویرایش انتخاب کنید.")
            return
        
        selected_row_indexes = selection_model.selectedRows()
        if not selected_row_indexes:
            QMessageBox.information(self, "انتخاب نشده", "موردی برای ویرایش انتخاب نشده است.")
            return
            
        row_to_edit = selected_row_indexes[0].row()
        
        if not (0 <= row_to_edit < len(self.current_bom_items)):
            QMessageBox.warning(self, "خطا", "ردیف انتخاب شده نامعتبر است.")
            return
            
        item_entity_to_edit = self.current_bom_items[row_to_edit]

        dialog = BomItemDialog(product_manager=self.product_manager, 
                               item_to_edit=item_entity_to_edit, # پاس دادن BomItemEntity موجود
                               parent=self)
        
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            updated_item_data_dict = dialog.get_item_data()
            if updated_item_data_dict and updated_item_data_dict.get("component_product_id") is not None:
                component_product = self.product_manager.get_product_by_id(updated_item_data_dict["component_product_id"])
                
                # به‌روزرسانی آبجکت BomItemEntity موجود در لیست
                self.current_bom_items[row_to_edit].component_product_id = updated_item_data_dict["component_product_id"]
                self.current_bom_items[row_to_edit].quantity_required = updated_item_data_dict["quantity_required"]
                self.current_bom_items[row_to_edit].notes = updated_item_data_dict.get("notes")
                # به‌روزرسانی فیلدهای نمایشی
                self.current_bom_items[row_to_edit].component_product_name = component_product.name if component_product else "جزء نامشخص"
                self.current_bom_items[row_to_edit].component_product_code = component_product.sku if component_product and component_product.sku else (str(component_product.id) if component_product and component_product.id else "-")
                self.current_bom_items[row_to_edit].component_unit_of_measure = component_product.unit_of_measure if component_product else "-"

                self.bom_items_table_model.update_data(self.current_bom_items) # یا فقط ردیف تغییر کرده را به‌روز کنید
                # self.bom_items_table_model.dataChanged.emit(self.bom_items_table_model.index(row_to_edit, 0), self.bom_items_table_model.index(row_to_edit, self.bom_items_table_model.columnCount() -1))
                logger.info(f"BOM item at row {row_to_edit} updated: {self.current_bom_items[row_to_edit].component_product_name}")


    def _remove_bom_item(self):
        logger.debug("BomDialog: Remove BOM item clicked.")
        selection_model = self.items_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک قلم ماده اولیه را برای حذف انتخاب کنید.")
            return

        selected_row_indexes = selection_model.selectedRows()
        if not selected_row_indexes:
             QMessageBox.information(self, "انتخاب نشده", "موردی برای حذف انتخاب نشده است.")
             return

        row_to_remove = selected_row_indexes[0].row()

        if not (0 <= row_to_remove < len(self.current_bom_items)):
            QMessageBox.warning(self, "خطا", "ردیف انتخاب شده برای حذف نامعتبر است.")
            return
            
        item_to_remove = self.current_bom_items[row_to_remove]
        reply = QMessageBox.question(self, "تایید حذف قلم",
                                     f"آیا از حذف قلم '{item_to_remove.component_product_name or 'نامشخص'}' مطمئن هستید؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.current_bom_items[row_to_remove]
            self.bom_items_table_model.update_data(self.current_bom_items)
            logger.info(f"BOM item '{item_to_remove.component_product_name}' removed from dialog list.")

    def _accept_dialog(self):
        # ... (کد این متد از پاسخ قبلی با اصلاحات لازم برای items_data_for_manager) ...
        # اطمینان حاصل کنید که items_data_for_manager لیستی از دیکشنری‌هاست
        # که هر دیکشنری شامل component_product_id, quantity_required, notes است.
        logger.debug("BomDialog: Accept (Save) clicked.")
        name = self.name_edit.text().strip()
        product_id_data = self.finished_product_combo.currentData()
        quantity_produced_value_float = self.quantity_produced_spinbox.value() # مقدار را به صورت float می‌گیرد
        
        description = self.description_edit.toPlainText().strip()
        is_active = self.active_checkbox.isChecked()

        if not name:
            QMessageBox.warning(self, "خطای ورودی", "نام/کد BOM الزامی است.")
            return
        if product_id_data is None:
            QMessageBox.warning(self, "خطای ورودی", "محصول نهایی باید انتخاب شود.")
            return
        
        
        if quantity_produced_value_float <= 0: # بررسی اولیه برای مثبت بودن
            QMessageBox.warning(self, "خطای ورودی", "مقدار تولیدی با این BOM باید یک عدد مثبت باشد.")
            self.quantity_produced_spinbox.setFocus()
            return
            
        try:
            # تبدیل مقدار float خوانده شده به Decimal با دقت
            quantity_produced = Decimal(str(quantity_produced_value_float)) 
        except InvalidOperation: # این خطا با .value() کمتر محتمل است مگر اینکه مقدار خیلی خاصی باشد
            QMessageBox.warning(self, "خطای ورودی", 
                                "مقدار وارد شده برای 'مقدار تولیدی با این BOM' نامعتبر است.\n"
                                "لطفاً یک عدد صحیح یا اعشاری معتبر وارد کنید.")
            self.quantity_produced_spinbox.setFocus()
            return
            
        product_id = int(product_id_data)
        
        # تبدیل self.current_bom_items (که لیست BomItemEntity است) به items_data_for_manager (لیست Dict)
        items_data_for_manager: List[Dict[str, Any]] = []
        for bom_item_entity_instance in self.current_bom_items:
            if bom_item_entity_instance.component_product_id is not None and bom_item_entity_instance.quantity_required is not None:
                items_data_for_manager.append({
                    "component_product_id": bom_item_entity_instance.component_product_id,
                    "quantity_required": str(bom_item_entity_instance.quantity_required), # ارسال به صورت رشته
                    "notes": bom_item_entity_instance.notes
                })
            else:
                logger.warning(f"Skipping BOM item with missing data: {bom_item_entity_instance}")


        try:
            if self.is_edit_mode and self.bom_to_edit and self.bom_to_edit.id:
                logger.info(f"Attempting to update BOM ID: {self.bom_to_edit.id}")
                updated_bom = self.bom_manager.update_bom(
                    bom_id=self.bom_to_edit.id,
                    name=name,
                    product_id=product_id,
                    items_data=items_data_for_manager, 
                    quantity_produced=quantity_produced,
                    description=description,
                    is_active=is_active
                )
                if updated_bom:
                    QMessageBox.information(self, "موفقیت", f"BOM '{updated_bom.name}' با موفقیت ویرایش شد.")
                    super().accept() # بستن دیالوگ با موفقیت
                else:
                    QMessageBox.warning(self, "خطا در ویرایش", "ویرایش BOM ناموفق بود (جزئیات در لاگ).")
            else: 
                logger.info(f"Attempting to create new BOM: {name}")
                created_bom = self.bom_manager.create_bom(
                    name=name,
                    product_id=product_id,
                    items_data=items_data_for_manager, 
                    quantity_produced=quantity_produced,
                    description=description,
                    is_active=is_active
                )
                if created_bom:
                    QMessageBox.information(self, "موفقیت", f"BOM '{created_bom.name}' با موفقیت ایجاد شد.")
                    super().accept() # بستن دیالوگ با موفقیت
                else:
                    QMessageBox.warning(self, "خطا در ایجاد", "ایجاد BOM ناموفق بود (جزئیات در لاگ).")
        except ValueError as ve:
            QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
        except Exception as e:
            logger.error(f"Error saving BOM in BomDialog: {e}", exc_info=True)
            QMessageBox.critical(self, "خطای سیستمی", f"خطا در ذخیره‌سازی BOM: {e}")

# متدهای _add_bom_item, _edit_bom_item, _remove_bom_item نیاز به پیاده‌سازی کامل با استفاده از BomItemDialog دارند.
# BomItemDialog باید بتواند یک دیکشنری از داده‌های قلم را برگرداند.

class BomItemDialog(QDialog):
    def __init__(self, 
                 product_manager: ProductManager, 
                 # item_data_to_edit می‌تواند BomItemEntity باشد یا یک Dict از آن
                 item_to_edit: Optional[BomItemEntity] = None, 
                 parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.item_to_edit = item_to_edit 
        self.is_edit_mode = self.item_to_edit is not None
       
        title = "افزودن قلم ماده اولیه به BOM"
        if self.is_edit_mode and self.item_to_edit and self.item_to_edit.component_product_name:
            title = f"ویرایش قلم: {self.item_to_edit.component_product_name}"
        elif self.is_edit_mode:
            title = "ویرایش قلم ماده اولیه"

        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui_elements()
        self._setup_ui_layout()

        self._populate_component_product_combo()

        if self.is_edit_mode and self.item_to_edit:
            self._load_item_for_editing()
        else:
            self.quantity_required_spinbox.setValue(1.0) # مقدار پیش‌فرض
            if self.component_product_combo.count() > 1: # اگر محصولی برای انتخاب وجود دارد
                 self.component_product_combo.setCurrentIndex(1) # انتخاب اولین محصول واقعی

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.setLayout(self.form_layout)

    def _setup_ui_elements(self):
        self.component_product_combo = QComboBox()
        self.quantity_required_spinbox = QDoubleSpinBox()
        self.quantity_required_spinbox.setDecimals(3) 
        self.quantity_required_spinbox.setMinimum(0.001)
        self.quantity_required_spinbox.setMaximum(999999.999)
        self.unit_of_measure_label = QLabel("-") 
        self.notes_edit = QLineEdit()
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("تایید قلم")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")

    def _setup_ui_layout(self):
        self.form_layout = QFormLayout(self)
        self.form_layout.addRow("جزء / ماده اولیه:*", self.component_product_combo)
        
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(self.quantity_required_spinbox)
        qty_layout.addWidget(QLabel("واحد:"))
        qty_layout.addWidget(self.unit_of_measure_label)
        qty_layout.addStretch()
        self.form_layout.addRow("مقدار مورد نیاز:*", qty_layout)
        
        self.form_layout.addRow("ملاحظات:", self.notes_edit)
        self.form_layout.addRow(self.button_box)
        
        self.component_product_combo.currentIndexChanged.connect(self._update_unit_of_measure_label)

    def _populate_component_product_combo(self):
        self.component_product_combo.clear()
        self.component_product_combo.addItem("-- انتخاب جزء --", None)
        if self.product_manager:
            # فقط مواد اولیه یا کالاهای نیمه‌ساخته را به عنوان کامپوننت نمایش بده
            products = self.product_manager.get_all_products(active_only=True)
            for p in products:
                if p.id and p.product_type in [ProductType.RAW_MATERIAL, ProductType.SEMI_FINISHED_GOOD]:
                    self.component_product_combo.addItem(f"{p.name} (کد: {p.sku or p.id})", p.id)
            
            if self.component_product_combo.count() <= 1: # فقط placeholder
                self.component_product_combo.addItem("ماده اولیه‌ای یافت نشد", None)
                self.component_product_combo.setEnabled(False)
        else:
            self.component_product_combo.setEnabled(False)
            logger.warning("ProductManager not available in BomItemDialog.")
        self._update_unit_of_measure_label()


    def _update_unit_of_measure_label(self):
        product_id_data = self.component_product_combo.currentData()
        if product_id_data and self.product_manager:
            product = self.product_manager.get_product_by_id(int(product_id_data))
            if product and product.unit_of_measure:
                self.unit_of_measure_label.setText(product.unit_of_measure)
                return
        self.unit_of_measure_label.setText("-")

    def _load_item_for_editing(self):
        if not self.item_to_edit: return # item_to_edit باید BomItemEntity باشد

        comp_id = self.item_to_edit.component_product_id
        if comp_id is not None:
            idx = self.component_product_combo.findData(int(comp_id))
            if idx != -1: 
                self.component_product_combo.setCurrentIndex(idx)
        
        # _update_unit_of_measure_label پس از setCurentIndex به طور خودکار فراخوانی می‌شود
        
        qty_req = self.item_to_edit.quantity_required
        self.quantity_required_spinbox.setValue(float(qty_req) if qty_req is not None else 1.0)
        self.notes_edit.setText(self.item_to_edit.notes or "")

    def get_item_data(self) -> Optional[Dict[str, Any]]:
        component_id_data = self.component_product_combo.currentData()
        if component_id_data is None:
            QMessageBox.warning(self, "خطا", "لطفاً یک جزء یا ماده اولیه انتخاب کنید.")
            return None

        quantity_value = self.quantity_required_spinbox.value() # مقدار را به صورت float می‌گیرد

        if quantity_value <= 0: # بررسی ساده برای مثبت بودن
            QMessageBox.warning(self, "خطا", "مقدار مورد نیاز باید یک عدد مثبت معتبر باشد.")
            self.quantity_required_spinbox.setFocus() # فوکوس روی فیلد مشکل‌دار
            return None

        try:
            # تبدیل مقدار float خوانده شده به Decimal با دقت
            quantity_decimal = Decimal(str(quantity_value)) 
        except InvalidOperation:
            QMessageBox.warning(self, "خطا", "مقدار وارد شده برای تعداد نامعتبر است.")
            self.quantity_required_spinbox.setFocus()
            return None

        return {
            "component_product_id": int(component_id_data),
            "quantity_required": quantity_decimal, 
            "notes": self.notes_edit.text().strip(),
            "id": self.item_to_edit.id if self.is_edit_mode and self.item_to_edit and hasattr(self.item_to_edit, 'id') else None 
        }

# --- پایان کلاس BomItemDialog ---
# --- پایان کلاس BomItemDialog ---
class BomsUI(QWidget):
    def __init__(self, 
                 bom_manager: BomManager, 
                 product_manager: ProductManager, # برای دیالوگ افزودن/ویرایش BOM لازم است
                 parent=None):
        super().__init__(parent)
        self.bom_manager = bom_manager
        self.product_manager = product_manager # برای پاس دادن به BomDialog
        
        self.table_model = BomTableModel()
        self._init_ui()
        self.load_boms_data()
        logger.info("BomsUI initialized.")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWindowTitle("مدیریت صورت مواد اولیه (BOM)")

        # TODO: افزودن فیلترها (مثلاً بر اساس محصول نهایی)

        self.bom_table_view = QTableView(self)
        self.bom_table_view.setModel(self.table_model)
        self.bom_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bom_table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.bom_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.bom_table_view.setSortingEnabled(True)
        self.bom_table_view.setAlternatingRowColors(True)

        header = self.bom_table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            # تنظیم عرض برای ستون‌های خاص در صورت نیاز
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # نام BOM
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # محصول نهایی
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch) # توضیحات
        
        # مرتب‌سازی پیش‌فرض (مثلاً بر اساس نام BOM)
        # self.bom_table_view.sortByColumn(1, Qt.SortOrder.AscendingOrder) 
        main_layout.addWidget(self.bom_table_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton(" (+) افزودن BOM جدید")
        self.edit_button = QPushButton("ویرایش BOM انتخاب شده")
        self.delete_button = QPushButton("حذف BOM انتخاب شده")
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_bom_dialog)
        self.edit_button.clicked.connect(self._open_edit_bom_dialog)
        self.delete_button.clicked.connect(self._delete_selected_bom)
        self.refresh_button.clicked.connect(self.load_boms_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def load_boms_data(self):
        logger.debug("BomsUI: Loading BOMs data...")
        try:
            # از متد get_all_boms_with_product_names برای نمایش نام محصول استفاده می‌کنیم
            boms_with_details = self.bom_manager.get_all_boms_with_product_names()
            self.table_model.update_data(boms_with_details)
            logger.info(f"BomsUI: {len(boms_with_details)} BOMs loaded.")
        except Exception as e:
            logger.error(f"Error loading BOMs: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری لیست BOM ها: {e}")

    def _get_selected_bom(self) -> Optional[BOMEntity]:
        selection_model = self.bom_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            return None
        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            return None
        return self.table_model.get_bom_at_row(selected_rows[0].row())

    def _open_add_bom_dialog(self):
        logger.debug("BomsUI: Add BOM button clicked.")
        # در اینجا باید BomDialog را فراخوانی کنیم
        dialog = BomDialog(bom_manager=self.bom_manager, product_manager=self.product_manager, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            self.load_boms_data()
       


    def _open_edit_bom_dialog(self):
        logger.debug("BomsUI: Edit BOM button clicked.")
        selected_bom_header = self._get_selected_bom()
        if not selected_bom_header or selected_bom_header.id is None:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک BOM را برای ویرایش انتخاب کنید.")
            return
        
        # برای ویرایش، باید BOM کامل با اقلام آن را واکشی کنیم
        # full_bom_to_edit = self.bom_manager.get_bom_with_details(selected_bom_header.id)
        # if not full_bom_to_edit:
        #     QMessageBox.critical(self, "خطا", f"اطلاعات کامل BOM با شناسه {selected_bom_header.id} یافت نشد.")
        #     return
            
        # dialog = BomDialog(bom_manager=self.bom_manager, 
        #                    product_manager=self.product_manager, 
        #                    bom_to_edit=full_bom_to_edit, 
        #                    parent=self)
        # if dialog.exec_() == QDialog.DialogCode.Accepted:
        #     self.load_boms_data()
        QMessageBox.information(self, "اطلاع", "عملکرد ویرایش BOM هنوز پیاده‌سازی نشده است.")


    def _delete_selected_bom(self):
        logger.debug("BomsUI: Delete BOM button clicked.")
        selected_bom = self._get_selected_bom()
        if not selected_bom or selected_bom.id is None:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک BOM را برای حذف انتخاب کنید.")
            return

        reply = QMessageBox.question(self, "تایید حذف BOM",
                                     f"آیا از حذف BOM '{selected_bom.name}' (برای محصول: {selected_bom.product_name or 'نامشخص'}) مطمئن هستید؟\n"
                                     "این عملیات تمام اقلام مرتبط با این BOM را نیز حذف خواهد کرد.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No) # type: ignore
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.bom_manager.delete_bom(selected_bom.id)
                if success:
                    QMessageBox.information(self, "موفقیت", f"BOM با شناسه {selected_bom.id} با موفقیت حذف شد.")
                    self.load_boms_data()
                else:
                    QMessageBox.warning(self, "ناموفق", f"حذف BOM با شناسه {selected_bom.id} انجام نشد (جزئیات در لاگ).")
            except Exception as e:
                logger.error(f"Error deleting BOM ID {selected_bom.id}: {e}", exc_info=True)
                QMessageBox.critical(self, "خطای سیستمی", f"خطا در حذف BOM: {e}")

# --- پایان کد کلاس BomsUI ---
