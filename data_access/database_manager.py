# src/data_access/database_manager.py

import sqlite3
import logging
from src.config import DATABASE_PATH
from src.constants import (
    AccountType, PersonType, ProductType, InvoiceType, FinancialTransactionType,
    PaymentMethod, InventoryMovementType, CheckType, CheckStatus, LoanStatus,InvoiceStatus,
    ProductionOrderStatus, PurchaseOrderStatus, FiscalYearStatus, ReferenceType
)
from src.config import DATABASE_PATH, LOGGING_CONFIG # Added LOGGING_CONFIG

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row # Access columns by name
            self.conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
            logger.debug(f"Database connection established to {self.db_path}")
            return self.conn
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database {self.db_path}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            logger.debug("Database connection closed.")

    def execute_query(self, query, params=None):
        try:
            with self as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {query} with params {params} - {e}")
            # Depending on the error, you might want to rollback or handle specific exceptions
            raise

    def fetch_one(self, query, params=None):
        try:
            with self as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Fetch one failed: {query} with params {params} - {e}")
            raise

    def fetch_all(self, query, params=None):
        try:
            with self as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Fetch all failed: {query} with params {params} - {e}")
            raise

    def create_tables(self):
        queries = [
            # ... (All your CREATE TABLE query strings as defined before) ...
            # Ensure all 21 CREATE TABLE query strings are listed here.
            # Example:
          """
            CREATE TABLE IF NOT EXISTS payment_headers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_date TEXT NOT NULL, -- ISO Date
                person_id INTEGER NOT NULL, 
                total_amount REAL NOT NULL,
                description TEXT,
                fiscal_year_id INTEGER, -- NOT NULL اگر الزامی است
                invoice_id INTEGER,
                purchase_order_id INTEGER,
                            payment_type TEXT NOT NULL, -- <<< این ستون اضافه شد

                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE RESTRICT, -- یا SET NULL اگر منطقی‌تر است
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id) ON DELETE RESTRICT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS payment_line_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_header_id INTEGER NOT NULL,
                payment_method TEXT NOT NULL CHECK(payment_method IN ({})),
                amount REAL NOT NULL,
                account_id INTEGER, -- حساب بانک/صندوق "ما" (می‌تواند NULL باشد برای خرج چک)
                check_id INTEGER,   -- شناسه چک مرتبط (می‌تواند NULL باشد)
                description TEXT,
                target_account_id INTEGER, -- <<< ستون جدید اضافه شد
                FOREIGN KEY (target_account_id) REFERENCES accounts(id) ON DELETE SET NULL -- <<< کلید خارجی جدید
                FOREIGN KEY (payment_header_id) REFERENCES payment_headers(id) ON DELETE CASCADE, -- اگر هدر حذف شد، اقلام هم حذف شوند
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
                FOREIGN KEY (check_id) REFERENCES checks(id) ON DELETE SET NULL
            );
            """.format(
                ', '.join(f"'{pm.value}'" for pm in PaymentMethod) # اطمینان از وجود PaymentMethod در import ها
            ),
            """
            CREATE TABLE IF NOT EXISTS fiscal_years (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('{}', '{}'))
            );
            """.format(FiscalYearStatus.OPEN.value, FiscalYearStatus.CLOSED.value),
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK(type IN ('{}', '{}', '{}', '{}', '{}')),
                balance REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (parent_id) REFERENCES accounts(id) ON DELETE SET NULL ON UPDATE CASCADE

            );
            """.format(AccountType.ASSET.value, AccountType.LIABILITY.value, AccountType.EQUITY.value, AccountType.REVENUE.value, AccountType.EXPENSE.value),
            """
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                person_type TEXT NOT NULL CHECK(person_type IN ('{}', '{}', '{}')),
                contact_info TEXT
            );
            """.format(PersonType.CUSTOMER.value, PersonType.SUPPLIER.value, PersonType.EMPLOYEE.value),
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL UNIQUE,
                national_id TEXT UNIQUE,
                position TEXT,
                base_salary REAL NOT NULL DEFAULT 0.0,
                hire_date TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sku TEXT UNIQUE,
                unit_price REAL NOT NULL DEFAULT 0.0,
                stock_quantity REAL NOT NULL DEFAULT 0.0,
                description TEXT,
                product_type TEXT NOT NULL CHECK(product_type IN ('{}', '{}', '{}')),
                unit_of_measure TEXT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                inventory_account_id INTEGER,
                FOREIGN KEY (inventory_account_id) REFERENCES accounts (id) 
            );
            """.format(ProductType.RAW_MATERIAL.value, ProductType.FINISHED_GOOD.value, ProductType.SERVICE.value),
             """
            CREATE TABLE IF NOT EXISTS manual_productions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            production_date TEXT NOT NULL,         -- تاریخ تولید به صورت رشته ISO (YYYY-MM-DD)
            finished_product_id INTEGER NOT NULL,  -- شناسه محصول نهایی تولید شده
            quantity_produced REAL NOT NULL,       -- مقدار محصول نهایی تولید شده (می‌تواند اعشاری باشد)
            description TEXT,
            -- fiscal_year_id INTEGER, -- اگر نیاز به اتصال به سال مالی دارید
            FOREIGN KEY (finished_product_id) REFERENCES products (id)
            -- FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years (id)
        );
    """,
     """
        CREATE TABLE IF NOT EXISTS consumed_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manual_production_id INTEGER NOT NULL, -- شناسه رکورد تولید دستی والد
            component_product_id INTEGER NOT NULL, -- شناسه ماده اولیه/جزء مصرف شده
            quantity_consumed REAL NOT NULL,       -- مقدار ماده اولیه مصرف شده (می‌تواند اعشاری باشد)
            notes TEXT,
            -- unit_cost_at_consumption REAL, -- هزینه واحد این ماده در زمان مصرف (اختیاری برای محاسبه بهای تمام شده)
            FOREIGN KEY (manual_production_id) REFERENCES manual_productions (id) ON DELETE CASCADE,
            FOREIGN KEY (component_product_id) REFERENCES products (id)
        );
    """,
             """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL UNIQUE,
                invoice_date TEXT NOT NULL,
                person_id INTEGER NOT NULL,
                invoice_type TEXT NOT NULL CHECK(invoice_type IN ('{sale_value}', '{purchase_value}')),
                total_amount REAL NOT NULL DEFAULT 0.0,
                paid_amount REAL NOT NULL DEFAULT 0.0,
                is_paid INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT '{default_status_value}' CHECK(status IN ({all_status_values})),
                due_date TEXT,
                description TEXT,
                fiscal_year_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES persons(id),
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """.format(
                sale_value=InvoiceType.SALE.value, 
                purchase_value=InvoiceType.PURCHASE.value,
                default_status_value=InvoiceStatus.ISSUED.value,
                all_status_values=', '.join(f"'{s.value}'" for s in InvoiceStatus)
            ),
            """
            CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    description TEXT, -- <<< ADD THIS LINE
    FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id)
);
            """,
            """
            CREATE TABLE IF NOT EXISTS financial_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('{}', '{}', '{}')),
                amount REAL NOT NULL,
                description TEXT,
                category TEXT,
                reference_id INTEGER,
                reference_type TEXT CHECK(reference_type IN ({})),
                fiscal_year_id INTEGER,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """.format(FinancialTransactionType.INCOME.value, FinancialTransactionType.EXPENSE.value, FinancialTransactionType.TRANSFER.value,
                       ', '.join(f"'{rt.value}'" for rt in ReferenceType)),
            """
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL UNIQUE,
                person_id INTEGER NOT NULL, -- Supplier
                order_date TEXT NOT NULL, 
                total_amount_expected REAL NOT NULL DEFAULT 0.0,
                paid_amount REAL NOT NULL DEFAULT 0.0,
                received_amount REAL NOT NULL DEFAULT 0.0, -- <<< ستون جدید اضافه شد
                status TEXT NOT NULL CHECK(status IN ({})), -- PurchaseOrderStatus values
                description TEXT,
                fiscal_year_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES persons(id),
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """.format(', '.join(f"'{pos.value}'" for pos in PurchaseOrderStatus)),
            """
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_number TEXT NOT NULL,
                amount REAL NOT NULL,
                issue_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                person_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                check_type TEXT NOT NULL CHECK(check_type IN ('{}', '{}')),
                status TEXT NOT NULL CHECK(status IN ({})),
                description TEXT,
                invoice_id INTEGER,
                purchase_order_id INTEGER,
                fiscal_year_id INTEGER,
                UNIQUE (check_number, account_id, check_type),
                FOREIGN KEY (person_id) REFERENCES persons(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE SET NULL,
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """.format(CheckType.RECEIVED.value, CheckType.ISSUED.value,
                       ', '.join(f"'{cs.value}'" for cs in CheckStatus)),
            
             """
            CREATE TABLE IF NOT EXISTS inventory_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_date TEXT NOT NULL, -- ISO DateTime
                quantity_change REAL NOT NULL,
                movement_type TEXT NOT NULL CHECK(movement_type IN ({})), -- <<< این بخش باید به‌روز شود
                reference_id INTEGER,
                reference_type TEXT CHECK(reference_type IN ({})),
                description TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """.format(
                ', '.join(f"'{imt.value}'" for imt in InventoryMovementType), # <<< از Enum کامل استفاده می‌کنیم
                ', '.join(f"'{rt.value}'" for rt in ReferenceType)
            ),
            """
            CREATE TABLE IF NOT EXISTS payrolls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                pay_period_start TEXT NOT NULL,
                pay_period_end TEXT NOT NULL,
                gross_salary REAL NOT NULL,
                deductions REAL NOT NULL DEFAULT 0.0,
                net_salary REAL NOT NULL,
                payment_date TEXT,
                paid_by_account_id INTEGER,
                description TEXT,
                is_paid INTEGER NOT NULL DEFAULT 0,
                transaction_id INTEGER UNIQUE,
                fiscal_year_id INTEGER,
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                FOREIGN KEY (paid_by_account_id) REFERENCES accounts(id),
                FOREIGN KEY (transaction_id) REFERENCES financial_transactions(id) ON DELETE SET NULL,
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                loan_amount REAL NOT NULL,
                interest_rate REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                installment_amount REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('{}', '{}', '{}')),
                description TEXT,
                fiscal_year_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES persons(id),
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """.format(LoanStatus.ACTIVE.value, LoanStatus.PAID_OFF.value, LoanStatus.DEFAULTED.value),
            """
            CREATE TABLE IF NOT EXISTS loan_installments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL,
                due_date TEXT NOT NULL,
                installment_amount REAL NOT NULL,
                principal_amount REAL NOT NULL DEFAULT 0.0,
                interest_amount REAL NOT NULL DEFAULT 0.0,
                paid_date TEXT,
                payment_method TEXT CHECK(payment_method IN ({})),
                description TEXT,
                fiscal_year_id INTEGER,
                FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE,
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """.format(', '.join(f"'{pm.value}'" for pm in PaymentMethod) if PaymentMethod else "NULL"),
            """
            CREATE TABLE IF NOT EXISTS boms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,       -- <<< Should be 'name'
    component_product_id INTEGER NOT NULL, -- <<< اطمینان از این نام و نوع
    quantity_produced REAL DEFAULT 1.0,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    creation_date DATE,
    last_modified_date DATE,
    FOREIGN KEY (component_product_id) REFERENCES products (id)
);
            """,
            """
            CREATE TABLE IF NOT EXISTS bom_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bom_id INTEGER NOT NULL,
                material_product_id INTEGER NOT NULL,
                quantity_used REAL NOT NULL,
                unit_of_measure TEXT NOT NULL,
                FOREIGN KEY (bom_id) REFERENCES boms(id) ON DELETE CASCADE,
                FOREIGN KEY (material_product_id) REFERENCES products(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS production_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bom_id INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                quantity_to_produce REAL NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('{}', '{}', '{}', '{}')),
                completion_date TEXT,
                produced_quantity REAL,
                description TEXT,
                fiscal_year_id INTEGER,
                FOREIGN KEY (bom_id) REFERENCES boms(id),
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """.format(ProductionOrderStatus.PENDING.value, ProductionOrderStatus.IN_PROGRESS.value, ProductionOrderStatus.COMPLETED.value, ProductionOrderStatus.CANCELED.value),
            """
            CREATE TABLE IF NOT EXISTS purchase_order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                ordered_quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_item_amount REAL NOT NULL,
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS material_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_date TEXT NOT NULL,
                person_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity_received REAL NOT NULL,
                unit_price REAL,
                purchase_order_id INTEGER,
                purchase_order_item_id INTEGER,
                description TEXT,
                fiscal_year_id INTEGER,
                FOREIGN KEY (person_id) REFERENCES persons(id),
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE SET NULL,
                FOREIGN KEY (purchase_order_item_id) REFERENCES purchase_order_items(id) ON DELETE SET NULL,
                FOREIGN KEY (fiscal_year_id) REFERENCES fiscal_years(id)
            );
            """
        ]
        
        query_map = {}
        malformed_queries_count = 0
        for q_idx, q_sql_str in enumerate(queries):
            stripped_q_sql_str = q_sql_str.strip() # Strip the individual query string
            lines = stripped_q_sql_str.splitlines()

            # Check if the first line (lines[0]) contains "CREATE TABLE IF NOT EXISTS"
            if lines and "CREATE TABLE IF NOT EXISTS" in lines[0].upper():
                try:
                    # Extract table name from lines[0]
                    # e.g., "CREATE TABLE IF NOT EXISTS fiscal_years ("
                    table_name_part = lines[0].upper().split("CREATE TABLE IF NOT EXISTS")[1].strip()
                    table_name = table_name_part.split("(")[0].strip()
                    if table_name:
                        query_map[table_name.lower()] = stripped_q_sql_str # Store the stripped query
                    else:
                        logger.error(f"PARSED EMPTY TABLE NAME for query starting with: {lines[0][:80]}...")
                        malformed_queries_count +=1
                except IndexError:
                    logger.error(f"COULD NOT PARSE TABLE NAME from line: {lines[0][:80]}...")
                    malformed_queries_count +=1
            else:
                first_line_snippet = lines[0][:100] if lines else "Query was empty or just whitespace"
                logger.error(f"Query at index {q_idx} does NOT start with 'CREATE TABLE IF NOT EXISTS' on its first effective line or is malformed. First line: '{first_line_snippet}'...")
                malformed_queries_count += 1
        
        if malformed_queries_count > 0:
            logger.warning(f"{malformed_queries_count} queries could not be properly parsed for table names during map creation.")

        order = [
            'fiscal_years', 'settings', 'accounts', 'persons', 'products',
            'employees', 'boms', 
            'purchase_orders', 
            'checks',          
            'invoices', 
            'invoice_items', 'financial_transactions', 
            'payments',        
            'inventory_movements', 'payrolls', 'loans', 'loan_installments', 
            'bom_items', 'production_orders', 'purchase_order_items', 'material_receipts'
        ]
        
        final_ordered_queries = []
        order_lower = [name.lower() for name in order]

        for table_name_key in order_lower:
            if table_name_key in query_map:
                final_ordered_queries.append(query_map.pop(table_name_key))
            else:
                logger.warning(f"Table '{table_name_key}' (from order list) was not found in query_map. Possible parsing issue or query missing.")

        if query_map: 
            for table_name_left, q_sql_left in query_map.items():
                logger.warning(f"Query for table '{table_name_left}' (key from query_map) was not in explicit order list, appending at the end.")
                final_ordered_queries.append(q_sql_left)
        
        if not final_ordered_queries and queries:
             logger.error("CRITICAL: No queries were prepared for execution. Check parsing logic and query list integrity.")
             return 

        try:
            with self as conn:
                cursor = conn.cursor()
                logger.info(f"Attempting to execute {len(final_ordered_queries)} table creation SQL query(ies).")
                for query_index, query_sql_to_execute in enumerate(final_ordered_queries):
                    table_name_log = "Unknown Table"
                    # Re-parse table name for logging from the actual query string to be executed
                    current_query_lines = query_sql_to_execute.strip().splitlines()
                    if current_query_lines and "CREATE TABLE IF NOT EXISTS" in current_query_lines[0].upper():
                         try:
                             table_name_part_log = current_query_lines[0].upper().split("CREATE TABLE IF NOT EXISTS")[1].strip()
                             table_name_log = table_name_part_log.split("(")[0].strip()
                         except IndexError:
                             table_name_log = "Unknown Table (parse error for log)"
                    
                    logger.debug(f"Executing SQL for: {table_name_log.lower()} (Query {query_index+1}/{len(final_ordered_queries)})")
                    try:
                        cursor.execute(query_sql_to_execute)
                    except sqlite3.Error as e_exec:
                        logger.error(f"SQLite error creating table '{table_name_log.lower()}': {e_exec}\nProblematic SQL (first 200 chars):\n{query_sql_to_execute[:200]}...")
                        raise 
                conn.commit()
                logger.info("Database tables checked/created successfully (or errors were raised).")
        except sqlite3.Error as e_conn:
            logger.error(f"Failed to create database tables due to SQLite connection/transaction error: {e_conn}")
            raise
        except Exception as e_general:
            logger.error(f"An unexpected error occurred during table creation: {e_general}", exc_info=True)
            raise
           # --- شروع بخش جدید: افزودن حساب‌های پیش‌فرض سیستمی ---
        default_accounts_data = [
            # Accounts for InvoiceManager & general accounting
            (1, "حساب‌های دریافتنی کل", AccountType.ASSET.value, None, 0.0),
            (2, "درآمد فروش", AccountType.REVENUE.value, None, 0.0),
            (3, "موجودی کالا (خرید/فروش)", AccountType.ASSET.value, None, 0.0), # حساب عمومی موجودی
            (4, "حساب‌های پرداختنی کل", AccountType.LIABILITY.value, None, 0.0),
            (5, "هزینه خرید (خدمات/متفرقه)", AccountType.EXPENSE.value, None, 0.0),
            (10, "صندوق/بانک اصلی", AccountType.ASSET.value, None, 0.0), # برای پرداخت حقوق و سایر پرداخت‌های پیش‌فرض

            # Accounts for CheckManager
            (101, "اسناد دریافتنی مدت‌دار", AccountType.ASSET.value, None, 0.0),
            (201, "اسناد پرداختنی مدت‌دار", AccountType.LIABILITY.value, None, 0.0),
            (501, "هزینه کارمزد بانکی", AccountType.EXPENSE.value, None, 0.0),

            # Accounts for PayrollManager
            (601, "هزینه حقوق و دستمزد", AccountType.EXPENSE.value, None, 0.0),

            # Accounts for LoanManager
            (701, "وام‌های پرداختی به دیگران (دارایی)", AccountType.ASSET.value, None, 0.0),
            (801, "وام‌های دریافتی (بدهی)", AccountType.LIABILITY.value, None, 0.0),
            (901, "درآمد بهره (وام)", AccountType.REVENUE.value, None, 0.0),
            (902, "هزینه بهره (وام)", AccountType.EXPENSE.value, None, 0.0),
            
            # می توانید حساب های گروه اصلی را هم اضافه کنید
            (1000, "دارایی‌ها", AccountType.ASSET.value, None, 0.0), # یک حساب گروه نمونه
            (2000, "بدهی‌ها", AccountType.LIABILITY.value, None, 0.0), # یک حساب گروه نمونه
            (3000, "سرمایه", AccountType.EQUITY.value, None, 0.0), # یک حساب گروه نمونه
            (4000, "درآمدها", AccountType.REVENUE.value, None, 0.0), # یک حساب گروه نمونه
            (5000, "هزینه‌ها", AccountType.EXPENSE.value, None, 0.0)  # یک حساب گروه نمونه
        ]
        
        insert_account_query = "INSERT OR IGNORE INTO accounts (id, name, type, parent_id, balance) VALUES (?, ?, ?, ?, ?);"
        # --- پایان بخش جدید ---

        try:
            with self as conn:
                cursor = conn.cursor()
                logger.info("Checking/Creating database tables...")
                for query_index, query in enumerate(queries):
                    # ... (کد قبلی برای اجرای CREATE TABLE ها) ...
                    table_name_log = "Unknown Table" # Fallback
                    lines_exec = query.strip().splitlines()
                    if lines_exec and "CREATE TABLE IF NOT EXISTS" in lines_exec[0].upper(): # Adjusted to check lines_exec[0]
                         try:
                             table_name_part_log = lines_exec[0].upper().split("CREATE TABLE IF NOT EXISTS")[1].strip()
                             table_name_log = table_name_part_log.split("(")[0].strip()
                         except IndexError:
                             table_name_log = f"Unknown Table (parse error on line: {lines_exec[0][:60]})"
                    
                    logger.debug(f"Executing table creation for: {table_name_log.lower()} (Query {query_index+1}/{len(queries)})")
                    try:
                        cursor.execute(query)
                    except sqlite3.Error as e_table:
                        logger.error(f"Error creating table {table_name_log.lower()}: {e_table}\nSQL:\n{query[:200]}...")
                        raise

                logger.info("Database tables checked/created successfully.")
                
                # --- افزودن حساب‌های پیش‌فرض ---
                logger.info("Seeding default system accounts if they don't exist...")
                for acc_data in default_accounts_data:
                    try:
                        cursor.execute(insert_account_query, acc_data)
                        if cursor.rowcount > 0: # اگر ردیفی اضافه شد
                             logger.info(f"Default account '{acc_data[1]}' (ID: {acc_data[0]}) seeded.")
                    except sqlite3.Error as e_seed:
                         logger.error(f"Error seeding default account '{acc_data[1]}' (ID: {acc_data[0]}): {e_seed}")
                         # ادامه می‌دهیم تا بقیه حساب‌ها هم سعی در ایجاد شوند
                logger.info("Default system accounts seeding process completed.")

                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database schema or seed data: {e}", exc_info=True)
            # در صورت بروز خطا، ممکن است بخواهید conn.rollback() را فراخوانی کنید اگر تراکنش صریحی باز کرده بودید
            raise


# Example usage (typically called once at application startup)
if __name__ == '__main__':
    # Apply the project's logging configuration
    import logging.config # Moved import here
    logging.config.dictConfig(LOGGING_CONFIG)
    
    main_logger = logging.getLogger() # Get root logger or a specific one like __name__
                                      # Using root logger here to catch all configured logs for the test.
    
    db_manager = DatabaseManager()
    try:
        main_logger.info("Initializing database setup test...")
        db_manager.create_tables()
        main_logger.info("Test table creation process completed.")
        
        with db_manager as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            main_logger.info(f"Tables found in database ({len(table_names)}): {table_names}")

    except Exception as e:
        main_logger.error(f"An error occurred during database setup test: {e}", exc_info=True)
