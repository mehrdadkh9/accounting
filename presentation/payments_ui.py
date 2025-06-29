# src/presentation/payments_ui.py

# --- Import‌های لازم برای این فایل ---
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QPushButton, QHBoxLayout,
    QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout, QGroupBox,
    QDialogButtonBox, QAbstractItemView, QDoubleSpinBox, QTextEdit,
    QHeaderView, QDateEdit, QSpinBox, QRadioButton,
    QApplication, QFileDialog, QTextBrowser
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate, pyqtSignal, QTimer, QSortFilterProxyModel
from PyQt5.QtGui import QColor, QFont, QTextDocument
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog

from typing import List, Optional, Any, Dict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from src.utils import date_converter
from .custom_widgets import ShamsiDateEdit
# --- Entities, Enums, Managers ---
from src.business_logic.entities.payment_header_entity import PaymentHeaderEntity
from src.business_logic.entities.payment_line_item_entity import PaymentLineItemEntity
from src.business_logic.entities.person_entity import PersonEntity
from src.business_logic.entities.account_entity import AccountEntity
from src.business_logic.entities.invoice_entity import InvoiceEntity
from src.business_logic.entities.purchase_order_entity import PurchaseOrderEntity
from src.business_logic.entities.check_entity import CheckEntity

from src.constants import (
    PaymentMethod, DATE_FORMAT, PersonType, AccountType, 
    InvoiceType, CheckType, CheckStatus, FinancialTransactionType, 
    ReferenceType, PurchaseOrderStatus, InvoiceStatus, PaymentMethod,PaymentType 
)

from src.business_logic.payment_manager import PaymentManager
from src.business_logic.person_manager import PersonManager
from src.business_logic.account_manager import AccountManager
from src.business_logic.invoice_manager import InvoiceManager
from src.business_logic.purchase_order_manager import PurchaseOrderManager
from src.business_logic.check_manager import CheckManager

import logging
logger = logging.getLogger(__name__)
# --- WeasyPrint Import ---
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    HTML, CSS = None, None
# ============================================================
#  PaymentTableModel (برای جدول اصلی لیست پرداخت‌ها)
# ============================================================
class PaymentTableModel(QAbstractTableModel):
    def __init__(self, 
                 person_manager: Optional[PersonManager] = None,
                 parent=None):
        super().__init__(parent)
        self._payment_headers: List[PaymentHeaderEntity] = []
        self._person_manager = person_manager
        self._headers = ["شناسه", "نوع", "تاریخ", "شخص", "مبلغ کل", "توضیحات"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._payment_headers)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._payment_headers)):
            return QVariant()
        
        payment = self._payment_headers[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(payment.id)
            elif col == 1: return payment.payment_type.value if hasattr(payment, 'payment_type') and isinstance(payment.payment_type, PaymentType) else "نامشخص"
            elif col == 2:                 return date_converter.to_shamsi_str(payment.payment_date)
            elif col == 3: 
                if getattr(payment, 'person_name', None): return payment.person_name
                if self._person_manager and payment.person_id:
                    person = self._person_manager.get_person_by_id(payment.person_id)
                    return person.name if person else f"ID: {payment.person_id}"
                return "متفرقه" if not payment.person_id else "-"
            elif col == 4: return f"{Decimal(str(payment.total_amount or '0')):,.0f}"
            elif col == 5: return payment.description or ""
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [0, 1, 2]: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            if col == 4: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[PaymentHeaderEntity]):
        self.beginResetModel()
        self._payment_headers = new_data if new_data is not None else []
        self.endResetModel()

    def get_payment_header_at_row(self, row: int) -> Optional[PaymentHeaderEntity]:
        if 0 <= row < len(self._payment_headers):
            return self._payment_headers[row]
        return None

# ============================================================
#  PaymentLineItemTableModel (برای جدول اقلام در دیالوگ پرداخت)
# ============================================================
class PaymentLineItemTableModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_items: List[Dict[str, Any]] = []
        self._headers = ["روش پرداخت", "مبلغ", "حساب/چک", "توضیحات"]


    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._line_items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._line_items)): return QVariant()
        item = self._line_items[index.row()]
        col = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return item.get("payment_method_display", "-")
            elif col == 1: return f"{Decimal(str(item.get('amount', '0'))):,.0f}"
            elif col == 2: return item.get("account_check_display", "-")
            elif col == 3: return item.get("description", "")
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 1: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._line_items = new_data if new_data is not None else []
        self.endResetModel()

    def get_item_data_at_row(self, row: int) -> Optional[Dict[str, Any]]:
        if 0 <= row < self.rowCount(): return self._line_items[row]
        return None

    def add_item(self, item_data: Dict[str, Any]):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._line_items.append(item_data)
        self.endInsertRows()

    def update_item(self, row: int, item_data: Dict[str, Any]):
        if 0 <= row < self.rowCount():
            self._line_items[row] = item_data
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1))

    def remove_item(self, row: int) -> bool:
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._line_items[row]
            self.endRemoveRows()
            return True
        return False
        
    def get_all_items_data(self) -> List[Dict[str, Any]]:
        return self._line_items
    
