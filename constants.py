# src/constants.py

from enum import Enum

# General
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class AccountType(Enum):
    ASSET = "دارایی"
    LIABILITY = "بدهی"
    EQUITY = "حقوق صاحبان سهام"
    REVENUE = "درآمد"
    EXPENSE = "هزینه"

class PersonType(Enum):
    CUSTOMER = "مشتری"
    SUPPLIER = "تامین کننده"
    EMPLOYEE = "کارمند"

class ProductType(Enum):
    RAW_MATERIAL = "ماده اولیه"
    FINISHED_GOOD = "محصول نهایی"
    SERVICE = "خدمات"
    SEMI_FINISHED_GOOD = "کالای نیمه ساخته"
class InvoiceType(Enum):
    SALE = "فروش"
    PURCHASE = "خرید"

class FinancialTransactionType(Enum):
    INCOME = "درآمد"
    EXPENSE = "هزینه"
    DEPOSIT = "واریز"  # <<< Ensure this member exists
    WITHDRAWAL = "برداشت"
    TRANSFER = "انتقال"

class PaymentMethod(Enum):
    CASH = "نقد"
    CARD = "کارت بانکی"
    BANK_TRANSFER = "انتقال بانکی"
    CHECK = "چک (صادره/دریافتی اولیه)" # برای صدور چک خودمان یا دریافت اولیه چک از مشتری
    ENDORSE_CHECK = "خرج چک (واگذاری چک دریافتی)" # <<< روش پرداخت جدید
class PaymentType(Enum):
    RECEIPT = "دریافت"  # دریافت وجه از مشتری یا سایر درآمدها
    PAYMENT = "پرداخت"  # پرداخت وجه به تامین‌کننده یا برای هزینه‌ها


class InventoryMovementType(Enum):
    INITIAL_STOCK = "موجودی اولیه"
    SALE = "فروش"
    SALE_RETURN = "برگشت از فروش" # <<< ADD THIS
    PURCHASE_RETURN = "برگشت به تامین کننده" # <<< ADD THIS
    PURCHASE = "خرید" # <<< ADD THIS
    PURCHASE_RECEIPT = "رسید خرید"
    PRODUCTION_ISSUE = "صدور برای تولید (دستور کار)" # For standard production orders
    PRODUCTION_RECEIPT = "رسید از تولید (دستور کار)" # For standard production orders
    MANUAL_PRODUCTION_RECEIPT = "رسید تولید دستی"  # <<< ADD THIS
    MANUAL_PRODUCTION_ISSUE = "صدور/مصرف برای تولید دستی" # <<< ADD THIS
    STOCK_ADJUSTMENT_INCREASE = "تعدیل موجودی (افزایش)"
    STOCK_ADJUSTMENT_DECREASE = "تعدیل موجودی (کاهش)"
    RETURN_FROM_CUSTOMER = "برگشت از فروش"
    RETURN_TO_SUPPLIER = "برگشت به تامین کننده"
    MANUAL_PRODUCTION_ADJUST_RETURN = "بازگشت مصرف برای ویرایش تولید دستی"  # <<< ADD THIS
    MANUAL_PRODUCTION_ADJUST_REVERSE = "بازگشت تولید برای ویرایش تولید دستی" #
    # ... any other types you have ...
class CheckType(Enum):
    RECEIVED = "دریافتی"
    ISSUED = "پرداختی"

class CheckStatus(Enum):
    PENDING = "در جریان"
    DEPOSITED = "واگذار به بانک (خوابانده به حساب)"
    CLEARED = "وصول شده (نقد شده در بانک ما)" # برای چک‌های دریافتی یا پاس شده از حساب ما
    CASHED = "نقد شده (مستقیم)" # برای چک‌های دریافتی که مستقیماً نقد شده‌اند نه از طریق بانک ما
    BOUNCED = "برگشت خورده"
    PAID_TO_BENEFICIARY = "خرج شده (واگذار به غیر)" # <<< این وضعیت از قبل وجود داشت و صحیح است
    CANCELED = "باطل شده"
