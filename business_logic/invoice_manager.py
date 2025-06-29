# src/business_logic/invoice_manager.py

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# --- Entity و Constant Imports ---
# FIX: افزودن ProductType و AccountType برای رفع NameError
from .entities.invoice_entity import InvoiceEntity
from .entities.invoice_item_entity import InvoiceItemEntity
from src.constants import (
    InvoiceType, PersonType, InvoiceStatus, 
    InventoryMovementType, ReferenceType, FinancialTransactionType, 
    DATE_FORMAT, ProductType, AccountType
)

# --- Manager and Repository Imports (با استفاده از TYPE_CHECKING برای جلوگیری از وابستگی دورانی) ---
if TYPE_CHECKING:
    from .product_manager import ProductManager
    from .person_manager import PersonManager
    from .financial_transaction_manager import FinancialTransactionManager
    from .account_manager import AccountManager
    from ..data_access.invoices_repository import InvoicesRepository
    from ..data_access.invoice_items_repository import InvoiceItemsRepository

import logging
logger = logging.getLogger(__name__)

# مقادیر پیش‌فرض شناسه‌های حساب برای عملیات فاکتور
DEFAULT_ACCOUNTS_CONFIG_FOR_INVOICE = {
    "accounts_receivable": 1,
    "sales_revenue": 2,
    "inventory_asset": 3,
    "accounts_payable": 4,
    "purchase_expense": 5,
    "cost_of_goods_sold": 602
}

