from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import date
from decimal import Decimal
from datetime import date, timedelta # <<< FIX: وارد کردن timedelta

from .entities.account_entity import AccountEntity
from ..constants import FinancialTransactionType,AccountType
from ..data_access.inventory_movements_repository import InventoryMovementsRepository
from .product_manager import ProductManager

if TYPE_CHECKING:
    from .account_manager import AccountManager
    from .financial_transaction_manager import FinancialTransactionManager
   
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
                 inventory_movement_repository: 'InventoryMovementsRepository'):
        self.account_manager = account_manager
        self.ft_manager = ft_manager
        self.product_manager = product_manager
        self.inventory_movement_repo = inventory_movement_repository

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
        این نسخه شامل لاگ‌های دقیق برای دیباگ است.
        """
        logger.info(f"Generating Stock Ledger for Product ID {product_id} from {start_date} to {end_date}...")
        
        product = self.product_manager.get_product_by_id(product_id)
        if not product:
            logger.error(f"Product with ID {product_id} not found for Stock Ledger.")
            return []

        # ۱. واکشی تمام حرکات انبار برای کالای مورد نظر
        all_movements = self.inventory_movement_repo.find_by_criteria(
            {"product_id": product_id}, 
            order_by="movement_date ASC, id ASC"
        )
        
        logger.debug(f"Found {len(all_movements)} total movements for Product ID {product_id}.")

        # ۲. محاسبه موجودی اولیه با پیمایش حرکات قبل از تاریخ شروع
        opening_stock = Decimal("0.0")
        for move in all_movements:
            move_date = move.movement_date.date()
            logger.debug(f"Processing movement ID {move.id} on {move_date} for opening balance. Comparing with start_date {start_date}.")
            if move_date < start_date:
                opening_stock += move.quantity_change
                logger.debug(f"  -> Included in opening balance. New opening balance: {opening_stock}")

        report_data: List[Dict[str, Any]] = []
        
        # افزودن ردیف مانده از قبل
        report_data.append({
            "movement_date": start_date,
            "description": "موجودی از قبل",
            "qty_in": Decimal("0.0"),
            "qty_out": Decimal("0.0"),
            "balance": opening_stock
        })

        # ۳. پردازش حرکات در بازه زمانی انتخاب شده
        running_balance = opening_stock
        for move in all_movements:
            move_date = move.movement_date.date()
            logger.debug(f"Processing movement ID {move.id} on {move_date} for report range. Comparing with start_date {start_date} and end_date {end_date}.")
            if start_date <= move_date <= end_date:
                logger.debug(f"  -> Movement ID {move.id} is WITHIN date range. Appending to report.")
                qty_in = Decimal("0.0")
                qty_out = Decimal("0.0")
                
                if move.quantity_change > 0:
                    qty_in = move.quantity_change
                else:
                    qty_out = -move.quantity_change
                
                running_balance += move.quantity_change
                
                report_data.append({
                    "movement_date": move_date,
                    "description": move.description,
                    "qty_in": qty_in,
                    "qty_out": qty_out,
                    "balance": running_balance
                })
            else:
                logger.debug(f"  -> Movement ID {move.id} is OUTSIDE date range.")
            
        logger.info(f"Stock Ledger report for Product ID {product_id} generated with {len(report_data)} entries.")
        return report_data