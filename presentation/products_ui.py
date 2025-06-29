# src/presentation/products_ui.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableView, QPushButton,
                             QHBoxLayout, QMessageBox, QDialog, QLineEdit, QComboBox,
                             QFormLayout, QDialogButtonBox, QAbstractItemView,
                             QDoubleSpinBox, QTextEdit, QHeaderView, QCheckBox) # QCheckBox اینجا بود
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex
from PyQt5.QtGui import QColor # <<< QColor وارد شد

from typing import List, Optional, Any, Dict

from src.business_logic.entities.product_entity import ProductEntity
from src.constants import ProductType
from src.business_logic.product_manager import ProductManager
import logging
from decimal import Decimal
logger = logging.getLogger(__name__)

# --- Custom Table Model for Products ---
class ProductTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[ProductEntity]] = None, parent=None):
        super().__init__(parent)
        self._data: List[ProductEntity] = data if data is not None else []
        self._headers = ["شناسه", "نام کالا/خدمت", "SKU", "نوع", "قیمت واحد", "موجودی", "واحد", "فعال", "توضیحات"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return QVariant()

        row = index.row()
        col = index.column()
        
        if not (0 <= row < len(self._data)):
            return QVariant()
        product = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(product.id)
            elif col == 1: return product.name
            elif col == 2: return product.sku if product.sku is not None else ""
            elif col == 3: return product.product_type.value 
            elif col == 4: return f"{product.unit_price:,.2f}"
            elif col == 5: return f"{product.stock_quantity:,.2f}" if product.product_type != ProductType.SERVICE else "N/A"
            elif col == 6: return product.unit_of_measure if product.unit_of_measure is not None else ""
            elif col == 7: 
                return "فعال" if product.is_active else "غیرفعال"
                logger.debug(f"Product ID {product.id}, is_active: {product.is_active}, Displaying: {status_text} for col 7")
            elif col == 8: 
                return product.description if product.description is not None else ""
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 7]: 
                 return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            if col in [4, 5]: 
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ForegroundRole: 
            if not product.is_active:
                return QColor(Qt.GlobalColor.gray) # QColor اکنون تعریف شده است

        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[ProductEntity]):
        logger.debug(f"Updating product table model with {len(new_data)} rows.")
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
        logger.debug("Product table model reset complete.")

    def get_product_at_row(self, row: int) -> Optional[ProductEntity]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

