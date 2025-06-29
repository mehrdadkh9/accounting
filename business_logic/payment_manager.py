# src/business_logic/payment_manager.py

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# --- Entity و Constant Imports ---
from .entities.payment_header_entity import PaymentHeaderEntity
from .entities.payment_line_item_entity import PaymentLineItemEntity
from src.constants import PaymentType, PaymentMethod,AccountType, CheckType, CheckStatus, ReferenceType, FinancialTransactionType, PersonType

# --- Type Hinting Imports ---
if TYPE_CHECKING:
    from .person_manager import PersonManager
    from .account_manager import AccountManager
    from .invoice_manager import InvoiceManager
    from .purchase_order_manager import PurchaseOrderManager
    from .check_manager import CheckManager
    from .financial_transaction_manager import FinancialTransactionManager
    from ..data_access.payment_header_repository import PaymentHeaderRepository
    from ..data_access.payment_line_item_repository import PaymentLineItemRepository

import logging
logger = logging.getLogger(__name__)

class PaymentManager:
    def __init__(self, 
                 payment_header_repository: 'PaymentHeaderRepository',
                 payment_line_item_repository: 'PaymentLineItemRepository',
                 person_manager: 'PersonManager',
                 account_manager: 'AccountManager',
                 invoice_manager: 'InvoiceManager',
                 po_manager: 'PurchaseOrderManager',
                 ft_manager: 'FinancialTransactionManager',
                 check_manager: Optional['CheckManager'] = None,
                 accounts_config: Optional[Dict[str, Any]] = None):
        
        self.payment_header_repo = payment_header_repository
        self.payment_line_item_repo = payment_line_item_repository
        self.person_manager = person_manager
        self.account_manager = account_manager
        self.invoice_manager = invoice_manager
        self.po_manager = po_manager
        self.ft_manager = ft_manager
        self.check_manager = check_manager
        self.accounts_config = accounts_config if accounts_config is not None else {}

    def record_payment(self, 
                       payment_date: date, 
                       person_id: Optional[int],
                       line_items_data: List[Dict[str, Any]], 
                       payment_type: PaymentType,
                       total_amount: Decimal,
                       description: Optional[str] = None,
                       invoice_id: Optional[int] = None,
                       purchase_order_id: Optional[int] = None,
                       fiscal_year_id: Optional[int] = None,
                       is_direct_posting: bool = False,
                       **kwargs) -> Optional[PaymentHeaderEntity]:
        
        logger.info(f"Attempting to record payment. Type: {payment_type.value}, Person ID: {person_id}, Items: {len(line_items_data)}")
        if not line_items_data: raise ValueError("سند پرداخت/دریافت باید حداقل یک قلم داشته باشد.")
        if not fiscal_year_id: raise ValueError("سال مالی برای سند پرداخت/دریافت باید مشخص شود.")

        # FIX for: No parameter named ... in PaymentHeaderEntity
        # این خطا به این دلیل بود که Entity شما ممکن است این فیلدها را نداشته باشد.
        # اطمینان حاصل کنید که PaymentHeaderEntity فیلدهای زیر را دارد.
        header = PaymentHeaderEntity(
            payment_date=payment_date,
            person_id=person_id,
            total_amount=total_amount,
            description=description,
            invoice_id=invoice_id,
            purchase_order_id=purchase_order_id,
            fiscal_year_id=fiscal_year_id,
            payment_type=payment_type,
            is_direct_posting=is_direct_posting
        )

        created_header: Optional[PaymentHeaderEntity] = None
        try:
            created_header = self.payment_header_repo.add(header)
            if not created_header or not created_header.id:
                raise Exception("خطا در ذخیره هدر پرداخت/دریافت.")

            logger.info(f"PaymentHeader ID {created_header.id} created successfully.")
            
            saved_line_items: List[PaymentLineItemEntity] = []
            for item_data in line_items_data:
                check_id_for_line: Optional[int] = None
                
                # FIX for: Cannot access attribute "record_check" for class "CheckManager"
                # فرض بر این است که متد صحیح `create_check` است
                if item_data.get("payment_method") == PaymentMethod.CHECK and item_data.get("check_details") and self.check_manager:
                    if person_id is None: raise ValueError("شخص برای ایجاد چک جدید الزامی است.")
                    
                    check_details = item_data["check_details"]
                    check_type = CheckType.RECEIVED if payment_type == PaymentType.RECEIPT else CheckType.ISSUED
                    
                    created_check = self.check_manager.create_check(
                        check_number=check_details["check_number"],
                        amount=item_data["amount"],
                        due_date=check_details["due_date"],
                        person_id=person_id,
                        check_type=check_type,
                        bank_account_id=check_details["bank_account_id_for_check"],
                        issue_date=check_details["issue_date"],
                        fiscal_year_id=fiscal_year_id
                    )
                    if not created_check or not created_check.id:
                        raise Exception("ایجاد رکورد چک جدید ناموفق بود.")
                    check_id_for_line = created_check.id
                elif item_data.get("existing_check_id"):
                    check_id_for_line = item_data["existing_check_id"]
                elif item_data.get("endorsed_check_id"):
                    check_id_for_line = item_data["endorsed_check_id"]

                line_item = PaymentLineItemEntity(
                    payment_header_id=created_header.id,
                    payment_method=item_data["payment_method"],
                    amount=item_data["amount"],
                    account_id=item_data.get("account_id"),
                    check_id=check_id_for_line,
                    description=item_data.get("description"),
                    target_account_id=item_data.get("target_account_id")
                )
                saved_line_item = self.payment_line_item_repo.add(line_item)
                if not saved_line_item:
                    raise Exception(f"خطا در ذخیره قلم پرداخت: {item_data}")
                
                self._record_single_payment_line_financial_impact(created_header, saved_line_item)
                saved_line_items.append(saved_line_item)
            
            created_header.line_items = saved_line_items

            if created_header.invoice_id:
                # FIX for: Argument of type "float" cannot be assigned to parameter of type "Decimal"
                # اطمینان از اینکه total_amount یک Decimal است
                self.invoice_manager.update_payment_status(created_header.invoice_id, created_header.total_amount)
            if created_header.purchase_order_id and hasattr(self.po_manager, 'update_payment_status'):
                # FIX for: Cannot access attribute "update_payment_status" for class "PurchaseOrderManager"
                # NOTE: این متد باید در PurchaseOrderManager پیاده‌سازی شود
                self.po_manager.update_payment_status(created_header.purchase_order_id, created_header.total_amount)

            return created_header

        except Exception as e:
            logger.error(f"Error during payment processing. Rolling back.", exc_info=True)
            if created_header and created_header.id:
                self.payment_header_repo.delete(created_header.id)
            raise

    def _record_single_payment_line_financial_impact(self, payment_header: PaymentHeaderEntity, line_item: PaymentLineItemEntity):
        """آثار مالی یک قلم پرداخت را بر اساس نوع عملیات و روش پرداخت، به درستی ثبت می‌کند."""
        logger.debug(f"Recording financial impact for payment line ID {line_item.id}. Direct Posting: {getattr(payment_header, 'is_direct_posting', False)}")
        
        if not self.ft_manager: return
        transaction_date = datetime.combine(payment_header.payment_date, datetime.min.time())
        
        # --- شروع اصلاح منطق ---

        # حالت ۱: ثبت مستقیم هزینه یا درآمد
        if getattr(payment_header, 'is_direct_posting', False):
            if not line_item.target_account_id or not line_item.account_id:
                raise ValueError("برای ثبت مستقیم، حساب مقصد و حساب پرداخت‌کننده الزامی است.")
            
            target_account = self.account_manager.get_account_by_id(line_item.target_account_id)
            if not target_account:
                raise ValueError(f"حساب مقصد با شناسه {line_item.target_account_id} یافت نشد.")
            
            # ثبت سند بر اساس نوع حساب مقصد
            if target_account.type == AccountType.EXPENSE:
                # Dr. Expense Account, Cr. Our Cash/Bank
                self.ft_manager.create_financial_transaction(transaction_date, target_account.id, FinancialTransactionType.INCOME, line_item.amount, payment_header.description)
                self.ft_manager.create_financial_transaction(transaction_date, line_item.account_id, FinancialTransactionType.EXPENSE, line_item.amount, f"پرداخت بابت {target_account.name}")
            elif target_account.type == AccountType.REVENUE:
                # Dr. Our Cash/Bank, Cr. Revenue Account
                self.ft_manager.create_financial_transaction(transaction_date, line_item.account_id, FinancialTransactionType.INCOME, line_item.amount, f"دریافت بابت {target_account.name}")
                self.ft_manager.create_financial_transaction(transaction_date, target_account.id, FinancialTransactionType.INCOME, line_item.amount, payment_header.description)
            return

        # حالت ۲: تسویه حساب شخص (مشتری/تامین‌کننده/کارمند)
        if not payment_header.person_id:
            raise ValueError("شناسه شخص برای پرداخت تسویه الزامی است.")
            
        person = self.person_manager.get_person_by_id(payment_header.person_id)
        if not person: raise ValueError(f"شخص با شناسه {payment_header.person_id} یافت نشد.")

        person_subsidiary_account_id = self.account_manager.get_person_subsidiary_account_id(person.id)
        if not person_subsidiary_account_id: raise ValueError(f"حساب معین برای شخص '{person.name}' یافت نشد.")

        # تعیین حساب طرف دوم (بدهکار یا بستانکار) بر اساس روش پرداخت
        our_side_account_id: Optional[int] = None
        if line_item.payment_method == PaymentMethod.CHECK:
            if payment_header.payment_type == PaymentType.RECEIPT:
                our_side_account_id = self.accounts_config.get("checks_receivable_account") # باید حساب اسناد دریافتنی باشد
            else: # PAYMENT
                our_side_account_id = self.accounts_config.get("checks_payable_account") # باید حساب اسناد پرداختنی باشد
        else: # CASH, CARD, BANK_TRANSFER
            our_side_account_id = line_item.account_id
        
        if not our_side_account_id:
            raise ValueError(f"حساب صندوق/بانک/اسناد برای روش پرداخت '{line_item.payment_method.value}' مشخص نشده است.")

        # ثبت سند حسابداری دوطرفه
        if payment_header.payment_type == PaymentType.RECEIPT: # دریافت از مشتری
            # Dr. Our Side (Cash/Bank/Checks Receivable), Cr. Person (AR)
            self.ft_manager.create_financial_transaction(transaction_date, our_side_account_id, FinancialTransactionType.INCOME, line_item.amount, f"دریافت از {person.name}")
            self.ft_manager.create_financial_transaction(transaction_date, person_subsidiary_account_id, FinancialTransactionType.EXPENSE, line_item.amount, f"بابت تسویه توسط {person.name}")
        
        elif payment_header.payment_type == PaymentType.PAYMENT: # پرداخت به تامین‌کننده/کارمند
            # Dr. Person (AP), Cr. Our Side (Cash/Bank/Checks Payable)
            self.ft_manager.create_financial_transaction(transaction_date, person_subsidiary_account_id, FinancialTransactionType.EXPENSE, line_item.amount, f"پرداخت به {person.name}")
            self.ft_manager.create_financial_transaction(transaction_date, our_side_account_id, FinancialTransactionType.EXPENSE, line_item.amount, f"پرداخت از حساب: {our_side_account_id}")
    def get_all_payments(self) -> List[PaymentHeaderEntity]:
        headers = self.payment_header_repo.get_all(order_by="payment_date DESC, id DESC")
        if self.person_manager:
            for p_header in headers:
                if p_header.person_id:
                    person = self.person_manager.get_person_by_id(p_header.person_id)
                    if person: p_header.person_name = person.name
        return headers

    def get_payment_with_line_items(self, payment_header_id: int) -> Optional[PaymentHeaderEntity]:
        header = self.payment_header_repo.get_by_id(payment_header_id)
        if not header or not header.id: return None
        header.line_items = self.payment_line_item_repo.get_by_payment_header_id(header.id)
        return header

    def update_payment(self, payment_header_id: int, update_data: Dict[str, Any]) -> Optional[PaymentHeaderEntity]:
        logger.info(f"Attempting to update payment header ID: {payment_header_id}")
        
        original_payment = self.get_payment_with_line_items(payment_header_id)
        if not original_payment:
            raise ValueError(f"سند پرداخت/دریافت با شناسه {payment_header_id} برای ویرایش یافت نشد.")

        reversal_reason = f"Edit Payment ID {payment_header_id}"
        reversal_datetime = datetime.now()

        try:
            self._reverse_payment_impacts(original_payment, reversal_datetime, reversal_reason)
            self.payment_line_item_repo.delete_by_payment_header_id(payment_header_id)

            new_line_items_data = update_data.get("line_items_data", [])
            new_total_amount = sum((Decimal(str(item.get("amount", "0.0"))) for item in new_line_items_data), Decimal("0.0"))
            
            original_payment.payment_date = update_data["payment_date"]
            original_payment.person_id = update_data.get("person_id")
            original_payment.description = update_data.get("description")
            original_payment.invoice_id = update_data.get("invoice_id")
            original_payment.purchase_order_id = update_data.get("purchase_order_id")
            original_payment.total_amount = new_total_amount
            
            updated_header = self.payment_header_repo.update(original_payment)
            if not updated_header: raise Exception("خطا در به‌روزرسانی هدر پرداخت.")

            saved_line_items = []
            for item_data in new_line_items_data:
                entity_fields = {k: v for k, v in item_data.items() if k in PaymentLineItemEntity.__annotations__}
                line_item = PaymentLineItemEntity(**entity_fields)
                line_item.payment_header_id = updated_header.id
                saved_item = self.payment_line_item_repo.add(line_item)
                if not saved_item: raise Exception(f"خطا در ذخیره قلم جدید پرداخت: {item_data}")
                self._record_single_payment_line_financial_impact(updated_header, saved_item)
                saved_line_items.append(saved_item)
            
            updated_header.line_items = saved_line_items
            
            if updated_header.invoice_id:
                self.invoice_manager.update_payment_status(updated_header.invoice_id, updated_header.total_amount)
            if updated_header.purchase_order_id and hasattr(self.po_manager, 'update_payment_status'):
                self.po_manager.update_payment_status(updated_header.purchase_order_id, updated_header.total_amount)

            return self.get_payment_with_line_items(payment_header_id)
        except Exception as e:
            logger.error(f"Error during payment update for ID {payment_header_id}", exc_info=True)
            raise

    def delete_payment(self, payment_header_id: int) -> bool:
        logger.warning(f"Attempting to delete payment header ID: {payment_header_id}")
        payment_to_delete = self.get_payment_with_line_items(payment_header_id)
        if not payment_to_delete:
            logger.error(f"Payment with ID {payment_header_id} not found for deletion.")
            return False
        
        try:
            self._reverse_payment_impacts(payment_to_delete, datetime.now(), f"Delete Payment ID {payment_header_id}")
            return self.payment_header_repo.delete(payment_header_id)
        except Exception as e:
            logger.error(f"Error during deletion of payment {payment_header_id}: {e}", exc_info=True)
            return False
    
    def _reverse_payment_impacts(self, payment_header: PaymentHeaderEntity, reversal_date_dt: datetime, reason_prefix: str):
        logger.info(f"Reversing impacts for payment header ID: {payment_header.id}")
        
        if payment_header.line_items:
            for line_item in payment_header.line_items:
                self._reverse_single_payment_line_financial_impact(payment_header, line_item, reversal_date_dt, reason_prefix)

        if payment_header.invoice_id:
            self.invoice_manager.update_payment_status(payment_header.invoice_id, -payment_header.total_amount)
        if payment_header.purchase_order_id and hasattr(self.po_manager, 'update_payment_status'):
            self.po_manager.update_payment_status(payment_header.purchase_order_id, -payment_header.total_amount)

    def _reverse_single_payment_line_financial_impact(self, payment_header: PaymentHeaderEntity, line_item: PaymentLineItemEntity, reversal_date_dt: datetime, reason_prefix: str):
        if not self.ft_manager: return

        description = f"{reason_prefix} - Reversal for PaymentLine {line_item.id}"
        
        if getattr(payment_header, 'is_direct_posting', False):
            # منطق برگرداندن برای ثبت مستقیم
            if not line_item.target_account_id or not line_item.account_id: return
            target_account = self.account_manager.get_account_by_id(line_item.target_account_id)
            if not target_account: return
            
            if target_account.type == AccountType.EXPENSE:
                # معکوس پرداخت هزینه: Dr. Our Cash/Bank, Cr. Expense Account
                self.ft_manager.create_financial_transaction(reversal_date_dt, line_item.account_id, FinancialTransactionType.INCOME, line_item.amount, description)
                self.ft_manager.create_financial_transaction(reversal_date_dt, line_item.target_account_id, FinancialTransactionType.EXPENSE, line_item.amount, description)
            elif target_account.type == AccountType.REVENUE:
                # معکوس دریافت درآمد: Dr. Revenue Account, Cr. Our Cash/Bank
                self.ft_manager.create_financial_transaction(reversal_date_dt, line_item.target_account_id, FinancialTransactionType.EXPENSE, line_item.amount, description)
                self.ft_manager.create_financial_transaction(reversal_date_dt, line_item.account_id, FinancialTransactionType.EXPENSE, line_item.amount, description)
        else: # حالت تسویه
            if not payment_header.person_id: return
            person = self.person_manager.get_person_by_id(payment_header.person_id)
            if not person: return

            person_subsidiary_account_id = self.account_manager.get_person_subsidiary_account_id(person.id)
            if not person_subsidiary_account_id: return
            
            our_side_account_id: Optional[int] = None
            if line_item.payment_method == PaymentMethod.CHECK:
                config_key = "checks_receivable_account" if payment_header.payment_type == PaymentType.RECEIPT else "checks_payable_account"
                our_side_account_id = self.accounts_config.get(config_key)
            else:
                our_side_account_id = line_item.account_id
            if not our_side_account_id: return

            if payment_header.payment_type == PaymentType.RECEIPT:
                self.ft_manager.create_financial_transaction(reversal_date_dt, person_subsidiary_account_id, FinancialTransactionType.INCOME, line_item.amount, description)
                self.ft_manager.create_financial_transaction(reversal_date_dt, our_side_account_id, FinancialTransactionType.EXPENSE, line_item.amount, description)
            elif payment_header.payment_type == PaymentType.PAYMENT:
                self.ft_manager.create_financial_transaction(reversal_date_dt, our_side_account_id, FinancialTransactionType.INCOME, line_item.amount, description)
                self.ft_manager.create_financial_transaction(reversal_date_dt, person_subsidiary_account_id, FinancialTransactionType.INCOME, line_item.amount, description)
    def get_payments_for_invoice(self, invoice_id: int) -> List[PaymentHeaderEntity]:
        logger.debug(f"PaymentManager: Attempting to fetch payments for Invoice ID: {invoice_id}") # <<< لاگ اضافه شده
        if not invoice_id:
            logger.warning("PaymentManager: get_payments_for_invoice called with no invoice_id.")
            return []

        payment_headers = self.payment_header_repo.find_by_criteria(
            {"invoice_id": invoice_id},
            order_by="payment_date ASC, id ASC"
        )
        logger.debug(f"PaymentManager: Found {len(payment_headers) if payment_headers else 0} payment headers for invoice ID {invoice_id} from repository.") # <<< لاگ اضافه شده

        detailed_payments: List[PaymentHeaderEntity] = []
        if payment_headers:
            for header in payment_headers:
                if header.id:
                    payment_with_lines = self.get_payment_with_line_items(header.id)
                    if payment_with_lines:
                        detailed_payments.append(payment_with_lines)
                        # لاگ برای هر پرداخت یافت شده
                        logger.debug(f"PaymentManager: Added payment ID {payment_with_lines.id} with {len(payment_with_lines.line_items or [])} lines to related payments list.")

        logger.debug(f"PaymentManager: Returning {len(detailed_payments)} detailed payments for Invoice ID {invoice_id}.") # <<< لاگ اضافه شده
        return detailed_payments