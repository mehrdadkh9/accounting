# src/data_access/__init__.py

from .database_manager import DatabaseManager
from .base_repository import BaseRepository

from .accounts_repository import AccountsRepository
from .fiscal_years_repository import FiscalYearsRepository
from .settings_repository import SettingsRepository
from .persons_repository import PersonsRepository
from .payment_header_repository import PaymentHeaderRepository # <<< اضافه شد
from .payment_line_item_repository import PaymentLineItemRepository # <<< اضافه شد
from .employees_repository import EmployeesRepository
from .products_repository import ProductsRepository
from .invoices_repository import InvoicesRepository
from .invoice_items_repository import InvoiceItemsRepository
from .financial_transactions_repository import FinancialTransactionsRepository
from .inventory_movements_repository import InventoryMovementsRepository
from .checks_repository import ChecksRepository
from .payrolls_repository import PayrollsRepository
from .loans_repository import LoansRepository
from .loan_installments_repository import LoanInstallmentsRepository
from .bom_repository import BOMsRepository
from .bom_item_repository import BomItemRepository
from .production_orders_repository import ProductionOrdersRepository
from .purchase_orders_repository import PurchaseOrdersRepository
from .purchase_order_items_repository import PurchaseOrderItemsRepository
from .material_receipts_repository import MaterialReceiptsRepository
from .manual_production_repository import ManualProductionRepository # <<< اضافه شد
from .consumed_material_repository import ConsumedMaterialRepository # <<< اضافه شد

# For convenience, you might create a list of all repository classes
# This isn't strictly necessary for operation but can be useful for DI setup later.
ALL_REPOSITORIES = [
    AccountsRepository, FiscalYearsRepository, SettingsRepository, PersonsRepository,
    EmployeesRepository, ProductsRepository, InvoicesRepository, InvoiceItemsRepository,
    FinancialTransactionsRepository, InventoryMovementsRepository,
    ChecksRepository, PayrollsRepository, LoansRepository, LoanInstallmentsRepository,
    BOMsRepository, BomItemRepository, ProductionOrdersRepository, PurchaseOrdersRepository,
    PurchaseOrderItemsRepository, MaterialReceiptsRepository,PaymentHeaderRepository,PaymentLineItemRepository ,ManualProductionRepository, ConsumedMaterialRepository
]