class InvoiceManager:
    def __init__(self, 
                 invoices_repository: 'InvoicesRepository',
                 invoice_items_repository: 'InvoiceItemsRepository',
                 product_manager: 'ProductManager',
                 ft_manager: 'FinancialTransactionManager',
                 person_manager: 'PersonManager',
                 account_manager: 'AccountManager',
                 accounts_config: Optional[Dict[str, int]] = None
                 ):
        """
        Initializes the InvoiceManager.
        """
        # FIX: اطمینان از مقداردهی اولیه تمام فیلدها با نام‌گذاری یکسان
        self.invoices_repo = invoices_repository
        self.invoice_items_repo = invoice_items_repository
        self.product_manager = product_manager
        self.ft_manager = ft_manager
        self.person_manager = person_manager
        self.account_manager = account_manager
        self.accounts_config = accounts_config if accounts_config is not None else DEFAULT_ACCOUNTS_CONFIG_FOR_INVOICE
    

    def _generate_invoice_number(self, invoice_type: InvoiceType) -> str:
        """Generates a new, unique invoice number with a prefix."""
        prefix = "INV-S-" if invoice_type == InvoiceType.SALE else "INV-P-"
        # Using a timestamp ensures uniqueness
        timestamp = int(datetime.now().timestamp()*2)
        return f"{prefix}{timestamp}"    
    def get_invoice_with_items(self, invoice_id: int) -> Optional[InvoiceEntity]:
        """یک فاکتور و اقلام آن را واکشی کرده و نام محصولات را برای نمایش پر می‌کند."""
        logger.debug(f"Fetching invoice with items for ID: {invoice_id}")
        invoice = self.invoices_repo.get_by_id(invoice_id)
        if not invoice:
            return None
        
        invoice.items = self.invoice_items_repo.get_by_invoice_id(invoice.id)
        
        if invoice.items and self.product_manager:
            for item in invoice.items:
                if item.product_id:
                    product = self.product_manager.get_product_by_id(item.product_id)
                    if product:
                        item.product_name = product.name
                        item.unit_of_measure = product.unit_of_measure
        return invoice


    def get_all_invoices_summary(self) -> List[InvoiceEntity]:
        """لیستی از تمام فاکتورها را برای نمایش در جدول اصلی برمی‌گرداند."""
        logger.debug("Fetching all invoice summaries.")
        all_invoices = self.invoices_repo.get_all(order_by="invoice_date DESC, id DESC")
        if self.person_manager:
            for inv in all_invoices:
                if inv.person_id:
                    person = self.person_manager.get_person_by_id(inv.person_id)
                    if person:
                        inv.person_name = person.name 
        return all_invoices

        return all_invoices
    def create_invoice(self, 
                       invoice_date: date, 
                       person_id: int, 
                       invoice_type: InvoiceType, 
                       items_data: List[Dict[str, Any]],
                       due_date: Optional[date] = None, 
                       description: Optional[str] = None, 
                       fiscal_year_id: Optional[int] = None,
                       invoice_number_override: Optional[str] = None) -> Optional[InvoiceEntity]:
        
        logger.info(f"Attempting to create {invoice_type.value} invoice for Person ID {person_id} with {len(items_data)} items.")
        # ... (اعتبارسنجی‌ها مانند قبل) ...
        
        calculated_total = sum((Decimal(str(item.get('quantity', '0'))) * Decimal(str(item.get('unit_price', '0')))) for item in items_data)
        
        processed_items: List[InvoiceItemEntity] = [
            InvoiceItemEntity(
                product_id=item_dict.get('product_id'),
                quantity=Decimal(str(item_dict.get('quantity', '0'))),
                unit_price=Decimal(str(item_dict.get('unit_price', '0'))),
                description=item_dict.get('description')
            ) for item_dict in items_data
        ]

        invoice_number = invoice_number_override or self._generate_invoice_number(invoice_type)
        if self.invoices_repo.get_by_invoice_number(invoice_number):
            raise ValueError(f"شماره فاکتور '{invoice_number}' تکراری است.")
            
        header_entity = InvoiceEntity(
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            person_id=person_id,
            invoice_type=invoice_type,
            is_paid=False,
            status=InvoiceStatus.ISSUED,
            fiscal_year_id=fiscal_year_id,
            due_date=due_date,
            total_amount=calculated_total, 
            paid_amount=Decimal("0.0"), 
            description=description
        )

        created_header: Optional[InvoiceEntity] = None
        try:
            created_header = self.invoices_repo.add(header_entity)
            if not created_header or not created_header.id:
                raise Exception("خطا در ذخیره هدر فاکتور در پایگاه داده.")
            
            for item in processed_items:
                item.invoice_id = created_header.id
                if not self.invoice_items_repo.add(item):
                     raise Exception(f"خطا در ذخیره قلم فاکتور برای کالا ID {item.product_id}.")
            
            created_header.items = processed_items
            
            self._record_financial_impact(created_header)
            self._record_stock_movements(created_header)
            
            return self.get_invoice_with_items(created_header.id)

        except Exception as e:
            logger.error(f"Error during Invoice creation for {invoice_number}. Rolling back if possible.", exc_info=True)
            if created_header and created_header.id:
                self.invoices_repo.delete(created_header.id)
            raise e
    
    def update_payment_status(self, invoice_id: int, payment_amount_change: Decimal):
        """
        وضعیت پرداخت یک فاکتور را بر اساس یک پرداخت/دریافت جدید به‌روز می‌کند.
        """
        invoice = self.invoices_repo.get_by_id(invoice_id)
        if not invoice:
            logger.warning(f"Invoice ID {invoice_id} not found for updating payment status.")
            return
        
        logger.info(f"Updating payment status for Invoice ID {invoice_id}. Change: {payment_amount_change}. Current Paid: {invoice.paid_amount}")
        
        # --- شروع اصلاحات ---
        # اطمینان حاصل کنید که تمام مقادیر قبل از عملیات، از نوع Decimal هستند.
        try:
            current_paid_dec = Decimal(str(invoice.paid_amount or '0.0'))
            change_dec = Decimal(str(payment_amount_change or '0.0'))
            total_amount_dec = Decimal(str(invoice.total_amount or '0.0'))
        except InvalidOperation:
            logger.error(f"Invalid amount format while updating payment status for invoice ID {invoice_id}.")
            return

        new_paid_amount = current_paid_dec + change_dec
        
        # Clamp paid_amount (محدود کردن مقدار پرداخت شده بین صفر و مبلغ کل)
        if new_paid_amount > total_amount_dec:
            logger.warning(f"Paid amount {new_paid_amount} exceeds total {total_amount_dec} for invoice {invoice_id}. Clamping.")
            new_paid_amount = total_amount_dec
        if new_paid_amount < Decimal("0.0"):
            logger.warning(f"Paid amount {new_paid_amount} is negative for invoice {invoice_id}. Clamping to 0.")
            new_paid_amount = Decimal("0.0")

        invoice.paid_amount = new_paid_amount

        tolerance = Decimal("0.001")
        if (total_amount_dec - new_paid_amount).copy_abs() <= tolerance:
            invoice.is_paid = True
            invoice.status = InvoiceStatus.FULLY_PAID
        elif new_paid_amount > tolerance:
            invoice.is_paid = False
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        else: # اگر مبلغ پرداخت شده صفر است
            invoice.is_paid = False
            invoice.status = InvoiceStatus.ISSUED

        self.invoices_repo.update(invoice)
        logger.info(f"Payment status updated for Invoice ID {invoice_id}. New Paid: {invoice.paid_amount}, IsPaid: {invoice.is_paid}, Status: {invoice.status.value}")
        # --- پایان اصلاحات ---
    def _reverse_current_financial_state(self, 
                                         invoice_to_reverse: InvoiceEntity, 
                                         reversal_date_dt: datetime, 
                                         reason_prefix: str):
        """
        آثار مالی آخرین وضعیت ذخیره شده یک فاکتور را برمی‌گرداند (خنثی می‌کند).
        این متد تراکنش‌های مالی جدیدی با اثر معکوس ایجاد می‌کند.
        """
        logger.info(f"Reversing current financial state for Invoice ID: {invoice_to_reverse.id} "
                    f"(Number: {invoice_to_reverse.invoice_number}) with Total Amount: {invoice_to_reverse.total_amount} "
                    f"due to: {reason_prefix}")

        if not invoice_to_reverse.id or not invoice_to_reverse.fiscal_year_id:
            logger.error("Cannot reverse current financial state for invoice: invoice_id or fiscal_year_id is missing.")
            raise ValueError("اطلاعات لازم برای برگرداندن آثار مالی فاکتور ناقص است (شناسه یا سال مالی).")
        
        # اگر مبلغ کل فاکتور برای برگرداندن صفر یا بسیار نزدیک به صفر است، عملیات برگشت معنی ندارد
        if Decimal(str(invoice_to_reverse.total_amount)).copy_abs() < Decimal("0.001"):
             logger.warning(f"Total amount for invoice ID {invoice_to_reverse.id} to reverse is effectively zero. "
                            "Skipping financial reversal for this invoice state.")
             return

        transaction_date_to_use = reversal_date_dt # تاریخ تراکنش‌های برگشتی
        base_description_reversal = f"{reason_prefix} - Reversal for Invoice {invoice_to_reverse.invoice_number}"
        
        # --- منطق برگرداندن آثار مالی بر اساس نوع فاکتور ---
        if invoice_to_reverse.invoice_type == InvoiceType.SALE:
            ar_account_id = self.accounts_config.get("accounts_receivable")
            revenue_account_id = self.accounts_config.get("sales_revenue")
            # cogs_account_id = self.accounts_config.get("cost_of_goods_sold") # برای برگرداندن بهای تمام شده
            # inventory_asset_id = self.accounts_config.get("inventory_asset") # برای برگرداندن بهای تمام شده

            if not ar_account_id or not revenue_account_id:
                raise ValueError("تنظیمات حساب‌های دریافتنی یا درآمد فروش برای برگرداندن آثار مالی فاکتور فروش یافت نشد.")

            # ۱. برگرداندن (بستانکار کردن) حساب دریافتنی کل
            logger.debug(f"  Reversing AR: Cr. Account ID {ar_account_id}, Amount {invoice_to_reverse.total_amount}")
            self.ft_manager.create_financial_transaction(
                transaction_date=transaction_date_to_use, 
                account_id=ar_account_id,
                transaction_type=FinancialTransactionType.EXPENSE, # برای بستانکار کردن حساب دارایی
                amount=invoice_to_reverse.total_amount, 
                description=f"{base_description_reversal} (Accounts Receivable)", 
                fiscal_year_id=invoice_to_reverse.fiscal_year_id, 
                reference_id=invoice_to_reverse.id, 
                reference_type=ReferenceType.INVOICE_REVERSAL # نوع مرجع جدید
            )
            # ۲. برگرداندن (بدهکار کردن) حساب درآمد فروش
            logger.debug(f"  Reversing Revenue: Dr. Account ID {revenue_account_id}, Amount {invoice_to_reverse.total_amount}")
            self.ft_manager.create_financial_transaction(
                transaction_date=transaction_date_to_use, 
                account_id=revenue_account_id,
                transaction_type=FinancialTransactionType.EXPENSE, # برای بدهکار کردن حساب درآمد
                amount=invoice_to_reverse.total_amount, 
                description=f"{base_description_reversal} (Sales Revenue)", 
                fiscal_year_id=invoice_to_reverse.fiscal_year_id, 
                reference_id=invoice_to_reverse.id, 
                reference_type=ReferenceType.INVOICE_REVERSAL
            )
            # TODO: برگرداندن آثار بهای تمام شده کالای فروش رفته (COGS)
            # اگر COGS ثبت شده بود، باید: Dr. Inventory, Cr. COGS Account

        elif invoice_to_reverse.invoice_type == InvoiceType.PURCHASE:
            ap_account_id = self.accounts_config.get("accounts_payable")
            
            # تعیین حساب بدهکار اصلی (موجودی کالا یا هزینه خرید) که در ثبت اولیه بدهکار شده بود
            original_debit_account_id: Optional[int] = None
            if invoice_to_reverse.items: # نیاز به اقلام برای تشخیص نوع حساب بدهکار
                is_inventory_item_present = any(
                    self.product_manager.get_product_by_id(item.product_id).product_type != ProductType.SERVICE # type: ignore
                    for item in invoice_to_reverse.items if item.product_id # اطمینان از وجود product_id
                )
                if is_inventory_item_present:
                    original_debit_account_id = self.accounts_config.get("inventory_asset")
            
            if not original_debit_account_id: # اگر کالای انباری نبود یا اقلامی وجود نداشت، هزینه خرید در نظر گرفته می‌شود
                original_debit_account_id = self.accounts_config.get("purchase_expense")

            if not ap_account_id or not original_debit_account_id:
                raise ValueError("تنظیمات حساب‌های پرداختنی یا حساب بدهکار (موجودی/هزینه) برای برگرداندن آثار فاکتور خرید یافت نشد.")

            # ۱. برگرداندن (بدهکار کردن) حساب پرداختنی کل
            logger.debug(f"  Reversing AP: Dr. Account ID {ap_account_id}, Amount {invoice_to_reverse.total_amount}")
            self.ft_manager.create_financial_transaction(
                transaction_date=transaction_date_to_use, 
                account_id=ap_account_id,
                transaction_type=FinancialTransactionType.EXPENSE, # برای بدهکار کردن حساب بدهی
                amount=invoice_to_reverse.total_amount, 
                description=f"{base_description_reversal} (Accounts Payable)", 
                fiscal_year_id=invoice_to_reverse.fiscal_year_id, 
                reference_id=invoice_to_reverse.id, 
                reference_type=ReferenceType.INVOICE_REVERSAL
            )
            # ۲. برگرداندن (بستانکار کردن) حساب موجودی کالا / هزینه خرید
            original_debit_account_entity = self.account_manager.get_account_by_id(original_debit_account_id)
            if not original_debit_account_entity:
                 raise ValueError(f"حساب بدهکار اصلی با شناسه {original_debit_account_id} یافت نشد.")
            
            # اگر حساب اصلی دارایی بود (موجودی کالا)، برای بستانکار کردنش از EXPENSE استفاده می‌کنیم
            # اگر حساب اصلی هزینه بود (هزینه خرید)، برای بستانکار کردنش (کاهش هزینه) از INCOME استفاده می‌کنیم
            reversal_type_for_debit_acc = FinancialTransactionType.EXPENSE if original_debit_account_entity.type == AccountType.ASSET else FinancialTransactionType.INCOME
            
            logger.debug(f"  Reversing Inventory/Expense: Cr. Account ID {original_debit_account_id}, Amount {invoice_to_reverse.total_amount}, Type: {reversal_type_for_debit_acc.value}")
            self.ft_manager.create_financial_transaction(
                transaction_date=transaction_date_to_use, 
                account_id=original_debit_account_id,
                transaction_type=reversal_type_for_debit_acc,
                amount=invoice_to_reverse.total_amount, 
                description=f"{base_description_reversal} (Inventory/Purchase Expense)", 
                fiscal_year_id=invoice_to_reverse.fiscal_year_id, 
                reference_id=invoice_to_reverse.id, 
                reference_type=ReferenceType.INVOICE_REVERSAL
            )
        
        logger.info(f"Financial state for Invoice ID {invoice_to_reverse.id} (Amount: {invoice_to_reverse.total_amount}) reversed successfully.")

    def _reverse_invoice_stock_movements(self, items: List[InvoiceItemEntity], invoice_type: InvoiceType, reversal_date_dt: datetime, invoice_id: int, invoice_number: str, reason_prefix: str):
        logger.info(f"Reversing stock movements for items of Invoice ID: {invoice_id} due to: {reason_prefix}")
        for item in items:
            product = self.product_manager.get_product_by_id(item.product_id) # type: ignore
            if product and product.product_type != ProductType.SERVICE:
                original_qty_effect = -item.quantity if invoice_type == InvoiceType.SALE else item.quantity
                reversal_qty_change = -original_qty_effect
                
                reversal_movement_type: InventoryMovementType
                if invoice_type == InvoiceType.SALE:
                    reversal_movement_type = InventoryMovementType.SALE_RETURN 
                elif invoice_type == InvoiceType.PURCHASE:
                     reversal_movement_type = InventoryMovementType.PURCHASE_RETURN
                else:
                    reversal_movement_type = InventoryMovementType.ADJUSTMENT_IN if reversal_qty_change > 0 else InventoryMovementType.ADJUSTMENT_OUT

                logger.debug(f"  Reversing stock for Product ID {item.product_id}: changing by {reversal_qty_change}, type {reversal_movement_type.value}")
                self.product_manager.adjust_stock(
                    product_id=item.product_id, # type: ignore
                    quantity_change=reversal_qty_change,
                    movement_type=reversal_movement_type, 
                    movement_date=reversal_date_dt,
                    reference_id=item.id, 
                    reference_type=ReferenceType.INVOICE_ITEM_REVERSAL, 
                    description=f"{reason_prefix} - Stock reversal for Inv: {invoice_number}, Item: {product.name}"
                )
        logger.info(f"Stock movements for items of Invoice ID {invoice_id} reversed successfully.")
    def _record_financial_impact(self, invoice: InvoiceEntity):
        logger.info(f"Attempting to record financial impact for Invoice ID: {invoice.id}")
        if not all([self.ft_manager, self.account_manager, invoice.id, invoice.fiscal_year_id]):
             logger.warning("Financial Transaction Manager, Account Manager, or key invoice IDs are missing. Skipping financial impact.")
             return

        transaction_date_dt = datetime.combine(invoice.invoice_date, datetime.min.time())
        description = f"Invoice {invoice.invoice_number} - {invoice.invoice_type.value}"
        
        ar_ap_account_id = self.account_manager.get_person_subsidiary_account_id(invoice.person_id)
        if not ar_ap_account_id:
            raise ValueError(f"Could not find AR/AP account for Person ID {invoice.person_id}")

        if invoice.invoice_type == InvoiceType.SALE:
            revenue_account_id = self.account_manager.get_default_account_id_by_name("فروش")
            if not revenue_account_id:
                 raise ValueError("حساب پیش‌فرض 'فروش' یافت نشد.")

            # --- شروع اصلاح منطق حسابداری ---
            # برای فاکتور فروش:
            # ۱. حساب‌های دریافتنی (دارایی) بدهکار (افزایش) می‌شود. نوع تراکنش: INCOME
            # ۲. حساب درآمد فروش (درآمد) بستانکار (افزایش) می‌شود. نوع تراکنش: INCOME

            logger.debug(f"  Recording financial impact: Dr. Accounts Receivable (ID: {ar_ap_account_id}), Amount: {invoice.total_amount}")
            self.ft_manager.create_financial_transaction(
                transaction_date=transaction_date_dt, 
                account_id=ar_ap_account_id, 
                transaction_type=FinancialTransactionType.INCOME, # <<< اصلاح شد: برای افزایش دارایی
                amount=invoice.total_amount, 
                description=f"{description} (AR)"
            )

            logger.debug(f"  Recording financial impact: Cr. Sales Revenue (ID: {revenue_account_id}), Amount: {invoice.total_amount}")
            self.ft_manager.create_financial_transaction(
                transaction_date=transaction_date_dt, 
                account_id=revenue_account_id, 
                transaction_type=FinancialTransactionType.INCOME, # صحیح بود
                amount=invoice.total_amount, 
                description=f"{description} (Revenue)"
            )

        # --- شروع بخش جدید برای فاکتور خرید ---
        elif invoice.invoice_type == InvoiceType.PURCHASE:
            ap_account_id = ar_ap_account_id # برای خوانایی بهتر، نام متغیر را تغییر می‌دهیم
            
            # تعیین اینکه آیا فاکتور شامل کالای انباری است یا فقط خدمات
            is_inventory_purchase = False
            if invoice.items:
                for item in invoice.items:
                    product = self.product_manager.get_product_by_id(item.product_id)
                    if product and product.product_type != ProductType.SERVICE:
                        is_inventory_purchase = True
                        break
            
            if is_inventory_purchase:
                debit_account_id = self.accounts_config.get("inventory_asset")
                if not debit_account_id: raise ValueError("حساب پیش‌فرض 'موجودی کالا' یافت نشد.")
                debit_desc_suffix = "(Inventory)"
            else: # اگر فقط خدمت است
                debit_account_id = self.accounts_config.get("purchase_expense")
                if not debit_account_id: raise ValueError("حساب پیش‌فرض 'هزینه خرید' یافت نشد.")
                debit_desc_suffix = "(Purchase Expense)"

            # ۱. بدهکار کردن حساب موجودی کالا / هزینه خرید
            # برای هر دو (که یکی دارایی و دیگری هزینه است)، افزایش آن‌ها با تراکنش INCOME ثبت می‌شود
            self.ft_manager.create_financial_transaction(transaction_date_dt, debit_account_id, FinancialTransactionType.INCOME, invoice.total_amount, f"{description} {debit_desc_suffix}")

            # ۲. بستانکار کردن حساب پرداختنی (یک بدهی افزایش می‌یابد)
            self.ft_manager.create_financial_transaction(transaction_date_dt, ap_account_id, FinancialTransactionType.INCOME, invoice.total_amount, f"{description} (AP)")
        # --- پایان بخش جدید برای فاکتور خرید ---
            # --- پایان اصلاح ---
    def _record_stock_movements(self, invoice: InvoiceEntity):
        """
        برای هر قلم کالای موجود در فاکتور، یک حرکت انبار ثبت می‌کند.
        """
        logger.info(f"Recording stock movements for items of Invoice ID: {invoice.id}")
        if not invoice.items:
            logger.warning(f"No items found in invoice {invoice.id} to record stock movements.")
            return

        movement_type = InventoryMovementType.SALE if invoice.invoice_type == InvoiceType.SALE else InventoryMovementType.PURCHASE_RECEIPT
        
        for item in invoice.items:
            product = self.product_manager.get_product_by_id(item.product_id)
            # فقط برای کالاهایی که خدماتی نیستند، حرکت انبار ثبت کن
            if product and product.product_type != ProductType.SERVICE:
                # مقدار برای فروش منفی و برای خرید مثبت است
                quantity_change = -item.quantity if invoice.invoice_type == InvoiceType.SALE else item.quantity
                
                description = f"مربوط به فاکتور شماره {invoice.invoice_number}"

                self.product_manager.adjust_stock(
                    product_id=item.product_id,
                    quantity_change=quantity_change,
                    movement_type=movement_type,
                    movement_date=datetime.combine(invoice.invoice_date, datetime.min.time()),
                    reference_id=invoice.id,
                    reference_type=ReferenceType.INVOICE,
                    description=description
                )

    def _reverse_financial_impact(self, invoice_to_reverse: InvoiceEntity, reversal_date_dt: datetime, reason_prefix: str) -> bool:
        logger.info(f"Reversing financial state for Invoice ID {invoice_to_reverse.id}")
        if not self.ft_manager: return True

        description = f"{reason_prefix} - Reversal for Inv {invoice_to_reverse.invoice_number}"
        ar_ap_account_id = self.account_manager.get_person_subsidiary_account_id(invoice_to_reverse.person_id)
        if not ar_ap_account_id: return False

        revenue_expense_account_id = self.account_manager.get_default_account_id_by_name("فروش")
        if not revenue_expense_account_id: return False

        if invoice_to_reverse.invoice_type == InvoiceType.SALE:
            # برگرداندن ثبت فروش:
            # ۱. حساب‌های دریافتنی (دارایی) بستانکار (کاهش) می‌شود. نوع تراکنش: EXPENSE
            # ۲. حساب درآمد فروش (درآمد) بدهکار (کاهش) می‌شود. نوع تراکنش: EXPENSE
            self.ft_manager.create_financial_transaction(reversal_date_dt, ar_ap_account_id, FinancialTransactionType.EXPENSE, invoice_to_reverse.total_amount, description)
            self.ft_manager.create_financial_transaction(reversal_date_dt, revenue_expense_account_id, FinancialTransactionType.EXPENSE, invoice_to_reverse.total_amount, description)
        elif invoice_to_reverse.invoice_type == InvoiceType.PURCHASE:
            ap_account_id = ar_ap_account_id
            
            is_inventory_purchase = any(
                p.product_type != ProductType.SERVICE 
                for p in (self.product_manager.get_product_by_id(item.product_id) for item in invoice_to_reverse.items) if p
            )

            if is_inventory_purchase:
                debit_account_id = self.accounts_config.get("inventory_asset")
            else:
                debit_account_id = self.accounts_config.get("purchase_expense")

            if not debit_account_id: return False
            
            # برگرداندن ثبت خرید:
            # ۱. بدهکار کردن حساب پرداختنی (کاهش بدهی)
            self.ft_manager.create_financial_transaction(reversal_date_dt, ap_account_id, FinancialTransactionType.EXPENSE, invoice_to_reverse.total_amount, description)
            # ۲. بستانکار کردن حساب موجودی کالا / هزینه خرید
            self.ft_manager.create_financial_transaction(reversal_date_dt, debit_account_id, FinancialTransactionType.EXPENSE, invoice_to_reverse.total_amount, description)
        # --- پایان بخش جدید ---
        return True

   

    def update_invoice(self, invoice_id: int, update_data: Dict[str, Any]) -> Optional[InvoiceEntity]:
        logger.info(f"Step 0: Attempting comprehensive update for Invoice ID: {invoice_id}")
        
        original_invoice = self.get_invoice_with_items(invoice_id)
        if not original_invoice:
            raise ValueError(f"فاکتور با شناسه {invoice_id} برای ویرایش یافت نشد.")

        reversal_reason = f"Edit Inv {original_invoice.invoice_number}"
        reversal_datetime = datetime.now()

        try:
            self._reverse_financial_impact(original_invoice, reversal_datetime, reversal_reason)
            self._reverse_stock_movements(original_invoice, reversal_datetime, reversal_reason)
            self.invoice_items_repo.delete_by_invoice_id(invoice_id)

            new_items_data = update_data.get("items_data", [])
            new_total_amount = sum(
                (Decimal(str(item_data.get('quantity', 0))) * Decimal(str(item_data.get('unit_price', 0)))) 
                for item_data in new_items_data
            )

            original_invoice.person_id = update_data.get("person_id", original_invoice.person_id)
            original_invoice.invoice_date = update_data.get("invoice_date", original_invoice.invoice_date)
            original_invoice.due_date = update_data.get("due_date", original_invoice.due_date)
            original_invoice.description = update_data.get("description", original_invoice.description)
            original_invoice.total_amount = new_total_amount

            updated_header = self.invoices_repo.update(original_invoice)
            if not updated_header: raise Exception("خطا در به‌روزرسانی هدر فاکتور.")

            for item_dict in new_items_data:
                item_entity = InvoiceItemEntity(
                    invoice_id=invoice_id,
                    product_id=item_dict.get('product_id'),
                    quantity=Decimal(str(item_dict.get('quantity', 0))),
                    unit_price=Decimal(str(item_dict.get('unit_price', 0))),
                    description=item_dict.get('description')
                )
                if not self.invoice_items_repo.add(item_entity):
                    raise Exception("خطا در ذخیره اقلام جدید فاکتور.")
            
            full_updated_invoice = self.get_invoice_with_items(invoice_id)
            if full_updated_invoice:
                self._record_financial_impact(full_updated_invoice)
                self._record_stock_movements(full_updated_invoice)

            return full_updated_invoice

        except Exception as e:
            logger.error(f"--- Error during comprehensive update of Invoice ID {invoice_id}: {e} ---", exc_info=True)
            raise
    
    def cancel_invoice(self, invoice_id: int, cancellation_date: Optional[date] = None) -> Optional[InvoiceEntity]:
        logger.info(f"Attempting to cancel Invoice ID: {invoice_id}")
        invoice_to_cancel = self.get_invoice_with_items(invoice_id) 

        if not invoice_to_cancel or not invoice_to_cancel.id:
            raise ValueError(f"فاکتور با شناسه {invoice_id} برای ابطال یافت نشد.")

        if invoice_to_cancel.status == InvoiceStatus.CANCELED:
            logger.info(f"Invoice ID {invoice_id} is already canceled.")
            return invoice_to_cancel
        
        if invoice_to_cancel.paid_amount > 0:
            raise ValueError(f"فاکتور شماره '{invoice_to_cancel.invoice_number}' دارای پرداخت ({invoice_to_cancel.paid_amount:,.0f}) است. ابتدا پرداخت‌ها را برگردانید، سپس فاکتور را باطل کنید.")

        cancel_dt = datetime.combine(cancellation_date if cancellation_date else date.today(), datetime.min.time())
        reason_for_reversal = f"Cancel Inv {invoice_to_cancel.invoice_number}"
        
        try:
            self._reverse_financial_impact(invoice_to_cancel, cancel_dt, reason_for_reversal)
            self._reverse_stock_movements(invoice_to_cancel, cancel_dt, reason_for_reversal)
            
            invoice_to_cancel.status = InvoiceStatus.CANCELED
            invoice_to_cancel.is_paid = False 
            invoice_to_cancel.paid_amount = Decimal("0.0") 
            
            updated_invoice = self.invoices_repo.update(invoice_to_cancel)
            logger.info(f"Invoice ID {invoice_id} status set to CANCELED.")
            
            return updated_invoice
        except Exception as e:
            logger.error(f"Error cancelling Invoice ID {invoice_id}: {e}", exc_info=True)
            raise
    # ... (سایر متدهای InvoiceManager)
    def get_invoices_by_person_id(self, person_id: int) -> List[InvoiceEntity]:
        logger.debug(f"Fetching all invoices for Person ID: {person_id}")
        return self.invoices_repo.find_by_criteria({"person_id": person_id})

    def get_unpaid_invoices_by_person_and_type(self, person_id: int, invoice_type: InvoiceType) -> List[InvoiceEntity]:
        """
        فاکتورهای پرداخت نشده (یا دارای مانده) یک شخص و نوع خاص را برمی‌گرداند.
        """
        logger.debug(f"Fetching unpaid {invoice_type.value} invoices for Person ID: {person_id}")
        if not isinstance(person_id, int) or person_id <= 0:
            logger.warning(f"Attempted to fetch unpaid invoices with invalid Person ID: {person_id}")
            return []
        if not isinstance(invoice_type, InvoiceType):
            logger.warning(f"Attempted to fetch unpaid invoices with invalid InvoiceType: {invoice_type}")
            return []

        all_person_invoices = self.invoices_repo.find_by_criteria({
            "person_id": person_id, 
            "invoice_type": invoice_type.value,
            "status": ("!=", InvoiceStatus.CANCELED.value)
        })
        
        unpaid_and_valid_invoices: List[InvoiceEntity] = []
        if all_person_invoices:
            for inv_header in all_person_invoices:
                if inv_header and inv_header.id:
                    # --- شروع اصلاح ---
                    # تبدیل مقادیر به Decimal قبل از انجام عملیات
                    try:
                        total_amount_dec = Decimal(str(inv_header.total_amount or '0.0'))
                        paid_amount_dec = Decimal(str(inv_header.paid_amount or '0.0'))
                    except InvalidOperation:
                        logger.error(f"Could not convert amounts to Decimal for Invoice ID {inv_header.id}. Skipping.")
                        continue

                    remaining_amount = total_amount_dec - paid_amount_dec
                    # بررسی اینکه آیا مانده قابل توجهی وجود دارد
                    if remaining_amount.copy_abs() > Decimal("0.001"):
                        unpaid_and_valid_invoices.append(inv_header)
                    # --- پایان اصلاح ---
        
        logger.debug(f"Found {len(unpaid_and_valid_invoices)} unpaid and valid {invoice_type.value} invoices for Person ID {person_id}.")
        return unpaid_and_valid_invoices