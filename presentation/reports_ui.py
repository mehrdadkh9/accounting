
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableView, QPushButton, QHBoxLayout,
    QMessageBox, QDialog, QFormLayout, QGroupBox, QHeaderView,QTabWidget,QComboBox,QTextBrowser
)
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex
from typing import List, Optional, Any, Dict
from datetime import date
from decimal import Decimal
from PyQt5.QtGui import QFont,QColor # <<< QColor وارد شد

from src.business_logic.reports_manager import ReportsManager
from src.business_logic.account_manager import AccountManager
from src.business_logic.product_manager import ProductManager
from .custom_widgets import ShamsiDateEdit
from src.utils import date_converter
from src.constants import PersonType # <<< Import جدید

import logging
logger = logging.getLogger(__name__)


# ============================================================
#  کلاس ۱: TrialBalanceTableModel
# ============================================================
class TrialBalanceTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = data if data is not None else []
        self._headers = ["کد حساب", "نام حساب", "گردش بدهکار", "گردش بستانکار", "مانده بدهکار", "مانده بستانکار"]
        self.total_row: Dict[str, Decimal] = {}
        self.calculate_totals()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data) + 1 # +1 for the total row

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        row = index.row()
        col = index.column()

        if not index.isValid():
            return QVariant()
        
        # --- Total Row ---
        if row == len(self._data):
            if role == Qt.ItemDataRole.DisplayRole:
                if col == 1: return "جمع کل"
                if col == 2: return f"{self.total_row.get('debit_turnover', 0):,.0f}"
                if col == 3: return f"{self.total_row.get('credit_turnover', 0):,.0f}"
                if col == 4: return f"{self.total_row.get('final_balance_debit', 0):,.0f}"
                if col == 5: return f"{self.total_row.get('final_balance_credit', 0):,.0f}"
            if role == Qt.ItemDataRole.FontRole:
                font = QFont(); font.setBold(True); return font
            if role == Qt.ItemDataRole.BackgroundRole:
                return QColor("#f0f0f0")
            return QVariant()

        # --- Data Rows ---
        item = self._data[row]
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return str(item.get("account_id", ""))
            elif col == 1: return item.get("account_name", "")
            elif col == 2: return f"{item.get('debit_turnover', 0):,.0f}"
            elif col == 3: return f"{item.get('credit_turnover', 0):,.0f}"
            elif col == 4: return f"{item.get('final_balance_debit', 0):,.0f}"
            elif col == 5: return f"{item.get('final_balance_credit', 0):,.0f}"
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.calculate_totals()
        self.endResetModel()

    def calculate_totals(self):
        self.total_row = {
            "debit_turnover": sum(item.get("debit_turnover", Decimal("0")) for item in self._data),
            "credit_turnover": sum(item.get("credit_turnover", Decimal("0")) for item in self._data),
            "final_balance_debit": sum(item.get("final_balance_debit", Decimal("0")) for item in self._data),
            "final_balance_credit": sum(item.get("final_balance_credit", Decimal("0")) for item in self._data),
        }
class TrialBalanceWidget(QWidget):
    def __init__(self, reports_manager: ReportsManager, parent=None):
        super().__init__(parent)
        self.reports_manager = reports_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        options_group = QGroupBox("تنظیمات گزارش تراز آزمایشی")
        options_layout = QFormLayout(options_group)
        
        self.end_date_edit = ShamsiDateEdit(self)
        self.generate_button = QPushButton("تهیه گزارش")
        
        options_layout.addRow("تاریخ تا:", self.end_date_edit)
        options_layout.addRow(self.generate_button)
        layout.addWidget(options_group)
        
        self.trial_balance_table = QTableView(self)
        self.trial_balance_model = TrialBalanceTableModel()
        self.trial_balance_table.setModel(self.trial_balance_model)
        self.trial_balance_table.setSortingEnabled(True)
        layout.addWidget(self.trial_balance_table)
        
        self.generate_button.clicked.connect(self._generate_trial_balance)

    def _generate_trial_balance(self):
        end_date = self.end_date_edit.date()
        if not end_date:
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ را انتخاب کنید.")
            return
            
        try:
            report_data = self.reports_manager.get_trial_balance(end_date=end_date)
            self.trial_balance_model.update_data(report_data)
            logger.info("Trial Balance report displayed successfully.")
        except Exception as e:
            logger.error(f"Error generating trial balance report: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا در گزارش‌گیری", f"خطا در تهیه تراز آزمایشی: {e}")

