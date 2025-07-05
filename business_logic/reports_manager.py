from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import date,datetime
from decimal import Decimal
from datetime import date, timedelta # <<< FIX: وارد کردن timedelta

from .entities.account_entity import AccountEntity
from ..constants import FinancialTransactionType,AccountType,PersonType
from .person_manager import PersonManager

if TYPE_CHECKING:
    from .account_manager import AccountManager
    from .financial_transaction_manager import FinancialTransactionManager
    from .product_manager import ProductManager
    from ..data_access.inventory_movements_repository import InventoryMovementsRepository

import logging
logger = logging.getLogger(__name__)

class ReportsManager:
    """
    Manages the generation of accounting and financial reports.
    """
   
    def __init__(self,
                 account_manager: 'AccountManager',
                 ft_manager: 'FinancialTransactionManager',
                 product_manager: 'ProductManager',
                 person_manager: 'PersonManager', # <<< اضافه شد

                 inventory_movement_repository: 'InventoryMovementsRepository'):
        self.account_manager = account_manager
        self.ft_manager = ft_manager
        self.product_manager = product_manager
        self.inventory_movement_repo = inventory_movement_repository
        self.person_manager = person_manager # <<< اضافه شد

    def get_trial_balance(self, end_date: date) -> List[Dict[str, Any]]:
        """
        Generates the trial balance data up to a specific end date.
        
        Returns:
            A list of dictionaries, where each dictionary represents an account
            with its debit/credit turnover and final balance.
        """
        logger.info(f"Generating Trial Balance for date up to {end_date}...")
        
        all_accounts = self.account_manager.get_all_accounts()
        if not all_accounts:
            return []
            
        all_transactions = self.ft_manager.get_transactions_by_date_range(end_date=end_date)
        
        # A dictionary to hold the turnover for each account
        # key: account_id, value: {"debit": Decimal, "credit": Decimal}
        account_turnovers: Dict[int, Dict[str, Decimal]] = {}

        for trans in all_transactions:
            acc_id = trans.account_id
            if acc_id not in account_turnovers:
                account_turnovers[acc_id] = {"debit": Decimal("0.0"), "credit": Decimal("0.0")}

            # Based on the logic in AccountManager.process_financial_transaction
            # INCOME increases the balance, EXPENSE decreases it.
            # For Asset/Expense accounts: Debit is increase (INCOME), Credit is decrease (EXPENSE)
            # For Liability/Equity/Revenue accounts: Debit is decrease (EXPENSE), Credit is increase (INCOME)

            account = self.account_manager.get_account_by_id(acc_id)
            if not account:
                continue

            # This logic assumes a standard chart of accounts.
            # You might need to adjust this based on your specific account types.
            is_debit_increase = account.type in (AccountType.ASSET, AccountType.EXPENSE)
            
            if trans.transaction_type == FinancialTransactionType.INCOME:
                if is_debit_increase:
                    account_turnovers[acc_id]["debit"] += trans.amount
                else: # Liability, Equity, Revenue
                    account_turnovers[acc_id]["credit"] += trans.amount
            elif trans.transaction_type == FinancialTransactionType.EXPENSE:
                if is_debit_increase:
                    account_turnovers[acc_id]["credit"] += trans.amount
                else: # Liability, Equity, Revenue
                    account_turnovers[acc_id]["debit"] += trans.amount
        
        report_data: List[Dict[str, Any]] = []
        for account in all_accounts:
            turnover = account_turnovers.get(account.id, {"debit": Decimal("0.0"), "credit": Decimal("0.0")})
            debit_turnover = turnover["debit"]
            credit_turnover = turnover["credit"]
            
            balance = debit_turnover - credit_turnover
            
            final_balance_debit = Decimal("0.0")
            final_balance_credit = Decimal("0.0")

            if balance > 0:
                final_balance_debit = balance
            else:
                final_balance_credit = -balance # show as positive number

            report_data.append({
                "account_id": account.id,
                "account_name": account.name,
                "debit_turnover": debit_turnover,
                "credit_turnover": credit_turnover,
                "final_balance_debit": final_balance_debit,
                "final_balance_credit": final_balance_credit,
            })
            
        logger.info(f"Trial Balance report generated with {len(report_data)} accounts.")
        return report_data
    def get_general_journal(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Data for the General Journal report within a date range.
        It resolves account names for display.
        """
        logger.info(f"Generating General Journal from {start_date} to {end_date}...")
        
        transactions = self.ft_manager.get_transactions_by_date_range(start_date=start_date, end_date=end_date)
        
        report_data: List[Dict[str, Any]] = []
        if not transactions:
            return report_data

        # مرتب‌سازی بر اساس تاریخ و سپس شناسه برای اطمینان از ترتیب صحیح
        transactions.sort(key=lambda t: (t.transaction_date, t.id))

        for trans in transactions:
            account = self.account_manager.get_account_by_id(trans.account_id)
            if not account:
                continue

            # بر اساس منطق قبلی، ماهیت حساب را برای تعیین بدهکار/بستانکار مشخص می‌کنیم
            is_debit_increase = account.type in (AccountType.ASSET, AccountType.EXPENSE)
            debit_amount = Decimal("0.0")
            credit_amount = Decimal("0.0")

            if trans.transaction_type == FinancialTransactionType.INCOME:
                if is_debit_increase:
                    debit_amount = trans.amount
                else:
                    credit_amount = trans.amount
            elif trans.transaction_type == FinancialTransactionType.EXPENSE:
                if is_debit_increase:
                    credit_amount = trans.amount
                else:
                    debit_amount = trans.amount
            
            report_data.append({
                "transaction_id": trans.id,
                "transaction_date": trans.transaction_date.date(),
                "account_id": account.id,
                "account_name": account.name,
                "description": trans.description,
                "debit": debit_amount,
                "credit": credit_amount,
                "reference_id": trans.reference_id,
                "reference_type": trans.reference_type.value if trans.reference_type else ""
            })
            
        logger.info(f"General Journal report generated with {len(report_data)} entries.")
        return report_data
    def get_general_ledger(self, account_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Generates the General Ledger for a specific account and date range.
        Calculates a running balance for each transaction.
        """
        logger.info(f"Generating General Ledger for Account ID {account_id} from {start_date} to {end_date}...")
        
        account = self.account_manager.get_account_by_id(account_id)
        if not account:
            logger.error(f"Account with ID {account_id} not found for General Ledger.")
            return []

        # ۱. محاسبه مانده اولیه (مانده از قبل)
        # FIX: واکشی تراکنش‌ها تا "روز قبل" از تاریخ شروع
        day_before_start = start_date - timedelta(days=1)
        transactions_before_start = self.ft_manager.get_transactions_by_date_range(end_date=day_before_start)
        
        opening_balance = Decimal("0.0")
        is_debit_increase = account.type in (AccountType.ASSET, AccountType.EXPENSE)
        
        for trans in transactions_before_start:
            if trans.account_id == account_id:
                 if trans.transaction_type == FinancialTransactionType.INCOME:
                     opening_balance += trans.amount
                 else: # EXPENSE
                     opening_balance -= trans.amount if is_debit_increase else -trans.amount
        
        transactions_in_range = self.ft_manager.get_transactions_by_date_range(start_date=start_date, end_date=end_date)
        
        report_data: List[Dict[str, Any]] = []
        report_data.append({
            "transaction_date": start_date,
            "description": "مانده از قبل",
            "debit": opening_balance if opening_balance > 0 else Decimal("0.0"),
            "credit": -opening_balance if opening_balance < 0 else Decimal("0.0"),
            "balance": opening_balance
        })

        running_balance = opening_balance
        transactions_in_range.sort(key=lambda t: t.transaction_date)

        for trans in transactions_in_range:
            if trans.account_id == account_id:
                debit_amount = Decimal("0.0")
                credit_amount = Decimal("0.0")
                
                if trans.transaction_type == FinancialTransactionType.INCOME:
                    if is_debit_increase:
                        debit_amount = trans.amount
                        running_balance += trans.amount
                    else:
                        credit_amount = trans.amount
                        running_balance -= trans.amount # Credit increases liability/revenue, so balance becomes more negative
                elif trans.transaction_type == FinancialTransactionType.EXPENSE:
                    if is_debit_increase:
                        credit_amount = trans.amount
                        running_balance -= trans.amount
                    else:
                        debit_amount = trans.amount
                        running_balance += trans.amount # Debit decreases liability/revenue
                
                report_data.append({
                    "transaction_date": trans.transaction_date.date(),
                    "description": trans.description,
                    "debit": debit_amount,
                    "credit": credit_amount,
                    "balance": running_balance,
                })
        
        logger.info(f"General Ledger report for Account ID {account_id} generated with {len(report_data)} entries.")
        return report_data

    def get_stock_ledger(self, product_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        کاردکس کالا را برای یک محصول و بازه زمانی مشخص تولید می‌کند.
        """
        logger.info(f"Generating Stock Ledger for Product ID {product_id} from {start_date} to {end_date}...")
        product = self.product_manager.get_product_by_id(product_id)
        opening_stock = product.stock_quantity if product else Decimal("0.0")
        all_movements = self.inventory_movement_repo.find_by_criteria(
        {"product_id": product_id},
        order_by="movement_date ASC, id ASC"
    )
        opening_movements = [
        move for move in all_movements 
        if isinstance(move.movement_date, (date, datetime)) 
        and move.movement_date.date() < start_date
    ]
        opening_stock += sum(
        Decimal(str(move.quantity_change)) for move in opening_movements
    )
        report_data: List[Dict[str, Any]] = [{
            "movement_date": start_date, "description": "موجودی از قبل",
            "qty_in": Decimal("0.0"), "qty_out": Decimal("0.0"), "balance": opening_stock
        }]

        running_balance = opening_stock
        for move in all_movements:
            if start_date <= move.movement_date.date() <= end_date:
                running_balance += move.quantity_change
                report_data.append({
                    "movement_date": move.movement_date.date(),
                    "description": move.description,
                    "qty_in": move.quantity_change if move.quantity_change > 0 else Decimal("0.0"),
                    "qty_out": -move.quantity_change if move.quantity_change < 0 else Decimal("0.0"),
                    "balance": running_balance,
                })
            
        return report_data


    def get_persons_balance_report(self, person_type_filter: PersonType) -> List[Dict[str, Any]]:
        """
        گزارش مانده حساب اشخاص را بر اساس نوع (مشتری/تامین‌کننده) تولید می‌کند.
        """
        logger.info(f"Generating Persons Balance Report for type: {person_type_filter.value}")
        
        persons = self.person_manager.get_persons_by_type(person_type_filter)
        if not persons:
            return []
            
        report_data = []
        for person in persons:
            if not person.id:
                continue
                
            subsidiary_account_id = self.account_manager.get_person_subsidiary_account_id(person.id)
            if not subsidiary_account_id:
                logger.warning(f"No subsidiary account found for Person ID {person.id} ({person.name}). Skipping.")
                continue
                
            account = self.account_manager.get_account_by_id(subsidiary_account_id)
            if not account:
                logger.warning(f"Subsidiary account with ID {subsidiary_account_id} not found for Person ID {person.id}. Skipping.")
                continue
                
            balance = account.balance
            
            # فقط اشخاصی که مانده غیر صفر دارند نمایش داده می‌شوند
            if balance.copy_abs() > Decimal("0.001"):
                report_data.append({
                    "person_id": person.id,
                    "person_name": person.name,
                    "balance": balance
                })
                
        logger.info(f"Generated balance report for {len(report_data)} persons.")
        return report_data

    def get_income_statement_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        داده‌های لازم برای صورت سود و زیان را در یک بازه زمانی مشخص تولید می‌کند.
        """
        logger.info(f"Generating Income Statement from {start_date} to {end_date}...")
        
        all_accounts = self.account_manager.get_all_accounts()
        transactions_in_range = self.ft_manager.get_transactions_by_date_range(start_date, end_date)
        
        report_data: Dict[str, Any] = {
            "revenues": [],
            "total_revenue": Decimal("0.0"),
            "expenses": [],
            "total_expense": Decimal("0.0"),
            "net_income": Decimal("0.0"),
            "start_date": start_date,
            "end_date": end_date
        }
        
        # محاسبه مجموع درآمدها
        revenue_accounts = [acc for acc in all_accounts if acc.type == AccountType.REVENUE]
        for account in revenue_accounts:
            account_turnover = sum(
                (t.amount if t.transaction_type == FinancialTransactionType.INCOME else -t.amount)
                for t in transactions_in_range if t.account_id == account.id
            )
            if account_turnover.copy_abs() > Decimal("0.001"):
                report_data["revenues"].append({"name": account.name, "amount": account_turnover})
                report_data["total_revenue"] += account_turnover
                
        # محاسبه مجموع هزینه‌ها
        expense_accounts = [acc for acc in all_accounts if acc.type == AccountType.EXPENSE]
        for account in expense_accounts:
            account_turnover = sum(
                (t.amount if t.transaction_type == FinancialTransactionType.INCOME else -t.amount)
                for t in transactions_in_range if t.account_id == account.id
            )
            if account_turnover.copy_abs() > Decimal("0.001"):
                report_data["expenses"].append({"name": account.name, "amount": account_turnover})
                report_data["total_expense"] += account_turnover
                
        # محاسبه سود (زیان) خالص
        report_data["net_income"] = report_data["total_revenue"] - report_data["total_expense"]
        
        logger.info(f"Income Statement generated. Net Income: {report_data['net_income']}")
        return report_data
