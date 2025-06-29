# src/data_access/loan_installments_repository.py

from typing import Dict, Any, Optional, List
from datetime import datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.business_logic.entities.loan_installment_entity import LoanInstallmentEntity
from src.constants import PaymentMethod, DATE_FORMAT
import logging

logger = logging.getLogger(__name__)

class LoanInstallmentsRepository(BaseRepository[LoanInstallmentEntity]):
    def __init__(self, db_manager: DatabaseManager):
        
        super().__init__(db_manager=db_manager, 
                         model_type=LoanInstallmentEntity,  # <<< Pass the CLASS AccountEntity
                         table_name="loan_installments") 
    def _entity_from_row(self, row: Dict[str, Any]) -> LoanInstallmentEntity:
        if row is None:
            raise ValueError("Input row cannot be None for LoanInstallmentEntity")
        try:
            # Assuming due_date is NOT NULL
            due_date_obj = datetime.strptime(row['due_date'], DATE_FORMAT).date()
            
            paid_date_str = row.get('paid_date')
            paid_date_obj = datetime.strptime(paid_date_str, DATE_FORMAT).date() if paid_date_str else None
            
            payment_method_str = row.get('payment_method')
            payment_method_obj = PaymentMethod(payment_method_str) if payment_method_str else None

            return LoanInstallmentEntity(
                id=row['id'],
                loan_id=row['loan_id'],
                due_date=due_date_obj,
                installment_amount=float(row['installment_amount']),
                principal_amount=float(row.get('principal_amount', 0.0)), # Default if NULL
                interest_amount=float(row.get('interest_amount', 0.0)),   # Default if NULL
                paid_date=paid_date_obj,
                payment_method=payment_method_obj,
                description=row.get('description'),
                fiscal_year_id=row.get('fiscal_year_id')
            )
        except KeyError as e:
            logger.error(f"KeyError when creating LoanInstallmentEntity from row: {e}. Row: {row}")
            raise
        except ValueError as e: # For Enum, date or float conversion
            logger.error(f"ValueError when creating LoanInstallmentEntity: {e}. Row: {row}")
            raise

    def get_by_loan_id(self, loan_id: int) -> List[LoanInstallmentEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE loan_id = ? ORDER BY due_date ASC"
        rows = self.db_manager.fetch_all(query, (loan_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_unpaid_installments_by_loan_id(self, loan_id: int) -> List[LoanInstallmentEntity]:
        query = f"SELECT * FROM {self._table_name} WHERE loan_id = ? AND paid_date IS NULL ORDER BY due_date ASC"
        rows = self.db_manager.fetch_all(query, (loan_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]