# src/business_logic/report_manager.py

from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta # <<< IMPORT TIMEDELTA ADDED

from src.business_logic.account_manager import AccountManager
from src.data_access.accounts_repository import AccountsRepository
from src.data_access.financial_transactions_repository import FinancialTransactionsRepository
from src.data_access.products_repository import ProductsRepository
from src.data_access.invoices_repository import InvoicesRepository
from src.data_access.invoice_items_repository import InvoiceItemsRepository
from src.data_access.checks_repository import ChecksRepository
from src.data_access.payrolls_repository import PayrollsRepository
from src.data_access.loans_repository import LoansRepository
from src.data_access.loan_installments_repository import LoanInstallmentsRepository
from src.data_access.purchase_orders_repository import PurchaseOrdersRepository
# ... import other repositories as needed for specific reports

from src.constants import AccountType, InvoiceType, DATE_FORMAT, ProductType # <<< ProductType ADDED
import logging

logger = logging.getLogger(__name__)

class ReportManager:
    def __init__(self,
                 account_manager: AccountManager, 
                 accounts_repository: AccountsRepository,
                 ft_repository: FinancialTransactionsRepository,
                 products_repository: ProductsRepository,
                 invoices_repository: InvoicesRepository,
                 invoice_items_repository: InvoiceItemsRepository,
                 checks_repository: ChecksRepository,
                 payrolls_repository: PayrollsRepository, 
                 loans_repository: LoansRepository,
                 loan_installments_repository: LoanInstallmentsRepository,
                 purchase_orders_repository: PurchaseOrdersRepository
                 ):
        self.account_manager = account_manager
        self.accounts_repository = accounts_repository
        self.ft_repository = ft_repository
        self.products_repository = products_repository
        self.invoices_repository = invoices_repository
        self.invoice_items_repository = invoice_items_repository
        self.checks_repository = checks_repository
        self.payrolls_repository = payrolls_repository
        self.loans_repository = loans_repository
        self.loan_installments_repository = loan_installments_repository
        self.purchase_orders_repository = purchase_orders_repository

    def generate_balance_sheet(self, as_of_date: date) -> Dict[str, Any]:
        logger.info(f"Generating Balance Sheet as of {as_of_date.strftime(DATE_FORMAT)}")
        report_data: Dict[str, Any] = {
            "as_of_date": as_of_date.strftime(DATE_FORMAT),
            "assets": [], "total_assets": 0.0,
            "liabilities": [], "total_liabilities": 0.0,
            "equity": [], "total_equity": 0.0,
            "total_liabilities_equity": 0.0
        }

        all_accounts = self.accounts_repository.get_all()
        for acc in all_accounts:
            if acc.id is None: continue

            balance_as_of = self.account_manager.get_account_balance_as_of(acc.id, as_of_date)
            account_info = {"id": acc.id, "name": acc.name, "balance": round(balance_as_of, 2)}

            if acc.type == AccountType.ASSET:
                report_data["assets"].append(account_info)
                report_data["total_assets"] += balance_as_of
            elif acc.type == AccountType.LIABILITY:
                report_data["liabilities"].append(account_info)
                report_data["total_liabilities"] += balance_as_of
            elif acc.type == AccountType.EQUITY:
                report_data["equity"].append(account_info)
                report_data["total_equity"] += balance_as_of
        
        report_data["total_liabilities_equity"] = round(report_data["total_liabilities"] + report_data["total_equity"], 2)
        report_data["total_assets"] = round(report_data["total_assets"], 2)
        if abs(report_data["total_assets"] - report_data["total_liabilities_equity"]) > 0.01:
            logger.warning(f"Balance Sheet out of balance! Assets: {report_data['total_assets']}, L&E: {report_data['total_liabilities_equity']}")
        return report_data

    def generate_income_statement(self, start_date: date, end_date: date) -> Dict[str, Any]:
        logger.info(f"Generating Income Statement from {start_date.strftime(DATE_FORMAT)} to {end_date.strftime(DATE_FORMAT)}")
        report_data: Dict[str, Any] = {
            "period_start": start_date.strftime(DATE_FORMAT),
            "period_end": end_date.strftime(DATE_FORMAT),
            "revenues": [], "total_revenue": 0.0,
            "expenses": [], "total_expense": 0.0,
            "net_income": 0.0
        }
        
        all_accounts = self.accounts_repository.get_all()
        for acc in all_accounts:
            if acc.id is None: continue
            if acc.type not in [AccountType.REVENUE, AccountType.EXPENSE]:
                continue

            # CORRECTED: Use timedelta from datetime module
            balance_at_start_minus_1 = self.account_manager.get_account_balance_as_of(acc.id, start_date - timedelta(days=1))
            balance_at_end = self.account_manager.get_account_balance_as_of(acc.id, end_date)
            period_activity = balance_at_end - balance_at_start_minus_1
            
            account_info = {"id": acc.id, "name": acc.name, "amount": round(period_activity, 2)}

            if acc.type == AccountType.REVENUE:
                report_data["revenues"].append(account_info)
                report_data["total_revenue"] += period_activity
            elif acc.type == AccountType.EXPENSE:
                report_data["expenses"].append(account_info)
                report_data["total_expense"] += period_activity
        
        report_data["net_income"] = round(report_data["total_revenue"] - report_data["total_expense"], 2)
        report_data["total_revenue"] = round(report_data["total_revenue"], 2)
        report_data["total_expense"] = round(report_data["total_expense"], 2)
        return report_data

    def generate_inventory_status_report(self) -> List[Dict[str, Any]]:
        logger.info("Generating Inventory Status Report.")
        products = self.products_repository.get_all()
        report_data = []
        for p in products:
            # CORRECTED: ProductType is now imported
            if p.product_type != ProductType.SERVICE: 
                report_data.append({
                    "product_id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "type": p.product_type.value,
                    "stock_quantity": p.stock_quantity,
                    "unit_price": p.unit_price
                })
        return report_data

    def generate_sales_report(self, 
                              start_date: date, 
                              end_date: date, 
                              customer_id: Optional[int] = None,
                              product_id: Optional[int] = None) -> List[Dict[str, Any]]:
        logger.info(f"Generating Sales Report from {start_date} to {end_date} "
                    f"(CustID: {customer_id}, ProdID: {product_id})")
        
        # CORRECTED: Explicitly type hint criteria
        criteria: Dict[str, Any] = {
            "invoice_type": InvoiceType.SALE.value,
        }
        if customer_id:
            criteria["person_id"] = customer_id # This should now be fine
            
        all_sales_invoices = self.invoices_repository.find_by_criteria(criteria)
        
        report_data = []
        for inv in all_sales_invoices:
            # Ensure inv.invoice_date is a string before strptime, or handle if it's already a date object
            inv_date_obj: date
            if isinstance(inv.invoice_date, str):
                 inv_date_obj = datetime.strptime(inv.invoice_date, DATE_FORMAT).date()
            elif isinstance(inv.invoice_date, date): # If it's already a date object
                 inv_date_obj = inv.invoice_date
            else:
                logger.warning(f"Invoice {inv.invoice_number} has invalid date format: {inv.invoice_date}")
                continue

            if not (start_date <= inv_date_obj <= end_date):
                continue

            if inv.id is None: continue # Should not happen for existing invoices

            items = self.invoice_items_repository.get_by_invoice_id(inv.id)
            for item in items:
                if product_id and item.product_id != product_id:
                    continue
                report_data.append({
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date, # Store original format or inv_date_obj.strftime(DATE_FORMAT)
                    "customer_id": inv.person_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_item_amount": item.total_item_amount
                })
        return report_data