# ============================================================
#  کلاس جدید: GeneralJournalTableModel
# ============================================================
class GeneralJournalTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = data if data is not None else []
        self._headers = ["تاریخ", "شرح", "نام حساب", "بدهکار", "بستانکار", "عطف"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return QVariant()
        
        item = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return date_converter.to_shamsi_str(item.get("transaction_date"))
            elif col == 1: return item.get("description", "")
            elif col == 2: return item.get("account_name", "")
            elif col == 3:
                debit = item.get("debit", Decimal("0.0"))
                return f"{debit:,.0f}" if debit > 0 else ""
            elif col == 4:
                credit = item.get("credit", Decimal("0.0"))
                return f"{credit:,.0f}" if credit > 0 else ""
            elif col == 5:
                ref_type = item.get("reference_type", "")
                ref_id = item.get("reference_id", "")
                return f"{ref_type} - {ref_id}" if ref_id else ""
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [3, 4]: return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
class PersonsBalanceTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = data if data is not None else []
        self._headers = ["نام شخص", "بدهکار", "بستانکار"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid(): return QVariant()
        item = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            balance = item.get('balance', Decimal('0.0'))
            if col == 0: return item.get("person_name", "")
            elif col == 1: return f"{balance:,.0f}" if balance > 0 else ""
            elif col == 2: return f"{-balance:,.0f}" if balance < 0 else ""
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
# ============================================================
#  ویجت دفتر روزنامه
# ============================================================
class GeneralJournalWidget(QWidget):
    def __init__(self, reports_manager: ReportsManager, parent=None):
        super().__init__(parent)
        self.reports_manager = reports_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        options_group = QGroupBox("فیلتر دفتر روزنامه")
        options_layout = QFormLayout(options_group)
        
        self.start_date_edit = ShamsiDateEdit(self)
        self.end_date_edit = ShamsiDateEdit(self)
        self.generate_button = QPushButton("تهیه گزارش")
        
        options_layout.addRow("از تاریخ:", self.start_date_edit)
        options_layout.addRow("تا تاریخ:", self.end_date_edit)
        options_layout.addRow(self.generate_button)
        layout.addWidget(options_group)
        
        self.journal_table = QTableView(self)
        self.journal_model = GeneralJournalTableModel()
        self.journal_table.setModel(self.journal_model)
        layout.addWidget(self.journal_table)
        
        self.generate_button.clicked.connect(self._generate_journal)

    def _generate_journal(self):
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        if not all([start_date, end_date]):
            QMessageBox.warning(self, "خطا", "لطفاً هر دو تاریخ شروع و پایان را انتخاب کنید.")
            return
            
        try:
            report_data = self.reports_manager.get_general_journal(start_date=start_date, end_date=end_date)
            self.journal_model.update_data(report_data)
            logger.info("General Journal report displayed successfully.")
        except Exception as e:
            logger.error(f"Error generating general journal report: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در تهیه دفتر روزنامه: {e}")
class GeneralLedgerTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = data if data is not None else []
        self._headers = ["تاریخ", "شرح", "بدهکار", "بستانکار", "مانده"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)): return QVariant()
        
        item = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0: return date_converter.to_shamsi_str(item.get("transaction_date"))
            elif col == 1: return item.get("description", "")
            elif col == 2: return f"{item.get('debit', 0):,.0f}" if item.get('debit') else ""
            elif col == 3: return f"{item.get('credit', 0):,.0f}" if item.get('credit') else ""
            elif col == 4:
                balance = item.get('balance', Decimal('0.0'))
                return f"{abs(balance):,.0f} {'بد' if balance >= 0 else 'بس'}"
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers): return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class StockLedgerTableModel(QAbstractTableModel):
    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = data if data is not None else []
        self._headers = ["تاریخ", "شرح", "وارده", "صادره", "مانده"]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return QVariant()
        
        item = self._data[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return date_converter.to_shamsi_str(item.get("movement_date"))
            elif col == 1:
                return item.get("description", "")
            elif col == 2:
                qty_in = item.get("qty_in", Decimal("0.0"))
                return f"{qty_in:.2f}" if qty_in > 0 else ""
            elif col == 3:
                qty_out = item.get("qty_out", Decimal("0.0"))
                return f"{qty_out:.2f}" if qty_out > 0 else ""
            elif col == 4:
                balance = item.get("balance", Decimal("0.0"))
                return f"{balance:.2f}"
        
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in [2, 3, 4]:
                return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            
        return QVariant()

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return QVariant()

    def update_data(self, new_data: List[Dict[str, Any]]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
# ============================================================
#  ویجت جدید: GeneralLedgerWidget
# ============================================================
class GeneralLedgerWidget(QWidget):
    def __init__(self, reports_manager: ReportsManager, account_manager: AccountManager, parent=None):
        super().__init__(parent)
        self.reports_manager = reports_manager
        self.account_manager = account_manager
        self._init_ui()
        self._populate_accounts_combo()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        options_group = QGroupBox("فیلتر دفتر کل")
        options_layout = QFormLayout(options_group)
        
        self.account_combo = QComboBox(self)
        self.start_date_edit = ShamsiDateEdit(self)
        self.end_date_edit = ShamsiDateEdit(self)
        self.generate_button = QPushButton("تهیه گزارش")
        
        options_layout.addRow("انتخاب حساب:", self.account_combo)
        options_layout.addRow("از تاریخ:", self.start_date_edit)
        options_layout.addRow("تا تاریخ:", self.end_date_edit)
        options_layout.addRow(self.generate_button)
        layout.addWidget(options_group)
        
        self.ledger_table = QTableView(self)
        self.ledger_model = GeneralLedgerTableModel()
        self.ledger_table.setModel(self.ledger_model)
        layout.addWidget(self.ledger_table)
        
        self.generate_button.clicked.connect(self._generate_ledger)

    def _populate_accounts_combo(self):
        """کمبوباکس حساب‌ها را با ساختار درختی پر می‌کند."""
        self.account_combo.clear()
        self.account_combo.addItem("-- انتخاب کنید --", None)
        try:
            # --- شروع اصلاح ---
            # استفاده از متد جدید برای دریافت لیست سلسله مراتبی
            accounts = self.account_manager.get_accounts_for_combobox()
            for acc_data in accounts:
                self.account_combo.addItem(acc_data["display_name"], acc_data["id"])
            # --- پایان اصلاح ---
        except Exception as e:
            logger.error(f"Error populating accounts combo for ledger: {e}", exc_info=True)


    def _generate_ledger(self):
        account_id = self.account_combo.currentData()
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        
        if not all([account_id, start_date, end_date]):
            QMessageBox.warning(self, "خطا", "لطفاً حساب، تاریخ شروع و تاریخ پایان را انتخاب کنید.")
            return
            
        try:
            report_data = self.reports_manager.get_general_ledger(account_id, start_date, end_date)
            self.ledger_model.update_data(report_data)
            logger.info("General Ledger report displayed successfully.")
        except Exception as e:
            logger.error(f"Error generating general ledger report: {e}", exc_info=True)
            QMessageBox.critical(self, "خطا", f"خطا در تهیه دفتر کل: {e}")
class StockLedgerWidget(QWidget):
    def __init__(self, reports_manager: ReportsManager, product_manager: ProductManager, parent=None):
        super().__init__(parent)
        self.reports_manager = reports_manager
        self.product_manager = product_manager
        self._init_ui()
        self._populate_products_combo()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        options_group = QGroupBox("فیلتر کاردکس کالا")
        options_layout = QFormLayout(options_group)
        
        self.product_combo = QComboBox(self)
        self.start_date_edit = ShamsiDateEdit(self)
        self.end_date_edit = ShamsiDateEdit(self)
        self.generate_button = QPushButton("تهیه گزارش")
        
        options_layout.addRow("انتخاب کالا:", self.product_combo)
        options_layout.addRow("از تاریخ:", self.start_date_edit)
        options_layout.addRow("تا تاریخ:", self.end_date_edit)
        options_layout.addRow(self.generate_button)
        layout.addWidget(options_group)
        
        self.ledger_table = QTableView(self)
        self.ledger_model = StockLedgerTableModel()
        self.ledger_table.setModel(self.ledger_model)
        layout.addWidget(self.ledger_table)
        
        self.generate_button.clicked.connect(self._generate_ledger)

    def _populate_products_combo(self):
        try:
            products = self.product_manager.get_all_products(active_only=False)
            self.product_combo.addItem("-- انتخاب کنید --", None)
            for p in products:
                self.product_combo.addItem(p.name, p.id)
        except Exception as e:
            logger.error(f"Error populating products combo for stock ledger: {e}")

    def _generate_ledger(self):
        product_id = self.product_combo.currentData()
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        
        if not all([product_id, start_date, end_date]):
            QMessageBox.warning(self, "خطا", "لطفاً کالا، تاریخ شروع و تاریخ پایان را انتخاب کنید.")
            return
            
        try:
            report_data = self.reports_manager.get_stock_ledger(product_id, start_date, end_date)
            self.ledger_model.update_data(report_data)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تهیه کاردکس کالا: {e}")
class PersonsBalanceWidget(QWidget):
    def __init__(self, reports_manager: ReportsManager, parent=None):
        super().__init__(parent)
        self.reports_manager = reports_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        options_group = QGroupBox("فیلتر گزارش مانده حساب")
        options_layout = QFormLayout(options_group)
        
        self.person_type_combo = QComboBox(self)
        self.person_type_combo.addItem("بدهکاران (مشتریان)", PersonType.CUSTOMER)
        self.person_type_combo.addItem("بستانکاران (تامین کنندگان)", PersonType.SUPPLIER)
        
        self.generate_button = QPushButton("تهیه گزارش")
        
        options_layout.addRow("نمایش:", self.person_type_combo)
        options_layout.addRow(self.generate_button)
        layout.addWidget(options_group)
        
        self.table = QTableView(self)
        self.model = PersonsBalanceTableModel()
        self.table.setModel(self.model)
        layout.addWidget(self.table)
        
        self.generate_button.clicked.connect(self._generate_report)

    def _generate_report(self):
        person_type = self.person_type_combo.currentData()
        try:
            report_data = self.reports_manager.get_persons_balance_report(person_type)
            self.model.update_data(report_data)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تهیه گزارش مانده حساب‌ها: {e}")
class IncomeStatementWidget(QWidget):
    def __init__(self, reports_manager: ReportsManager, parent=None):
        super().__init__(parent)
        self.reports_manager = reports_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        options_group = QGroupBox("فیلتر صورت سود و زیان")
        options_layout = QFormLayout(options_group)
        
        self.start_date_edit = ShamsiDateEdit(self)
        self.end_date_edit = ShamsiDateEdit(self)
        self.generate_button = QPushButton("تهیه گزارش")
        
        options_layout.addRow("از تاریخ:", self.start_date_edit)
        options_layout.addRow("تا تاریخ:", self.end_date_edit)
        options_layout.addRow(self.generate_button)
        layout.addWidget(options_group)
        
        self.report_display = QTextBrowser(self)
        self.report_display.document().setDefaultStyleSheet("body { font-family: 'Tahoma'; }")
        layout.addWidget(self.report_display)
        
        self.generate_button.clicked.connect(self._generate_report)

    def _generate_report(self):
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        
        if not all([start_date, end_date]):
            QMessageBox.warning(self, "خطا", "لطفاً هر دو تاریخ شروع و پایان را انتخاب کنید.")
            return
            
        try:
            report_data = self.reports_manager.get_income_statement_data(start_date, end_date)
            html_content = self._format_report_as_html(report_data)
            self.report_display.setHtml(html_content)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تهیه صورت سود و زیان: {e}")

    def _format_report_as_html(self, data: Dict[str, Any]) -> str:
        start_shamsi = date_converter.to_shamsi_str(data['start_date'])
        end_shamsi = date_converter.to_shamsi_str(data['end_date'])
        
        html = f"""
        <html><head><style>
            body {{ direction: rtl; padding: 15px; }}
            h1, h2 {{ text-align: center; color: #2c3e50; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
            th, td {{ padding: 8px 12px; border: 1px solid #ddd; }}
            .header-row {{ background-color: #f2f2f2; font-weight: bold; }}
            .total-row td {{ background-color: #ecf0f1; font-weight: bold; border-top: 2px solid #bdc3c7; }}
            .amount {{ text-align: left; padding-left: 20px; font-family: monospace; }}
            .section-title {{ font-size: 18px; font-weight: bold; color: #34495e; margin-top: 25px; border-bottom: 2px solid #34495e; padding-bottom: 5px;}}
        </style></head><body>
            <h1>صورت سود و زیان</h1>
            <h2>برای دوره از {start_shamsi} تا {end_shamsi}</h2>
            <p class="section-title">درآمدها</p><table>
        """
        
        if data['revenues']:
            for item in data['revenues']:
                html += f"<tr><td>{item['name']}</td><td class='amount'>{item['amount']:,.0f}</td></tr>"
        else:
            html += "<tr><td colspan='2'>هیچ درآمدی در این دوره ثبت نشده است.</td></tr>"
            
        html += f"<tr class='total-row'><td>جمع کل درآمدها</td><td class='amount'>{data['total_revenue']:,.0f}</td></tr></table>"
        html += f'<p class="section-title">هزینه‌ها</p><table>'
        
        if data['expenses']:
            for item in data['expenses']:
                html += f"<tr><td>{item['name']}</td><td class='amount'>{item['amount']:,.0f}</td></tr>"
        else:
            html += "<tr><td colspan='2'>هیچ هزینه‌ای در این دوره ثبت نشده است.</td></tr>"
            
        html += f"<tr class='total-row'><td>جمع کل هزینه‌ها</td><td class='amount'>{data['total_expense']:,.0f}</td></tr></table>"
        
        net_income = data['net_income']
        income_label = "سود خالص" if net_income >= 0 else "زیان خالص"
        income_color = "#2ecc71" if net_income >= 0 else "#e74c3c"
        
        html += f"""
            <br>
            <table style="font-size: 16px;">
                <tr style='background-color: {income_color}; color: white; font-weight: bold;'>
                    <td>{income_label}</td>
                    <td class='amount'>{abs(net_income):,.0f}</td>
                </tr>
            </table></body></html>
        """
        return html

# ============================================================
#  کلاس اصلی: ReportsUI
# ============================================================
class ReportsUI(QWidget):
    def __init__(self, reports_manager: ReportsManager, account_manager: AccountManager, product_manager: ProductManager, parent=None):
        super().__init__(parent)
        self.reports_manager = reports_manager
        self.account_manager = account_manager
        self.product_manager = product_manager
        self._init_ui()
        
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.report_tabs = QTabWidget()
        main_layout.addWidget(self.report_tabs)

        self.trial_balance_widget = TrialBalanceWidget(self.reports_manager)
        self.report_tabs.addTab(self.trial_balance_widget, "تراز آزمایشی")
        
        self.general_journal_widget = GeneralJournalWidget(self.reports_manager)
        self.report_tabs.addTab(self.general_journal_widget, "دفتر روزنامه")
        
        self.general_ledger_widget = GeneralLedgerWidget(self.reports_manager, self.account_manager)
        self.report_tabs.addTab(self.general_ledger_widget, "دفتر کل")

        self.stock_ledger_widget = StockLedgerWidget(self.reports_manager, self.product_manager)
        self.report_tabs.addTab(self.stock_ledger_widget, "کاردکس کالا")

        self.persons_balance_widget = PersonsBalanceWidget(self.reports_manager)
        self.report_tabs.addTab(self.persons_balance_widget, "مانده حساب اشخاص")
        self.income_statement_widget = IncomeStatementWidget(self.reports_manager)
        self.report_tabs.addTab(self.income_statement_widget, "صورت سود و زیان")
