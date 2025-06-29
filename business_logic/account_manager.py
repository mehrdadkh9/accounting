# src/business_logic/account_manager.py

from typing import Optional, List, Dict, Any # <<< Dict, Any اضافه شد
from datetime import date, datetime
from src.business_logic.person_manager import PersonManager

from src.business_logic.entities.account_entity import AccountEntity
from src.business_logic.entities.financial_transaction_entity import FinancialTransactionEntity
from src.data_access.accounts_repository import AccountsRepository
from src.data_access.financial_transactions_repository import FinancialTransactionsRepository
from src.constants import AccountType, FinancialTransactionType, DATE_FORMAT,PersonType
import logging
from decimal import Decimal
logger = logging.getLogger(__name__)

class AccountManager:
    def __init__(self, 
                 accounts_repository: 'AccountsRepository', 
                 financial_transactions_repository: 'FinancialTransactionsRepository',
                 person_manager: 'PersonManager'
                 ):
        # FIX: اطمینان از اینکه نام فیلد با چیزی که در متدهای دیگر استفاده می‌شود، یکی است
        self.accounts_repository = accounts_repository
        self.financial_transactions_repository = financial_transactions_repository
        self.person_manager = person_manager
    

    def add_account(self, 
                    name: str, 
                    account_type: AccountType, 
                    parent_id: Optional[int] = None, # <<< پارامتر parent_id اضافه شد
                    initial_balance: float = 0.0
                    ) -> AccountEntity:
        if not name or not isinstance(name, str):
            logger.error("Account name cannot be empty.")
            raise ValueError("نام حساب نمی‌تواند خالی باشد.")
        if not isinstance(account_type, AccountType):
            logger.error(f"Invalid account_type: {account_type}")
            raise ValueError("نوع حساب نامعتبر است.")

        if parent_id is not None:
            if not isinstance(parent_id, int) or parent_id <= 0:
                raise ValueError("شناسه حساب والد نامعتبر است.")
            parent_account = self.accounts_repository.get_by_id(parent_id)
            if not parent_account:
                raise ValueError(f"حساب والد با شناسه {parent_id} یافت نشد.")
            # TODO: Optional: Add validation, e.g., a Revenue account cannot be child of an Asset account.
            # For now, basic existence check.

        # Optional: Check for duplicate account name under the same parent (if parent_id is not None)
        # Or duplicate name globally if that's the business rule.
        # existing_accounts_with_name = self.accounts_repository.find_by_criteria({"name": name, "parent_id": parent_id})
        # if existing_accounts_with_name:
        #     raise ValueError(f"حسابی با نام '{name}' و والد مشخص شده از قبل موجود است.")

        account_entity = AccountEntity(
            name=name,
            type=account_type,
            parent_id=parent_id, # <<< مقداردهی parent_id
            balance=initial_balance 
        )
        try:
            created_account = self.accounts_repository.add(account_entity)
            logger.info(f"Account '{created_account.name}' (ID: {created_account.id}, ParentID: {parent_id}, Type: {account_type.value}) added with balance {initial_balance}.")
            return created_account
        except Exception as e:
            logger.error(f"Error adding account '{name}': {e}", exc_info=True)
            raise

    def get_account_by_id(self, account_id: int) -> Optional[AccountEntity]:
        # بدون تغییر
        if not isinstance(account_id, int) or account_id <= 0:
            logger.error(f"Invalid account_id: {account_id}")
            return None
        return self.accounts_repository.get_by_id(account_id)

    def get_all_accounts(self) -> List[AccountEntity]:
        # بدون تغییر - همه حساب‌ها را برمی‌گرداند، نه ساختار درختی
        return self.accounts_repository.get_all()
        
    def get_top_level_accounts(self) -> List[AccountEntity]:
        """Retrieves all top-level accounts (those without a parent)."""
        return self.accounts_repository.get_child_accounts(None)

    def get_child_accounts(self, parent_id: int) -> List[AccountEntity]:
        """Retrieves direct children of a given parent account."""
        if not isinstance(parent_id, int) or parent_id <= 0:
            logger.warning(f"Invalid parent_id {parent_id} for get_child_accounts, returning empty list.")
            return []
        return self.accounts_repository.get_child_accounts(parent_id)

    def _build_account_tree_recursive(self, parent_id: Optional[int]) -> List[Dict[str, Any]]:
        """
        Helper recursive function to build a tree structure of accounts.
        Each node in the tree is a dictionary with account data and a 'children' key.
        """
        children_list = []
        child_accounts = self.accounts_repository.get_child_accounts(parent_id)
        for account in child_accounts:
            if account.id is None: continue # Should not happen
            children_of_this_account = self._build_account_tree_recursive(account.id)
            children_list.append({
                "id": account.id,
                "name": account.name,
                "type": account.type, # Keep enum for potential use, or .value for string
                "parent_id": account.parent_id,
                "balance": account.balance, # Direct balance
                # "code": account.code, # If code was implemented
                "children": children_of_this_account
            })
        return children_list

    def get_account_tree(self) -> List[AccountEntity]:
        """
        یک ساختار درختی از تمام حساب‌ها ایجاد می‌کند.
        """
        logger.debug("Building account tree...")
        all_accounts = self.get_all_accounts()
        # ایجاد یک دیکشنری برای دسترسی سریع به هر حساب با شناسه آن
        account_map: Dict[int, AccountEntity] = {acc.id: acc for acc in all_accounts if acc.id is not None}
        
        root_nodes: List[AccountEntity] = []
        for acc in all_accounts:
            # پاک کردن لیست فرزندان قبلی برای جلوگیری از داده‌های تکراری
            acc.children = [] 
            if acc.parent_id in account_map:
                parent = account_map[acc.parent_id]
                parent.children.append(acc)
            # اگر حساب والد ندارد، یک نود ریشه است
            elif acc.parent_id is None:
                root_nodes.append(acc)
        
        logger.debug("Account tree built.")
        return root_nodes

    def get_accounts_for_combobox(self) -> List[Dict[str, Any]]:
        """
        یک لیست مسطح از تمام حساب‌ها با تورفتگی برای نمایش در کمبوباکس برمی‌گرداند.
        """
        account_tree = self.get_account_tree()
        flat_list: List[Dict[str, Any]] = []
        self._flatten_tree_for_combo(account_tree, "", flat_list)
        return flat_list

    def _flatten_tree_for_combo(self, nodes: List[AccountEntity], prefix: str, flat_list: List[Dict[str, Any]]):
        """
        به صورت بازگشتی درخت حساب‌ها را برای استفاده در کمبوباکس مسطح می‌کند.
        """
        for node in nodes:
            if node.id is not None:
                flat_list.append({
                    "display_name": f"{prefix}{node.name}",
                    "id": node.id
                })
                # اگر حساب فرزند داشت، به صورت بازگشتی آن‌ها را نیز اضافه کن
                if node.children:
                    self._flatten_tree_for_combo(node.children, prefix + "--- ", flat_list)


    def get_accounts_by_type(self, account_type: AccountType) -> List[AccountEntity]:
        # بدون تغییر - این متد همه حساب‌های یک نوع خاص را برمی‌گرداند، صرف نظر از ساختار درختی
        if not isinstance(account_type, AccountType):
            logger.error(f"Invalid account_type for get_accounts_by_type: {account_type}")
            return []
        return self.accounts_repository.get_by_type(account_type)
    _UNCHANGED = object() 
    def update_account_details(self, 
                               account_id: int, 
                               name: Optional[str] = None, 
                               account_type: Optional[AccountType] = None,
                               parent_id: Any = _UNCHANGED # <<< می‌تواند int, None, یا _UNCHANGED باشد
                               ) -> Optional[AccountEntity]:
        if not isinstance(account_id, int) or account_id <= 0:
            raise ValueError("شناسه حساب نامعتبر است.")

        account_to_update = self.accounts_repository.get_by_id(account_id)
        if not account_to_update:
            logger.warning(f"Account with ID {account_id} not found for update.")
            return None

        updated_fields = False
        if name is not None:
            if not name: raise ValueError("نام حساب برای به‌روزرسانی نمی‌تواند خالی باشد.")
            account_to_update.name = name
            updated_fields = True

        if account_type is not None:
            if not isinstance(account_type, AccountType):
                raise ValueError("نوع حساب برای به‌روزرسانی نامعتبر است.")
            if account_to_update.type != account_type:
                logger.warning(f"Changing account type for ID {account_id} from {account_to_update.type.value} to {account_type.value}.")
                account_to_update.type = account_type
                updated_fields = True

        if parent_id != self._UNCHANGED: # اگر parent_id به عنوان آرگومان پاس داده شده باشد
            if parent_id is None: # یعنی می‌خواهیم به حساب سطح بالا تبدیل شود
                if account_to_update.parent_id is not None: # فقط اگر قبلا والد داشته
                    account_to_update.parent_id = None
                    updated_fields = True
            elif isinstance(parent_id, int): # یک والد جدید مشخص شده
                if parent_id == account_id: 
                    raise ValueError("یک حساب نمی‌تواند والد خودش باشد.")

                parent_account = self.accounts_repository.get_by_id(parent_id)
                if not parent_account:
                    raise ValueError(f"حساب والد جدید با شناسه {parent_id} یافت نشد.")

                # TODO: Advanced: Add cycle detection

                if account_to_update.parent_id != parent_id:
                    account_to_update.parent_id = parent_id
                    updated_fields = True
            else: # parent_id مقدار نامعتبری دارد (نه int، نه None، نه _UNCHANGED)
                raise ValueError("مقدار parent_id برای به‌روزرسانی نامعتبر است.")

        if updated_fields:
            try:
                updated_account = self.accounts_repository.update(account_to_update)
                logger.info(f"Account '{updated_account.name}' (ID: {updated_account.id}) details updated.")
                return updated_account
            except Exception as e:
                logger.error(f"Error updating account ID {account_id} details: {e}", exc_info=True)
                raise
        else:
            logger.info(f"No details provided for update for account ID {account_id}.")
            return account_to_update

    # ... (متدهای get_account_balance_as_of, process_financial_transaction بدون تغییر) ...
    def get_account_balance_as_of(self, account_id: int, as_of_date: date) -> float:
        # ... (کد قبلی این متد، که مانده مستقیم حساب را بر اساس تراکنش‌ها محاسبه می‌کند) ...
        # برای ترازنامه درختی، این متد باید بتواند مانده‌های فرزندان را هم جمع بزند (پیچیدگی بیشتر)
        # فعلاً همان مانده مستقیم را برمی‌گرداند.
        if not isinstance(account_id, int) or account_id <= 0:
            raise ValueError("شناسه حساب نامعتبر است.")
        if not isinstance(as_of_date, date):
            raise ValueError("تاریخ مورد نظر نامعتبر است.")

        account = self.accounts_repository.get_by_id(account_id)
        if not account:
            raise ValueError(f"حسابی با شناسه {account_id} یافت نشد.")
        
        all_transactions_for_account = self.financial_transactions_repository.get_by_account_id(account_id)
        calculated_balance = 0.0
        
        for transaction in all_transactions_for_account:
            if not isinstance(transaction.transaction_date, str):
                logger.error(f"Transaction {transaction.id} has an invalid date format type: {type(transaction.transaction_date)}")
                continue

            transaction_date_obj = datetime.strptime(transaction.transaction_date.split(" ")[0], DATE_FORMAT).date() 
            if transaction_date_obj <= as_of_date:
                change_amount = 0.0
                transaction_amount = transaction.amount

                if account.type == AccountType.ASSET:
                    if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                        change_amount = transaction_amount
                    elif transaction.transaction_type == FinancialTransactionType.EXPENSE:
                        change_amount = -transaction_amount
                elif account.type == AccountType.LIABILITY:
                    if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                        change_amount = transaction_amount
                    elif transaction.transaction_type == FinancialTransactionType.EXPENSE:
                        change_amount = -transaction_amount
                elif account.type == AccountType.EQUITY:
                    if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                        change_amount = transaction_amount
                    elif transaction.transaction_type == FinancialTransactionType.EXPENSE:
                        change_amount = -transaction_amount
                elif account.type == AccountType.REVENUE: 
                    if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                        change_amount = transaction_amount
                    elif transaction.transaction_type == FinancialTransactionType.EXPENSE: 
                        change_amount = -transaction_amount
                elif account.type == AccountType.EXPENSE: 
                    if transaction.transaction_type in [FinancialTransactionType.EXPENSE, FinancialTransactionType.TRANSFER]:
                        change_amount = transaction_amount
                    elif transaction.transaction_type == FinancialTransactionType.INCOME: 
                        change_amount = -transaction_amount
                
                calculated_balance += change_amount
        
        logger.debug(f"Direct balance for account ID {account_id} as of {as_of_date} is {calculated_balance:.2f}")
        return calculated_balance
    def get_person_subsidiary_account_id(self, person_id: int) -> Optional[int]:
        """
        شناسه حساب معین (فرعی) مربوط به یک شخص را پیدا کرده یا ایجاد می‌کند.
        این حساب معمولاً زیرمجموعه "حساب‌های دریافتنی" (برای مشتریان) یا "حساب‌های پرداختنی" (برای تامین‌کنندگان) است.
        """
        logger.debug(f"Searching for or creating subsidiary account for Person ID: {person_id}")
        
        # قرارداد نامگذاری برای حساب‌های اشخاص: "PERSON-[person_id]"
        # این نام در UI به کاربر نمایش داده نمی‌شود و فقط برای شناسایی داخلی است.
        account_name_for_person = f"PERSON-{person_id}"
        
        # 1. ابتدا سعی می‌کنیم حساب را بر اساس نام پیدا کنیم.
        existing_account = self.accounts_repository.get_by_name(account_name_for_person)
        if existing_account and existing_account.id:
            logger.debug(f"Found existing subsidiary account ID {existing_account.id} for Person ID {person_id}.")
            return existing_account.id

        # 2. اگر حساب وجود نداشت، آن را ایجاد می‌کنیم.
        logger.info(f"Subsidiary account for Person ID {person_id} not found. Creating a new one.")
        
        person = self.person_manager.get_person_by_id(person_id)
        if not person:
            raise ValueError(f"شخص با شناسه {person_id} برای ایجاد حساب معین یافت نشد.")
        
        # تعیین حساب کل (والد) بر اساس نوع شخص
        parent_account_name = "حساب‌های دریافتنی" if person.person_type == PersonType.CUSTOMER else "حساب‌های پرداختنی"
        parent_account = self.accounts_repository.get_by_name(parent_account_name)
        
        if not parent_account or not parent_account.id:
            logger.error(f"Parent account '{parent_account_name}' not found. Cannot create subsidiary account.")
            # این خطا باید در UI نمایش داده شود تا کاربر بداند که باید حساب کل را ایجاد کند
            raise ValueError(f"حساب کل '{parent_account_name}' برای ایجاد حساب معین یافت نشد. لطفاً ابتدا این حساب را در سرفصل حساب‌ها تعریف کنید.")
        
        # ایجاد حساب جدید
        new_account_entity = AccountEntity(
            name=account_name_for_person, # نام داخلی برای شناسایی
            type=AccountType.ASSET if person.person_type == PersonType.CUSTOMER else AccountType.LIABILITY,
            parent_id=parent_account.id,
          #  description=f"حساب معین برای: {person.name}" # توضیحات خودکار
        )
        created_account = self.accounts_repository.add(new_account_entity)
        if created_account and created_account.id:
            logger.info(f"Created new subsidiary account ID {created_account.id} for Person ID {person_id}.")
            return created_account.id
        
        raise Exception(f"ایجاد خودکار حساب معین برای شخص با شناسه {person_id} ناموفق بود.")

    
    def get_default_account_id_by_name(self, account_name: str) -> Optional[int]:
        """
        شناسه یک حساب پیش‌فرض را بر اساس نام دقیق آن جستجو و برمی‌گرداند.
        """
        logger.debug(f"Searching for default account by name: '{account_name}'")
        account = self.accounts_repository.get_by_name(account_name)
        if account and account.id:
            logger.debug(f"Found account '{account_name}' with ID: {account.id}")
            return account.id
        
        logger.warning(f"Default account with name '{account_name}' not found in the database.")
        return None


    def process_financial_transaction(self, transaction: FinancialTransactionEntity) -> bool:
        # ... (کد قبلی این متد بدون تغییر) ...
        if not isinstance(transaction, FinancialTransactionEntity):
            logger.error("Invalid transaction object passed to process_financial_transaction.")
            return False
            
        account = self.accounts_repository.get_by_id(transaction.account_id)
        if not account:
            logger.error(f"Account ID {transaction.account_id} not found for processing FT ID {transaction.id}.")
            return False 

        change_amount = 0.0
        transaction_amount = transaction.amount 

        if account.type == AccountType.ASSET:
            if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                change_amount = transaction_amount
            elif transaction.transaction_type == FinancialTransactionType.EXPENSE:
                change_amount = -transaction_amount
        elif account.type == AccountType.LIABILITY:
            if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                change_amount = transaction_amount
            elif transaction.transaction_type == FinancialTransactionType.EXPENSE:
                change_amount = -transaction_amount
        elif account.type == AccountType.EQUITY:
            if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                change_amount = transaction_amount
            elif transaction.transaction_type == FinancialTransactionType.EXPENSE:
                change_amount = -transaction_amount
        elif account.type == AccountType.REVENUE: 
            if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.TRANSFER]:
                change_amount = transaction_amount
            elif transaction.transaction_type == FinancialTransactionType.EXPENSE: 
                change_amount = -transaction_amount
        elif account.type == AccountType.EXPENSE: 
            if transaction.transaction_type in [FinancialTransactionType.EXPENSE, FinancialTransactionType.TRANSFER]:
                change_amount = transaction_amount
            elif transaction.transaction_type == FinancialTransactionType.INCOME: 
                change_amount = -transaction_amount
        if not isinstance(account.balance, Decimal):
            account.balance = Decimal(str(account.balance or '0.0'))

    # اطمینان از اینکه transaction.amount از نوع Decimal است
        transaction_amount = transaction.amount if isinstance(transaction.amount, Decimal) else Decimal(str(transaction.amount or '0.0'))
        change_amount = Decimal("0.0")
        if transaction.transaction_type in [FinancialTransactionType.INCOME, FinancialTransactionType.DEPOSIT]:
            change_amount = transaction_amount # باید Decimal باشد
        elif transaction.transaction_type in [FinancialTransactionType.EXPENSE, FinancialTransactionType.WITHDRAWAL]:
             change_amount = -transaction_amount # باید Decimal باشد

        if change_amount != 0:
            original_balance = account.balance
            account.balance += change_amount
            try:
                self.accounts_repository.update(account) 
                logger.info(f"Balance for account '{account.name}' (ID: {account.id}) changed by {change_amount:.2f} due to FT ID {transaction.id} (Type: {transaction.transaction_type.value}). Old: {original_balance:.2f}, New: {account.balance:.2f}.")
                return True
            except Exception as e:
                logger.error(f"Failed to update balance for account ID {account.id} after processing FT ID {transaction.id}: {e}", exc_info=True)
                account.balance = original_balance 
                return False
        else:
            logger.debug(f"No balance change calculated for account ID {account.id} from FT ID {transaction.id} (FT Type: {transaction.transaction_type.value}, Acc Type: {account.type.value}).")
            return False


    def delete_account(self, account_id: int) -> bool:
        if not isinstance(account_id, int) or account_id <= 0:
            logger.error(f"Invalid account_id for delete: {account_id}")
            return False

        account_to_delete = self.accounts_repository.get_by_id(account_id)
        if not account_to_delete:
            logger.warning(f"Account with ID {account_id} not found for deletion.")
            return True 
            
        # بررسی اینکه آیا حساب فرزند دارد یا خیر
        children = self.accounts_repository.get_child_accounts(account_id)
        if children:
            # اگر ON DELETE SET NULL در دیتابیس فعال باشد، فرزندان والد خود را از دست می‌دهند.
            # کاربر باید از این موضوع مطلع شود.
            logger.warning(f"Account ID {account_id} ('{account_to_delete.name}') has {len(children)} child account(s). "
                           "Upon deletion, these children will become top-level accounts due to 'ON DELETE SET NULL'.")
            # می‌توان در اینجا از کاربر تاییدیه اضافی گرفت یا از حذف جلوگیری کرد اگر فرزند دارد.
            # raise ValueError(f"امکان حذف حساب '{account_to_delete.name}' وجود ندارد زیرا دارای حساب‌های زیرمجموعه است. ابتدا حساب‌های فرزند را منتقل یا حذف کنید.")

        try:
            self.accounts_repository.delete(account_id)
            logger.info(f"Account with ID {account_id} (Name: {account_to_delete.name}) deleted successfully.")
            return True
        except Exception as e: 
            logger.error(f"Error deleting account ID {account_id}: {e}", exc_info=True)
            raise ValueError(f"امکان حذف حساب '{account_to_delete.name}' وجود ندارد. ممکن است تراکنش‌های مرتبط داشته باشد یا خطای دیگری رخ داده باشد.") from e