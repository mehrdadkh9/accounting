# src/presentation/purchase_orders_ui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QPushButton, QHBoxLayout,
    QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout, QGroupBox,
    QDialogButtonBox, QAbstractItemView, QDoubleSpinBox, QTextEdit,
    QHeaderView, QDateEdit, QSpinBox, QTextBrowser)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate, QSortFilterProxyModel
from PyQt5.QtGui import QColor, QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from typing import List, Optional, Any, Dict, Union
from datetime import date, datetime # <<< datetime اضافه شد برای ترکیب با زمان
from src.utils import date_converter
from .custom_widgets import ShamsiDateEdit # <<< ویجت جدید تاریخ شمسی
# Import entities, enums, and managers
from src.business_logic.entities.purchase_order_entity import PurchaseOrderEntity
from src.business_logic.entities.purchase_order_item_entity import PurchaseOrderItemEntity
from src.business_logic.entities.person_entity import PersonEntity
from src.business_logic.entities.product_entity import ProductEntity

from src.constants import PurchaseOrderStatus, PersonType, ProductType, DATE_FORMAT

from src.business_logic.purchase_order_manager import PurchaseOrderManager
from src.business_logic.person_manager import PersonManager
from src.business_logic.product_manager import ProductManager

import logging
logger = logging.getLogger(__name__)

# --- Table Model for the main list of Purchase Orders ---
class PurchaseOrderTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[PurchaseOrderEntity]] = None, 
                 person_manager: Optional[PersonManager] = None, # <<< person_manager به عنوان آرگومان اضافه شده
                 parent=None):
        super().__init__(parent)
        self._data: List[PurchaseOrderEntity] = data if data is not None else []
        self._person_manager = person_manager # <<< person_manager ذخیره می‌شود
        self._headers = ["شماره سفارش", "تامین‌کننده", "تاریخ سفارش", 
                         "مبلغ کل", "پرداخت شده", "دریافت شده (ارزش)", "وضعیت"]

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
        po = self._data[row] # po یک آبجکت PurchaseOrderEntity است

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: # شماره سفارش
                return po.order_number
            elif col == 1: # تامین‌کننده
                if self._person_manager and po.person_id is not None:
                    supplier = self._person_manager.get_person_by_id(po.person_id)
                    return supplier.name if supplier else f"ID: {po.person_id}"
                return str(po.person_id) # اگر person_manager پاس داده نشده یا person_id موجود نیست
            elif col == 2: # تاریخ سفارش
                order_date_val = po.order_date
                if isinstance(order_date_val, date):
                    return date_converter.to_shamsi_str(order_date_val)

                return str(order_date_val) # Fallback
            elif col == 3: # مبلغ کل
                return f"{po.total_amount_expected:,.2f}"
            elif col == 4: # پرداخت شده
                return f"{po.paid_amount:,.2f}"
            elif col == 5: # دریافت شده (ارزش)
                return f"{po.received_amount:,.2f}"
            elif col == 6: # وضعیت
                return po.status.value
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 2, 6]: # شماره سفارش، تاریخ، وضعیت
                return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            if col in [3, 4, 5]: # مبالغ
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            # برای ستون تامین‌کننده (col == 1) هم راست‌چین مناسب است
            return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[PurchaseOrderEntity]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_po_at_row(self, row: int) -> Optional[PurchaseOrderEntity]:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None