# --- Add/Edit Product Dialog ---
class ProductDialog(QDialog):
    def __init__(self, product_types: List[ProductType], product: Optional[ProductEntity] = None, parent=None):
        super().__init__(parent)
        self.product = product
        self.product_types_map = {pt.value: pt for pt in product_types}

        self.setWindowTitle("افزودن کالا/خدمت جدید" if not product else f"ویرایش: {product.name}")
        self.setMinimumWidth(400)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QFormLayout(self)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.name_edit = QLineEdit(self)
        self.sku_edit = QLineEdit(self)
        self.type_combo = QComboBox(self)
        self.unit_price_spinbox = QDoubleSpinBox(self)
        self.initial_stock_spinbox = QDoubleSpinBox(self)
        self.unit_of_measure_edit = QLineEdit(self)
        self.description_edit = QTextEdit(self)
        self.description_edit.setFixedHeight(80)
        self.is_active_checkbox = QCheckBox("فعال", self) # QCheckBox اکنون تعریف شده است

        self.type_combo.addItems([pt.value for pt in product_types])
        self.type_combo.currentIndexChanged.connect(self._on_product_type_changed)

        self.unit_price_spinbox.setDecimals(2); self.unit_price_spinbox.setMinimum(0.00)
        self.unit_price_spinbox.setMaximum(999999999.99); self.unit_price_spinbox.setGroupSeparatorShown(True)

        self.initial_stock_spinbox.setDecimals(2); self.initial_stock_spinbox.setMinimum(0.00)
        self.initial_stock_spinbox.setMaximum(9999999.99); self.initial_stock_spinbox.setGroupSeparatorShown(True)

        if self.product: 
            self.name_edit.setText(self.product.name)
            self.sku_edit.setText(self.product.sku if self.product.sku else "")
            self.type_combo.setCurrentText(self.product.product_type.value)
            self.unit_price_spinbox.setValue(self.product.unit_price)
            self.unit_of_measure_edit.setText(self.product.unit_of_measure if self.product.unit_of_measure else "")
            self.description_edit.setText(self.product.description if self.product.description else "")
            self.is_active_checkbox.setChecked(self.product.is_active)
            
            self.initial_stock_spinbox.setValue(self.product.stock_quantity)
            self.initial_stock_spinbox.setEnabled(False)
            self.initial_stock_spinbox.setToolTip("موجودی فعلی. برای تغییر از طریق عملیات انبار اقدام کنید.")
        else: 
            self.initial_stock_spinbox.setEnabled(True)
            self.is_active_checkbox.setChecked(True)

        layout.addRow("نام کالا/خدمت:", self.name_edit)
        layout.addRow("SKU (کد انبار):", self.sku_edit)
        layout.addRow("نوع:", self.type_combo)
        layout.addRow("قیمت واحد:", self.unit_price_spinbox)
        layout.addRow("واحد اندازه‌گیری:", self.unit_of_measure_edit)
        if not self.product:
            layout.addRow("موجودی اولیه:", self.initial_stock_spinbox)
        else:
            layout.addRow("موجودی فعلی:", self.initial_stock_spinbox)
        layout.addRow("توضیحات:", self.description_edit)
        layout.addRow("", self.is_active_checkbox) 
        
        # خط ۱۴۴: خطای Pylance برای buttons در اینجا ممکن است همچنان نمایش داده شود اما باید کار کند
        buttons_flags = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons_flags, Qt.Orientation.Horizontal, self) # type: ignore
        
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("تایید")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        self._on_product_type_changed()

    def _on_product_type_changed(self): # حدود ردیف ۱۷۳ شما اینجا بود
        selected_type_value = self.type_combo.currentText()
        selected_type_enum = self.product_types_map.get(selected_type_value)
        
        is_service = (selected_type_enum == ProductType.SERVICE)
        
        self.sku_edit.setEnabled(not is_service)
        self.unit_of_measure_edit.setEnabled(not is_service)
        
        if is_service:
            self.sku_edit.setText("")
            self.unit_of_measure_edit.setText("")
        
        if not self.product: # Only for new products being added
            self.initial_stock_spinbox.setEnabled(not is_service)
            if is_service:
                self.initial_stock_spinbox.setValue(0)
        # For existing products, initial_stock_spinbox is already disabled and shows current stock.

    def get_product_data(self) -> Optional[Dict[str, Any]]:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "ورودی نامعتبر", "نام کالا/خدمت نمی‌تواند خالی باشد.")
            return None
        
        selected_type_value = self.type_combo.currentText()
        product_type_enum = self.product_types_map.get(selected_type_value)
        if not product_type_enum:
            QMessageBox.critical(self, "خطا", "نوع کالا/خدمت انتخاب شده نامعتبر است.")
            return None

        uom_value = self.unit_of_measure_edit.text().strip() if self.unit_of_measure_edit.isEnabled() else None
        # logger.debug(f"Unit of Measure from Dialog: '{uom_value}'") # لاگ برای واحد اندازه‌گیری

        sku_text = self.sku_edit.text().strip() # مقدار SKU را از فیلد ورودی بخوانید

        data = {
            "name": self.name_edit.text().strip(),
            # اگر sku_text دارای مقدار (غیر خالی) است و فیلد فعال است، آن را برگردان، در غیر این صورت None
            "sku": sku_text if sku_text and self.sku_edit.isEnabled() else None, # <<< این خط بسیار مهم است
            "product_type": product_type_enum,
            "unit_price": self.unit_price_spinbox.value(),
            "unit_of_measure": uom_value,
            "description": self.description_edit.toPlainText().strip(),
            "stock_quantity": Decimal(str(self.initial_stock_spinbox.value())) if self.initial_stock_spinbox.isEnabled() else Decimal("0.0"),             "is_active": self.is_active_checkbox.isChecked()
        }
        # اگر در حالت ویرایش هستیم و داده‌های اولیه موجودند، employee_id را هم برمی‌گردانیم
        # این بخش مربوط به EmployeeDialog بود و در ProductDialog نیست، مگر اینکه منطق مشابهی برای product_id داشته باشید
        # if self.product and self.product.id: # اگر در حالت ویرایش محصول هستیم
        #    data["product_id"] = self.product.id
            
        return data


