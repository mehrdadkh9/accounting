# src/main_app.py
import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import Qt, QLocale
from PyQt5.QtGui import QFont

# --- Configuration and Constants ---
from src.config import DATABASE_PATH, LOG_LEVEL, LOG_FORMAT
from src.constants import DEFAULT_ACCOUNTS_CONFIG_FOR_PAYMENT, DEFAULT_ACCOUNTS_CONFIG_FOR_CHECKS

# --- Data Access Layer (DAL) ---
from src.data_access.database_manager import DatabaseManager
from src.data_access.accounts_repository import AccountsRepository
from src.data_access.persons_repository import PersonsRepository
from src.data_access.products_repository import ProductsRepository
from src.data_access.employees_repository import EmployeesRepository
from src.data_access.fiscal_years_repository import FiscalYearsRepository
from src.data_access.financial_transactions_repository import FinancialTransactionsRepository
from src.data_access.invoices_repository import InvoicesRepository
from src.data_access.invoice_items_repository import InvoiceItemsRepository
from src.data_access.payment_header_repository import PaymentHeaderRepository
from src.data_access.payment_line_item_repository import PaymentLineItemRepository
from src.data_access.checks_repository import ChecksRepository
from src.data_access.purchase_orders_repository import PurchaseOrdersRepository
from src.data_access.purchase_order_items_repository import PurchaseOrderItemsRepository
from src.data_access.material_receipts_repository import MaterialReceiptsRepository
from src.data_access.inventory_movements_repository import InventoryMovementsRepository
from src.data_access.manual_production_repository import ManualProductionRepository 
from src.data_access.consumed_material_repository import ConsumedMaterialRepository
from src.data_access.loans_repository import LoansRepository
from src.data_access.loan_installments_repository import LoanInstallmentsRepository
from src.data_access.payrolls_repository import PayrollsRepository

# --- Business Logic Layer (BLL) ---
from src.business_logic.account_manager import AccountManager
from src.business_logic.person_manager import PersonManager
from src.business_logic.product_manager import ProductManager
from src.business_logic.employee_manager import EmployeeManager
from src.business_logic.fiscal_year_manager import FiscalYearManager
from src.business_logic.financial_transaction_manager import FinancialTransactionManager
from src.business_logic.invoice_manager import InvoiceManager
from src.business_logic.payment_manager import PaymentManager
from src.business_logic.check_manager import CheckManager
from src.business_logic.purchase_order_manager import PurchaseOrderManager
from src.business_logic.material_receipt_manager import MaterialReceiptManager
from src.business_logic.production_manager import ProductionManager
from src.business_logic.loan_manager import LoanManager
from src.business_logic.payroll_manager import PayrollManager

