# src/data_access/payrolls_repository.py

from typing import Dict, Any, Optional, List
from datetime import datetime,date
from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.payroll_entity import PayrollEntity
from src.constants import DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class PayrollsRepository(BaseRepository[PayrollEntity]):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager=db_manager, 
                         model_type=PayrollEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="payrolls") 

    def _entity_from_row(self, row: Dict[str, Any]) -> PayrollEntity:
        if row is None:
            raise ValueError("Input row cannot be None for PayrollEntity")
        try:
            # Assuming pay_period_start and pay_period_end are NOT NULL
            pay_period_start_obj = datetime.strptime(row['pay_period_start'], DATE_FORMAT).date()
            pay_period_end_obj = datetime.strptime(row['pay_period_end'], DATE_FORMAT).date()
            
            payment_date_str = row.get('payment_date')
            payment_date_obj = datetime.strptime(payment_date_str, DATE_FORMAT).date() if payment_date_str else None
            
            return PayrollEntity(
                id=row['id'],
                employee_id=row['employee_id'],
                pay_period_start=pay_period_start_obj,
                pay_period_end=pay_period_end_obj,
                gross_salary=float(row['gross_salary']),
                deductions=float(row['deductions']),
                # net_salary is a @property in the entity
                payment_date=payment_date_obj,
                paid_by_account_id=row.get('paid_by_account_id'),
                is_paid=bool(row['is_paid']),
                description=row.get('description'),
                transaction_id=row.get('transaction_id'),
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except KeyError as e:
            logger.error(f"KeyError when creating PayrollEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For date, bool or float conversion
            logger.error(f"ValueError when creating PayrollEntity: {e}. Row: {row}")
            raise

    def get_by_employee_id(self, employee_id: int) -> List[PayrollEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE employee_id = ? ORDER BY pay_period_start DESC"
        rows = self.db_manager.fetch_all(query, (employee_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

     # MODIFIED method signature for type hints
    def get_by_pay_period(self, start_date: date, end_date: date) -> List[PayrollEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE pay_period_start >= ? AND pay_period_end <= ?"
        rows = self.db_manager.fetch_all(query, (start_date.strftime(DATE_FORMAT), end_date.strftime(DATE_FORMAT)))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_unpaid_payrolls(self) -> List[PayrollEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE is_paid = 0 ORDER BY pay_period_start ASC"
        rows = self.db_manager.fetch_all(query)
        return [self._entity_from_row(dict(row)) for row in rows if row]