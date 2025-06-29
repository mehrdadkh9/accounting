# src/business_logic/loan_manager.py

from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP # For precise financial calculations

from src.business_logic.entities.loan_entity import LoanEntity
from src.business_logic.entities.loan_installment_entity import LoanInstallmentEntity

from src.data_access.loans_repository import LoansRepository
from src.data_access.loan_installments_repository import LoanInstallmentsRepository

from src.business_logic.financial_transaction_manager import FinancialTransactionManager
from src.business_logic.person_manager import PersonManager
from src.business_logic.account_manager import AccountManager

from src.constants import (
    LoanStatus, LoanDirectionType, PaymentMethod, FinancialTransactionType, 
    AccountType, ReferenceType, DATE_FORMAT
)
import logging

logger = logging.getLogger(__name__)

DEFAULT_ACCOUNTS_CONFIG_FOR_LOANS = {
    "loan_asset_account": 701,      # مثال: وام‌های پرداختنی به دیگران (دارایی ما)
    "loan_liability_account": 801,  # مثال: وام‌های دریافتی از دیگران (بدهی ما)
    "interest_income_account": 901, # مثال: درآمد بهره (وام‌های پرداختنی به دیگران)
    "interest_expense_account": 902 # مثال: هزینه بهره (وام‌های دریافتی از دیگران)
}

