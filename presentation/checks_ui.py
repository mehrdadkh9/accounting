# src/presentation/checks_ui.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableView, QPushButton,
                             QHBoxLayout, QMessageBox, QDialog, QLineEdit, QComboBox,
                             QFormLayout, QDialogButtonBox, QAbstractItemView,
                             QDoubleSpinBox, QTextEdit, QHeaderView, QDateEdit, QSpinBox)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QDate, pyqtSignal, QSortFilterProxyModel
from PyQt5.QtGui import QColor
from decimal import InvalidOperation,Decimal
from typing import List, Optional, Any, Dict
from datetime import date
from src.utils import date_converter
from .custom_widgets import ShamsiDateEdit # <<< ویجت جدید تاریخ شمسی
# Import entities, enums, and managers
from src.business_logic.entities.check_entity import CheckEntity
from src.constants import CheckType, CheckStatus, DATE_FORMAT, PersonType, AccountType
# PersonType و AccountType برای نمایش نام در جدول

from src.business_logic.check_manager import CheckManager
from src.business_logic.person_manager import PersonManager
from src.business_logic.account_manager import AccountManager # برای نمایش نام حساب بانکی

import logging
logger = logging.getLogger(__name__)

# --- Table Model for Checks ---
class CheckTableModel(QAbstractTableModel):
    def __init__(self, 
                 data: Optional[List[CheckEntity]] = None, 
                 person_manager: Optional[PersonManager] = None,
                 account_manager: Optional[AccountManager] = None,
                 parent=None):
        super().__init__(parent)
        self._data: List[CheckEntity] = data if data is not None else []
        self._person_manager = person_manager
        self._account_manager = account_manager
        self._headers = ["شناسه", "شماره چک", "مبلغ", "تاریخ صدور", "تاریخ سررسید", 
                         "شخص", "حساب بانکی", "نوع چک", "وضعیت", "توضیحات"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid(): return QVariant()
        row, col = index.row(), index.column()
        if not (0 <= row < len(self._data)): return QVariant()
        
        check = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(check.id)
            elif col == 1: return check.check_number
            elif col == 2: return f"{check.amount:,.2f}"
            elif col == 3: return date_converter.to_shamsi_str(check.issue_date)

            elif col == 4: return date_converter.to_shamsi_str(check.due_date)

            elif col == 5: # Person Name
                if self._person_manager and check.person_id:
                    person = self._person_manager.get_person_by_id(check.person_id)
                    return person.name if person else f"ID: {check.person_id}"
                return str(check.person_id)
            elif col == 6: # Bank Account Name
                if self._account_manager and check.account_id:
                    acc = self._account_manager.get_account_by_id(check.account_id)
                    return acc.name if acc else f"ID: {check.account_id}"
                return str(check.account_id)
            elif col == 7: return check.check_type.value
            elif col == 8: return check.status.value
            elif col == 9: return check.description if check.description is not None else ""
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter # ID
            if col == 2: return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter  # Amount
            if col in [3,4]: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter # Dates
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter # Default for others

        elif role == Qt.ItemDataRole.ForegroundRole:
            if check.status == CheckStatus.BOUNCED:
                return QColor("red")
            elif check.status == CheckStatus.CANCELED:
                return QColor(Qt.GlobalColor.gray)
            elif check.status == CheckStatus.CLEARED or check.status == CheckStatus.CASHED:
                return QColor("green")
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[CheckEntity]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def get_check_at_row(self, row: int) -> Optional[CheckEntity]:
        if 0 <= row < len(self._data): return self._data[row]
        return None

class CheckDialog(QDialog):
    def __init__(self, 
                 person_manager: PersonManager, 
                 account_manager: AccountManager, # For bank account selection
                 check_entity: Optional[CheckEntity] = None, # For editing
                 parent=None):
        super().__init__(parent)
        self.person_manager = person_manager
        self.account_manager = account_manager
        self.check_to_edit = check_entity
        self.is_edit_mode = self.check_to_edit is not None

        title = "افزودن چک جدید"
        if self.is_edit_mode and self.check_to_edit:
            title = f"ویرایش چک شماره: {self.check_to_edit.check_number}"
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QFormLayout(self)

        self.check_number_edit = QLineEdit(self)
        self.amount_spinbox = QDoubleSpinBox(self)
        
        self.person_combo = QComboBox(self) # Drawer or Beneficiary
        self.bank_account_combo = QComboBox(self)
        self.check_type_combo = QComboBox(self)
        self.status_combo = QComboBox(self)
        self.description_edit = QLineEdit(self)
        self.description_edit.setFixedHeight(60)
        self.fiscal_year_id_spinbox = QSpinBox(self)
        # Optional: Fields for invoice_id and purchase_order_id if direct linking is needed from this dialog
        # self.invoice_id_spinbox = QSpinBox(self); self.invoice_id_spinbox.setRange(0, 999999) # 0 for None
        # self.po_id_spinbox = QSpinBox(self); self.po_id_spinbox.setRange(0, 999999) # 0 for None


        # Setup numeric fields
        self.amount_spinbox.setDecimals(2)
        self.amount_spinbox.setMinimum(0.01) # Check amount must be positive
        self.amount_spinbox.setMaximum(9999999999.99)
        self.amount_spinbox.setGroupSeparatorShown(True)
        self.issue_date_edit = ShamsiDateEdit(self)
        self.due_date_edit = ShamsiDateEdit(self)
        
        # Populate combos
        self._populate_person_combo()
        self._populate_account_combo()
        self.check_type_combo.addItems([ct.value for ct in CheckType])

        self.fiscal_year_id_spinbox.setRange(0, 9999) # 0 for None or auto-detect

        if self.is_edit_mode and self.check_to_edit:
            self._load_data_for_editing()
            # --- پایان اصلاح مقداردهی QDateEdit ---
            
            person_idx = self.person_combo.findData(self.check_to_edit.person_id)
            if person_idx != -1: self.person_combo.setCurrentIndex(person_idx)
            
            account_idx = self.bank_account_combo.findData(self.check_to_edit.account_id)
            if account_idx != -1: self.bank_account_combo.setCurrentIndex(account_idx)

            type_idx = self.check_type_combo.findText(self.check_to_edit.check_type.value)
            if type_idx != -1: self.check_type_combo.setCurrentIndex(type_idx)
            
            self.description_edit.setText(self.check_to_edit.description or "")
            self.fiscal_year_id_spinbox.setValue(self.check_to_edit.fiscal_year_id or 0)
            # self.invoice_id_spinbox.setValue(self.check_to_edit.invoice_id or 0)
            # self.po_id_spinbox.setValue(self.check_to_edit.purchase_order_id or 0)
          
            # For editing, some fields might become read-only if status is not PENDING
            if self.check_to_edit.status != CheckStatus.PENDING:
                self.check_number_edit.setReadOnly(True)
                self.amount_spinbox.setReadOnly(True)
                self.person_combo.setEnabled(False)
                self.bank_account_combo.setEnabled(False)
                self.check_type_combo.setEnabled(False)
                # Only description and fiscal_year_id might be editable for processed checks


        layout.addRow("شماره چک:", self.check_number_edit)
        layout.addRow("مبلغ:", self.amount_spinbox)
        layout.addRow("تاریخ صدور:", self.issue_date_edit)
        layout.addRow("تاریخ سررسید:", self.due_date_edit)
        layout.addRow("شخص (گیرنده/دهنده):", self.person_combo)
        layout.addRow("حساب بانکی (ما):", self.bank_account_combo)
        layout.addRow("نوع چک (دریافتی/پرداختی):", self.check_type_combo)
        layout.addRow("شناسه سال مالی:", self.fiscal_year_id_spinbox)
        # layout.addRow("شناسه فاکتور مرتبط:", self.invoice_id_spinbox)
        # layout.addRow("شناسه سفارش خرید مرتبط:", self.po_id_spinbox)
        layout.addRow("توضیحات:", self.description_edit)
        
        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.button_box = QDialogButtonBox(buttons, Qt.Orientation.Horizontal, self) # type: ignore
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button: ok_button.setText("تایید")
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button: cancel_button.setText("انصراف")
        
        layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.setLayout(layout)

    def _populate_person_combo(self):
        self.person_combo.clear()
        try:
            # For checks, person can be anyone (customer, supplier, employee, other)
            persons = self.person_manager.get_all_persons() 
            if not persons:
                self.person_combo.addItem("شخصی یافت نشد", -1)
                return
            for p in persons:
                if p.id is not None:
                    self.person_combo.addItem(f"{p.name} (ID: {p.id}, نوع: {p.person_type.value})", p.id)
        except Exception as e:
            logger.error(f"Error populating persons combo for CheckDialog: {e}", exc_info=True)

    def _populate_account_combo(self):
        self.bank_account_combo.clear()
        try:
            # Bank accounts are typically Asset accounts
            bank_accounts = self.account_manager.get_accounts_by_type(AccountType.ASSET)
            if not bank_accounts:
                self.bank_account_combo.addItem("حساب بانکی (دارایی) یافت نشد", -1)
                return
            for acc in bank_accounts:
                if acc.id is not None:
                    self.bank_account_combo.addItem(f"{acc.name} (ID: {acc.id})", acc.id)
        except Exception as e:
            logger.error(f"Error populating bank accounts combo for CheckDialog: {e}", exc_info=True)


    def get_check_data(self) -> Optional[Dict[str, Any]]:
        if not self.check_number_edit.text().strip():
            QMessageBox.warning(self, "ورودی نامعتبر", "شماره چک نمی‌تواند خالی باشد.")
            return None
        if self.amount_spinbox.value() <= 0:
            QMessageBox.warning(self, "ورودی نامعتبر", "مبلغ چک باید مثبت باشد.")
            return None
        
        person_id_val = self.person_combo.currentData()
        if person_id_val is None or person_id_val == -1:
            QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک شخص انتخاب کنید.")
            return None
            
        account_id_val = self.bank_account_combo.currentData()
        if account_id_val is None or account_id_val == -1:
            QMessageBox.warning(self, "ورودی نامعتبر", "لطفاً یک حساب بانکی انتخاب کنید.")
            return None
            
        selected_check_type_text = self.check_type_combo.currentText()
        check_type_enum = next((ct for ct in CheckType if ct.value == selected_check_type_text), None)
        if not check_type_enum:
            QMessageBox.warning(self, "ورودی نامعتبر", "نوع چک نامعتبر است.")
            return None
        issue_date_val = self.issue_date_edit.date()
        due_date_val = self.due_date_edit.date()
        data_dict = {
            "check_number": self.check_number_edit.text().strip(),
            "amount": self.amount_spinbox.value(),
            "issue_date": issue_date_val,
            "due_date": due_date_val,
            "person_id": person_id_val,
            "account_id": account_id_val,
            "check_type": check_type_enum,
            "description": self.description_edit.toPlainText().strip(),
            "fiscal_year_id": self.fiscal_year_id_spinbox.value() if self.fiscal_year_id_spinbox.value() > 0 else None,
            # "invoice_id": self.invoice_id_spinbox.value() if self.invoice_id_spinbox.value() > 0 else None,
            # "purchase_order_id": self.po_id_spinbox.value() if self.po_id_spinbox.value() > 0 else None,
        }
        if self.is_edit_mode and self.check_to_edit and self.check_to_edit.id:
            data_dict["check_id"] = self.check_to_edit.id # برای ارسال به متد update_check_info
            data_dict["current_status"] = self.check_to_edit.status # ارسال وضعیت فعلی برای اطلاع مدیر
        else: # برای افزودن چک جدید، وضعیت پیش‌فرض در جریان است
            data_dict["status"] = CheckStatus.PENDING
            
        return data_dict
    def _load_data_for_editing(self):
        """
        داده‌های یک چک موجود را برای ویرایش در ویجت‌های دیالوگ بارگذاری می‌کند.
        """
        if not self.is_edit_mode or not self.check_to_edit:
            return

        chk = self.check_to_edit
        logger.debug(f"CheckDialog: Loading data for Check ID: {chk.id} for editing.")

        # ۱. پر کردن فیلدهای متنی و عددی
        self.check_number_edit.setText(chk.check_number or "")
        try:
            # QDoubleSpinBox انتظار float دارد، بنابراین Decimal را تبدیل می‌کنیم
            self.amount_spinbox.setValue(float(chk.amount or 0.0))
        except (TypeError, InvalidOperation):
            self.amount_spinbox.setValue(0.0)
        
        self.description_edit.setText(chk.description or "")

        # ۲. تنظیم تاریخ‌های شمسی با استفاده از ویجت اختصاصی
        # متد setDate آبجکت date استاندارد پایتون را می‌پذیرد
        self.issue_date_edit.setDate(chk.issue_date)
        self.due_date_edit.setDate(chk.due_date)

        # ۳. پیدا کردن و انتخاب آیتم‌های صحیح در کمبوباکس‌ها
        # برای کمبوباکس‌هایی که با ID کار می‌کنند (findData)
        if chk.person_id is not None:
            person_index = self.person_combo.findData(chk.person_id)
            if person_index != -1:
                self.person_combo.setCurrentIndex(person_index)
        
        if chk.account_id is not None:
            account_index = self.bank_account_combo.findData(chk.account_id)
            if account_index != -1:
                self.bank_account_combo.setCurrentIndex(account_index)

        # برای کمبوباکس‌هایی که با مقدار رشته‌ای Enum کار می‌کنند (findText)
        if hasattr(chk, 'check_type') and chk.check_type:
            type_index = self.check_type_combo.findText(chk.check_type.value)
            if type_index != -1:
                self.check_type_combo.setCurrentIndex(type_index)

        if hasattr(chk, 'status') and chk.status:
            status_index = self.status_combo.findText(chk.status.value)
            if status_index != -1:
                self.status_combo.setCurrentIndex(status_index)
# --- Dialog for Updating Check Status ---
class UpdateCheckStatusDialog(QDialog):
    def __init__(self, current_check: CheckEntity, parent=None):
        super().__init__(parent)
        self.current_check = current_check
        self.setWindowTitle(f"تغییر وضعیت چک شماره: {current_check.check_number}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        # --- ایجاد ویجت‌ها ---
        self.status_combo = QComboBox(self)
        self.transaction_date_edit = ShamsiDateEdit(self)
        self.bank_fee_spinbox = QDoubleSpinBox(self)
        self.bank_fee_spinbox.setDecimals(0)
        self.bank_fee_spinbox.setRange(0, 999999999)
        self.bank_fee_spinbox.setGroupSeparatorShown(True)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn: ok_btn.setText("تایید")
        cancel_btn = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn: cancel_btn.setText("انصراف")
        
        # --- چیدمان UI ---
        layout = QFormLayout(self)
        layout.addRow("وضعیت جدید:*", self.status_combo)
        layout.addRow("تاریخ تراکنش:", self.transaction_date_edit)
        layout.addRow("کارمزد بانکی (در صورت وجود):", self.bank_fee_spinbox)
        layout.addWidget(self.button_box)
        
        self._populate_status_combo()
        
        # اتصال سیگنال‌ها
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def _populate_status_combo(self):
        """لیست وضعیت‌های مجاز را بر اساس وضعیت فعلی چک پر می‌کند."""
        self.status_combo.clear()
        # منطق برای نمایش وضعیت‌های مجاز
        # برای مثال، چکی که وصول شده را نمی‌توان دوباره برگشت زد.
        for status in CheckStatus:
            if status != self.current_check.status: # وضعیت فعلی را نشان نده
                self.status_combo.addItem(status.value, status)
    def get_status_update_data(self) -> Optional[Dict[str, Any]]: # <<< FIX: نام متد اصلاح شد
        """داده‌های انتخاب شده در دیالوگ را برمی‌گرداند."""
        new_status = self.status_combo.currentData()
        if not isinstance(new_status, CheckStatus):
            QMessageBox.warning(self, "خطا", "لطفاً یک وضعیت معتبر انتخاب کنید.")
            return None
            
        transaction_date = self.transaction_date_edit.date()
        if not transaction_date:
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ تراکنش را مشخص کنید.")
            return None
        
        return {
            "new_status": new_status,
            "transaction_date": transaction_date,
            "bank_fee": Decimal(str(self.bank_fee_spinbox.value()))
        }

    def get_data(self) -> Optional[Dict[str, Any]]:
        """داده‌های انتخاب شده در دیالوگ را برمی‌گرداند."""
        new_status = self.status_combo.currentData()
        if not isinstance(new_status, CheckStatus):
            QMessageBox.warning(self, "خطا", "لطفاً یک وضعیت معتبر انتخاب کنید.")
            return None
            
        transaction_date = self.transaction_date_edit.date()
        if not transaction_date:
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ تراکنش را مشخص کنید.")
            return None
        
        return {
            "new_status": new_status,
            "transaction_date": transaction_date,
            "bank_fee": Decimal(str(self.bank_fee_spinbox.value()))
        }
# --- Main Checks UI Widget ---
class ChecksUI(QWidget):
    def __init__(self, 
                 check_manager: CheckManager, 
                 person_manager: PersonManager,    # برای پاس دادن به CheckDialog
                 account_manager: AccountManager,  # برای پاس دادن به CheckDialog و CheckTableModel
                 parent=None):
        super().__init__(parent)
        self.check_manager = check_manager
        self.person_manager = person_manager
        self.account_manager = account_manager

        self.table_model = CheckTableModel(
            person_manager=self.person_manager,
            account_manager=self.account_manager
        )
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterKeyColumn(-1)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # فیلترهای اولیه (می‌توان بعداً پیچیده‌تر کرد)
        self.current_status_filter: Optional[CheckStatus] = None
        self.current_type_filter: Optional[CheckType] = None

        self._init_ui()
        self.load_checks_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("جستجو:"))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("جستجو در شماره چک، مبلغ، نام شخص و ...")
        self.search_input.textChanged.connect(self.proxy_model.setFilterRegExp)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        

        # --- Table View ---
        self.checks_table_view = QTableView(self)
        self.checks_table_view.setModel(self.proxy_model) # اتصال جدول به پروکسی مدل
        self.checks_table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.checks_table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.checks_table_view.setSortingEnabled(True)
        self.checks_table_view.setAlternatingRowColors(True)
        main_layout.addWidget(self.checks_table_view)

        header = self.checks_table_view.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            # تنظیم عرض ستون‌های مهم‌تر
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # شماره چک
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch) # شخص
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch) # حساب بانکی
            header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch) # توضیحات
        
        self.checks_table_view.sortByColumn(4, Qt.SortOrder.AscendingOrder) # مرتب‌سازی پیش‌فرض بر اساس تاریخ سررسید
        main_layout.addWidget(self.checks_table_view)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("افزودن چک جدید")
        self.edit_button = QPushButton("ویرایش اطلاعات چک") # ویرایش اطلاعات اولیه، نه وضعیت
        self.update_status_button = QPushButton("تغییر وضعیت چک")
        self.delete_button = QPushButton("حذف/ابطال چک") 
        self.refresh_button = QPushButton("بارگذاری مجدد")

        self.add_button.clicked.connect(self._open_add_check_dialog)
        self.edit_button.clicked.connect(self._open_edit_check_dialog)
        self.update_status_button.clicked.connect(self._open_update_check_status_dialog)
        self.delete_button.clicked.connect(self._delete_or_cancel_selected_check)
        self.refresh_button.clicked.connect(self.load_checks_data)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.update_status_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        logger.info("ChecksUI initialized.")

    def load_checks_data(self):
        logger.debug("Loading checks data...")
        try:
            checks = self.check_manager.get_all_checks()
            self.table_model.update_data(checks)
            logger.info(f"{len(checks)} checks loaded.")
        except Exception as e:
            logger.error(f"Error loading checks: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری لیست چک‌ها: {e}")

    def _get_selected_check(self) -> Optional[CheckEntity]:
        selection_model = self.checks_table_view.selectionModel()
        if not selection_model or not selection_model.hasSelection():
            QMessageBox.information(self, "انتخاب نشده", "لطفاً یک چک را انتخاب کنید.")
            return None
        
        proxy_index = selection_model.selectedRows()[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        
        return self.table_model.get_check_at_row(source_index.row())
    def _open_add_check_dialog(self):
        logger.debug("Opening Add Check dialog.")
        dialog = CheckDialog(
            person_manager=self.person_manager,
            account_manager=self.account_manager,
            parent=self
        )
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_check_data()
            if data:
                try:
                    # status به طور پیش‌فرض توسط دیالوگ در حالت افزودن PENDING تنظیم می‌شود
                    created_check = self.check_manager.record_check(
                        check_number=data["check_number"],
                        amount=data["amount"],
                        issue_date=data["issue_date"],
                        due_date=data["due_date"],
                        person_id=data["person_id"],
                        account_id=data["account_id"],
                        check_type=data["check_type"],
                        status=data.get("status", CheckStatus.PENDING), # اطمینان از وجود وضعیت
                        description=data.get("description"),
                        # invoice_id=data.get("invoice_id"), # این فیلدها فعلا مستقیما از این دیالوگ نمی‌آیند
                        # purchase_order_id=data.get("purchase_order_id"),
                        fiscal_year_id=data.get("fiscal_year_id")
                    )
                    if created_check:
                        QMessageBox.information(self, "موفقیت", f"چک شماره '{created_check.check_number}' با موفقیت ثبت شد.")
                        self.load_checks_data()
                    else:
                        QMessageBox.warning(self, "خطا", "ثبت چک ناموفق بود.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی", str(ve))
                except Exception as e:
                    logger.error(f"Error recording check: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ثبت چک: {e}")

    def _open_edit_check_dialog(self):
        check_to_edit = self._get_selected_check()
        if not check_to_edit:
            return

        logger.debug(f"Opening Edit Check dialog for Check ID: {check_to_edit.id}.")
        dialog = CheckDialog(
            person_manager=self.person_manager,
            account_manager=self.account_manager,
            check_entity=check_to_edit, # ارسال چک موجود برای ویرایش
            parent=self
        )
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            data = dialog.get_check_data()
            if data and check_to_edit.id is not None: # اطمینان از وجود شناسه برای ویرایش
                try:
                    # از متد update_check_info برای ویرایش اطلاعات پایه استفاده می‌کنیم
                    updated_check = self.check_manager.update_check_info(
                        check_id=check_to_edit.id,
                        check_number=data.get("check_number"),
                        amount=data.get("amount"),
                        issue_date=data.get("issue_date"),
                        due_date=data.get("due_date"),
                        person_id=data.get("person_id"),
                        account_id=data.get("account_id"),
                        check_type=data.get("check_type"),
                        description=data.get("description"),
                        # invoice_id=data.get("invoice_id"),
                        # purchase_order_id=data.get("purchase_order_id"),
                        fiscal_year_id=data.get("fiscal_year_id")
                    )
                    if updated_check:
                        QMessageBox.information(self, "موفقیت", f"اطلاعات چک شماره '{updated_check.check_number}' با موفقیت ویرایش شد.")
                        self.load_checks_data()
                    else:
                         QMessageBox.warning(self, "عدم تغییر", "تغییری در اطلاعات چک اعمال نشد یا ویرایش ناموفق بود.")
                except ValueError as ve:
                    QMessageBox.warning(self, "خطای اعتبارسنجی یا ویرایش", str(ve))
                except Exception as e:
                    logger.error(f"Error updating check info: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در ویرایش اطلاعات چک: {e}")
    
    def _open_update_check_status_dialog(self):
        check_to_update = self._get_selected_check()
        if not check_to_update:
            return

        logger.debug(f"Opening Update Check Status dialog for Check ID: {check_to_update.id}, Current Status: {check_to_update.status.value}")
        dialog = UpdateCheckStatusDialog(current_check=check_to_update, parent=self)
        
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            status_data = dialog.get_status_update_data()
            if status_data and check_to_update.id is not None:
                try:
                    updated_check = self.check_manager.update_check_status(
                        check_id=check_to_update.id,
                        new_status=status_data["new_status"],
                        transaction_date_override=status_data.get("transaction_date")
                    )
                    if updated_check:
                        QMessageBox.information(self, "موفقیت", 
                                                f"وضعیت چک شماره '{updated_check.check_number}' با موفقیت به '{updated_check.status.value}' تغییر یافت.")
                        self.load_checks_data()
                        # مهم: ممکن است نیاز به رفرش کردن تب حساب‌ها نیز باشد، اما فعلاً انجام نمی‌شود.
                    else:
                        QMessageBox.warning(self, "ناموفق", "تغییر وضعیت چک انجام نشد.")
                except ValueError as ve:
                     QMessageBox.warning(self, "خطا در تغییر وضعیت", str(ve))
                except Exception as e:
                    logger.error(f"Error updating check status: {e}", exc_info=True)
                    QMessageBox.critical(self, "خطا", f"خطا در تغییر وضعیت چک: {e}")

    def _delete_or_cancel_selected_check(self):
        check_to_action = self._get_selected_check()
        if not check_to_action or check_to_action.id is None:
            return

        action_text = "حذف فیزیکی" if check_to_action.status == CheckStatus.PENDING else "ابطال"
        confirm_message = (f"آیا از {action_text} چک شماره '{check_to_action.check_number}' مطمئن هستید؟\n"
                           f"وضعیت فعلی: {check_to_action.status.value}.")
        if action_text == "ابطال":
            confirm_message += "\nتوجه: ابطال چک، وضعیت آن را به 'باطل شده' تغییر می‌دهد و آثار مالی آن (اگر قبلاً وصول یا خرج شده) برگردانده **نخواهد** شد."
        else: # حذف فیزیکی
            confirm_message += "\nاین عملیات چک را به طور کامل از سیستم حذف می‌کند و قابل بازگشت نیست (فقط برای چک‌های در جریان توصیه می‌شود)."


        reply = QMessageBox.question(self, f"تایید {action_text}", confirm_message,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, # type: ignore
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if check_to_action.status == CheckStatus.PENDING:
                    logger.debug(f"Attempting physical delete for Check ID: {check_to_action.id}")
                    success = self.check_manager.delete_check(check_to_action.id) # type: ignore
                    if success:
                        QMessageBox.information(self, "موفقیت", f"چک شماره '{check_to_action.check_number}' با موفقیت حذف شد.")
                    else:
                        QMessageBox.warning(self, "ناموفق", f"حذف چک شماره '{check_to_action.check_number}' انجام نشد.")
                else: # برای سایر وضعیت‌ها، به "باطل شده" تغییر می‌دهیم
                    logger.debug(f"Attempting to cancel Check ID: {check_to_action.id} by setting status to CANCELED.")
                    updated_check = self.check_manager.update_check_status(
                        check_id=check_to_action.id, # type: ignore
                        new_status=CheckStatus.CANCELED,
                        transaction_date_override=date.today() # یا تاریخ مورد نظر کاربر
                    )
                    if updated_check:
                        QMessageBox.information(self, "موفقیت", f"چک شماره '{updated_check.check_number}' با موفقیت باطل شد.")
                    else:
                        QMessageBox.warning(self, "ناموفق", f"ابطال چک شماره '{check_to_action.check_number}' انجام نشد.")
                
                self.load_checks_data()
            except ValueError as ve:
                 QMessageBox.critical(self, f"خطا در {action_text}", str(ve))
            except Exception as e:
                logger.error(f"Error during check delete/cancel action for ID {check_to_action.id}: {e}", exc_info=True)
                QMessageBox.critical(self, "خطا", f"خطا در انجام عملیات {action_text} چک: {e}")