class LoanDirectionType(Enum):
    RECEIVED = "دریافتی توسط ما" # وامی که ما دریافت کرده‌ایم (بدهی ماست)
    GIVEN = "پرداختی توسط ما"    # وامی که ما به دیگری داده‌ایم (دارایی ماست)
class LoanStatus(Enum):
    ACTIVE = "فعال"
    PAID_OFF = "تسویه شده"
    DEFAULTED = "معوق"
    PENDING_DISBURSEMENT = "در انتظار پرداخت/دریافت اولیه" 


class PurchaseOrderStatus(Enum):
    PENDING = "در انتظار"
    PARTIALLY_PAID = "بخشی پرداخت شده"
    FULLY_PAID = "کاملا پرداخت شده"
    PARTIALLY_RECEIVED = "بخشی دریافت شده"
    FULLY_RECEIVED = "کاملا دریافت شده"
    COMPLETED = "تکمیل شده" # Both fully paid and fully received
    CANCELED = "لغو شده"
class ProductionOrderStatus(Enum):
    PENDING = "در انتظار"
    IN_PROGRESS = "در حال تولید"
    COMPLETED = "تکمیل شده"
    PARTIALLY_COMPLETED = "بخشی تکمیل شده" # اگر تولید بخشی مجاز است
    CANCELED = "لغو شده"
class FiscalYearStatus(Enum):
    OPEN = "باز"
    CLOSED = "بسته"

class InvoiceStatus(Enum): # <<< جدید
    DRAFT = "پیش‌نویس"
    ISSUED = "صادر شده" # یا POSTED
    PARTIALLY_PAID = "بخشی پرداخت شده"
    FULLY_PAID = "پرداخت شده کامل"
    CANCELED = "باطل شده"
    OVERDUE = "سررسید گذشته"
# For FinancialTransaction.reference_type and InventoryMovement.reference_type
class ReferenceType(Enum):
    INVOICE = "Invoice"
    INVOICE_ITEM = "InvoiceItem" # For inventory specific to an item line
    INVOICE_REVERSAL = "InvoiceReversal" # برای تراکنش‌های مالی برگشتی
    INVOICE_ITEM_REVERSAL = "InvoiceItemReversal" # برای حرکات انبار برگشتی
    PAYMENT = "Payment" # برای هدر پرداخت
    PAYMENT_LINE = "PaymentLineItem" # <<< این عضو جدید اضافه شد
    CHECK = "Check"
    PAYROLL = "Payroll"
    LOAN = "Loan"
    PURCHASE_ORDER = "PurchaseOrder"
    PRODUCTION_ORDER = "ProductionOrder"
    MATERIAL_RECEIPT = "MaterialReceipt"
    MANUAL_ADJUSTMENT = "ManualAdjustment" # For general financial or inventory adjustments
    PAYMENT_LINE_REVERSAL = "PaymentLineReversal" # <<< این عضو جدید اضافه شد
    MANUAL_PRODUCTION = "ManualProduction" # <<< ADD THIS
    STOCK_ADJUSTMENT = "StockAdjustment"
    

DEFAULT_ACCOUNTS_CONFIG_FOR_PAYMENT = {
    # حساب‌های کل
    "accounts_receivable": 1,           # حساب "حساب‌های دریافتنی"
    "accounts_payable": 2,              # حساب "حساب‌های پرداختنی"
    
    # حساب‌های معین برای روش‌های پرداخت
    "cash_in_hand": 3,                  # حساب "صندوق"
    "bank_accounts_default": 4,         # حساب پیش‌فرض بانک (اگر حساب خاصی مشخص نشده باشد)
    "checks_receivable_account": 101,   # <<< حساب "اسناد دریافتنی" اضافه شد
    "checks_payable_account": 201       # <<< حساب "اسناد پرداختنی" اضافه شد
}

# دیکشنری برای پیکربندی حساب‌های پیش‌فرض در ماژول چک
DEFAULT_ACCOUNTS_CONFIG_FOR_CHECKS = {
    "checks_receivable_account": 101,
    "checks_payable_account": 201,
    "bank_charges_expense_account": 501,
    "accounts_receivable": 1,
    "accounts_payable": 2, # قبلاً ۴ بود، با بالا یکسان‌سازی شد
}