class PaymentLineItemDialog(QDialog):
    def __init__(self, 
                 account_manager: AccountManager,
                 check_manager: CheckManager,   
                 person_manager: PersonManager,   
                 line_data_to_edit: Optional[Dict[str, Any]] = None, 
                 parent_dialog_person_id: Optional[int] = None,
                 parent_dialog_is_receipt: Optional[bool] = None, 
                 parent=None):
        super().__init__(parent)
        self.account_manager = account_manager
        self.check_manager = check_manager
        self.person_manager = person_manager
        self.line_data_to_edit = line_data_to_edit
        self.is_edit_mode = self.line_data_to_edit is not None
        
        self.parent_dialog_person_id = parent_dialog_person_id
        self.parent_dialog_is_receipt = parent_dialog_is_receipt if parent_dialog_is_receipt is not None else False

        self.setWindowTitle("افزودن/ویرایش قلم پرداخت/دریافت")
        self.setMinimumWidth(480)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self._setup_ui_elements() 
        self._setup_ui_layout()   
        self.setLayout(self.main_layout_form)

        # اتصال سیگنال‌ها
        self.payment_method_combo_line.currentIndexChanged.connect(self._on_line_payment_method_changed)
        self.line_link_existing_radio.toggled.connect(self._on_line_check_type_option_changed)
        self.line_create_new_radio.toggled.connect(self._on_line_check_type_option_changed)
        self.line_endorse_existing_radio.toggled.connect(self._on_line_check_type_option_changed)
        self.line_endorse_check_combo.currentIndexChanged.connect(self._on_endorse_check_selected)
        
        self.button_box_line.accepted.connect(self.accept)
        self.button_box_line.rejected.connect(self.reject)
        
        if self.is_edit_mode and self.line_data_to_edit:
            self._load_line_item_for_editing()
        else:
            self.line_new_check_issue_date_edit.setDate(QDate.currentDate())
            self.line_new_check_due_date_edit.setDate(QDate.currentDate())
            if self.payment_method_combo_line.count() > 0:
                self.payment_method_combo_line.setCurrentIndex(0)
            self._on_line_payment_method_changed()


    def _setup_ui_elements(self):
        """تمام ویجت‌های دیالوگ را ایجاد می‌کند."""
        self.main_layout_form = QFormLayout(self)

        self.payment_method_combo_line = QComboBox(self)
        allowed_methods = [PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.BANK_TRANSFER, PaymentMethod.CHECK]
        if not self.parent_dialog_is_receipt:
            allowed_methods.append(PaymentMethod.ENDORSE_CHECK)
        for pm_enum in allowed_methods:
            self.payment_method_combo_line.addItem(pm_enum.value, pm_enum)

        self.amount_spinbox_line = QDoubleSpinBox(self)
        self.amount_spinbox_line.setDecimals(0)
        self.amount_spinbox_line.setMinimum(0.01)
        self.amount_spinbox_line.setMaximum(999999999999.00)
        self.amount_spinbox_line.setGroupSeparatorShown(True)

        self.our_account_label = QLabel("از/به حساب (ما):*", self)
        self.account_combo_line = QComboBox(self) 
        self._populate_line_payment_account_combo()

        self.description_edit_line = QLineEdit(self)
        self.description_edit_line.setPlaceholderText("توضیحات اختیاری برای این قلم")

        self.line_check_group = QGroupBox("جزئیات چک")
        self.line_check_group.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        line_check_layout = QFormLayout(self.line_check_group)
        
        self.line_link_existing_radio = QRadioButton("لینک به چک موجود", self.line_check_group)
        self.line_existing_check_combo = QComboBox(self.line_check_group)
        self.line_create_new_radio = QRadioButton("ایجاد چک جدید", self.line_check_group)
        self.line_new_check_number_edit = QLineEdit(self.line_check_group)
        self.line_new_check_issue_date_edit = ShamsiDateEdit(self)
        self.line_new_check_due_date_edit = ShamsiDateEdit(self)
        self.line_new_check_bank_account_combo = QComboBox(self.line_check_group)
        self._populate_line_check_bank_account_combo()
        self.line_endorse_existing_radio = QRadioButton("خرج چک دریافتی موجود", self.line_check_group)
        self.line_endorse_check_combo = QComboBox(self.line_check_group)
        
        line_check_layout.addRow(self.line_link_existing_radio); line_check_layout.addRow("انتخاب چک موجود:", self.line_existing_check_combo)
        line_check_layout.addRow(self.line_create_new_radio); line_check_layout.addRow("شماره چک جدید:", self.line_new_check_number_edit)
        line_check_layout.addRow("تاریخ صدور:", self.line_new_check_issue_date_edit); line_check_layout.addRow("تاریخ سررسید:", self.line_new_check_due_date_edit)
        line_check_layout.addRow("از حساب بانکی (ما):", self.line_new_check_bank_account_combo)
        line_check_layout.addRow(self.line_endorse_existing_radio); line_check_layout.addRow("انتخاب چک دریافتی برای خرج:", self.line_endorse_check_combo)

        self.button_box_line = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = self.button_box_line.button(QDialogButtonBox.StandardButton.Ok); ok_btn.setText("تایید قلم")
        cancel_btn = self.button_box_line.button(QDialogButtonBox.StandardButton.Cancel); cancel_btn.setText("انصراف")

    def _setup_ui_layout(self):
        self.main_layout_form.addRow("روش پرداخت قلم:*", self.payment_method_combo_line)
        self.main_layout_form.addRow("مبلغ قلم (ریال):*", self.amount_spinbox_line)
        self.main_layout_form.addRow(self.our_account_label, self.account_combo_line)
        self.main_layout_form.addRow("توضیحات قلم:", self.description_edit_line)
        self.main_layout_form.addWidget(self.line_check_group)
        self.main_layout_form.addWidget(self.button_box_line)

    def _populate_line_payment_account_combo(self):
        self.account_combo_line.clear()
        self.account_combo_line.addItem("-- انتخاب حساب (ما) --", None)
        if self.account_manager:
            try:
                asset_accounts = self.account_manager.get_accounts_by_type(AccountType.ASSET)
                cash_bank_accounts = [acc for acc in (asset_accounts or []) if acc.id and any(keyword in acc.name.lower() for keyword in ["بانک", "صندوق", "نقد"])]
                if cash_bank_accounts:
                    for acc in cash_bank_accounts: self.account_combo_line.addItem(f"{acc.name} (ID: {acc.id})", int(acc.id))
                else: self.account_combo_line.addItem("حساب نقد/بانک یافت نشد", None)
            except Exception as e: logger.error(f"Error populating 'our' accounts for line item: {e}")
        self.account_combo_line.setCurrentIndex(0)

    def _populate_line_check_bank_account_combo(self):
        self.line_new_check_bank_account_combo.clear()
        self.line_new_check_bank_account_combo.addItem("-- حساب بانکی چک --", None)
        if self.account_manager:
            try:
                asset_accounts = self.account_manager.get_accounts_by_type(AccountType.ASSET)
                bank_accounts = [acc for acc in (asset_accounts or []) if acc.id and ("بانک" in acc.name or "جاری" in acc.name)]
                if bank_accounts:
                    for acc in bank_accounts: self.line_new_check_bank_account_combo.addItem(f"{acc.name} (ID: {acc.id})", int(acc.id))
                else: self.line_new_check_bank_account_combo.addItem("حساب بانکی یافت نشد", None)
            except Exception as e: logger.error(f"Error populating line check bank accounts: {e}")
        self.line_new_check_bank_account_combo.setCurrentIndex(0)
    
    def _populate_line_existing_checks_combo(self):
        self.line_existing_check_combo.clear()
        self.line_existing_check_combo.addItem("-- انتخاب چک موجود --", None)
        self.line_existing_check_combo.setEnabled(False) 
        if not all([self.check_manager, self.parent_dialog_person_id, self.parent_dialog_is_receipt is not None]):
            self.line_existing_check_combo.addItem("اطلاعات شخص/جهت نامشخص", None)
            return
        
        expected_check_type = CheckType.RECEIVED if not self.parent_dialog_is_receipt else CheckType.ISSUED
        try:
            eligible_checks = self.check_manager.get_all_checks(person_id=self.parent_dialog_person_id, type_filter=expected_check_type, status_filter=CheckStatus.PENDING)
            if eligible_checks:
                self.line_existing_check_combo.setEnabled(True)
                for chk in eligible_checks:
                    self.line_existing_check_combo.addItem(f"ش: {chk.check_number} (م: {chk.amount:,.0f})", int(chk.id))
        except Exception as e: logger.error(f"Error populating existing checks: {e}", exc_info=True)

    def _populate_line_endorse_check_combo(self):
        self.line_endorse_check_combo.clear()
        self.line_endorse_check_combo.addItem("-- انتخاب چک دریافتی برای خرج --", None)
        self.line_endorse_check_combo.setEnabled(False)
        if not self.check_manager: return
        try:
            eligible_checks = self.check_manager.get_all_checks(type_filter=CheckType.RECEIVED, status_filter=CheckStatus.PENDING)
            if eligible_checks:
                self.line_endorse_check_combo.setEnabled(True)
                for chk in eligible_checks:
                    drawer = self.person_manager.get_person_by_id(chk.person_id)
                    drawer_name = drawer.name if drawer else "ناشناس"
                    self.line_endorse_check_combo.addItem(f"ش: {chk.check_number} (از: {drawer_name}, م: {chk.amount:,.0f})", int(chk.id))
        except Exception as e: logger.error(f"Error populating endorse checks: {e}", exc_info=True)

    def _on_line_payment_method_changed(self):
        method = self.payment_method_combo_line.currentData()
        is_check = (method == PaymentMethod.CHECK)
        is_endorse = (method == PaymentMethod.ENDORSE_CHECK)
        
        self.line_check_group.setVisible(is_check or is_endorse)
        self.account_combo_line.setEnabled(not is_check and not is_endorse)
        self.our_account_label.setVisible(not is_check and not is_endorse)
        
        if is_check:
            if not self.line_link_existing_radio.isChecked() and not self.line_create_new_radio.isChecked():
                self.line_link_existing_radio.setChecked(True)
        elif is_endorse:
            self.line_endorse_existing_radio.setChecked(True)
        self._on_line_check_type_option_changed()

    def _on_line_check_type_option_changed(self):
        is_link = self.line_link_existing_radio.isChecked() and self.line_link_existing_radio.isVisible()
        is_new = self.line_create_new_radio.isChecked() and self.line_create_new_radio.isVisible()
        is_endorse = self.line_endorse_existing_radio.isChecked() and self.line_endorse_existing_radio.isVisible()

        for widget in [self.line_existing_check_combo] + self.line_existing_check_combo.parent().findChildren(QLabel):
            widget.setVisible(is_link)
        if is_link: self._populate_line_existing_checks_combo()

        for widget in [self.line_new_check_number_edit, self.line_new_check_issue_date_edit, self.line_new_check_due_date_edit, self.line_new_check_bank_account_combo] + self.line_create_new_radio.parent().findChildren(QLabel):
            if any(w == widget for w in [self.line_create_new_radio, self.line_link_existing_radio, self.line_endorse_existing_radio]): continue
            widget.setVisible(is_new)
            
        for widget in [self.line_endorse_check_combo] + self.line_endorse_check_combo.parent().findChildren(QLabel):
            widget.setVisible(is_endorse)
        if is_endorse:
            self._populate_line_endorse_check_combo()
            self.amount_spinbox_line.setReadOnly(True)
            self._on_endorse_check_selected()
        else:
            self.amount_spinbox_line.setReadOnly(False)

    def _on_endorse_check_selected(self):
        if not self.line_endorse_existing_radio.isChecked(): return
        check_id = self.line_endorse_check_combo.currentData()
        if check_id and self.check_manager:
            chk = self.check_manager.get_check_by_id(int(check_id))
            if chk: self.amount_spinbox_line.setValue(float(chk.amount))
        else: self.amount_spinbox_line.setValue(0.01)

    def _load_line_item_for_editing(self):
        if not (self.is_edit_mode and self.line_data_to_edit): return
        data = self.line_data_to_edit
        
        method_enum = data.get("payment_method")
        if isinstance(method_enum, PaymentMethod):
            self.payment_method_combo_line.setCurrentIndex(self.payment_method_combo_line.findData(method_enum))
        
        self.amount_spinbox_line.setValue(float(data.get("amount", 0.0)))
        if data.get("account_id"):
            self.account_combo_line.setCurrentIndex(self.account_combo_line.findData(int(data["account_id"])))
        self.description_edit_line.setText(data.get("description", ""))

        if method_enum == PaymentMethod.ENDORSE_CHECK:
            self.line_endorse_existing_radio.setChecked(True)
            QTimer.singleShot(50, lambda: self._try_select_in_combo(self.line_endorse_check_combo, data.get("endorsed_check_id")))
        elif method_enum == PaymentMethod.CHECK:
            check_details = data.get("check_details")
            existing_check_id = data.get("existing_check_id")
            if check_details:
                self.line_create_new_radio.setChecked(True)
                self.line_new_check_number_edit.setText(check_details.get("check_number", ""))
                self.line_new_check_issue_date_edit.setDate(check_details.get("issue_date"))
                self.line_new_check_due_date_edit.setDate(check_details.get("due_date"))
                bank_id = check_details.get("bank_account_id_for_check")
                if bank_id: self.line_new_check_bank_account_combo.setCurrentIndex(self.line_new_check_bank_account_combo.findData(bank_id))
            elif existing_check_id:
                self.line_link_existing_radio.setChecked(True)
                QTimer.singleShot(50, lambda: self._try_select_in_combo(self.line_existing_check_combo, existing_check_id))
        QTimer.singleShot(100, self._on_line_payment_method_changed)

    def _try_select_in_combo(self, combo: QComboBox, data_id: Optional[int]):
        if data_id is None: return
        idx = combo.findData(int(data_id))
        if idx != -1: combo.setCurrentIndex(idx)

    def get_line_item_data(self) -> Optional[Dict[str, Any]]:
        method = self.payment_method_combo_line.currentData()
        if not isinstance(method, PaymentMethod):
            QMessageBox.warning(self, "خطا", "روش پرداخت انتخاب نشده است."); return None
        
        amount = Decimal(str(self.amount_spinbox_line.value()))
        if amount <= 0:
            QMessageBox.warning(self, "خطا", "مبلغ باید مثبت باشد."); return None

        line_data: Dict[str, Any] = {"payment_method": method, "amount": amount, "description": self.description_edit_line.text().strip()}
        
        # Data for display in parent table
        line_data["payment_method_display"] = method.value
        line_data["account_check_display"] = "-"

        if method == PaymentMethod.ENDORSE_CHECK:
            check_id = self.line_endorse_check_combo.currentData()
            if check_id is None: QMessageBox.warning(self, "خطا", "چک برای خرج انتخاب نشده."); return None
            line_data["endorsed_check_id"] = int(check_id)
            line_data["account_check_display"] = self.line_endorse_check_combo.currentText()
        elif method == PaymentMethod.CHECK:
            if self.line_create_new_radio.isChecked():
                bank_acc_id = self.line_new_check_bank_account_combo.currentData()
                check_num = self.line_new_check_number_edit.text().strip()
                if not check_num or bank_acc_id is None:
                    QMessageBox.warning(self, "خطا", "شماره چک و حساب بانکی برای چک جدید الزامی است."); return None
                line_data["check_details"] = {
                    "check_number": check_num,
                    "issue_date": self.line_new_check_issue_date_edit.date(),
                    "due_date": self.line_new_check_due_date_edit.date(),
                    "bank_account_id_for_check": int(bank_acc_id)
                }
                line_data["account_id"] = int(bank_acc_id)
                line_data["account_check_display"] = f"چک جدید: {check_num}"
            elif self.line_link_existing_radio.isChecked():
                check_id = self.line_existing_check_combo.currentData()
                if check_id is None: QMessageBox.warning(self, "خطا", "چک موجود انتخاب نشده."); return None
                line_data["existing_check_id"] = int(check_id)
                if self.parent_dialog_is_receipt: # دریافت چک از مشتری و واریز به حساب
                    our_account_id = self.account_combo_line.currentData()
                    if our_account_id is None: QMessageBox.warning(self, "خطا", "حساب واریزی برای چک دریافتی انتخاب نشده."); return None
                    line_data["account_id"] = int(our_account_id)
                    line_data["account_check_display"] = f"{self.line_existing_check_combo.currentText()} -> {self.account_combo_line.currentText()}"
                else: # پرداخت با چک موجود (که قبلا صادر شده)
                    line_data["account_check_display"] = self.line_existing_check_combo.currentText()
        else: # Cash, Card, Bank Transfer
            our_account_id = self.account_combo_line.currentData()
            if our_account_id is None: QMessageBox.warning(self, "خطا", "حساب (ما) باید انتخاب شود."); return None
            line_data["account_id"] = int(our_account_id)
            line_data["account_check_display"] = self.account_combo_line.currentText()
        
        if self.is_edit_mode and self.line_data_to_edit and self.line_data_to_edit.get("line_item_id_db"):
            line_data["line_item_id_db"] = self.line_data_to_edit.get("line_item_id_db")
            
        logger.debug(f"PaymentLineItemDialog.get_line_item_data returning: {line_data}")
        return line_data
    @staticmethod
    def convert_entity_to_dict_for_dialog(line_entity: 'PaymentLineItemEntity', 
                                          check_manager: 'CheckManager',
                                          account_manager: 'AccountManager',
                                          person_manager: 'PersonManager') -> Dict[str, Any]:
        """
        یک آبجکت PaymentLineItemEntity را به یک دیکشنری مناسب برای استفاده در دیالوگ‌ها تبدیل می‌کند.
        این دیکشنری شامل فیلدهای نمایشی نیز می‌باشد.
        """
        logger.debug(f"Converting PaymentLineItemEntity (ID: {line_entity.id}) to dict for dialog.")
        
        line_dict: Dict[str, Any] = {
            "line_item_id_db": line_entity.id,
            "payment_method": line_entity.payment_method,
            "amount": line_entity.amount,
            "account_id": line_entity.account_id,
            "check_id": line_entity.check_id,
            "description": line_entity.description,
            "payment_method_display": line_entity.payment_method.value,
            "account_check_display": "-", # مقدار پیش‌فرض
            "existing_check_id": None,
            "endorsed_check_id": None,
            "check_details": None,
        }

        # تعیین متن نمایشی برای ستون "حساب/چک"
        method = line_entity.payment_method
        if method == PaymentMethod.CHECK:
            if line_entity.check_id and check_manager:
                chk = check_manager.get_check_by_id(line_entity.check_id)
                if chk:
                    line_dict["account_check_display"] = f"چک ش: {chk.check_number}"
                    line_dict["existing_check_id"] = chk.id
        elif method == PaymentMethod.ENDORSE_CHECK:
            if line_entity.check_id and check_manager:
                chk = check_manager.get_check_by_id(line_entity.check_id)
                if chk:
                    drawer = person_manager.get_person_by_id(chk.person_id)
                    drawer_name = drawer.name if drawer else "ناشناس"
                    line_dict["account_check_display"] = f"خرج چک: {chk.check_number} (از: {drawer_name})"
                    line_dict["endorsed_check_id"] = chk.id
        elif method in [PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.BANK_TRANSFER]:
            if line_entity.account_id and account_manager:
                acc = account_manager.get_account_by_id(line_entity.account_id)
                if acc:
                    line_dict["account_check_display"] = acc.name
        
        return line_dict