# --- Main Products UI Widget ---
class ProductsUI(QWidget):
    def __init__(self, product_manager: ProductManager, parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.table_model = ProductTableModel()
        self.show_active_only = True 
        self._init_ui() # <<< این خط باید اینجا باشد
        # self.load_products_data() # load_products_data در انتهای _init_ui یا پس از آن فراخوانی می‌شود

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        self.active_filter_checkbox = QCheckBox("فقط نمایش فعال‌ها", self) # QCheckBox اکنون تعریف شده است
        self.active_filter_checkbox.setChecked(self.show_active_only)
        self.active_filter_checkbox.stateChanged.connect(self._on_filter_changed)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.active_filter_checkbox)
        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        # ... (بقیه تنظیمات table_view و دکمه‌ها مانند قبل) ...
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSortingEnabled(True)

        header = self.table_view.horizontalHeader()
        if header:
            header.setStretchLastSection(False) 
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents) 
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch) 
        
        self.table_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        main_layout.addWidget(self.table_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("افزودن کالا/خدمت")
        self.edit_button = QPushButton("ویرایش کالا/خدمت")
        self.toggle_activity_button = QPushButton("تغییر وضعیت (فعال/غیرفعال)") 
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_product_dialog)
        self.edit_button.clicked.connect(self._open_edit_product_dialog)
        self.toggle_activity_button.clicked.connect(self._toggle_selected_product_activity)
        self.refresh_button.clicked.connect(self.load_products_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.toggle_activity_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("ProductsUI initialized.")
        self.load_products_data() # بارگذاری اولیه داده‌ها پس از ساخت UI


    def _on_filter_changed(self, state): # state اینجا int است
        self.show_active_only = self.active_filter_checkbox.isChecked()
        # برای اطمینان بیشتر: self.show_active_only = self.active_filter_checkbox.isChecked()
        self.load_products_data()

    # ... (بقیه متدهای ProductsUI مانند load_products_data، _open_add_product_dialog و غیره) ...
    # اطمینان حاصل کنید که خط ۳۵۰ شما (مربوط به QMessageBox.question) به صورت زیر است یا مشابه آن
    # که دکمه‌ها را در یک متغیر جداگانه تعریف می‌کند:
    # ...
    # در متد _toggle_selected_product_activity:
    # ...
    #        buttons_msg = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    #        reply = QMessageBox.question(self, f"تایید تغییر وضعیت", 
    #                                     f"...",
    #                                     buttons_msg,  # type: ignore
    #                                     QMessageBox.StandardButton.No)
    # ...

    # متدهای قبلی بدون تغییر زیاد (فقط اطمینان از type ignore برای QMessageBox اگر لازم است)
    def load_products_data(self):
        logger.debug(f"Loading products data... (Active only: {self.show_active_only})")
        try:
            products = self.product_manager.get_all_products(active_only=self.show_active_only)
            self.table_model.update_data(products)
            logger.info(f"{len(products)} products loaded into table.")
        except Exception as e:
            logger.error(f"Error loading products: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا در بارگذاری", f"خطا در بارگذاری لیست کالاها/خدمات: {e}")

    def _open_add_product_dialog(self):
        logger.debug("Opening Add Product dialog.")
        product_types_list = list(ProductType)
        
        dialog = ProductDialog(product_types=product_types_list, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            product_data = dialog.get_product_data() # <<< استفاده از نام متد صحیح
            if product_data:
                try:
                    created_product = self.product_manager.create_product(
                        name=product_data["name"],
                        product_type=product_data["product_type"], # باید ProductType enum باشد
                        sku=product_data.get("sku"),
                        unit_price=product_data["unit_price"], # از get_product_data به صورت Decimal می‌آید
                        stock_quantity=product_data.get("stock_quantity"), # از get_product_data به صورت Decimal می‌آید
                        unit_of_measure=product_data.get("unit_of_measure"),
                        description=product_data.get("description"),
                        is_active=product_data.get("is_active", True) 
                        # inventory_account_id=product_data.get("inventory_account_id") # اگر دارید
                    )
                    if created_product:
                        QMessageBox.information(self, "موفقیت", f"کالا/خدمت '{created_product.name}' با موفقیت اضافه شد.")
                        self.load_products_data()
                    else:
                        QMessageBox.warning(self, "خطا", "اضافه کردن کالا/خدمت ناموفق بود.")
                except ValueError as ve: QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except KeyError as ke: logger.error(f"KeyError: {ke}. Data: {product_data}"); QMessageBox.critical(self, "خطای داده", f"کلید {ke} یافت نشد.")
                except Exception as e: logger.error(f"Error adding product: {e}", exc_info=True); QMessageBox.critical(self, "خطا", f"خطا در افزودن: {e}")


    def _open_edit_product_dialog(self):
        selection_model = self.table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک کالا/خدمت را برای ویرایش انتخاب کنید.")
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows: return

        selected_row_index = selected_rows[0].row()
        product_to_edit = self.table_model.get_product_at_row(selected_row_index)

        if not product_to_edit or product_to_edit.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات کالا/خدمت برای ویرایش.")
            return

        logger.debug(f"Opening Edit Product dialog for Product ID: {product_to_edit.id}.")
        product_types_list = list(ProductType)
        
        dialog = ProductDialog(product_types_list, product=product_to_edit, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_product_data() # <<< استفاده از نام متد صحیح
            if data:
                try:
                # --- Correct way to call update_product ---
                    updated_product = self.product_manager.update_product(
                    product_id=product_to_edit.id, # type: ignore 
                    update_data=data  # Pass the dictionary directly
                )
                    if updated_product:
                            QMessageBox.information(self, "موفقیت", f"کالا/خدمت '{updated_product.name}' با موفقیت ویرایش شد.")
                            self.load_products_data()
                    else:
                            QMessageBox.warning(self, "هشدار", f"تغییری در کالا/خدمت '{data['name']}' اعمال نشد یا مورد یافت نشد.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error editing product: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ویرایش کالا/خدمت: {e}")

    def _toggle_selected_product_activity(self):
        selection_model = self.table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک کالا/خدمت را انتخاب کنید.")
            return
            
        selected_rows = selection_model.selectedRows()
        if not selected_rows: return

        selected_row_index = selected_rows[0].row()
        product = self.table_model.get_product_at_row(selected_row_index)

        if not product or product.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات کالا/خدمت.")
            return

        new_active_state = not product.is_active
        new_status_text = "فعال" if new_active_state else "غیرفعال"
        current_status_text = "فعال" if product.is_active else "غیرفعال"

        
        buttons_msg = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        reply = QMessageBox.question(self, f"تایید تغییر وضعیت", 
                                     f"وضعیت فعلی کالا '{product.name}' (شناسه: {product.id}) '{current_status_text}' است.\n"
                                     f"آیا مایل به تغییر وضعیت به '{new_status_text}' هستید؟",
                                     buttons_msg, # type: ignore 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            new_active_state = not product.is_active
            logger.debug(f"Attempting to set active status of Product ID {product.id} to {new_active_state}")
            try:
                updated_product = self.product_manager.set_product_activity(product.id, new_active_state) # type: ignore
                if updated_product:
                    QMessageBox.information(self, "موفقیت", f"وضعیت کالا '{product.name}' با موفقیت به '{new_status_text}' تغییر یافت.")
                    self.load_products_data()
                else:
                    QMessageBox.warning(self, "ناموفق", f"تغییر وضعیت کالا '{product.name}' انجام نشد.")
            except ValueError as ve:
                 QMessageBox.critical(self, "خطا در تغییر وضعیت", str(ve))
            except Exception as e:
                logger.error(f"Error toggling product activity: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"خطا در تغییر وضعیت کالا: {e}")