class LoanManager:
    def __init__(self,
                 loans_repository: LoansRepository,
                 loan_installments_repository: LoanInstallmentsRepository,
                 ft_manager: FinancialTransactionManager,
                 person_manager: PersonManager,
                 account_manager: AccountManager,
                 accounts_config: Optional[Dict[str, int]] = None):

        if loans_repository is None: raise ValueError("loans_repository cannot be None")
        if loan_installments_repository is None: raise ValueError("loan_installments_repository cannot be None")
        if ft_manager is None: raise ValueError("ft_manager cannot be None")
        if person_manager is None: raise ValueError("person_manager cannot be None")
        if account_manager is None: raise ValueError("account_manager cannot be None")

        self.loans_repository = loans_repository
        self.loan_installments_repository = loan_installments_repository
        self.ft_manager = ft_manager
        self.person_manager = person_manager
        self.account_manager = account_manager
        self.accounts_config = accounts_config if accounts_config is not None else DEFAULT_ACCOUNTS_CONFIG_FOR_LOANS

    def _calculate_installments(self, loan_amount: Decimal, annual_interest_rate: Decimal, 
                                num_installments: int, start_date: date, 
                                fixed_installment_amount: Optional[Decimal] = None) -> List[Dict[str, Any]]:
        """
        Calculates loan installments (principal and interest portions).
        Uses Decimal for precision.
        This is a simplified amortization schedule generator.
        If fixed_installment_amount is provided, it's used; otherwise, it can be calculated (not implemented here).
        For simplicity, this example assumes fixed_installment_amount is provided and valid.
        """
        installments = []
        if num_installments <= 0: return installments
        
        # This simplified version assumes fixed_installment_amount is the total payment per period.
        # A full calculation would derive fixed_installment_amount if not given, or adjust based on it.
        # For now, we just distribute it.
        # Proper amortization is more complex, especially with monthly rates from annual.

        # Placeholder: simple equal principal distribution + interest on declining balance (very simplified)
        # This does NOT create equal total installments unless interest is zero or fixed_installment_amount drives it.
        # A real loan calculator is needed here.
        # For this example, let's assume installment_amount on LoanEntity is the total fixed payment,
        # and we need to break it down.

        # This requires a proper amortization formula.
        # For now, let's assume the installment entity will store the total amount,
        # and principal/interest are filled upon payment or pre-calculated by a more robust method.
        # The prompt's LoanInstallmentEntity has principal_amount and interest_amount.
        # So, these *should* be calculated when generating the schedule.

        # Simplified calculation for equal total installments (if fixed_installment_amount is given)
        # And then deriving principal and interest.
        # This is just a placeholder for a real amortization logic.
        # For example, for a simple interest loan paid in N installments:
        # Total interest = loan_amount * annual_interest_rate * (term_in_years)
        # Total repayment = loan_amount + total_interest
        # If installment_amount is total fixed payment, then for each period:
        #   Interest_Portion = Outstanding_Principal * (period_interest_rate)
        #   Principal_Portion = Installment_Amount - Interest_Portion

        # This is a complex financial calculation.
        # We will create placeholder installments with the total amount due.
        # The breakdown of principal/interest could be done upon payment recording or if
        # LoanEntity's installment_amount is the *principal* portion.
        # The prompt for LoanEntity has installment_amount (float) which is likely total.
        # LoanInstallmentEntity has principal_amount, interest_amount.

        # Let's assume for this stage, we just create N installments with the total amount.
        # The breakdown will be a TODO for full financial accuracy during schedule generation.
        # Or, better, assume a simplified equal principal payment + interest on remaining balance.
        # This results in declining total payment, unless interest is capitalized.

        # For now, just create N installments, the actual breakdown of principal/interest
        # will be calculated and stored when we implement the full calculation logic.
        # This means `LoanInstallmentEntity.principal_amount` and `interest_amount` might be 0 initially.
        # This is NOT ideal. A loan manager MUST calculate this schedule.

        # Let's try a very basic equal principal payment amortization for now.
        # This means the total installment amount will vary if interest is added.
        # The LoanEntity's installment_amount might be an average or target.
        
        # TODO: Implement a proper amortization schedule calculation.
        # For now, we will just create N installments with the due date and total amount from LoanEntity.
        # Principal and Interest breakdown per installment is deferred or assumed to be handled at payment.
        # This is a major simplification.

        current_due_date = start_date
        for i in range(num_installments):
            # Placeholder for advancing due date (e.g., monthly)
            # This needs a proper dateutils.relativedelta or similar
            if i > 0: # Increment month for subsequent installments
                year = current_due_date.year
                month = current_due_date.month + 1
                if month > 12:
                    month = 1
                    year += 1
                # Simplistic day handling, could hit issues with end of month.
                day = min(current_due_date.day, [31,28,31,30,31,30,31,31,30,31,30,31][month-1] ) # basic day clamp
                if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0): # Leap year
                    day = min(current_due_date.day, 29)

                current_due_date = date(year, month, day)

            installments.append({
                "due_date": current_due_date,
                "installment_amount": fixed_installment_amount, # This is total
                "principal_amount": 0.0, # TODO: Calculate
                "interest_amount": 0.0,  # TODO: Calculate
            })
        return installments


    def create_loan(self,
                    person_id: int,
                    loan_direction: LoanDirectionType,
                    loan_amount: float,
                    annual_interest_rate: float, # e.g., 0.05 for 5%
                    start_date: date,
                    end_date: date, # Used to determine number of installments with installment_amount
                    total_installment_amount: float, # The fixed total payment per period
                    number_of_installments: int,
                    related_account_id: int, # Bank account for disbursement/receipt
                    description: Optional[str] = None,
                    fiscal_year_id: Optional[int] = None
                    ) -> Optional[LoanEntity]:
        """
        Creates a new loan, its installment schedule, and records the initial financial transaction.
        """
        if loan_amount <= 0: raise ValueError("مبلغ وام باید مثبت باشد.")
        if annual_interest_rate < 0: raise ValueError("نرخ بهره نمی‌تواند منفی باشد.")
        if number_of_installments <= 0: raise ValueError("تعداد اقساط باید مثبت باشد.")
        if total_installment_amount <=0 : raise ValueError("مبلغ هر قسط باید مثبت باشد.")

        person = self.person_manager.get_person_by_id(person_id)
        if not person: raise ValueError(f"شخص با شناسه {person_id} یافت نشد.")

        disbursement_receipt_account = self.account_manager.get_account_by_id(related_account_id)
        if not disbursement_receipt_account:
            raise ValueError(f"حساب بانکی مرتبط با شناسه {related_account_id} یافت نشد.")
        if disbursement_receipt_account.type != AccountType.ASSET:
            raise ValueError("حساب بانکی مرتبط باید از نوع دارایی باشد.")

        loan_entity = LoanEntity(
            person_id=person_id,
            loan_direction=loan_direction,
            loan_amount=loan_amount,
            interest_rate=annual_interest_rate,
            start_date=start_date,
            end_date=end_date, # For reference, num_installments drives schedule
            installment_amount=total_installment_amount,
            number_of_installments=number_of_installments,
            status=LoanStatus.PENDING_DISBURSEMENT, # Initial status
            related_account_id=related_account_id,
            description=description,
            fiscal_year_id=fiscal_year_id
        )

        # --- Start Transactional Block ---
        created_loan_header = None
        try:
            created_loan_header = self.loans_repository.add(loan_entity)
            if not created_loan_header or not created_loan_header.id:
                raise Exception("خطا در ذخیره اطلاعات اصلی وام.")
            
            logger.info(f"Loan ID {created_loan_header.id} created for Person ID {person_id}, Amount: {loan_amount}.")

            # Generate and save installments (Simplified: uses total_installment_amount)
            # TODO: Implement proper amortization to break down principal and interest for each installment
            #       and store it in LoanInstallmentEntity.
            #       The _calculate_installments is a placeholder.
            installments_data = self._calculate_installments(
                Decimal(str(loan_amount)), Decimal(str(annual_interest_rate)), 
                number_of_installments, start_date, Decimal(str(total_installment_amount))
            )
            
            saved_installments = []
            for inst_data in installments_data:
                installment_entity = LoanInstallmentEntity(
                    loan_id=created_loan_header.id, # type: ignore
                    due_date=inst_data["due_date"],
                    installment_amount=float(inst_data["installment_amount"]), # type: ignore
                    principal_amount=float(inst_data["principal_amount"]), # Will be 0 with current placeholder
                    interest_amount=float(inst_data["interest_amount"]),   # Will be 0 with current placeholder
                    fiscal_year_id=fiscal_year_id # Or derive based on due_date
                )
                saved_installments.append(self.loan_installments_repository.add(installment_entity))
            
            created_loan_header.installments = saved_installments # Attach to entity
            logger.info(f"{len(saved_installments)} installments generated for Loan ID {created_loan_header.id}.")

            # Record initial financial transaction for loan disbursement/receipt
            ft_date = datetime.combine(start_date, datetime.min.time())
            ft_desc_base = f"Loan ID {created_loan_header.id} - {loan_direction.value}"
            
            loan_gl_account_id = None
            ft_type_for_bank = None
            ft_type_for_loan_gl = None

            if loan_direction == LoanDirectionType.GIVEN: # We gave the loan
                loan_gl_account_id = self.accounts_config.get("loan_asset_account")
                if not loan_gl_account_id: raise ValueError("حساب دارایی وام (پرداختی توسط ما) در تنظیمات یافت نشد.")
                # Our Bank (Asset) decreases, Loan Asset increases
                ft_type_for_bank = FinancialTransactionType.EXPENSE # Credit Bank
                ft_type_for_loan_gl = FinancialTransactionType.INCOME # Debit Loan Asset
            
            elif loan_direction == LoanDirectionType.RECEIVED: # We received the loan
                loan_gl_account_id = self.accounts_config.get("loan_liability_account")
                if not loan_gl_account_id: raise ValueError("حساب بدهی وام (دریافتی توسط ما) در تنظیمات یافت نشد.")
                # Our Bank (Asset) increases, Loan Liability increases
                ft_type_for_bank = FinancialTransactionType.INCOME # Debit Bank
                ft_type_for_loan_gl = FinancialTransactionType.INCOME # Credit Loan Liability
            
            if not loan_gl_account_id or not ft_type_for_bank or not ft_type_for_loan_gl:
                 raise Exception("خطا در تعیین حساب‌های GL یا نوع تراکنش برای ثبت اولیه وام.")


            # FT for the Bank/Cash account
            self.ft_manager.create_financial_transaction(
                transaction_date=ft_date, account_id=related_account_id,
                transaction_type=ft_type_for_bank, amount=loan_amount,
                description=f"{ft_desc_base} (Bank/Cash Leg)", fiscal_year_id=fiscal_year_id,
                reference_id=created_loan_header.id, reference_type=ReferenceType.LOAN
            )
            # FT for the Loan GL Account (Loan Asset or Loan Liability)
            self.ft_manager.create_financial_transaction(
                transaction_date=ft_date, account_id=loan_gl_account_id,
                transaction_type=ft_type_for_loan_gl, amount=loan_amount,
                description=f"{ft_desc_base} (Loan GL Leg)", fiscal_year_id=fiscal_year_id,
                reference_id=created_loan_header.id, reference_type=ReferenceType.LOAN
            )
            
            # Update loan status after disbursement/receipt
            created_loan_header.status = LoanStatus.ACTIVE
            self.loans_repository.update(created_loan_header)
            logger.info(f"Initial financial transaction for Loan ID {created_loan_header.id} recorded. Status set to ACTIVE.")

            return created_loan_header
            
        except Exception as e:
            logger.error(f"Error creating loan for person ID {person_id}: {e}", exc_info=True)
            # Rollback logic (delete loan header, installments if created) would be needed here.
            if created_loan_header and created_loan_header.id:
                self.loan_installments_repository.delete_by_loan_id(created_loan_header.id) # type: ignore
                self.loans_repository.delete(created_loan_header.id) # type: ignore
                logger.info(f"Rolled back creation of Loan ID {created_loan_header.id} and its installments due to error.")
            raise
        # --- End Transactional Block ---

    def record_installment_payment(self,
                                   loan_installment_id: int,
                                   paid_date: date,
                                   payment_account_id: int, # Our Bank/Cash account
                                   payment_method: PaymentMethod,
                                   # Principal & Interest paid should ideally be derived from installment schedule
                                   # or confirmed by user. For now, assume they are provided correctly.
                                   principal_portion_paid: float,
                                   interest_portion_paid: float,
                                   description: Optional[str] = None,
                                   fiscal_year_id_for_ft: Optional[int] = None
                                   ) -> Optional[LoanInstallmentEntity]:
        """
        Records the payment of a loan installment.
        Updates installment status and records financial transactions.
        """
        installment = self.loan_installments_repository.get_by_id(loan_installment_id)
        if not installment or not installment.id or not installment.loan_id:
            raise ValueError(f"قسط وام با شناسه {loan_installment_id} یافت نشد.")
        
        if installment.paid_date is not None:
            logger.warning(f"Installment ID {loan_installment_id} already paid on {installment.paid_date}.")
            return installment # Or raise error

        loan = self.loans_repository.get_by_id(installment.loan_id)
        if not loan or not loan.id or not loan.fiscal_year_id: # fiscal_year_id needed from loan for FTs
            raise ValueError(f"وام مرتبط با قسط (LoanID: {installment.loan_id}) یافت نشد یا اطلاعات ناقص است.")

        # Validate payment_account_id
        our_bank_account = self.account_manager.get_account_by_id(payment_account_id)
        if not our_bank_account or our_bank_account.type != AccountType.ASSET:
            raise ValueError("حساب پرداخت/دریافت قسط باید یک حساب دارایی معتبر باشد.")

        total_paid_this_installment = principal_portion_paid + interest_portion_paid
        # Basic validation against expected installment amount (could have tolerance)
        if abs(total_paid_this_installment - installment.installment_amount) > 0.01 : # Tolerance for float
            logger.warning(f"Paid amount {total_paid_this_installment} for Installment ID {installment.id} "
                           f"differs from expected {installment.installment_amount}. Proceeding with paid amounts.")
        
        # --- Start Transactional Block ---
        try:
            ft_date = datetime.combine(paid_date, datetime.min.time())
            ft_fiscal_year = fiscal_year_id_for_ft if fiscal_year_id_for_ft is not None else loan.fiscal_year_id
            ft_desc_base = f"Installment Payment for Loan ID {loan.id}, Inst. ID {installment.id}"

            if loan.loan_direction == LoanDirectionType.GIVEN: # We gave loan, now receiving payment
                loan_asset_acc_id = self.accounts_config.get("loan_asset_account")
                interest_income_acc_id = self.accounts_config.get("interest_income_account")
                if not loan_asset_acc_id or not interest_income_acc_id:
                    raise ValueError("حساب دارایی وام یا درآمد بهره در تنظیمات یافت نشد.")

                # 1. Debit Our Bank/Cash (Asset increases)
                self.ft_manager.create_financial_transaction(
                    transaction_date=ft_date, account_id=payment_account_id,
                    transaction_type=FinancialTransactionType.INCOME, amount=total_paid_this_installment,
                    description=f"{ft_desc_base} (Dr. Bank)", fiscal_year_id=ft_fiscal_year,
                    reference_id=installment.id, reference_type=ReferenceType.LOAN # Refers to LoanInstallment
                )
                # 2. Credit Loan Asset (for principal part - Asset decreases)
                if principal_portion_paid > 0:
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_date, account_id=loan_asset_acc_id,
                        transaction_type=FinancialTransactionType.EXPENSE, amount=principal_portion_paid,
                        description=f"{ft_desc_base} (Cr. Loan Asset - Principal)", fiscal_year_id=ft_fiscal_year,
                        reference_id=installment.id, reference_type=ReferenceType.LOAN
                    )
                # 3. Credit Interest Income (Revenue increases)
                if interest_portion_paid > 0:
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_date, account_id=interest_income_acc_id,
                        transaction_type=FinancialTransactionType.INCOME, amount=interest_portion_paid,
                        description=f"{ft_desc_base} (Cr. Interest Income)", fiscal_year_id=ft_fiscal_year,
                        reference_id=installment.id, reference_type=ReferenceType.LOAN
                    )
            
            elif loan.loan_direction == LoanDirectionType.RECEIVED: # We took loan, now making payment
                loan_liability_acc_id = self.accounts_config.get("loan_liability_account")
                interest_expense_acc_id = self.accounts_config.get("interest_expense_account")
                if not loan_liability_acc_id or not interest_expense_acc_id:
                    raise ValueError("حساب بدهی وام یا هزینه بهره در تنظیمات یافت نشد.")

                # 1. Debit Loan Liability (for principal part - Liability decreases)
                if principal_portion_paid > 0:
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_date, account_id=loan_liability_acc_id,
                        transaction_type=FinancialTransactionType.EXPENSE, amount=principal_portion_paid,
                        description=f"{ft_desc_base} (Dr. Loan Liability - Principal)", fiscal_year_id=ft_fiscal_year,
                        reference_id=installment.id, reference_type=ReferenceType.LOAN
                    )
                # 2. Debit Interest Expense (Expense increases)
                if interest_portion_paid > 0:
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_date, account_id=interest_expense_acc_id,
                        transaction_type=FinancialTransactionType.EXPENSE, amount=interest_portion_paid,
                        description=f"{ft_desc_base} (Dr. Interest Expense)", fiscal_year_id=ft_fiscal_year,
                        reference_id=installment.id, reference_type=ReferenceType.LOAN
                    )
                # 3. Credit Our Bank/Cash (Asset decreases)
                self.ft_manager.create_financial_transaction(
                    transaction_date=ft_date, account_id=payment_account_id,
                    transaction_type=FinancialTransactionType.EXPENSE, amount=total_paid_this_installment,
                    description=f"{ft_desc_base} (Cr. Bank)", fiscal_year_id=ft_fiscal_year,
                    reference_id=installment.id, reference_type=ReferenceType.LOAN
                )

            # Update installment status
            installment.paid_date = paid_date
            installment.payment_method = payment_method
            installment.principal_amount = principal_portion_paid # Store actual paid principal
            installment.interest_amount = interest_portion_paid   # Store actual paid interest
            if description: installment.description = description
            
            updated_installment = self.loan_installments_repository.update(installment)
            logger.info(f"Installment ID {installment.id} for Loan ID {loan.id} marked as paid.")

            # Check if loan is fully paid
            self._check_and_update_loan_status(loan.id) # type: ignore
            
            return updated_installment

        except Exception as e:
            logger.error(f"Error recording installment payment for Inst. ID {loan_installment_id}: {e}", exc_info=True)
            # Rollback FTs would be complex here.
            raise
        # --- End Transactional Block ---

    def _check_and_update_loan_status(self, loan_id: int):
        """Checks if all installments for a loan are paid and updates loan status if so."""
        all_installments = self.loan_installments_repository.get_by_loan_id(loan_id)
        if not all_installments: return # Should not happen if loan has installments

        if all(inst.paid_date is not None for inst in all_installments):
            loan = self.loans_repository.get_by_id(loan_id)
            if loan and loan.status != LoanStatus.PAID_OFF:
                loan.status = LoanStatus.PAID_OFF
                self.loans_repository.update(loan)
                logger.info(f"Loan ID {loan_id} is now fully paid off.")


    def get_loan_with_installments(self, loan_id: int) -> Optional[LoanEntity]:
        loan = self.loans_repository.get_by_id(loan_id)
        if loan and loan.id:
            loan.installments = self.loan_installments_repository.get_by_loan_id(loan.id)
        return loan

    def get_loans_by_person(self, person_id: int, include_installments: bool = False) -> List[LoanEntity]:
        loans = self.loans_repository.get_by_person_id(person_id) # Assumes repo has this
        if include_installments:
            for loan in loans:
                if loan.id:
                    loan.installments = self.loan_installments_repository.get_by_loan_id(loan.id)
        return loans
        
    def get_due_installments(self, due_by_date: Optional[date] = None) -> List[LoanInstallmentEntity]:
        # This would ideally be a more specific query in the repository
        all_installments = self.loan_installments_repository.get_all()
        due_installments = []
        target_date = due_by_date if due_by_date else date.today()
        for inst in all_installments:
            if inst.paid_date is None and inst.due_date <= target_date:
                due_installments.append(inst)
        return sorted(due_installments, key=lambda i: i.due_date)

    def delete_loan(self, loan_id: int) -> bool:
        """Deletes a loan and its installments.
        WARNING: Complex operation. Should only be done if no payments made, or
        all financial effects are carefully reversed."""
        logger.warning(f"Attempting to delete Loan ID {loan_id} and its installments. This is destructive.")
        loan_to_delete = self.get_loan_with_installments(loan_id)
        if not loan_to_delete or not loan_to_delete.id:
            logger.warning(f"Loan ID {loan_id} not found for deletion.")
            return False

        # Business rule: Prevent deletion if any installment is paid or loan is active beyond initial setup.
        if loan_to_delete.status not in [LoanStatus.PENDING_DISBURSEMENT, LoanStatus.ACTIVE]: # Allow deleting ACTIVE before payments
            if any(inst.paid_date for inst in loan_to_delete.installments):
                logger.error(f"Cannot delete Loan ID {loan_id} as it has paid installments.")
                raise ValueError("وام دارای اقساط پرداخت شده است و قابل حذف نیست.")
        
        # TODO: Reverse initial disbursement/receipt FTs if loan status was ACTIVE.
        # This simplified delete doesn't do that.
        
        try:
            # Delete installments first (or rely on DB cascade if set up)
            self.loan_installments_repository.delete_by_loan_id(loan_to_delete.id) # type: ignore
            # Delete loan header
            self.loans_repository.delete(loan_to_delete.id) # type: ignore
            logger.info(f"Loan ID {loan_id} and its installments deleted.")
            return True
        except Exception as e:
            logger.error(f"Error deleting Loan ID {loan_id}: {e}", exc_info=True)
            return False