# --- Table Model for Purchase Order Items ---
class PurchaseOrderItemTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, product_manager: Optional[ProductManager] = None, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = data if data is not None else []
        self._product_manager = product_manager 
        self._headers = ["کد کالا", "نام کالا", "تعداد سفارش", "قیمت واحد", "مبلغ کل آیتم"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid(): return QVariant()
        row = index.row()
        col = index.column()
        if not (0 <= row < len(self._data)): return QVariant()
        
        item_data = self._data[row] 

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(item_data.get("product_id", ""))
            elif col == 1: 
                if self._product_manager and item_data.get("product_id"):
                    product = self._product_manager.get_product_by_id(item_data["product_id"])
                    return product.name if product else "کالای نامشخص"
                return item_data.get("product_name_display", "نامشخص") 
            elif col == 2: return str(item_data.get("ordered_quantity", 0))
            elif col == 3: return f"{item_data.get('unit_price', 0.0):,.2f}"
            elif col == 4: 
                total = item_data.get("ordered_quantity", 0) * item_data.get("unit_price", 0.0)
                return f"{total:,.2f}"
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0]: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            if col in [2,3,4]: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_item_data_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < len(self._data): return self._data[row]
        return None
    
    def add_item(self, item_data: Dict[str, Any]):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        self._data.append(item_data)
        self.endInsertRows()

    def remove_item(self, row: int):
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._data[row]
            self.endRemoveRows()
            return True
        return False
        
    def update_item(self, row: int, item_data: Dict[str, Any]):
        if 0 <= row < len(self._data):
            self._data[row] = item_data
            # Emit dataChanged for the entire row
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount(QModelIndex()) - 1))
            return True
        return False

# --- Dialog for adding/editing a single Purchase Order Item ---
class PurchaseOrderItemDialog(QDialog):
    def __init__(self, product_manager: ProductManager, 
                 item_data: Optional[Dict[str, Any]] = None, 
                 parent=None):
        super().__init__(parent)
        self.product_manager = product_manager
        self.item_data_to_edit = item_data
        self.products_cache: List[ProductEntity] = [] 

        self.setWindowTitle("افزودن/ویرایش قلم سفارش خرید")
        self.setMinimumWidth(350)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QFormLayout(self)
        self.product_combo = QComboBox(self)
        self.quantity_spinbox = QDoubleSpinBox(self)
        self.unit_price_spinbox = QDoubleSpinBox(self)

        self._populate_products_combo()

        self.quantity_spinbox.setDecimals(2)
        self.quantity_spinbox.setMinimum(0.01) 
        self.quantity_spinbox.setMaximum(999999.99)
        
        self.unit_price_spinbox.setDecimals(2)
        self.unit_price_spinbox.setMinimum(0.00)
        self.unit_price_spinbox.setMaximum(99999999.99)
        self.unit_price_spinbox.setGroupSeparatorShown(True)
        
        if self.item_data_to_edit: 
            product_id = self.item_data_to_edit.get("product_id")
            if product_id:
                idx = self.product_combo.findData(product_id)
                if idx != -1: self.product_combo.setCurrentIndex(idx)
            self.quantity_spinbox.setValue(self.item_data_to_edit.get("ordered_quantity", 1.0))
            self.unit_price_spinbox.setValue(self.item_data_to_edit.get("unit_price", 0.0))
        else: 
             self.product_combo.currentIndexChanged.connect(self._on_product_selected)

        layout.addRow("کالا:", self.product_combo)
        layout.addRow("تعداد سفارش:", self.quantity_spinbox)
        layout.addRow("قیمت واحد:", self.unit_price_spinbox)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons, Qt.Orientation.Horizontal, self) # type: ignore
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("تایید")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        if not self.item_data_to_edit and self.product_combo.count() > 0 : # If adding new, trigger prefill for initial product
            self._on_product_selected(0) # Pass index, not value

    def _populate_products_combo(self):
        self.products_cache = self.product_manager.get_all_products(active_only=True)
        eligible_products = [p for p in self.products_cache if p.product_type != ProductType.SERVICE and p.id is not None]
        
        self.product_combo.clear()
        if not eligible_products:
            self.product_combo.addItem("کالایی (غیرخدماتی) یافت نشد", -1)
            self.product_combo.setEnabled(False)
            return
        self.product_combo.setEnabled(True)
        for product in eligible_products:
            self.product_combo.addItem(f"{product.name} (SKU: {product.sku or 'N/A'})", product.id)

    def _on_product_selected(self, index: int): # index is passed by currentIndexChanged
        product_id = self.product_combo.itemData(index) # Use itemData with index
        if product_id and product_id != -1 and not self.item_data_to_edit: 
            selected_product = next((p for p in self.products_cache if p.id == product_id), None)
            if selected_product:
                self.unit_price_spinbox.setValue(selected_product.unit_price)

    def get_item_data(self) -> Optional[Dict[str, Any]]:
        product_id = self.product_combo.currentData()
        if not product_id or product_id == -1:
            QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک کالا انتخاب کنید.")
            return None
        
        quantity = self.quantity_spinbox.value()
        if quantity <= 0:
            QMessageBox.warning(self, "ورودی نامعتبر", "تعداد سفارش باید مثبت باشد.")
            return None
            
        unit_price = self.unit_price_spinbox.value()
        # Allow 0 price for unit_price
        if unit_price < 0: 
            QMessageBox.warning(self, "ورودی نامعتبر", "قیمت واحد نمی‌تواند منفی باشد.")
            return None
        
        selected_product_text = self.product_combo.currentText()
        return {
            "product_id": product_id,
            "product_name_display": selected_product_text, 
            "ordered_quantity": quantity,
            "unit_price": unit_price
        }

