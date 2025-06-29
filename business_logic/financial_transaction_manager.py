# src/business_logic/financial_transaction_manager.py

from typing import Optional, List, Dict, Any # <<< Add Any
from datetime import date, datetime # <<< Add date and datetime

from src.business_logic.entities.financial_transaction_entity import FinancialTransactionEntity
from src.data_access.financial_transactions_repository import FinancialTransactionsRepository
from src.business_logic.account_manager import AccountManager # Important for updating balances
from src.constants import FinancialTransactionType, ReferenceType
import logging
from decimal import Decimal, InvalidOperation # <<< Add InvalidOperation
logger = logging.getLogger(__name__)

class FinancialTransactionManager:
    def __init__(self, 
                 ft_repository: FinancialTransactionsRepository,
                 account_manager: AccountManager):
        """
        Initializes the FinancialTransactionManager.
        :param ft_repository: An instance of FinancialTransactionsRepository.
        :param account_manager: An instance of AccountManager to process transactions for balance updates.
        """
        if ft_repository is None:
            raise ValueError("ft_repository cannot be None")
        if account_manager is None:
            raise ValueError("account_manager cannot be None")
            
        self.ft_repository = ft_repository
        self.account_manager = account_manager

    def create_financial_transaction(self, 
                                     transaction_date: datetime, 
                                     account_id: int, 
                                     transaction_type: FinancialTransactionType, 
                                     amount: Decimal, # <<< نوع را Any در نظر می‌گیریم تا ورودی‌های مختلف را مدیریت کنیم
                                     description: Optional[str], 
                                     category: Optional[str] = None, 
                                     reference_id: Optional[int] = None, 
                                     reference_type: Optional[ReferenceType] = None,
                                     fiscal_year_id: Optional[int] = None) -> Optional[FinancialTransactionEntity]:
        """
        یک تراکنش مالی جدید ایجاد و ثبت می‌کند و سپس بالانس حساب مربوطه را به‌روز می‌کند.
        مقدار amount باید یک عدد مثبت باشد.
        """
        # --- اعتبارسنجی‌های اولیه برای پارامترهای دیگر ---
        if not isinstance(transaction_date, (datetime, date)):
            logger.error("Transaction date must be a date or datetime object.")
            raise ValueError("تاریخ تراکنش باید معتبر باشد.")
        # اگر فقط date پاس داده شده، آن را به datetime تبدیل می‌کنیم
        transaction_date_dt = transaction_date if isinstance(transaction_date, datetime) else datetime.combine(transaction_date, datetime.min.time())

        if not isinstance(account_id, int) or account_id <= 0:
            logger.error(f"Invalid account_id: {account_id}")
            raise ValueError("شناسه حساب نامعتبر است.")
        if not isinstance(transaction_type, FinancialTransactionType):
            logger.error(f"Invalid transaction_type: {transaction_type}")
            raise ValueError("نوع تراکنش نامعتبر است.")

        # --- شروع اصلاحات در اعتبارسنجی و تبدیل amount ---
        try:
            # ابتدا سعی می‌کنیم amount را به Decimal تبدیل کنیم
            amount_dec = Decimal(str(amount))
        except (InvalidOperation, TypeError):
            logger.error(f"Invalid amount format for financial transaction: '{amount}'")
            raise ValueError("مقدار مبلغ تراکنش باید عددی باشد.")

        # حالا که از Decimal بودن آن مطمئن هستیم، مقدارش را بررسی می‌کنیم
        if amount_dec <= Decimal("0"):
            logger.error(f"Transaction amount must be a positive number, but got: {amount_dec}")
            raise ValueError("مبلغ تراکنش باید یک عدد مثبت باشد.")
        # --- پایان اصلاحات ---

        ft_entity = FinancialTransactionEntity(
            transaction_date=transaction_date_dt,
            account_id=account_id,
            transaction_type=transaction_type,
            amount=amount_dec, # <<< پاس دادن مقدار Decimal
            description=description,
            category=category,
            reference_id=reference_id,
            reference_type=reference_type,
            fiscal_year_id=fiscal_year_id
        )

        try:
            created_ft = self.ft_repository.add(ft_entity)
            if not created_ft or not created_ft.id:
                logger.error(f"Failed to save financial transaction to DB for account {account_id}")
                return None

            logger.info(f"FinancialTransaction ID {created_ft.id} created for account ID {account_id}, amount {created_ft.amount}, type {transaction_type.value}.")
            
            # به‌روزرسانی بالانس حساب
            balance_updated = self.account_manager.process_financial_transaction(created_ft)
            if not balance_updated:
                # این مورد باید با دقت مدیریت شود. آیا باید تراکنش را برگردانیم؟
                logger.warning(f"Account balance may not have been updated for FT ID {created_ft.id}. Review AccountManager logs.")
            
            return created_ft
        except Exception as e:
            logger.error(f"Error creating financial transaction for account {account_id}: {e}", exc_info=True)
            # اگر تراکنش در دیتابیس ایجاد شده اما در ادامه خطا رخ داده، باید Rollback شود
            # این منطق باید در لایه بالاتر یا با استفاده از تراکنش‌های دیتابیس مدیریت شود.
            raise # خطا را دوباره raise کنید تا لایه بالاتر (مثلاً InvoiceManager) آن را مدیریت کند


    def record_transfer(self,
                        transaction_date: datetime,
                        from_account_id: int,
                        to_account_id: int,
                        amount: float,
                        description: Optional[str],
                        category: Optional[str] = "Transfer",
                        reference_id: Optional[int] = None,
                        reference_type: Optional[ReferenceType] = None,
                        fiscal_year_id: Optional[int] = None) -> tuple[Optional[FinancialTransactionEntity], Optional[FinancialTransactionEntity]]:
        """
        Records a transfer between two accounts.
        This creates two financial transactions: one 'EXPENSE' from the source, one 'INCOME' to the destination.
        Returns a tuple of the two created FinancialTransactionEntity objects.
        This entire operation should ideally be atomic (all or nothing).
        """
        if from_account_id == to_account_id:
            raise ValueError("حساب مبدا و مقصد نمی‌توانند یکسان باشند.")
        if amount <= 0:
            raise ValueError("مبلغ انتقال باید مثبت باشد.")

        logger.info(f"Recording transfer of {amount} from AccID {from_account_id} to AccID {to_account_id}.")
        
        # For simplicity, we perform these sequentially.
        # In a production system, this should be a database transaction.
        ft_out = None
        ft_in = None
        
        try:
            # Leg 1: Outflow from source account (treated as an EXPENSE for this account's balance)
            desc_out = f"Transfer to account ID {to_account_id}"
            if description: desc_out = f"{description} (To Acc: {to_account_id})"
            
            ft_out = self.create_financial_transaction(
                transaction_date=transaction_date,
                account_id=from_account_id,
                transaction_type=FinancialTransactionType.EXPENSE, # Or FinancialTransactionType.TRANSFER if AccountManager interprets it as outflow
                amount=amount,
                description=desc_out,
                category=category,
                reference_id=reference_id,
                reference_type=reference_type,
                fiscal_year_id=fiscal_year_id
            )
            if not ft_out: # If first leg fails
                logger.error(f"Failed to create outflow transaction for transfer from {from_account_id}.")
                # No rollback needed for ft_in as it hasn't been created.
                raise Exception("مرحله اول انتقال (خروج از حساب مبدا) ناموفق بود.")

            # Leg 2: Inflow to destination account (treated as an INCOME for this account's balance)
            desc_in = f"Transfer from account ID {from_account_id}"
            if description: desc_in = f"{description} (From Acc: {from_account_id})"
            
            ft_in = self.create_financial_transaction(
                transaction_date=transaction_date,
                account_id=to_account_id,
                transaction_type=FinancialTransactionType.INCOME, # Or FinancialTransactionType.TRANSFER if AccountManager interprets it as inflow
                amount=amount,
                description=desc_in,
                category=category,
                reference_id=reference_id, # Could link ft_out.id as reference too
                reference_type=reference_type,
                fiscal_year_id=fiscal_year_id
            )
            if not ft_in: # If second leg fails
                logger.error(f"Failed to create inflow transaction for transfer to {to_account_id}. First leg (FT ID: {ft_out.id}) was successful but needs reversal.")
                # CRITICAL: Rollback or reverse ft_out here!
                # This is where a true transaction management system is needed.
                # For now, we'll log and raise. Manual correction would be needed.
                # A simple reversal would be to create an opposite FT for from_account_id.
                self._attempt_reversal(ft_out)
                raise Exception("مرحله دوم انتقال (ورود به حساب مقصد) ناموفق بود. انتقال کامل نشد و نیاز به بررسی دستی دارد.")
                
            logger.info(f"Transfer successful: FT_Out_ID={ft_out.id}, FT_In_ID={ft_in.id}")
            return ft_out, ft_in

        except Exception as e:
            logger.error(f"Transfer failed: {e}", exc_info=True)
            # If ft_out was created but ft_in failed, ft_out needs reversal if not handled by _attempt_reversal
            # This simplistic try-except doesn't guarantee atomicity.
            raise # Re-raise the exception


    def _attempt_reversal(self, original_ft: FinancialTransactionEntity):
        """Helper to attempt reversing a transaction. FOR INTERNAL USE AND SIMPLIFICATION."""
        if not original_ft: return
        logger.warning(f"Attempting to reverse FT ID: {original_ft.id} for account {original_ft.account_id}")
        reversal_type = None
        if original_ft.transaction_type == FinancialTransactionType.INCOME:
            reversal_type = FinancialTransactionType.EXPENSE
        elif original_ft.transaction_type == FinancialTransactionType.EXPENSE:
            reversal_type = FinancialTransactionType.INCOME
        
        if reversal_type:
            try:
                self.create_financial_transaction(
                    transaction_date=datetime.now(), # Reversal date
                    account_id=original_ft.account_id,
                    transaction_type=reversal_type,
                    amount=original_ft.amount,
                    description=f"Reversal of FT ID: {original_ft.id} - {original_ft.description}",
                    category="Reversal",
                    fiscal_year_id=original_ft.fiscal_year_id 
                    # reference_id could point to original_ft.id
                )
                logger.info(f"Reversal transaction created for FT ID: {original_ft.id}")
            except Exception as rev_e:
                logger.error(f"CRITICAL: Failed to create reversal for FT ID: {original_ft.id}. Manual correction required. Error: {rev_e}")
        else:
            logger.error(f"Cannot determine reversal type for FT ID: {original_ft.id} with type {original_ft.transaction_type}. Manual correction required.")


    def get_transaction_by_id(self, transaction_id: int) -> Optional[FinancialTransactionEntity]:
        if not isinstance(transaction_id, int) or transaction_id <= 0: return None
        return self.ft_repository.get_by_id(transaction_id)

    def get_transactions_for_account(self, account_id: int, limit: Optional[int] = None) -> List[FinancialTransactionEntity]:
        # Add limit functionality if needed in repository or here
        return self.ft_repository.get_by_account_id(account_id) # Assumes repo method handles ordering

    def get_transactions_by_reference(self, reference_id: int, reference_type: ReferenceType) -> List[FinancialTransactionEntity]:
        """
        تراکنش‌های مرتبط با یک عطف خاص را واکشی می‌کند.
        """
        return self.ft_repository.find_by_criteria({
            "reference_id": reference_id,
            "reference_type": reference_type.value
        })
    def delete_financial_transaction(self, transaction_id: int) -> bool:
        """
        Deletes a financial transaction.
        WARNING: This is a hard delete. In proper accounting, transactions are usually
        reversed with new offsetting entries, not deleted, to maintain audit trails.
        Deleting a transaction will require its effect on account balances to be manually
        or programmatically reversed, which is NOT automatically handled by this simple delete.
        """
        logger.warning(f"Attempting hard delete of FinancialTransaction ID {transaction_id}. "
                       "This does NOT automatically reverse its impact on account balances. "
                       "Reversing entries are preferred for auditability.")
        
        ft_to_delete = self.ft_repository.get_by_id(transaction_id)
        if not ft_to_delete:
            logger.warning(f"FinancialTransaction ID {transaction_id} not found for deletion.")
            return False # Or True if "not found" means "already deleted"

        try:
            self.ft_repository.delete(transaction_id)
            logger.info(f"FinancialTransaction ID {transaction_id} deleted from repository.")
            # CRITICAL: The balance on account ft_to_delete.account_id is now stale.
            # A robust system would require calling account_manager.process_financial_transaction
            # with a transaction that has the *opposite* effect of ft_to_delete before deletion.
            # Or AccountManager needs a reverse_financial_transaction(ft) method.
            # Example of what should happen:
            # self.account_manager.reverse_financial_transaction_effect(ft_to_delete)
            return True
        except Exception as e:
            logger.error(f"Error deleting FinancialTransaction ID {transaction_id}: {e}", exc_info=True)
            return False
        
    def get_transactions_by_date_range(self, 
                                       start_date: Optional[date] = None, 
                                       end_date: Optional[date] = None
                                       ) -> List[FinancialTransactionEntity]:
        """
        تمام تراکنش‌های مالی را در یک بازه زمانی مشخص واکشی می‌کند.
        """
        criteria = {}
        # --- شروع اصلاح ---
        if start_date and end_date:
            criteria['transaction_date'] = ('BETWEEN', (
                start_date.strftime('%Y-%m-%d 00:00:00'), 
                end_date.strftime('%Y-%m-%d 23:59:59')
            ))
        elif start_date:
            criteria['transaction_date'] = ('>=', start_date.strftime('%Y-%m-%d 00:00:00'))
        elif end_date:
            criteria['transaction_date'] = ('<=', end_date.strftime('%Y-%m-%d 23:59:59'))
        # --- پایان اصلاح ---
        
        if not criteria:
            return self.ft_repository.get_all(order_by="transaction_date ASC, id ASC")

        logger.debug(f"Fetching transactions with criteria: {criteria}")
        return self.ft_repository.find_by_criteria(criteria, order_by="transaction_date ASC, id ASC")
