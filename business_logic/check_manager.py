
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from decimal import Decimal

# --- Entity و Constant Imports ---
from .entities.check_entity import CheckEntity
from ..constants import CheckType, CheckStatus, FinancialTransactionType, ReferenceType,AccountType

# --- Type Hinting Imports ---
if TYPE_CHECKING:
    from ..data_access.checks_repository import ChecksRepository
    from ..data_access.payment_header_repository import PaymentHeaderRepository

    from .financial_transaction_manager import FinancialTransactionManager
    from .account_manager import AccountManager
    from .person_manager import PersonManager
    from .invoice_manager import InvoiceManager
    from .payment_manager import PaymentManager

import logging
logger = logging.getLogger(__name__)

DEFAULT_ACCOUNTS_CONFIG_FOR_CHECKS = {
    "checks_receivable_account": 101,
    "checks_payable_account": 201,
    "bank_charges_expense_account": 501,
    "accounts_receivable": 1,
    "accounts_payable": 2, # قبلاً ۴ بود، با بالا یکسان‌سازی شد
}
class CheckManager:
    def __init__(self, 
                 checks_repository: 'ChecksRepository',
                 ft_manager: 'FinancialTransactionManager',
                 account_manager: 'AccountManager',
                 person_manager: 'PersonManager',
                 invoice_manager: 'InvoiceManager',
                 accounts_config: Dict[str, Any]):
        
        # FIX: استفاده یکسان از self.checks_repo در کل کلاس
        self.checks_repository = checks_repository
        self.ft_manager = ft_manager
        self.account_manager = account_manager
        self.person_manager = person_manager
        self.invoice_manager = invoice_manager
        self.accounts_config = accounts_config
        self.payment_manager: 'PaymentManager'


    def create_check(self, 
                     check_number: str, 
                     amount: Decimal, 
                     due_date: date, 
                     person_id: int, 
                     check_type: CheckType,
                     bank_account_id: int,
                     issue_date: Optional[date] = None,
                     description: Optional[str] = None,
                     fiscal_year_id: Optional[int] = None,
                     status: CheckStatus = CheckStatus.PENDING
                     ) -> Optional[CheckEntity]:
        """
        یک چک جدید ایجاد و در دیتابیس ذخیره می‌کند.
        """
        logger.info(f"Attempting to create a new check: Number {check_number}, Amount: {amount}")
        if not all([check_number, amount > 0, due_date, person_id, bank_account_id]):
            raise ValueError("اطلاعات اصلی چک (شماره، مبلغ، تاریخ سررسید، شخص، حساب بانکی) الزامی است.")
            
        check_entity = CheckEntity(
            check_number=check_number,
            amount=Decimal(str(amount)),
            issue_date=issue_date or date.today(),
            due_date=due_date,
            person_id=person_id,
            account_id=bank_account_id,
            check_type=check_type,
            status=status,
            fiscal_year_id=fiscal_year_id,
            description=description
        )
        created_check = self.checks_repository.add(check_entity)
        if created_check:
            logger.info(f"Check ID {created_check.id} created successfully.")
        return created_check

    def update_check_status(self, 
                            check_id: int, 
                            new_status: CheckStatus, 
                            transaction_date_override: Optional[date] = None) -> Optional[CheckEntity]:
        """
        وضعیت یک چک را به‌روز کرده و تراکنش‌های مالی مربوط به تغییر وضعیت را ثبت می‌کند.
        """
        logger.info(f"Attempting to update status for Check ID: {check_id} to {new_status.value}")
        if not isinstance(check_id, int) or check_id <= 0: raise ValueError("شناسه چک نامعتبر است.")
        if not isinstance(new_status, CheckStatus): raise ValueError("وضعیت جدید چک نامعتبر است.")

        check_to_update = self.checks_repository.get_by_id(check_id)
        if not check_to_update or not check_to_update.id or check_to_update.fiscal_year_id is None:
            logger.warning(f"Check ID {check_id} not found or missing fiscal_year_id for status update.")
            raise ValueError(f"چک با شناسه {check_id} یافت نشد یا اطلاعات سال مالی آن ناقص است.")
        
        if check_to_update.status == new_status:
            logger.info(f"Check ID {check_id} already has status {new_status.value}. No update performed.")
            return check_to_update

        original_status = check_to_update.status
        check_to_update.status = new_status
        
        ft_date_to_use = transaction_date_override if transaction_date_override else date.today()
        ft_datetime = datetime.combine(ft_date_to_use, datetime.min.time())
        ft_fiscal_year_id = check_to_update.fiscal_year_id # استفاده از سال مالی خود چک

        try:
            updated_check_db = self.checks_repository.update(check_to_update) # ابتدا وضعیت در دیتابیس آپدیت شود
            if not updated_check_db:
                raise Exception("Failed to update check status in repository.")
            logger.info(f"Check ID {check_id} status updated in DB from {original_status.value} to {new_status.value}.")

            our_bank_account_id = check_to_update.account_id 
            check_amount = check_to_update.amount
            ft_description_base = f"Check {check_to_update.check_number} status: {original_status.value} -> {new_status.value}"

            # --- ثبت تراکنش‌های مالی بر اساس تغییر وضعیت ---
            if new_status == CheckStatus.CLEARED or new_status == CheckStatus.CASHED:
                if check_to_update.check_type == CheckType.ISSUED: # چک پرداختنی ما وصول شده
                    checks_payable_acc_id = self.accounts_config.get("checks_payable_account")
                    if not checks_payable_acc_id: raise ValueError("حساب 'اسناد پرداختنی مدت‌دار' در تنظیمات یافت نشد.")
                    
                    logger.info(f"Issued Check Cleared (ID: {check_id}): Dr. Checks Payable ({checks_payable_acc_id}), Cr. Bank ({our_bank_account_id})")
                    # بدهکار: اسناد پرداختنی مدت‌دار (بدهی کاهش می‌یابد)
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=checks_payable_acc_id,
                        transaction_type=FinancialTransactionType.EXPENSE, amount=check_amount, 
                        description=f"{ft_description_base} (Dr. Checks Payable)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )
                    # بستانکار: حساب بانک ما (دارایی کاهش می‌یابد)
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=our_bank_account_id,
                        transaction_type=FinancialTransactionType.EXPENSE, amount=check_amount, 
                        description=f"{ft_description_base} (Cr. Bank)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )
                elif check_to_update.check_type == CheckType.RECEIVED: # چک دریافتنی مشتری وصول شده
                    checks_receivable_acc_id = self.accounts_config.get("checks_receivable_account")
                    if not checks_receivable_acc_id: raise ValueError("حساب 'اسناد دریافتنی مدت‌دار' در تنظیمات یافت نشد.")

                    logger.info(f"Received Check Cleared (ID: {check_id}): Dr. Bank ({our_bank_account_id}), Cr. Checks Receivable ({checks_receivable_acc_id})")
                    # بدهکار: حساب بانک ما (دارایی افزایش می‌یابد)
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=our_bank_account_id,
                        transaction_type=FinancialTransactionType.INCOME, amount=check_amount, 
                        description=f"{ft_description_base} (Dr. Bank)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )
                    # بستانکار: حساب اسناد دریافتنی مدت‌دار (دارایی کاهش می‌یابد)
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=checks_receivable_acc_id,
                        transaction_type=FinancialTransactionType.EXPENSE, amount=check_amount, 
                        description=f"{ft_description_base} (Cr. Checks Receivable)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )

            elif new_status == CheckStatus.BOUNCED:
                if check_to_update.check_type == CheckType.RECEIVED: # چک دریافتنی مشتری برگشت خورده
                    checks_receivable_acc_id = self.accounts_config.get("checks_receivable_account")
                    ar_account_id = self.accounts_config.get("accounts_receivable")
                    if not checks_receivable_acc_id or not ar_account_id:
                        raise ValueError("حساب 'اسناد دریافتنی مدت‌دار' یا 'حساب دریافتنی کل' برای چک برگشتی در تنظیمات یافت نشد.")

                    logger.info(f"Received Check Bounced (ID: {check_id}): Dr. AR ({ar_account_id}), Cr. Checks Receivable ({checks_receivable_acc_id})")
                    # بدهکار: حساب دریافتنی کل (مشتری دوباره بدهکار می‌شود)
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=ar_account_id,
                        transaction_type=FinancialTransactionType.INCOME, amount=check_amount,
                        description=f"{ft_description_base} (Dr. AR - Bounced)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )
                    # بستانکار: حساب اسناد دریافتنی مدت‌دار
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=checks_receivable_acc_id,
                        transaction_type=FinancialTransactionType.EXPENSE, amount=check_amount,
                        description=f"{ft_description_base} (Cr. Checks Receivable - Bounced)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )
                    # TODO: Handle bank charges (Dr. Bank Charges Expense, Cr. Bank)
                    if check_to_update.invoice_id is not None:
                        logger.info(f"Received check {check_id} for Invoice ID {check_to_update.invoice_id} bounced. Reversing payment on invoice.")
                        try:
                            self.invoice_manager.update_payment_status(
                                invoice_id=check_to_update.invoice_id,
                                payment_amount_change= -check_amount # ارسال مبلغ منفی برای کاهش paid_amount
                            )
                            logger.info(f"Invoice ID {check_to_update.invoice_id} payment status updated due to bounced check.")
                        except Exception as e_inv_update:
                            logger.error(f"Error updating payment status for Invoice ID {check_to_update.invoice_id} after check bounce: {e_inv_update}", exc_info=True)
                            # این خطا نباید مانع از بقیه عملیات برگشت چک شود، اما باید لاگ شود.
                elif check_to_update.check_type == CheckType.ISSUED: # <<< چک پرداختنی ما برگشت خورده
                    checks_payable_acc_id = self.accounts_config.get("checks_payable_account")
                    ap_account_id = self.accounts_config.get("accounts_payable") 
                    if not checks_payable_acc_id or not ap_account_id:
                        raise ValueError("حساب 'اسناد پرداختنی مدت‌دار' یا 'حساب پرداختنی کل' برای چک صادره برگشتی در تنظیمات یافت نشد.")
                    
                    logger.info(f"Issued Check Bounced (ID: {check_id}): Dr. Checks Payable ({checks_payable_acc_id}), Cr. AP ({ap_account_id})")
                    # ۱. بدهکار کردن "اسناد پرداختنی مدت‌دار" (خنثی کردن بستانکاری اولیه که توسط PaymentManager انجام شده بود)
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=checks_payable_acc_id,
                        transaction_type=FinancialTransactionType.EXPENSE, # بدهکار کردن این حساب بدهی
                        amount=check_amount,
                        description=f"{ft_description_base} (Dr. Checks Payable - Bounced)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )
                    # ۲. بستانکار کردن "حساب پرداختنی کل" (برقراری مجدد بدهی اولیه به تامین‌کننده)
                    self.ft_manager.create_financial_transaction(
                        transaction_date=ft_datetime, account_id=ap_account_id,
                        transaction_type=FinancialTransactionType.INCOME, # بستانکار کردن این حساب بدهی (افزایش بدهی)
                        amount=check_amount,
                        description=f"{ft_description_base} (Cr. Accounts Payable - Bounced)", fiscal_year_id=ft_fiscal_year_id,
                        reference_id=check_id, reference_type=ReferenceType.CHECK
                    )
                    
                    # ۳. برگرداندن اثر پرداخت روی فاکتور خرید یا سفارش خرید مرتبط (اگر وجود دارد)
                    # برای این کار باید پرداختی که این چک به آن متصل بوده را پیدا کنیم
                    linked_payments = self.payments_repository.find_by_criteria({"check_id": check_id}) # type: ignore
                    if linked_payments:
                        for payment in linked_payments:
                            logger.info(f"Issued check {check_id} was linked to Payment ID {payment.id}. Reversing payment application.")
                            if self.payment_manager: # اطمینان از وجود payment_manager
                                try:
                                    # PaymentManager نیاز به متدی برای برگرداندن اثر پرداخت دارد
                                    # مثلاً self.payment_manager.reverse_payment_effects(payment.id)
                                    # که این متد باید paid_amount فاکتور/سفارش خرید را کاهش دهد
                                    # فعلا به صورت دستی این کار را می‌کنیم (اگرچه بهتر است در PaymentManager باشد)
                                    if payment.invoice_id is not None:
                                        self.invoice_manager.update_payment_status(payment.invoice_id, -payment.amount)
                                        logger.info(f"Reversed paid amount on Invoice ID {payment.invoice_id} due to bounced issued check.")
                                    if payment.purchase_order_id is not None and self.payment_manager.po_manager: # po_manager از payment_manager
                                        self.payment_manager.po_manager.update_paid_amount(payment.purchase_order_id, -payment.amount)
                                        logger.info(f"Reversed paid amount on PO ID {payment.purchase_order_id} due to bounced issued check.")
                                    # همچنین می‌توان وضعیت خود PaymentEntity را به "ناموفق" یا "برگشت خورده" تغییر داد
                                except Exception as e_pay_rev:
                                    logger.error(f"Error reversing payment effects for Payment ID {payment.id} due to bounced check: {e_pay_rev}", exc_info=True)
                    else:
                        logger.warning(f"No payment record found linked to bounced issued Check ID {check_id}. Cannot auto-reverse PO/Invoice payment status.")

                
            elif new_status == CheckStatus.PAID_TO_BENEFICIARY: # خرج کردن چک دریافتنی
                if check_to_update.check_type == CheckType.RECEIVED:
                    logger.info(f"Received Check ID {check_id} status being updated to PAID_TO_BENEFICIARY.")
                    # آثار مالی اصلی این عملیات (Dr. AP/Expense of third party, Cr. Checks Receivable Account)
                    # توسط PaymentManager هنگام ثبت پرداخت با روش "خرج چک" انجام شده است.
                    # CheckManager در اینجا فقط وضعیت خود چک را به‌روز می‌کند.
                    # بنابراین، هیچ تراکنش مالی جدیدی در این نقطه توسط CheckManager ایجاد نمی‌شود.
                    pass # فقط وضعیت چک در دیتابیس (که در ابتدای متد انجام شد) به‌روز می‌شود.
                else: # چک پرداختنی را نمی‌توان به این روش "خرج" کرد
                    logger.error(f"Invalid attempt to set ISSUED Check ID {check_id} to PAID_TO_BENEFICIARY.")
                    check_to_update.status = original_status # برگرداندن وضعیت در حافظه
                    # self.checks_repository.update(check_to_update) # ذخیره وضعیت قبلی - این باعث حلقه نمی‌شود چون فقط در صورت خطا است
                    raise ValueError("چک‌های پرداختنی را نمی‌توان به این روش خرج (واگذار به غیر) کرد.")
            return updated_check_db 
        except Exception as e:
            logger.error(f"Error in post-status-update financial processing for check ID {check_id}: {e}", exc_info=True)
            # اگر در ثبت FT ها خطا رخ داد، باید وضعیت چک را به حالت اولیه برگردانیم
            check_to_update.status = original_status 
            try:
                self.checks_repository.update(check_to_update)
                logger.info(f"Rolled back status of Check ID {check_id} to {original_status.value} due to error in FT processing.")
            except Exception as rb_e:
                logger.critical(f"CRITICAL: Failed to rollback status for Check ID {check_id} after FT error: {rb_e}")
            raise # خطای اصلی را دوباره ایجاد کن


    def get_check_by_id(self, check_id: int) -> Optional[CheckEntity]:
        return self.checks_repository.get_by_id(check_id)

    def get_all_checks(self, 
                       person_id: Optional[int] = None, 
                       status_filter: Optional[CheckStatus] = None, 
                       type_filter: Optional[CheckType] = None) -> List[CheckEntity]:
        
        criteria = {}
        if person_id: criteria["person_id"] = person_id
        if status_filter: criteria["status"] = status_filter.value
        if type_filter: criteria["check_type"] = type_filter.value
        
        checks = self.checks_repository.find_by_criteria(criteria, order_by="due_date ASC")
        if self.person_manager and self.account_manager:
            for chk in checks:
                if chk.person_id:
                    person = self.person_manager.get_person_by_id(chk.person_id)
                    if person: chk.person_name = person.name
                if chk.account_id:
                    account = self.account_manager.get_account_by_id(chk.account_id)
                    if account: chk.bank_account_name = account.name
        return checks
        
    def update_check_info(self, 
                          check_id: int,
                          check_number: Optional[str] = None,
                          amount: Optional[float] = None,
                          issue_date: Optional[date] = None,
                          due_date: Optional[date] = None,
                          person_id: Optional[int] = None,
                          account_id: Optional[int] = None, 
                          check_type: Optional[CheckType] = None,
                          description: Optional[str] = None,
                          invoice_id: Optional[int] = None, 
                          purchase_order_id: Optional[int] = None, 
                          fiscal_year_id: Optional[int] = None
                          ) -> Optional[CheckEntity]:
        logger.info(f"Attempting to update info for Check ID: {check_id}")
        check_to_update = self.checks_repository.get_by_id(check_id)
        if not check_to_update:
            raise ValueError(f"چک با شناسه {check_id} یافت نشد.")

        can_edit_fully = (check_to_update.status == CheckStatus.PENDING)
        updated_fields = False

        if check_number is not None and check_to_update.check_number != check_number:
            if not can_edit_fully: raise ValueError("فقط شماره چک‌های در جریان قابل ویرایش است.")
            if not check_number: raise ValueError("شماره چک نمی‌تواند خالی باشد.")
            check_to_update.check_number = check_number
            updated_fields = True
        if amount is not None and abs(check_to_update.amount - amount) > 0.001 :
            if not can_edit_fully: raise ValueError("فقط مبلغ چک‌های در جریان قابل ویرایش است.")
            if amount <=0 : raise ValueError("مبلغ چک باید مثبت باشد.")
            check_to_update.amount = amount
            updated_fields = True
        # ... (سایر فیلدها با بررسی can_edit_fully در صورت نیاز) ...
        if issue_date is not None and check_to_update.issue_date != issue_date:
            if not can_edit_fully: raise ValueError("فقط تاریخ صدور چک‌های در جریان قابل ویرایش است.")
            check_to_update.issue_date = issue_date
            updated_fields = True
        if due_date is not None and check_to_update.due_date != due_date:
            if not can_edit_fully: raise ValueError("فقط تاریخ سررسید چک‌های در جریان قابل ویرایش است.")
            check_to_update.due_date = due_date
            updated_fields = True
        if person_id is not None and check_to_update.person_id != person_id:
            if not can_edit_fully: raise ValueError("فقط شخص چک‌های در جریان قابل ویرایش است.")
            if not self.person_manager.get_person_by_id(person_id): raise ValueError("شخص جدید نامعتبر است.")
            check_to_update.person_id = person_id
            updated_fields = True
        if account_id is not None and check_to_update.account_id != account_id:
            if not can_edit_fully: raise ValueError("فقط حساب بانکی چک‌های در جریان قابل ویرایش است.")
            bank_acc = self.account_manager.get_account_by_id(account_id)
            if not bank_acc or bank_acc.type != AccountType.ASSET: raise ValueError("حساب بانکی جدید نامعتبر است.")
            check_to_update.account_id = account_id
            updated_fields = True
        if check_type is not None and check_to_update.check_type != check_type:
            if not can_edit_fully: raise ValueError("فقط نوع چک‌های در جریان قابل ویرایش است.")
            check_to_update.check_type = check_type
            updated_fields = True
        
        # این فیلدها همیشه قابل ویرایش هستند
        if description is not None and check_to_update.description != description:
            check_to_update.description = description
            updated_fields = True
        if fiscal_year_id is not None and check_to_update.fiscal_year_id != fiscal_year_id:
            check_to_update.fiscal_year_id = fiscal_year_id
            updated_fields = True
        if invoice_id is not None and check_to_update.invoice_id != invoice_id:
            check_to_update.invoice_id = invoice_id
            updated_fields = True
        elif invoice_id is None and check_to_update.invoice_id is not None:
             check_to_update.invoice_id = None
             updated_fields = True
        if purchase_order_id is not None and check_to_update.purchase_order_id != purchase_order_id:
            check_to_update.purchase_order_id = purchase_order_id
            updated_fields = True
        elif purchase_order_id is None and check_to_update.purchase_order_id is not None:
             check_to_update.purchase_order_id = None
             updated_fields = True


        if updated_fields:
            return self.checks_repository.update(check_to_update)
        logger.info(f"No updatable info provided or check not in PENDING state for full edit (Check ID: {check_id}).")
        return check_to_update 

    def get_checks_by_person(self, person_id: int) -> List[CheckEntity]:
        return self.checks_repository.get_by_person_id(person_id) # type: ignore

    def get_checks_by_status(self, status: CheckStatus) -> List[CheckEntity]:
        return self.checks_repository.get_by_status(status) # type: ignore
        
    def get_checks_by_due_date_range(self, start_date: date, end_date: date) -> List[CheckEntity]:
        return self.checks_repository.get_by_due_date_range(start_date, end_date) # type: ignore


    def delete_check(self, check_id: int) -> bool:
        logger.warning(f"Attempting physical delete of Check ID {check_id}. Consider using 'CANCELED' status instead.")
        check_to_delete = self.checks_repository.get_by_id(check_id)
        if not check_to_delete:
            logger.warning(f"Check ID {check_id} not found for deletion.")
            return False # یا True اگر "یافت نشد" به معنی "قبلاً حذف شده" باشد

        if check_to_delete.status != CheckStatus.PENDING:
             logger.error(f"Cannot delete Check ID {check_id} with status {check_to_delete.status.value}. Only PENDING checks can be physically deleted.")
             raise ValueError("فقط چک‌های در جریان (Pending) قابل حذف فیزیکی هستند. سایر چک‌ها را ابتدا باطل کنید.")
        
        # اگر چک به پرداختی لینک شده باشد، باید ابتدا آن لینک برداشته شود یا پرداخت مدیریت شود.
        # این بخش نیاز به بررسی دارد.
        
        try:
            self.checks_repository.delete(check_id)
            logger.info(f"Check ID {check_id} (Number: {check_to_delete.check_number}) physically deleted.")
            return True
        except Exception as e:
            logger.error(f"Error deleting Check ID {check_id}: {e}", exc_info=True)
            return False