# ============================================================
#  کلاس ۴: PaymentDialog (کامل و اصلاح شده)
# ============================================================
class PaymentDialog(QDialog):
    def __init__(self, 
                 payment_manager: PaymentManager,
                 person_manager: PersonManager,
                 account_manager: AccountManager,
                 invoice_manager: InvoiceManager,
                 po_manager: PurchaseOrderManager,
                 check_manager: CheckManager,
                 payment_header: Optional[PaymentHeaderEntity] = None,
                 parent=None):
        super().__init__(parent)
        
        # --- ذخیره وابستگی‌ها ---
        self.payment_manager = payment_manager
        self.person_manager = person_manager
        self.account_manager = account_manager
        self.invoice_manager = invoice_manager
        self.po_manager = po_manager
        self.check_manager = check_manager
        
        # --- تنظیمات اولیه ---
        self.payment_to_edit_header = payment_header
        self.is_edit_mode = self.payment_to_edit_header is not None
        
        # --- داده‌های داخلی ---
        self.line_items_model = PaymentLineItemTableModel(parent=self)
        self.unpaid_invoices_cache: Dict[int, List[InvoiceEntity]] = {} 
        self.open_pos_cache: Dict[int, List[PurchaseOrderEntity]] = {}

        # --- متغیرهای حالت UI ---
        self.is_direct_posting_mode: bool = False
        
        # --- تنظیمات پنجره ---
        title = "ثبت پرداخت/دریافت جدید"
        if self.is_edit_mode and self.payment_to_edit_header:
            title = f"ویرایش سند (شناسه: {self.payment_to_edit_header.id})"
        self.setWindowTitle(title)
        self.setMinimumSize(750, 600)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self._setup_ui()
        self._connect_signals()
        self._populate_initial_data()

    def _setup_ui(self):
        """تمام ویجت‌ها و layout های دیالوگ را ایجاد و چیدمان می‌کند."""
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # --- بخش انتخاب نوع عملیات ---
        context_layout = QHBoxLayout()
        context_layout.addWidget(QLabel("<b>نوع عملیات:</b>"))
        self.payment_context_combo = QComboBox(self)
        self.payment_context_combo.addItems(["تسویه فاکتور/سفارش خرید", "ثبت مستقیم هزینه/درآمد"])
        context_layout.addWidget(self.payment_context_combo)
        context_layout.addStretch()
        self.main_layout.addLayout(context_layout)

        # --- گروه هدر ---
        self.header_group = QGroupBox("مشخصات کلی سند")
        header_form_layout = QFormLayout(self.header_group)
        self.person_label = QLabel("پرداخت/دریافت از/به:*", self)
        self.person_combo = QComboBox(self)
        self.fiscal_year_spinbox = QSpinBox(self); self.fiscal_year_spinbox.setRange(1, 9999)
        self.description_edit = QTextEdit(self); self.description_edit.setFixedHeight(60)
        self.payment_date_edit = ShamsiDateEdit(self)

        header_form_layout.addRow("تاریخ پرداخت/دریافت:*", self.payment_date_edit)
        header_form_layout.addRow(self.person_label, self.person_combo)
        header_form_layout.addRow("سال مالی:*", self.fiscal_year_spinbox)
        header_form_layout.addRow("توضیحات کلی:", self.description_edit)
        self.main_layout.addWidget(self.header_group)

        # --- گروه ثبت مستقیم هزینه/درآمد (در ابتدا مخفی) ---
        self.direct_posting_group = QGroupBox("جزئیات ثبت مستقیم")
        direct_posting_layout = QFormLayout(self.direct_posting_group)
        self.target_account_combo = QComboBox(self) # حساب هزینه/درآمد
        self.direct_amount_spinbox = QDoubleSpinBox(self); self.direct_amount_spinbox.setDecimals(0); self.direct_amount_spinbox.setMinimum(1); self.direct_amount_spinbox.setMaximum(999999999999.00); self.direct_amount_spinbox.setGroupSeparatorShown(True)
        self.direct_payment_method_combo = QComboBox(self)
        self.direct_our_account_combo = QComboBox(self)
        direct_posting_layout.addRow("به حساب هزینه/درآمد:*", self.target_account_combo)
        direct_posting_layout.addRow("مبلغ:*", self.direct_amount_spinbox)
        direct_posting_layout.addRow("از طریق روش:*", self.direct_payment_method_combo)
        direct_posting_layout.addRow("از/به حساب (ما):*", self.direct_our_account_combo)
        self.main_layout.addWidget(self.direct_posting_group)

        # --- گروه اقلام (برای تسویه) ---
        self.items_group = QGroupBox("اقلام پرداخت/دریافت (برای تسویه)")
        items_layout = QVBoxLayout(self.items_group)
        self.items_table_view = QTableView(self)
        self.items_table_view.setModel(self.line_items_model)
        self.items_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        items_header = self.items_table_view.horizontalHeader()
        if items_header:
            items_header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            items_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            items_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            
        item_buttons_layout = QHBoxLayout()
        self.add_item_button = QPushButton(" (+) افزودن قلم")
        self.edit_item_button = QPushButton("ویرایش قلم")
        self.remove_item_button = QPushButton("حذف قلم")
        item_buttons_layout.addWidget(self.add_item_button); item_buttons_layout.addWidget(self.edit_item_button); item_buttons_layout.addWidget(self.remove_item_button); item_buttons_layout.addStretch()
        items_layout.addLayout(item_buttons_layout)
        items_layout.addWidget(self.items_table_view)
        self.main_layout.addWidget(self.items_group)

        # --- گروه اتصال به اسناد (برای تسویه) ---
        self.references_group = QGroupBox("اتصال به اسناد (اختیاری)")
        references_form_layout = QFormLayout(self.references_group)
        self.invoice_combo = QComboBox(self)
        self.po_combo = QComboBox(self)
        references_form_layout.addRow("اتصال به فاکتور:", self.invoice_combo)
        references_form_layout.addRow("اتصال به سفارش خرید:", self.po_combo)
        self.main_layout.addWidget(self.references_group)

        # --- فوتر ---
        footer_layout = QHBoxLayout()
        self.total_payment_label = QLabel("جمع کل: 0")
        self.total_payment_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok); ok_btn.setText("ثبت سند")
        cancel_btn = self.button_box.button(QDialogButtonBox.StandardButton.Cancel); cancel_btn.setText("انصراف")
        footer_layout.addWidget(self.total_payment_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.button_box)
        self.main_layout.addLayout(footer_layout)

    def _connect_signals(self):
        """اتصال سیگنال‌ها به اسلات‌ها."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.payment_context_combo.currentIndexChanged.connect(self._on_payment_context_changed)
        self.person_combo.currentIndexChanged.connect(self._on_person_selected)
        self.add_item_button.clicked.connect(self._add_line_item)
        self.edit_item_button.clicked.connect(self._edit_line_item)
        self.remove_item_button.clicked.connect(self._remove_line_item)
        self.direct_amount_spinbox.valueChanged.connect(self._calculate_and_display_totals)
        
    def _populate_initial_data(self):
        """داده‌های اولیه دیالوگ را پر می‌کند."""
        self.payment_date_edit.setDate(QDate.currentDate())
        self._populate_person_combo()
        if self.is_edit_mode and self.payment_to_edit_header:
            self._load_payment_header_for_editing()
        else:
            self._on_payment_context_changed(0) # فراخوانی برای تنظیم اولیه UI به حالت تسویه


    def _populate_person_combo(self):
        self.person_combo.blockSignals(True)
        self.person_combo.clear()
        self.person_combo.addItem("-- انتخاب شخص --", None)
        try:
            persons = self.person_manager.get_all_persons()
            for p in persons:
                if p.id: self.person_combo.addItem(f"{p.name} ({p.person_type.value})", int(p.id))
        except Exception as e:
            logger.error(f"Error populating person combo: {e}")
        self.person_combo.blockSignals(False)

   
    def _on_payment_context_changed(self, index: int = 0):
        self.is_direct_posting_mode = (index == 1)
        
        self.items_group.setVisible(not self.is_direct_posting_mode)
        self.references_group.setVisible(not self.is_direct_posting_mode)
        self.direct_posting_group.setVisible(self.is_direct_posting_mode)

        if self.is_direct_posting_mode:
            self._populate_direct_posting_combos()
        
        self._on_person_selected()
        self._calculate_and_display_totals()
    def _on_person_selected(self):
        person_id = self.person_combo.currentData()
        self.unpaid_invoices_cache.clear()
        self.open_pos_cache.clear()

        if person_id is None:
            self._update_reference_combos([], [])
            return

        person = self.person_manager.get_person_by_id(person_id)
        if not person: 
            self._update_reference_combos([], [])
            return

        is_receipt = (person.person_type == PersonType.CUSTOMER)
        
        invoices = self.invoice_manager.get_unpaid_invoices_by_person_and_type(
            person_id, InvoiceType.SALE if is_receipt else InvoiceType.PURCHASE
        )
        
        purchase_orders = []
        if person.person_type == PersonType.SUPPLIER:
            purchase_orders = self.po_manager.get_open_purchase_orders_by_supplier(person_id)
            
        self._update_reference_combos(invoices, purchase_orders)
    
    def _update_reference_combos(self, invoices: List[InvoiceEntity], purchase_orders: List[PurchaseOrderEntity]):
        self.invoice_combo.blockSignals(True)
        self.po_combo.blockSignals(True)

        self.invoice_combo.clear(); self.invoice_combo.addItem("-- انتخاب فاکتور --", None)
        if invoices:
            for inv in invoices:
                if inv.id and hasattr(inv, 'remaining_amount'):
                    display = f"ش: {inv.invoice_number} (مانده: {inv.remaining_amount:,.0f})"
                    self.invoice_combo.addItem(display, inv.id)
            self.invoice_combo.setEnabled(self.invoice_combo.count() > 1)
        else:
            self.invoice_combo.setEnabled(False)

        self.po_combo.clear(); self.po_combo.addItem("-- انتخاب سفارش خرید --", None)
        if purchase_orders:
            for po in purchase_orders:
                if po.id and hasattr(po, 'total_amount_expected') and hasattr(po, 'paid_amount'):
                    remaining = po.total_amount_expected - po.paid_amount
                    if remaining > Decimal("0.01"):
                        display = f"ش: {po.order_number} (مانده: {remaining:,.0f})"
                        self.po_combo.addItem(display, po.id)
            self.po_combo.setEnabled(self.po_combo.count() > 1)
        else:
            self.po_combo.setEnabled(False)

        self.invoice_combo.blockSignals(False)
        self.po_combo.blockSignals(False)
    
    def _add_line_item(self):
        person_id = self.person_combo.currentData()
        if person_id is None:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا شخص را انتخاب کنید."); return

        person = self.person_manager.get_person_by_id(person_id)
        if not person: return

        is_receipt = (person.person_type == PersonType.CUSTOMER)
        
        dialog = PaymentLineItemDialog(self.account_manager, self.check_manager, self.person_manager,
                                       parent_dialog_person_id=person_id, parent_dialog_is_receipt=is_receipt, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            line_data = dialog.get_line_item_data()
            if line_data:
                self.line_items_model.add_item(line_data)
                self._calculate_and_display_totals()

    def _edit_line_item(self):
        selected_rows = self.items_table_view.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک قلم را برای ویرایش انتخاب کنید."); return
        
        row_to_edit = selected_rows[0].row()
        item_to_edit_dict = self.line_items_model.get_item_data_at_row(row_to_edit)
        if not item_to_edit_dict: return
        
        person_id = self.person_combo.currentData()
        person = self.person_manager.get_person_by_id(person_id) if person_id else None
        if not person: return

        is_receipt = (person.person_type == PersonType.CUSTOMER)
        
        dialog = PaymentLineItemDialog(self.account_manager, self.check_manager, self.person_manager,
                                       line_data_to_edit=item_to_edit_dict, parent_dialog_person_id=person_id,
                                       parent_dialog_is_receipt=is_receipt, parent=self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            updated_line_data = dialog.get_line_item_data()
            if updated_line_data:
                self.line_items_model.update_item(row_to_edit, updated_line_data)
                self._calculate_and_display_totals()

    def _remove_line_item(self):
        selected_rows = self.items_table_view.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک قلم را برای حذف انتخاب کنید."); return
        
        row_to_remove = selected_rows[0].row()
        if self.line_items_model.remove_item(row_to_remove):
            self._calculate_and_display_totals()

    def _calculate_and_display_totals(self):
        """جمع کل را بر اساس حالت فعلی دیالوگ محاسبه و نمایش می‌دهد."""
        total_amount = Decimal("0.0")
        if self.is_direct_posting_mode:
            total_amount = Decimal(str(self.direct_amount_spinbox.value()))
            self.total_payment_label.setText(f"مبلغ کل: {total_amount:,.0f}")
        else:
            start_value = Decimal("0.0")
            total_amount = sum(
                (Decimal(str(item.get("amount", "0.0"))) for item in self.line_items_model.get_all_items_data()), 
                start_value
            )
            self.total_payment_label.setText(f"جمع کل اقلام: {total_amount:,.0f}")

    def _load_payment_header_for_editing(self):
        if not self.is_edit_mode or not self.payment_to_edit_header: return
        p_header = self.payment_to_edit_header
        
        self.payment_date_edit.setDate(p_header.payment_date)
        self.description_edit.setText(p_header.description or "")
        self.fiscal_year_spinbox.setValue(p_header.fiscal_year_id or 1)

        if p_header.person_id:
            self._try_select_in_combo(self.person_combo, p_header.person_id)
        
        QTimer.singleShot(150, lambda: self._try_select_in_combo(self.invoice_combo, p_header.invoice_id))
        QTimer.singleShot(150, lambda: self._try_select_in_combo(self.po_combo, p_header.purchase_order_id))

        if p_header.line_items:
            line_items_for_model = [
                PaymentLineItemDialog.convert_entity_to_dict_for_dialog(
                    line, self.check_manager, self.account_manager, self.person_manager
                ) for line in p_header.line_items
            ]
            self.line_items_model.update_data(line_items_for_model)
            self._calculate_and_display_totals()
    def _try_select_in_combo(self, combo: QComboBox, data_id: Optional[int]):
        if data_id is None: return
        idx = combo.findData(data_id)
        if idx != -1: combo.setCurrentIndex(idx)

    def get_payment_data(self) -> Optional[Dict[str, Any]]:
        person_id = self.person_combo.currentData()
        if person_id is None and not self.is_direct_posting_mode:
            QMessageBox.warning(self, "خطا", "لطفاً شخص را برای عملیات تسویه انتخاب کنید.")
            return None
        payment_date_val = self.payment_date_edit.date()
        data_to_return: Dict[str, Any] = {
            "payment_date": payment_date_val,
            "person_id": person_id,
            "description": self.description_edit.toPlainText().strip(),
            "fiscal_year_id": self.fiscal_year_spinbox.value(),
            "is_direct_posting": self.is_direct_posting_mode
        }
        
        if self.is_direct_posting_mode:
            target_account_id = self.target_account_combo.currentData()
            if not target_account_id:
                QMessageBox.warning(self, "خطا", "لطفاً حساب هزینه/درآمد را انتخاب کنید.")
                return None
            
            amount = Decimal(str(self.direct_amount_spinbox.value()))
            method = self.direct_payment_method_combo.currentData()
            our_account_id = self.direct_our_account_combo.currentData()
            
            if amount <= 0: QMessageBox.warning(self, "خطا", "مبلغ باید مثبت باشد."); return None
            if not method: QMessageBox.warning(self, "خطا", "روش پرداخت را انتخاب کنید."); return None
            if not our_account_id: QMessageBox.warning(self, "خطا", "حساب پرداخت کننده/دریافت کننده (ما) را انتخاب کنید."); return None

            line_item_direct = {
                "payment_method": method,
                "amount": amount,
                "account_id": our_account_id,
                "target_account_id": target_account_id
            }
            
            data_to_return["line_items_data"] = [line_item_direct]
            data_to_return["total_amount"] = amount
            data_to_return["payment_type"] = PaymentType.PAYMENT if "هزینه" in self.target_account_combo.currentText() else PaymentType.RECEIPT

        else: # حالت تسویه
            line_items = self.line_items_model.get_all_items_data()
            if not line_items:
                QMessageBox.warning(self, "خطا", "حداقل یک قلم پرداخت باید اضافه شود."); return None

            total_amount = sum((Decimal(str(item.get("amount", "0.0"))) for item in line_items), Decimal("0.0"))
            person = self.person_manager.get_person_by_id(person_id)
            payment_type = PaymentType.RECEIPT if person and person.person_type == PersonType.CUSTOMER else PaymentType.PAYMENT
           

            data_to_return.update({
                

                "invoice_id": self.invoice_combo.currentData(),
                "purchase_order_id": self.po_combo.currentData(),
                "total_amount": total_amount,
                "line_items_data": line_items,
                "payment_type": payment_type
            })
        
        if self.is_edit_mode and self.payment_to_edit_header:
            data_to_return['payment_header_id'] = self.payment_to_edit_header.id
        
        return data_to_return
    def _populate_our_accounts_combos(self, combo: QComboBox):
        combo.clear(); combo.addItem("-- انتخاب حساب --", None)
        try:
            asset_accounts = self.account_manager.get_accounts_by_type(AccountType.ASSET)
            cash_bank_accounts = [acc for acc in (asset_accounts or []) if acc.id and any(keyword in acc.name.lower() for keyword in ["بانک", "صندوق", "نقد"])]
            for acc in cash_bank_accounts: combo.addItem(f"{acc.name} (ID: {acc.id})", acc.id)
        except Exception as e: logger.error(f"Error populating our accounts combo: {e}")

    def _populate_direct_posting_combos(self):
        """کمبوباکس‌های بخش ثبت مستقیم را پر می‌کند."""
        self.target_account_combo.clear(); self.target_account_combo.addItem("-- انتخاب حساب --", None)
        try:
            expense_accounts = self.account_manager.get_accounts_by_type(AccountType.EXPENSE)
            revenue_accounts = self.account_manager.get_accounts_by_type(AccountType.REVENUE)
            for acc in (expense_accounts or []): self.target_account_combo.addItem(f"{acc.name} (هزینه)", acc.id)
            for acc in (revenue_accounts or []): self.target_account_combo.addItem(f"{acc.name} (درآمد)", acc.id)
        except Exception as e: logger.error(f"Error populating target accounts: {e}")
        
        self.direct_payment_method_combo.clear()
        for method in [PaymentMethod.CASH, PaymentMethod.CARD, PaymentMethod.BANK_TRANSFER]:
            self.direct_payment_method_combo.addItem(method.value, method)
        
        self._populate_our_accounts_combos(self.direct_our_account_combo)

    
class PaymentViewDialog(QDialog):
    def __init__(self, 
                 payment_header: PaymentHeaderEntity,
                 person_manager: PersonManager,
                 account_manager: AccountManager,
                 check_manager: CheckManager,
                 invoice_manager: InvoiceManager,
                 po_manager: PurchaseOrderManager,
                 parent=None):
        super().__init__(parent)
        self.payment_header = payment_header
        self.person_manager = person_manager
        self.account_manager = account_manager
        self.check_manager = check_manager
        self.invoice_manager = invoice_manager
        self.po_manager = po_manager
        
        self.company_details = {"name": "شرکت نمونه شما", "report_header": "سند پرداخت/دریافت"}

        self.setWindowTitle(f"مشاهده سند - شناسه: {self.payment_header.id}")
        self.setMinimumSize(800, 600)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self._setup_ui()
        self._populate_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        button_layout = QHBoxLayout()
        self.pdf_button = QPushButton("خروجی PDF")
        self.print_button = QPushButton("چاپ")
        button_layout.addWidget(self.pdf_button)
        button_layout.addWidget(self.print_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.display_browser = QTextBrowser(self)
        self.display_browser.setOpenExternalLinks(True)
        main_layout.addWidget(self.display_browser)
        
        self.dialog_button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = self.dialog_button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_button: close_button.setText("بستن")
        main_layout.addWidget(self.dialog_button_box)
        
        self.pdf_button.clicked.connect(self._handle_pdf_export)
        self.print_button.clicked.connect(self._handle_print)
        self.dialog_button_box.rejected.connect(self.reject)

    def _populate_data(self):
        html_content = self._get_payment_html_representation()
        self.display_browser.setHtml(html_content)

    def _get_payment_css_styles(self) -> str:
        # (کد CSS مشابه فاکتور، با کمی تغییرات)
        return """
            body { font-family: 'Tahoma', 'B Nazanin', Arial, sans-serif; direction: rtl; font-size: 10pt; }
            .container { padding: 15px; }
            h2 { text-align: center; color: #333; }
            .header-info { border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; border-radius: 5px; background-color: #f9f9f9; }
            .header-info p { margin: 5px 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }
            th { background-color: #f2f2f2; font-weight: bold; text-align: center; }
            .amount { text-align: right; font-family: Tahoma, sans-serif; }
            .center { text-align: center; }
        """

    def _get_payment_html_representation(self) -> str:
        header = self.payment_header
        
        # --- واکشی اطلاعات تکمیلی ---
        person_name = f"ID: {header.person_id}"
        if header.person_id:
            person = self.person_manager.get_person_by_id(header.person_id)
            if person: person_name = f"{person.name} ({person.person_type.value})"
        
        invoice_num = "-"
        if header.invoice_id and self.invoice_manager:
            inv = self.invoice_manager.get_invoice_with_items(header.invoice_id)
            if inv: invoice_num = inv.invoice_number
        
        po_num = "-"
        if header.purchase_order_id and self.po_manager:
            po = self.po_manager.get_purchase_order_with_items(header.purchase_order_id)
            if po: po_num = po.order_number

        # --- ساخت HTML ---
        css = self._get_payment_css_styles()
        html = f"<html><head><meta charset='UTF-8'><style>{css}</style></head><body><div class='container'>"
        html += f"<h2>{self.company_details.get('report_header', 'سند پرداخت/دریافت')}</h2>"
        html += "<div class='header-info'>"
        html += f"<p><b>شماره سند:</b> {header.id}</p>"
        html += f"<p><b>تاریخ:</b> {header.payment_date.strftime(DATE_FORMAT)}</p>"
        html += f"<p><b>طرف حساب:</b> {person_name}</p>"
        html += f"<p><b>مبلغ کل:</b> {header.total_amount:,.0f} ریال</p>"
        if invoice_num != "-": html += f"<p><b>فاکتور مرتبط:</b> {invoice_num}</p>"
        if po_num != "-": html += f"<p><b>سفارش خرید مرتبط:</b> {po_num}</p>"
        if header.description: html += f"<p><b>توضیحات:</b> {header.description}</p>"
        html += "</div>"
        
        html += "<h3>اقلام</h3><table><thead><tr><th>روش پرداخت</th><th>مبلغ</th><th>حساب/چک</th><th>شرح</th></tr></thead><tbody>"
        if header.line_items:
            for item in header.line_items:
                account_check_display = "-"
                # منطق نمایش جزئیات حساب/چک
                if item.payment_method == PaymentMethod.CHECK and item.check_id and self.check_manager:
                    chk = self.check_manager.get_check_by_id(item.check_id)
                    account_check_display = f"چک ش: {chk.check_number}" if chk else f"چک ID: {item.check_id}"
                elif item.account_id and self.account_manager:
                    acc = self.account_manager.get_account_by_id(item.account_id)
                    account_check_display = acc.name if acc else f"حساب ID: {item.account_id}"
                
                html += f"<tr><td>{item.payment_method.value}</td><td class='amount'>{item.amount:,.0f}</td><td>{account_check_display}</td><td>{item.description or ''}</td></tr>"
        else:
            html += "<tr><td colspan='4' class='center'>اقلامی برای این سند ثبت نشده است.</td></tr>"

        html += "</tbody></table></div></body></html>"
        return html

    def _handle_pdf_export(self):
        if not WEASYPRINT_AVAILABLE:
            QMessageBox.critical(self, "خطا", "کتابخانه WeasyPrint برای خروجی PDF نصب نشده است.")
            return

        default_filename = f"PaymentDoc_{self.payment_header.id}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره سند به PDF", default_filename, "PDF Files (*.pdf)")
        if file_path:
            try:
                html_content = self._get_payment_html_representation()
                HTML(string=html_content).write_pdf(file_path)
                QMessageBox.information(self, "موفقیت", f"سند با موفقیت در فایل PDF ذخیره شد:\n{file_path}")
            except Exception as e:
                logger.error(f"Failed to export payment to PDF: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا در خروجی PDF", f"خطا در ایجاد فایل PDF: {e}")

    def _handle_print(self):
        dialog = QPrintDialog()
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            document = QTextDocument()
            document.setHtml(self._get_payment_html_representation())
            document.print_(dialog.printer())
# ============================================================
#  PaymentsUI (کلاس اصلی تب پرداخت‌ها)
# ============================================================
class PaymentsUI(QWidget):
    def __init__(self,
                 payment_manager: PaymentManager,
                 person_manager: PersonManager,
                 account_manager: AccountManager,
                 invoice_manager: InvoiceManager,
                 po_manager: PurchaseOrderManager,
                 check_manager: CheckManager,
                 parent=None):
        super().__init__(parent)
        self.payment_manager = payment_manager
        self.person_manager = person_manager
        self.account_manager = account_manager
        self.invoice_manager = invoice_manager
        self.po_manager = po_manager
        self.check_manager = check_manager

        self.table_model = PaymentTableModel(person_manager=self.person_manager)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterKeyColumn(-1)  # جستجو در تمام ستون‌ها
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._init_ui()
        self.load_payments_data()
        logger.info("PaymentsUI initialized.")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("جستجو در شماره، شخص، مبلغ و ...")
        self.search_input.textChanged.connect(self.proxy_model.setFilterRegExp)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        self.payment_table_view = QTableView(self)
        self.payment_table_view.setModel(self.proxy_model) # اتصال جدول به پروکسی مدل
        self.payment_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.payment_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.payment_table_view.setSortingEnabled(True)
        self.payment_table_view.setAlternatingRowColors(True)


        header = self.payment_table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        self.payment_table_view.sortByColumn(1, Qt.SortOrder.DescendingOrder) 
        main_layout.addWidget(self.payment_table_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton(" (+) ثبت پرداخت/دریافت جدید")
        self.edit_button = QPushButton("ویرایش سند") 
        self.delete_button = QPushButton("حذف سند")    
        self.view_details_button = QPushButton("مشاهده جزئیات")
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_payment_dialog)
        self.edit_button.clicked.connect(self._open_edit_payment_dialog) 
        self.delete_button.clicked.connect(self._delete_selected_payment) 
        self.view_details_button.clicked.connect(self._open_view_payment_details_dialog)
        self.refresh_button.clicked.connect(self.load_payments_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button) 
        button_layout.addWidget(self.delete_button) 
        button_layout.addWidget(self.view_details_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def load_payments_data(self):
        logger.debug("PaymentsUI: Loading payment headers data...")
        try:
            payment_headers = self.payment_manager.get_all_payments()
            self.table_model.update_data(payment_headers)
            logger.info(f"PaymentsUI: {len(payment_headers)} payment headers loaded.")
        except Exception as e:
            logger.error(f"Error loading payments: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری لیست پرداخت/دریافت‌ها: {e}")

    def _get_selected_payment_header(self) -> Optional[PaymentHeaderEntity]:
        selection_model = self.payment_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک سند را برای عملیات انتخاب کنید.")
            return None
        selected_rows = selection_model.selectedRows()
        if not selected_rows: return None
        
        proxy_index = selected_rows[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        
        return self.table_model.get_payment_header_at_row(source_index.row()) 


    def _call_payment_dialog(self, payment_to_edit: Optional[PaymentHeaderEntity] = None):
        action = "ویرایش" if payment_to_edit else "افزودن"
        logger.debug(f"PaymentsUI: Calling PaymentDialog for {action}.")

        full_payment_to_edit = None
        if payment_to_edit and payment_to_edit.id:
            full_payment_to_edit = self.payment_manager.get_payment_with_line_items(payment_to_edit.id)
            if not full_payment_to_edit:
                QMessageBox.critical(self, "خطا", f"اطلاعات کامل پرداخت/دریافت با شناسه {payment_to_edit.id} یافت نشد.")
                return

        dialog = PaymentDialog(
            payment_manager=self.payment_manager,
            person_manager=self.person_manager,
            account_manager=self.account_manager, 
            invoice_manager=self.invoice_manager,
            po_manager=self.po_manager,
            check_manager=self.check_manager,
            payment_header=full_payment_to_edit,
            parent=self
        )
        
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_payment_data()
            if data:
                try:
                    if dialog.is_edit_mode:
                        if dialog.payment_to_edit_header and dialog.payment_to_edit_header.id:
                            logger.info(f"Attempting to update payment header ID: {dialog.payment_to_edit_header.id}")
                            updated_payment = self.payment_manager.update_payment(payment_header_id=dialog.payment_to_edit_header.id, update_data=data)
                            if updated_payment: QMessageBox.information(self, "موفقیت", "سند با موفقیت ویرایش شد.")
                            else: QMessageBox.warning(self, "عدم تغییر", "ویرایش ناموفق بود.")
                    else: 
                        logger.info(f"Attempting to create new payment with data: {data}")
                        created_payment_header = self.payment_manager.record_payment(**data)
                        if created_payment_header:
                            QMessageBox.information(self, "موفقیت", f"سند با شناسه {created_payment_header.id} با موفقیت ثبت شد.")
                        else:
                            QMessageBox.warning(self, "خطا", "ثبت ناموفق بود.")
                    
                    self.load_payments_data()
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error processing payment from dialog: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطای سیستمی", f"خطا در پردازش: {e}")
    def _open_view_payment_details_dialog(self):
        logger.debug("PaymentsUI: View Payment Details button clicked.")
        selected_header = self._get_selected_payment_header()
        if not selected_header or not selected_header.id:
            return

        full_payment_header = self.payment_manager.get_payment_with_line_items(selected_header.id)
        if not full_payment_header:
            QMessageBox.critical(self, "خطا", f"اطلاعات کامل پرداخت/دریافت با شناسه {selected_header.id} یافت نشد.")
            return
        
        view_dialog = PaymentViewDialog(
            payment_header=full_payment_header,
            person_manager=self.person_manager,
            account_manager=self.account_manager,
            check_manager=self.check_manager,
            invoice_manager=self.invoice_manager,
            po_manager=self.po_manager,
            parent=self
        )
        view_dialog.exec_()                

    def _open_add_payment_dialog(self):
        self._call_payment_dialog(payment_to_edit=None)

    def _open_edit_payment_dialog(self):
        selected_header = self._get_selected_payment_header()
        if not selected_header: return
        self._call_payment_dialog(payment_to_edit=selected_header)

    def _delete_selected_payment(self):
        selected_header = self._get_selected_payment_header()
        if not selected_header or not selected_header.id: return

        reply = QMessageBox.question(self, "تایید حذف", 
                                     f"آیا از حذف سند پرداخت/دریافت با شناسه {selected_header.id} مطمئن هستید؟\nاین عملیات، آثار مالی مرتبط را برمی‌گرداند.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.payment_manager.delete_payment(selected_header.id):
                    QMessageBox.information(self, "موفقیت", f"سند با شناسه {selected_header.id} با موفقیت حذف شد.")
                    self.load_payments_data()
                else:
                    QMessageBox.warning(self, "ناموفق", f"حذف سند با شناسه {selected_header.id} انجام نشد.")
            except Exception as e:
                logger.error(f"Error deleting payment ID {selected_header.id}: {e}", exc_info=True)
                QMessageBox.critical(self, "خطای سیستمی", f"خطا در حذف سند: {e}")
