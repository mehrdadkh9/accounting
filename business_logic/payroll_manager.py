# src/business_logic/payroll_manager.py

from typing import Optional, List, Dict, Any
from datetime import date, datetime

from src.business_logic.entities.payroll_entity import PayrollEntity
from src.data_access.payrolls_repository import PayrollsRepository
from src.business_logic.employee_manager import EmployeeManager
from src.business_logic.financial_transaction_manager import FinancialTransactionManager
from src.business_logic.account_manager import AccountManager # To validate payment account
from src.business_logic.entities.financial_transaction_entity import FinancialTransactionEntity

from src.constants import FinancialTransactionType, ReferenceType, AccountType
import logging

logger = logging.getLogger(__name__)

# Placeholder for account IDs from settings
DEFAULT_ACCOUNTS_CONFIG_FOR_PAYROLL = {
    "salary_expense_account": 601,  # مثال: شناسه حساب هزینه حقوق و دستمزد
    "default_payroll_bank_account": 10 # مثال: شناسه حساب بانکی پیش‌فرض برای پرداخت حقوق
}

class PayrollManager:
    def __init__(self,
                 payrolls_repository: PayrollsRepository,
                 employee_manager: EmployeeManager,
                 ft_manager: FinancialTransactionManager,
                 account_manager: AccountManager, # Added for account validation
                 accounts_config: Optional[Dict[str, int]] = None):

        if payrolls_repository is None: raise ValueError("payrolls_repository cannot be None")
        if employee_manager is None: raise ValueError("employee_manager cannot be None")
        if ft_manager is None: raise ValueError("ft_manager cannot be None")
        if account_manager is None: raise ValueError("account_manager cannot be None")

        self.payrolls_repository = payrolls_repository
        self.employee_manager = employee_manager
        self.ft_manager = ft_manager
        self.account_manager = account_manager
        self.accounts_config = accounts_config if accounts_config is not None else DEFAULT_ACCOUNTS_CONFIG_FOR_PAYROLL

    def generate_payroll_for_employee(self,
                                      employee_id: int,
                                      pay_period_start: date,
                                      pay_period_end: date,
                                      gross_salary_override: Optional[float] = None,
                                      deductions: float = 0.0,
                                      description: Optional[str] = "Payroll",
                                      fiscal_year_id: Optional[int] = None) -> Optional[PayrollEntity]:
        """
        Generates a payroll record for an employee for a specific pay period.
        Does NOT process payment; use process_payroll_payment for that.
        """
        if not isinstance(employee_id, int) or employee_id <= 0:
            raise ValueError("شناسه کارمند نامعتبر است.")
        if not isinstance(pay_period_start, date) or not isinstance(pay_period_end, date):
            raise ValueError("دوره پرداخت نامعتبر است.")
        if pay_period_end < pay_period_start:
            raise ValueError("تاریخ پایان دوره پرداخت نمی‌تواند قبل از تاریخ شروع باشد.")
        if deductions < 0:
            raise ValueError("کسورات نمی‌تواند منفی باشد.")

        employee_details = self.employee_manager.get_employee_details_by_employee_id(employee_id)
        if not employee_details:
            raise ValueError(f"کارمندی با شناسه {employee_id} یافت نشد.")
        if not employee_details.get("is_active"):
            logger.warning(f"Generating payroll for inactive employee ID {employee_id}.")
            # Depending on policy, this might be an error or just a warning.

        gross_salary: float
        if gross_salary_override is not None:
            if gross_salary_override < 0: raise ValueError("حقوق ناخالص جایگزین نمی‌تواند منفی باشد.")
            gross_salary = gross_salary_override
        else:
            base_salary = employee_details.get("base_salary")
            if base_salary is None: # Should not happen if employee_details is correctly populated
                raise ValueError(f"حقوق پایه برای کارمند {employee_id} یافت نشد.")
            gross_salary = float(base_salary)

        if gross_salary < deductions:
            raise ValueError("کسورات نمی‌تواند بیشتر از حقوق ناخالص باشد.")
        
        # net_salary is calculated by the entity's @property

        payroll_entity = PayrollEntity(
            employee_id=employee_id,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end,
            gross_salary=gross_salary,
            deductions=deductions,
            # payment_date, paid_by_account_id, transaction_id are set upon payment
            is_paid=False,
            description=description,
            fiscal_year_id=fiscal_year_id
        )

        try:
            created_payroll = self.payrolls_repository.add(payroll_entity)
            logger.info(f"Payroll ID {created_payroll.id} generated for employee ID {employee_id} for period "
                        f"{pay_period_start} to {pay_period_end}. Net Salary: {created_payroll.net_salary:.2f}")
            return created_payroll
        except Exception as e:
            logger.error(f"Error generating payroll for employee ID {employee_id}: {e}", exc_info=True)
            raise

    def process_payroll_payment(self,
                                payroll_id: int,
                                payment_date: date,
                                paid_by_account_id: int,
                                fiscal_year_id_for_ft: Optional[int] = None) -> Optional[PayrollEntity]:
        if not isinstance(payroll_id, int) or payroll_id <= 0: raise ValueError("شناسه لیست حقوق نامعتبر است.")
        if not isinstance(payment_date, date): raise ValueError("تاریخ پرداخت نامعتبر است.")
        if not isinstance(paid_by_account_id, int) or paid_by_account_id <= 0:
            raise ValueError("شناسه حساب پرداخت کننده نامعتبر است.")

        payroll_to_pay = self.payrolls_repository.get_by_id(payroll_id)
        if not payroll_to_pay or not payroll_to_pay.id:
            raise ValueError(f"لیست حقوق با شناسه {payroll_id} یافت نشد.")
        
        if payroll_to_pay.is_paid:
            logger.warning(f"Payroll ID {payroll_id} has already been paid on {payroll_to_pay.payment_date}.")
            return payroll_to_pay 

        payment_bank_account = self.account_manager.get_account_by_id(paid_by_account_id)
        if not payment_bank_account:
            raise ValueError(f"حساب پرداخت کننده با شناسه {paid_by_account_id} یافت نشد.")
        if payment_bank_account.type != AccountType.ASSET:
            raise ValueError(f"حساب پرداخت کننده (ID: {paid_by_account_id}) باید از نوع دارایی (مانند بانک/صندوق) باشد.")

        salary_expense_account_id = self.accounts_config.get("salary_expense_account")
        if not salary_expense_account_id:
            raise ValueError("شناسه حساب هزینه حقوق در تنظیمات یافت نشد.")

        net_salary_to_pay = payroll_to_pay.net_salary
        if net_salary_to_pay <= 0:
            logger.warning(f"Net salary for payroll ID {payroll_id} is zero or negative. No payment processed.")
            return payroll_to_pay

        ft_date = datetime.combine(payment_date, datetime.min.time())
        ft_fiscal_year_id = fiscal_year_id_for_ft if fiscal_year_id_for_ft is not None else payroll_to_pay.fiscal_year_id
        if not ft_fiscal_year_id:
            logger.warning(f"Fiscal year ID for payroll FT (Payroll ID: {payroll_id}) not explicitly set.")

        ft_description = f"Salary payment for Payroll ID {payroll_id}, Employee ID {payroll_to_pay.employee_id}"
        
        # Use a more specific variable name for the first financial transaction leg
        created_ft_expense_leg: Optional[FinancialTransactionEntity] = None
        try:
            created_ft_expense_leg = self.ft_manager.create_financial_transaction(
                transaction_date=ft_date,
                account_id=salary_expense_account_id,
                transaction_type=FinancialTransactionType.EXPENSE,
                amount=net_salary_to_pay,
                description=f"{ft_description} (Dr. Salary Expense)",
                reference_id=payroll_id,
                reference_type=ReferenceType.PAYROLL,
                fiscal_year_id=ft_fiscal_year_id
            )
            # Explicit check for None and then for id
            if created_ft_expense_leg is None:
                 raise Exception("خطا در ایجاد آبجکت تراکنش بدهکار هزینه حقوق.")
            if created_ft_expense_leg.id is None:
                 raise Exception("خطا در دریافت شناسه برای تراکنش بدهکار هزینه حقوق.")

            # Now created_ft_expense_leg is confirmed to be a FinancialTransactionEntity with an id
            valid_ft_expense_leg: FinancialTransactionEntity = created_ft_expense_leg


            created_ft_cash_leg = self.ft_manager.create_financial_transaction(
                transaction_date=ft_date,
                account_id=paid_by_account_id,
                transaction_type=FinancialTransactionType.EXPENSE, 
                amount=net_salary_to_pay,
                description=f"{ft_description} (Cr. Bank/Cash)",
                reference_id=payroll_id,
                reference_type=ReferenceType.PAYROLL,
                fiscal_year_id=ft_fiscal_year_id
            )
            if not created_ft_cash_leg: # Check if cash leg object itself is None
                logger.error(f"Failed to create cash leg object for payroll ID {payroll_id}. Salary expense leg (FT ID: {valid_ft_expense_leg.id}) was successful but needs reversal.")
                self.ft_manager._attempt_reversal(valid_ft_expense_leg) 
                raise Exception("خطا در ایجاد آبجکت تراکنش بستانکار بانک/صندوق. پرداخت کامل نشد.")
            if not created_ft_cash_leg.id: # Check if cash leg object has an ID
                logger.error(f"Failed to get ID for cash leg for payroll ID {payroll_id}. Salary expense leg (FT ID: {valid_ft_expense_leg.id}) was successful but needs reversal.")
                self.ft_manager._attempt_reversal(valid_ft_expense_leg)
                raise Exception("خطا در دریافت شناسه تراکنش بستانکار بانک/صندوق. پرداخت کامل نشد.")


            payroll_to_pay.is_paid = True
            payroll_to_pay.payment_date = payment_date
            payroll_to_pay.paid_by_account_id = paid_by_account_id
            payroll_to_pay.transaction_id = valid_ft_expense_leg.id 

            updated_payroll = self.payrolls_repository.update(payroll_to_pay)
            logger.info(f"Payroll ID {payroll_id} processed for payment. Net: {net_salary_to_pay:.2f}, Paid from AccID: {paid_by_account_id}.")
            return updated_payroll

        except Exception as e:
            logger.error(f"Error processing payroll payment for ID {payroll_id}: {e}", exc_info=True)
            if created_ft_expense_leg and not (locals().get('created_ft_cash_leg') and locals().get('created_ft_cash_leg').id): # type: ignore
                 if hasattr(self.ft_manager, '_attempt_reversal'):
                    logger.warning(f"Attempting reversal for expense leg FT {created_ft_expense_leg} due to payment processing failure.")
                    self.ft_manager._attempt_reversal(created_ft_expense_leg) 
            raise

    def get_payroll_by_id(self, payroll_id: int) -> Optional[PayrollEntity]:
        return self.payrolls_repository.get_by_id(payroll_id)

    def get_payrolls_for_employee(self, employee_id: int, fiscal_year_id: Optional[int] = None) -> List[PayrollEntity]:
        # Assuming repository has a method that can filter by employee_id and optionally fiscal_year_id
        # If not, filter here or add to repository.
        # For now, using a hypothetical extended repository method or filtering:
        if hasattr(self.payrolls_repository, 'get_by_employee_and_fiscal_year'):
            return self.payrolls_repository.get_by_employee_and_fiscal_year(employee_id, fiscal_year_id) # type: ignore
        else: # Basic filter
            payrolls = self.payrolls_repository.get_by_employee_id(employee_id) # type: ignore # Assumes this exists
            if fiscal_year_id:
                payrolls = [p for p in payrolls if p.fiscal_year_id == fiscal_year_id]
            return payrolls


    def get_payrolls_for_period(self, pay_period_start: date, pay_period_end: date, fiscal_year_id: Optional[int] = None) -> List[PayrollEntity]:
        # Assuming repository has get_by_pay_period method
        if hasattr(self.payrolls_repository, 'get_by_pay_period_and_fiscal_year'):
             return self.payrolls_repository.get_by_pay_period_and_fiscal_year(pay_period_start, pay_period_end, fiscal_year_id) # type: ignore
        else:
            payrolls = self.payrolls_repository.get_by_pay_period(pay_period_start, pay_period_end) # type: ignore
            if fiscal_year_id:
                payrolls = [p for p in payrolls if p.fiscal_year_id == fiscal_year_id]
            return payrolls


    def get_unpaid_payrolls(self) -> List[PayrollEntity]:
        return self.payrolls_repository.get_unpaid_payrolls() # Assumes repo has this
        
    def delete_payroll_record(self, payroll_id: int) -> bool:
        """
        Deletes a payroll record.
        WARNING: Only non-paid payrolls should be deleted. If paid, it should be reversed.
        This does not reverse financial transactions.
        """
        payroll_to_delete = self.payrolls_repository.get_by_id(payroll_id)
        if not payroll_to_delete:
            logger.warning(f"Payroll ID {payroll_id} not found for deletion.")
            return False
        
        if payroll_to_delete.is_paid:
            logger.error(f"Cannot delete Payroll ID {payroll_id} as it has been paid. Create a reversal if needed.")
            raise ValueError("لیست حقوق پرداخت شده قابل حذف نیست. لطفاً در صورت نیاز، یک سند برگشتی ایجاد کنید.")

        try:
            self.payrolls_repository.delete(payroll_id)
            logger.info(f"Payroll ID {payroll_id} for employee ID {payroll_to_delete.employee_id} deleted.")
            return True
        except Exception as e:
            logger.error(f"Error deleting Payroll ID {payroll_id}: {e}", exc_info=True)
            return False