# --- Presentation Layer (UI Tabs) ---
from src.presentation.accounts_ui import AccountsUI
from src.presentation.products_ui import ProductsUI
from src.presentation.persons_ui import PersonsUI
from src.presentation.employees_ui import EmployeesUI
from src.presentation.purchase_orders_ui import PurchaseOrdersUI
from src.presentation.material_receipts_ui import MaterialReceiptsUI
from src.presentation.invoices_ui import InvoicesUI
from src.presentation.checks_ui import ChecksUI
from src.presentation.payments_ui import PaymentsUI
from src.presentation.production_ui import ManualProductionUI
from src.business_logic.reports_manager import ReportsManager
from src.presentation.reports_ui import ReportsUI
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("سیستم حسابداری و مدیریت کارگاهی")
        self.setGeometry(100, 100, 1300, 800)
        
        logger.info("Initializing Database Manager and creating tables...")
        self.db_manager = DatabaseManager(DATABASE_PATH)
        try:
            self.db_manager.create_tables()
            logger.info("Database tables checked/created/seeded successfully.")
        except Exception as e:
            logger.error(f"FATAL: Could not initialize database: {e}", exc_info=True)
            QMessageBox.critical(self, "خطای پایگاه داده", f"امکان ایجاد یا اتصال به پایگاه داده وجود ندارد: {e}")
            sys.exit(1)
        
        self.company_details = {
            "name": "نام شرکت نمونه", 
            "logo_path": None, 
            "app_name": "نرم افزار حسابداری",
            'setting_display_company_name_invoice_header': True,
            'min_item_rows_on_invoice_print': 7,
            "production_accounts_config": {
                # Add your production account IDs here if needed
            }
        }

        logger.info("Initializing Repositories...")
        self.accounts_repo = AccountsRepository(self.db_manager)
        self.persons_repo = PersonsRepository(self.db_manager)
        self.products_repo = ProductsRepository(self.db_manager)
        self.employees_repo = EmployeesRepository(self.db_manager)
        self.fiscal_years_repo = FiscalYearsRepository(self.db_manager)
        self.financial_transactions_repository = FinancialTransactionsRepository(self.db_manager)
        self.invoices_repo = InvoicesRepository(self.db_manager)
        self.invoice_items_repo = InvoiceItemsRepository(self.db_manager)
        self.payment_header_repo = PaymentHeaderRepository(self.db_manager)
        self.payment_line_item_repo = PaymentLineItemRepository(self.db_manager)
        self.checks_repo = ChecksRepository(self.db_manager)
        self.po_repo = PurchaseOrdersRepository(self.db_manager)
        self.po_items_repo = PurchaseOrderItemsRepository(self.db_manager)
        self.receipts_repo = MaterialReceiptsRepository(self.db_manager)
        self.inventory_movements_repo = InventoryMovementsRepository(self.db_manager)
        self.manual_production_repo = ManualProductionRepository(self.db_manager)
        self.consumed_material_repo = ConsumedMaterialRepository(self.db_manager)
        self.loans_repo = LoansRepository(self.db_manager)
        self.loan_installments_repo = LoanInstallmentsRepository(self.db_manager)
        self.payrolls_repo = PayrollsRepository(self.db_manager)
        
        logger.info("Initializing Managers...")
        # --- ترتیب صحیح نمونه‌سازی مدیران ---
        self.person_manager = PersonManager(self.persons_repo)
        self.account_manager = AccountManager(
            accounts_repository=self.accounts_repo, 
           financial_transactions_repository=self.financial_transactions_repository,
            person_manager=self.person_manager
        )
        self.product_manager = ProductManager(product_repository=self.products_repo,inventory_movements_repository=self.inventory_movements_repo)
        self.ft_manager = FinancialTransactionManager(self.financial_transactions_repository, self.account_manager)
        
        self.invoice_manager = InvoiceManager(
            invoices_repository=self.invoices_repo,
            invoice_items_repository=self.invoice_items_repo,
            product_manager=self.product_manager,
            ft_manager=self.ft_manager,
            person_manager=self.person_manager,
            account_manager=self.account_manager
        )
        self.po_manager = PurchaseOrderManager(
            po_repository=self.po_repo,
            po_items_repository=self.po_items_repo,
            person_manager=self.person_manager,
            product_manager=self.product_manager
        )
        self.check_manager = CheckManager(
            checks_repository=self.checks_repo,
            ft_manager=self.ft_manager,
            account_manager=self.account_manager,
            person_manager=self.person_manager,
            invoice_manager=self.invoice_manager,
            accounts_config=DEFAULT_ACCOUNTS_CONFIG_FOR_CHECKS 
        )
        self.payment_manager = PaymentManager(
            payment_header_repository=self.payment_header_repo,
            payment_line_item_repository=self.payment_line_item_repo,
            person_manager=self.person_manager,
            invoice_manager=self.invoice_manager, 
            po_manager=self.po_manager,
            ft_manager=self.ft_manager, 
            check_manager=self.check_manager,
            account_manager=self.account_manager,
            accounts_config=DEFAULT_ACCOUNTS_CONFIG_FOR_PAYMENT 
        )
        self.check_manager.payment_manager = self.payment_manager

        # نمونه‌سازی دو مرحله‌ای برای PaymentManager و CheckManager
       
        
        self.employee_manager = EmployeeManager(self.employees_repo, self.person_manager)
        self.payroll_manager = PayrollManager(
            payrolls_repository=self.payrolls_repo,
            employee_manager=self.employee_manager,
            ft_manager=self.ft_manager,
            account_manager=self.account_manager
        )
        self.loan_manager = LoanManager(
            loans_repository=self.loans_repo,
            loan_installments_repository=self.loan_installments_repo,
            ft_manager=self.ft_manager,
            person_manager=self.person_manager,
            account_manager=self.account_manager
        )
        # FIX: Instantiating the MANAGER, not the repository again
        self.receipt_manager = MaterialReceiptManager(
            receipts_repository=self.receipts_repo,
            product_manager=self.product_manager,
            po_manager=self.po_manager,
            po_items_repository=self.po_items_repo,
            person_manager=self.person_manager
        )
        self.production_manager = ProductionManager( 
            product_manager=self.product_manager,
            manual_production_repository=self.manual_production_repo,
            consumed_material_repository=self.consumed_material_repo,
            ft_manager=self.ft_manager, 
            account_manager=self.account_manager,
            accounts_config=self.company_details.get("production_accounts_config")
        )
        self.reports_manager = ReportsManager(
            account_manager=self.account_manager,
            ft_manager=self.ft_manager,
            product_manager=self.product_manager, # <<< اضافه شد
            inventory_movement_repository=self.inventory_movements_repo # <<< اضافه شد
        )
        self.fiscal_year_manager = FiscalYearManager(self.fiscal_years_repo)

        logger.info("Setting up UI...")
        self._setup_ui()
        logger.info("MainWindow initialized and UI setup complete.")

    def _setup_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # --- افزودن تب‌ها ---
        self.accounts_tab = AccountsUI(self.account_manager, self)
        self.tabs.addTab(self.accounts_tab, "حساب‌ها")
        
        self.products_tab = ProductsUI(self.product_manager, self)
        self.tabs.addTab(self.products_tab, "کالاها/خدمات")
        
        self.persons_tab = PersonsUI(self.person_manager, self)
        self.tabs.addTab(self.persons_tab, "اشخاص")
        
        self.employees_tab = EmployeesUI(self.employee_manager, self)
        self.tabs.addTab(self.employees_tab, "کارمندان")
        
        self.purchase_orders_tab = PurchaseOrdersUI(
            po_manager=self.po_manager, 
            person_manager=self.person_manager, 
            product_manager=self.product_manager, 
            parent=self
        )
        self.tabs.addTab(self.purchase_orders_tab, "سفارشات خرید")
        
        # FIX: Using the correct manager instance
        self.material_receipts_tab = MaterialReceiptsUI(
            receipt_manager=self.receipt_manager, 
            po_manager=self.po_manager, 
            product_manager=self.product_manager, 
            person_manager=self.person_manager, 
            parent=self
        )
        self.tabs.addTab(self.material_receipts_tab, "رسید انبار")
        
        self.invoices_tab = InvoicesUI(
            invoice_manager=self.invoice_manager,
            person_manager=self.person_manager,
            product_manager=self.product_manager,
            payment_manager=self.payment_manager, 
            company_details=self.company_details
        )
        self.tabs.addTab(self.invoices_tab, "فاکتورها")
        
        self.checks_tab = ChecksUI(
            check_manager=self.check_manager, 
            person_manager=self.person_manager, 
            account_manager=self.account_manager, 
            parent=self
        )
        self.tabs.addTab(self.checks_tab, "چک‌ها")
        
        self.payments_tab = PaymentsUI(
            payment_manager=self.payment_manager, 
            person_manager=self.person_manager, 
            account_manager=self.account_manager, 
            invoice_manager=self.invoice_manager, 
            po_manager=self.po_manager, 
            check_manager=self.check_manager, 
            parent=self
        )
        self.tabs.addTab(self.payments_tab, "پرداخت/دریافت")
        
        self.manual_production_tab = ManualProductionUI(
            production_manager=self.production_manager,
            product_manager=self.product_manager,
            parent=self
        )
        self.tabs.addTab(self.manual_production_tab, "ثبت تولید دستی")
        self.reports_tab = ReportsUI(
            reports_manager=self.reports_manager,
            account_manager=self.account_manager,
            product_manager=self.product_manager # <<< اضافه شد
        )
        self.tabs.addTab(self.reports_tab, "گزارشات")
        
        self.setCentralWidget(self.tabs)

def main():
    logger.info("Application starting...")
    app = QApplication(sys.argv)
    english_locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
    QLocale.setDefault(english_locale)
    logger.info(f"Application default locale set to: {QLocale.system().name()}")
    
    main_window = MainWindow()
    main_window.show()
    logger.info("Application started successfully. Main window shown.")
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