# --- Main Purchase Order Dialog ---
class PurchaseOrderDialog(QDialog):
    def __init__(self,
                 person_manager: PersonManager,
                 product_manager: ProductManager, # Needed for PurchaseOrderItemTableModel & Dialog
                 po_entity_data: Optional[PurchaseOrderEntity] = None, 
                 parent=None):
        super().__init__(parent)
        self.person_manager = person_manager
        self.product_manager = product_manager # Store product_manager
        self.po_entity_data_to_edit = po_entity_data
        self.current_po_items_data: List[Dict[str, Any]] = [] 

        self.is_edit_mode = self.po_entity_data_to_edit is not None

        title = "افزودن سفارش خرید جدید"
        if self.is_edit_mode and self.po_entity_data_to_edit:
            title = f"ویرایش سفارش خرید: {self.po_entity_data_to_edit.order_number}"
        self.setWindowTitle(title)
        self.setMinimumSize(700, 550) 
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui()

        if self.is_edit_mode and self.po_entity_data_to_edit:
            self._load_po_data_for_editing()

        self._calculate_and_display_total()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        header_groupbox = QGroupBox("اطلاعات کلی سفارش")
        header_groupbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        form_layout = QFormLayout(header_groupbox)

        self.supplier_combo = QComboBox()
       
        self.order_number_edit = QLineEdit() 
        self.order_date_edit = ShamsiDateEdit(self)

        self.fiscal_year_id_spinbox = QSpinBox(self) # QSpinBox is now imported
        self.fiscal_year_id_spinbox.setRange(0, 9999) 
        self.description_edit = QTextEdit()
        self.description_edit.setFixedHeight(60)
        
        self._populate_suppliers_combo()

        form_layout.addRow("شماره سفارش:", self.order_number_edit)
        form_layout.addRow("تامین‌کننده:", self.supplier_combo)
        form_layout.addRow("تاریخ سفارش:", self.order_date_edit)
        form_layout.addRow("شناسه سال مالی:", self.fiscal_year_id_spinbox)
        form_layout.addRow("توضیحات:", self.description_edit)
        
        if self.is_edit_mode:
            self.status_label = QLabel()
            self.paid_amount_label = QLabel()
            self.received_amount_label = QLabel()
            form_layout.addRow("وضعیت:", self.status_label)
            form_layout.addRow("مبلغ پرداخت شده:", self.paid_amount_label)
            form_layout.addRow("ارزش کالای دریافتی:", self.received_amount_label)

        main_layout.addWidget(header_groupbox)

        items_groupbox = QGroupBox("اقلام سفارش")
        items_groupbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        items_layout = QVBoxLayout(items_groupbox)

        self.items_table_view = QTableView()
        # Pass product_manager to item table model for fetching product names
        self.items_table_model = PurchaseOrderItemTableModel(product_manager=self.product_manager) 
        self.items_table_view.setModel(self.items_table_model)
        self.items_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        items_header = self.items_table_view.horizontalHeader()
        if items_header:
            items_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            items_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

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

        footer_layout = QHBoxLayout()
        self.total_amount_label = QLabel("جمع کل سفارش: 0.00")
        self.total_amount_label.setStyleSheet("font-weight: bold;")
        footer_layout.addStretch()
        footer_layout.addWidget(self.total_amount_label)
        main_layout.addLayout(footer_layout)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons, Qt.Orientation.Horizontal, self) # type: ignore
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("ذخیره سفارش")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        
        main_layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.setLayout(main_layout)

    def _populate_suppliers_combo(self):
        self.supplier_combo.clear()
        try:
            suppliers = self.person_manager.get_persons_by_type(PersonType.SUPPLIER)
            if not suppliers:
                self.supplier_combo.addItem("تامین‌کننده‌ای یافت نشد", -1) # Use -1 or None for invalid data
                self.supplier_combo.setEnabled(False)
                return
            self.supplier_combo.setEnabled(True)
            for supplier in suppliers:
                if supplier.id is not None:
                    self.supplier_combo.addItem(f"{supplier.name} (ID: {supplier.id})", supplier.id)
        except Exception as e:
            logger.error(f"Error populating suppliers combo: {e}", exc_info=True)
            self.supplier_combo.addItem("خطا در بارگذاری تامین‌کنندگان", -1)
            self.supplier_combo.setEnabled(False)

    def _load_po_data_for_editing(self):
        if self.po_entity_data_to_edit:
            po = self.po_entity_data_to_edit
            self.order_number_edit.setText(po.order_number)
            self.order_number_edit.setReadOnly(True)

            supplier_idx = self.supplier_combo.findData(po.person_id)
            if supplier_idx != -1: self.supplier_combo.setCurrentIndex(supplier_idx)
            
            # Ensure po.order_date is a datetime.date object before creating QDate
            self.order_date_edit.setDate(self.po_to_edit.order_date)

            
            self.description_edit.setText(po.description or "")
            self.fiscal_year_id_spinbox.setValue(po.fiscal_year_id or 0)
            
            if hasattr(self, 'status_label'): # Check if labels exist (only in edit mode)
              self.status_label.setText(po.status.value)
              self.paid_amount_label.setText(f"{po.paid_amount:,.2f}")
              self.received_amount_label.setText(f"{po.received_amount:,.2f}")

            self.current_po_items_data = []
            if po.items: # po.items should be List[PurchaseOrderItemEntity]
                for item_entity in po.items:
                    product_name = "کالای نامشخص"
                    if self.product_manager and item_entity.product_id is not None:
                         product = self.product_manager.get_product_by_id(item_entity.product_id)
                         if product: product_name = product.name
                    
                    self.current_po_items_data.append({
                        "item_id_db": item_entity.id, 
                        "product_id": item_entity.product_id,
                        "product_name_display": product_name,
                        "ordered_quantity": item_entity.ordered_quantity,
                        "unit_price": item_entity.unit_price
                    })
            self.items_table_model.update_data(self.current_po_items_data)
            self._calculate_and_display_total()

    def _add_item_clicked(self):
        item_dialog = PurchaseOrderItemDialog(self.product_manager, parent=self)
        if item_dialog.exec_() == QDialog.DialogCode.Accepted:
            new_item_data = item_dialog.get_item_data()
            if new_item_data:
                self.items_table_model.add_item(new_item_data)
                self.current_po_items_data = list(self.items_table_model._data) # Create new list
                self._calculate_and_display_total()

    def _edit_item_clicked(self):
        selected_indexes = self.items_table_view.selectionModel().selectedRows() # type: ignore
        if not selected_indexes:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک قلم را برای ویرایش انتخاب کنید.")
            return
        
        row_to_edit = selected_indexes[0].row()
        item_data_to_edit = self.items_table_model.get_item_data_at_row(row_to_edit)
        if not item_data_to_edit: return

        item_dialog = PurchaseOrderItemDialog(self.product_manager, item_data=item_data_to_edit, parent=self)
        if item_dialog.exec_() == QDialog.DialogCode.Accepted:
            updated_item_data = item_dialog.get_item_data()
            if updated_item_data:
                if "item_id_db" in item_data_to_edit: # Preserve original DB ID if present
                    updated_item_data["item_id_db"] = item_data_to_edit["item_id_db"]
                self.items_table_model.update_item(row_to_edit, updated_item_data)
                self.current_po_items_data = list(self.items_table_model._data)
                self._calculate_and_display_total()

    def _remove_item_clicked(self):
        selected_indexes = self.items_table_view.selectionModel().selectedRows() # type: ignore
        if not selected_indexes:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک قلم را برای حذف انتخاب کنید.")
            return
        
        row_to_remove = selected_indexes[0].row()
        item_to_remove = self.items_table_model.get_item_data_at_row(row_to_remove)
        if not item_to_remove: return # Should not happen
        
        reply = QMessageBox.question(self, "تایید حذف قلم", 
                                     f"آیا از حذف قلم '{item_to_remove.get('product_name_display', 'نامشخص')}' مطمئن هستید؟",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, # type: ignore 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.items_table_model.remove_item(row_to_remove)
            self.current_po_items_data = list(self.items_table_model._data)
            self._calculate_and_display_total()

    def _calculate_and_display_total(self) -> float: # Return float for get_po_data
        total = sum(item.get("ordered_quantity", 0) * item.get("unit_price", 0.0) for item in self.current_po_items_data)
        self.total_amount_label.setText(f"جمع کل سفارش: {total:,.2f}")
        return total

    def get_po_data(self) -> Optional[Dict[str, Any]]:
        supplier_id = self.supplier_combo.currentData()
        if supplier_id is None or supplier_id == -1: # Check for placeholder data too
            QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک تامین‌کننده انتخاب کنید.")
            return None
        
        if not self.current_po_items_data:
            QMessageBox.warning(self, "ورودی نامعتبر", "سفارش خرید باید حداقل یک قلم کالا داشته باشد.")
            return None
            
        order_date_val = self.order_date_edit.date()

        data_dict = { # Renamed to avoid conflict
            "supplier_person_id": supplier_id,
            "order_date": order_date_val,
            "order_number_override": self.order_number_edit.text().strip() or None,
            "description": self.description_edit.toPlainText().strip(),
            "fiscal_year_id": self.fiscal_year_id_spinbox.value() if self.fiscal_year_id_spinbox.value() > 0 else None,
            "items_data": [ # Ensure only relevant fields are passed for items
                {
                    "product_id": item.get("product_id"),
                    "ordered_quantity": item.get("ordered_quantity"),
                    "unit_price": item.get("unit_price"),
                    # "item_id_db": item.get("item_id_db") # Manager needs this if updating items
                } for item in self.current_po_items_data
            ], 
            "total_amount_expected": self._calculate_and_display_total() 
        }
        if self.is_edit_mode and self.po_entity_data_to_edit and self.po_entity_data_to_edit.id:
            data_dict["po_id"] = self.po_entity_data_to_edit.id
            # data_dict["current_status"] = self.po_entity_data_to_edit.status # Manager handles status

        return data_dict
class PurchaseOrderViewDialog(QDialog):
    """
    دیالوگی برای نمایش جزئیات کامل یک سفارش خرید به صورت فقط خواندنی.
    """
    def __init__(self, 
                 po_header: PurchaseOrderEntity,
                 person_manager: PersonManager,
                 product_manager: ProductManager,
                 parent=None):
        super().__init__(parent)
        self.po_header = po_header
        self.person_manager = person_manager
        self.product_manager = product_manager
        
        self.setWindowTitle(f"مشاهده سفارش خرید - شماره: {self.po_header.order_number}")
        self.setMinimumSize(800, 600)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self._setup_ui()
        self._populate_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        button_layout = QHBoxLayout()
        # دکمه‌های چاپ و PDF در آینده می‌توانند اضافه شوند
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.display_browser = QTextBrowser(self)
        main_layout.addWidget(self.display_browser)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn = self.button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_btn: close_btn.setText("بستن")
        main_layout.addWidget(self.button_box)
        
        self.button_box.rejected.connect(self.reject)

    def _populate_data(self):
        html_content = self._get_po_html_representation()
        self.display_browser.setHtml(html_content)

    def _get_po_html_representation(self) -> str:
        header = self.po_header
        
        supplier = self.person_manager.get_person_by_id(header.person_id)
        supplier_name = supplier.name if supplier else f"ID: {header.person_id}"

        css = """
            body { font-family: 'Tahoma', 'B Nazanin'; direction: rtl; }
            h2, h3 { text-align: center; color: #333; }
            .header-info { border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; border-radius: 5px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
            th { background-color: #f2f2f2; }
            .amount { text-align: right; }
        """
        html = f"<html><head><style>{css}</style></head><body>"
        html += f"<h2>سفارش خرید شماره: {header.order_number}</h2>"
        html += f"<div class='header-info'>"
        html += f"<p><b>تاریخ سفارش:</b> {date_converter.to_shamsi_str(header.order_date)}</p>"
        html += f"<p><b>تامین‌کننده:</b> {supplier_name}</p>"
        html += f"<p><b>وضعیت:</b> {header.status.value}</p>"
        html += f"<p><b>مبلغ کل:</b> {header.total_amount_expected:,.0f} ریال</p>"
        if header.description: html += f"<p><b>توضیحات:</b> {header.description}</p>"
        html += "</div>"
        
        html += "<h3>اقلام سفارش</h3><table><thead><tr><th>کد کالا</th><th>نام کالا</th><th>تعداد</th><th>قیمت واحد</th><th>مبلغ کل</th></tr></thead><tbody>"
        if header.items:
            for item in header.items:
                product = self.product_manager.get_product_by_id(item.product_id)
                product_name = product.name if product else f"ID: {item.product_id}"
                
                html += f"""
                    <tr>
                        <td>{item.product_id}</td>
                        <td>{product_name}</td>
                        <td class='amount'>{item.ordered_quantity:.2f}</td>
                        <td class='amount'>{item.unit_price:,.0f}</td>
                        <td class='amount'>{item.total_item_amount:,.0f}</td>
                    </tr>
                """
        else:
            html += "<tr><td colspan='5' style='text-align:center;'>اقلامی برای این سفارش ثبت نشده است.</td></tr>"

        html += "</tbody></table></body></html>"
        return html
# --- Main Purchase Orders UI Widget ---
class PurchaseOrdersUI(QWidget):
    def __init__(self, 
                 po_manager: PurchaseOrderManager, 
                 person_manager: PersonManager, 
                 product_manager: ProductManager,
                 parent=None):
        super().__init__(parent)
        self.po_manager = po_manager
        self.person_manager = person_manager 
        self.product_manager = product_manager

        # ارسال person_manager به مدل جدول
        self.table_model = PurchaseOrderTableModel(person_manager=self.person_manager) 
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        
        self._init_ui()
        self.load_purchase_orders_data()
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # --- بخش جستجو ---
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("جستجو در شماره، تامین‌کننده و ...")
        self.search_input.textChanged.connect(self.proxy_model.setFilterRegExp)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)

        # --- جدول ---
        self.po_table_view = QTableView(self)
        self.po_table_view.setModel(self.proxy_model)
        self.po_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.po_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.po_table_view.setSortingEnabled(True)
        header = self.po_table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) 
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) 
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch) 
        
        self.po_table_view.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        main_layout.addWidget(self.po_table_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("افزودن سفارش خرید جدید")
        self.edit_button = QPushButton("ویرایش سفارش انتخاب شده")
        self.cancel_button = QPushButton("لغو سفارش انتخاب شده")
        self.view_details_button = QPushButton("مشاهده جزئیات") # <<< دکمه جدید

        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_po_dialog)
        self.edit_button.clicked.connect(self._open_edit_po_dialog)

        self.cancel_button.clicked.connect(self._cancel_selected_po)
        self.view_details_button.clicked.connect(self._open_view_dialog) # <<< اتصال سیگنال

        self.refresh_button.clicked.connect(self.load_purchase_orders_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.view_details_button)

        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("PurchaseOrdersUI initialized.")

    def load_purchase_orders_data(self):
        logger.debug("Loading purchase orders data...")
        try:
            # Assuming PurchaseOrderManager has get_all_purchase_orders_summary or similar
            purchase_orders = self.po_manager.get_all_purchase_orders_summary()
            self.table_model.update_data(purchase_orders)
            logger.info(f"{len(purchase_orders)} purchase orders loaded into table.")
        except Exception as e:
            logger.error(f"Error loading purchase orders: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا در بارگذاری", f"خطا در بارگذاری لیست سفارشات خرید: {e}")

    def _open_add_po_dialog(self):
        logger.debug("Opening Add Purchase Order dialog.")
        dialog = PurchaseOrderDialog(
            person_manager=self.person_manager,
            product_manager=self.product_manager,
            parent=self
        )
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_po_data()
            if data:
                try:
                    created_po = self.po_manager.create_purchase_order( # Returns PurchaseOrderEntity
                        order_date=data["order_date"],
                        supplier_person_id=data["supplier_person_id"],
                        items_data=data["items_data"],
                        description=data.get("description"),
                        fiscal_year_id=data.get("fiscal_year_id"),
                        order_number_override=data.get("order_number_override")
                    )
                    if created_po:
                        QMessageBox.information(self, "موفقیت", f"سفارش خرید شماره '{created_po.order_number}' با موفقیت ایجاد شد.")
                        self.load_purchase_orders_data()
                    else:
                        QMessageBox.warning(self, "خطا", "ایجاد سفارش خرید ناموفق بود.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error creating purchase order: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ایجاد سفارش خرید: {e}")

    def _open_edit_po_dialog(self):
        selection_model = self.po_table_view.selectionModel()
        if not selection_model: 
            logger.error("PO Table: Selection model not found for edit.")
            QMessageBox.critical(self, "خطای داخلی", "مدل انتخاب جدول برای ویرایش یافت نشد.")
            return
        
        if not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک سفارش خرید را برای ویرایش انتخاب کنید.")
            return
        
        selected_rows = selection_model.selectedRows()
        if not selected_rows: # این شرط معمولاً با hasSelection پوشش داده می‌شود
            return 
        
        # get_po_at_row از PurchaseOrderTableModel یک PurchaseOrderEntity (فقط هدر) برمی‌گرداند
        selected_po_header = self.table_model.get_po_at_row(selected_rows[0].row())
        if not selected_po_header or selected_po_header.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات سفارش خرید انتخاب شده برای ویرایش.")
            return

        # برای ویرایش، نیاز به سفارش خرید کامل با اقلام آن داریم
        full_po_to_edit = self.po_manager.get_purchase_order_with_items(selected_po_header.id)
        if not full_po_to_edit:
            QMessageBox.critical(self, "خطا", f"سفارش خرید با شناسه {selected_po_header.id} برای ویرایش کامل یافت نشد (ممکن است اخیراً حذف شده باشد).")
            self.load_purchase_orders_data() # بارگذاری مجدد لیست
            return

        logger.debug(f"Opening Edit Purchase Order dialog for PO ID: {full_po_to_edit.id}, Order Number: {full_po_to_edit.order_number}")
        
        # ارسال مدیران لازم و سفارش خرید کامل به دیالوگ
        dialog = PurchaseOrderDialog(
            person_manager=self.person_manager,
            product_manager=self.product_manager,
            po_entity_data=full_po_to_edit, # ارسال آبجکت کامل سفارش خرید
            parent=self
        )

        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data_from_dialog = dialog.get_po_data()
            if data_from_dialog and full_po_to_edit.id is not None: # اطمینان از وجود شناسه برای ویرایش
                try:
                    # متد update_purchase_order در PurchaseOrderManager باید پیاده‌سازی شده باشد
                    # و بتواند تغییرات در هدر و لیست اقلام را مدیریت کند.
                    if hasattr(self.po_manager, 'update_purchase_order'):
                        updated_po = self.po_manager.update_purchase_order(
                            po_id=full_po_to_edit.id, # شناسه سفارش برای به‌روزرسانی
                            order_date=data_from_dialog["order_date"],
                            supplier_person_id=data_from_dialog["supplier_person_id"],
                            items_data=data_from_dialog["items_data"], # لیست جدید اقلام
                            description=data_from_dialog.get("description"),
                            fiscal_year_id=data_from_dialog.get("fiscal_year_id"),
                            # وضعیت (status) توسط فرآیندهای دیگر (پرداخت، رسید) مدیریت می‌شود
                        )
                        if updated_po:
                             QMessageBox.information(self, "موفقیت", f"سفارش خرید شماره '{updated_po.order_number}' با موفقیت ویرایش شد.")
                             self.load_purchase_orders_data()
                        else:
                             # این حالت زمانی رخ می‌دهد که update_purchase_order مقدار None برگرداند (مثلاً اگر تغییری اعمال نشده باشد)
                             QMessageBox.warning(self, "عدم تغییر", "تغییری در سفارش خرید اعمال نشد یا ویرایش ناموفق بود.")
                    else:
                        QMessageBox.warning(self, "عدم پیاده‌سازی", "عملکرد ویرایش سفارش خرید هنوز به طور کامل در مدیر مربوطه پیاده‌سازی نشده است.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error updating purchase order ID {full_po_to_edit.id}: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ویرایش سفارش خرید: {e}")
            else:
                logger.debug("Edit Purchase Order dialog returned no data or PO ID was missing.")
        else:
            logger.debug("Edit Purchase Order dialog cancelled.")
    def _cancel_selected_po(self):
        selection_model = self.po_table_view.selectionModel()
        if not selection_model: 
            logger.error("PO Table: Selection model not found for cancel.")
            QMessageBox.critical(self, "خطای داخلی", "مدل انتخاب جدول برای لغو یافت نشد.")
            return
        
        if not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک سفارش خرید را برای لغو انتخاب کنید.")
            return
        
        selected_rows = selection_model.selectedRows()
        if not selected_rows: return
        
        selected_po_header = self.table_model.get_po_at_row(selected_rows[0].row())
        if not selected_po_header or selected_po_header.id is None:
            QMessageBox.critical(self, "خطا", "خطا در دریافت اطلاعات سفارش خرید برای لغو.")
            return

        reply = QMessageBox.question(self, "تایید لغو", 
                                     f"آیا از لغو سفارش خرید شماره '{selected_po_header.order_number}' (شناسه: {selected_po_header.id}) مطمئن هستید؟\n"
                                     "توجه: این عملیات وضعیت سفارش را به 'لغو شده' تغییر می‌دهد.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, # type: ignore
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                cancelled_po = self.po_manager.cancel_purchase_order(selected_po_header.id) # type: ignore
                if cancelled_po:
                    QMessageBox.information(self, "موفقیت", f"سفارش خرید '{cancelled_po.order_number}' با موفقیت لغو شد.")
                    self.load_purchase_orders_data()
                else:
                    # این حالت زمانی رخ می‌دهد که cancel_purchase_order مقدار None برگرداند
                    QMessageBox.warning(self, "ناموفق", "لغو سفارش خرید انجام نشد (ممکن است وضعیت فعلی آن اجازه لغو ندهد یا خطایی رخ داده باشد).")
            except ValueError as ve: # اگر cancel_purchase_order خطای اعتبارسنجی ایجاد کند
                QMessageBox.warning(self, "خطا در لغو", str(ve))
            except Exception as e:
                logger.error(f"Error cancelling PO ID {selected_po_header.id}: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"خطا در لغو سفارش خرید: {e}")
    def _get_selected_po(self) -> Optional[PurchaseOrderEntity]:
        selection_model = self.po_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک سفارش خرید را انتخاب کنید.")
            return None
        
        proxy_index = selection_model.selectedRows()[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        
        return self.table_model.get_po_at_row(source_index.row())

    def _call_po_dialog(self, po_to_edit: Optional[PurchaseOrderEntity] = None):
        # ... (کد کامل این متد از پاسخ‌های قبلی)
        pass
    def _open_view_dialog(self):
        """دیالوگ مشاهده جزئیات را برای سفارش انتخاب شده باز می‌کند."""
        selected_po = self._get_selected_po()
        if not selected_po or not selected_po.id:
            return
        
        full_po = self.po_manager.get_purchase_order_with_items(selected_po.id)
        if not full_po:
            QMessageBox.warning(self, "خطا", "اطلاعات کامل سفارش برای مشاهده یافت نشد.")
            return
            
        dialog = PurchaseOrderViewDialog(
            po_header=full_po,
            person_manager=self.person_manager,
            product_manager=self.product_manager,
            parent=self
        )
        dialog.exec_()