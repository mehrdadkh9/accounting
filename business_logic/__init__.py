# src/business_logic/__init__.py
from .person_manager import PersonManager
from .account_manager import AccountManager
from .product_manager import ProductManager
from .financial_transaction_manager import FinancialTransactionManager
from .invoice_manager import InvoiceManager
from .payment_manager import PaymentManager
from .check_manager import CheckManager
from .employee_manager import EmployeeManager
from .payroll_manager import PayrollManager
from .purchase_order_manager import PurchaseOrderManager
from .material_receipt_manager import MaterialReceiptManager
from .production_manager import ProductionManager
from .report_manager import ReportManager
from .fiscal_year_manager import FiscalYearManager # <<< اضافه شد

# ALL_MANAGERS = [PersonManager, AccountManager, ProductManager, FinancialTransactionManager, InvoiceManager, PaymentManager, ...]