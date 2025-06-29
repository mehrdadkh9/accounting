# src/data_access/payment_header_repository.py

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import date, datetime

from src.data_access.base_repository import BaseRepository
from src.data_access.database_manager import DatabaseManager
from src.constants import DATE_FORMAT,PaymentType # برای تبدیل تاریخ
import logging
from src.business_logic.entities.payment_header_entity import PaymentHeaderEntity
from decimal import Decimal # برای مبلغ

logger = logging.getLogger(__name__)

class PaymentHeaderRepository(BaseRepository['PaymentHeaderEntity']):
    def __init__(self, db_manager: DatabaseManager):
        db_columns = [
            "payment_date", 
            "person_id", 
            "total_amount", 
            "description", 
            "invoice_id", 
            "purchase_order_id", 
            "fiscal_year_id",
            "payment_type" # <<< اضافه شد
        ]
        super().__init__(db_manager, PaymentHeaderEntity, "payment_headers", db_columns=db_columns)

    def _entity_from_row(self, row: Dict[str, Any]) -> PaymentHeaderEntity:
        # تبدیل رشته به Enum برای payment_type
        payment_type_val = row.get('payment_type')
        try:
            payment_type_enum = PaymentType(payment_type_val) if payment_type_val else PaymentType.PAYMENT
        except ValueError:
            logger.warning(f"Invalid payment_type value '{payment_type_val}' from DB. Defaulting to PAYMENT.")
            payment_type_enum = PaymentType.PAYMENT
            
        return PaymentHeaderEntity(
            id=row.get('id'),
            payment_date=date.fromisoformat(row['payment_date']) if row.get('payment_date') else date.today(),
            person_id=row.get('person_id'),
            total_amount=Decimal(str(row.get('total_amount', '0.0'))),
            description=row.get('description'),
            invoice_id=row.get('invoice_id'),
            purchase_order_id=row.get('purchase_order_id'),
            fiscal_year_id=row.get('fiscal_year_id'),
            payment_type=payment_type_enum # <<< اضافه شد
        )

    def get_by_person_id(self, person_id: int) -> List['PaymentHeaderEntity']:
        query = f"SELECT * FROM {self._table_name} WHERE person_id = ? ORDER BY payment_date DESC"
        rows = self.db_manager.fetch_all(query, (person_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_invoice_id(self, invoice_id: int) -> List['PaymentHeaderEntity']:
        query = f"SELECT * FROM {self._table_name} WHERE invoice_id = ? ORDER BY payment_date ASC"
        rows = self.db_manager.fetch_all(query, (invoice_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    def get_by_purchase_order_id(self, purchase_order_id: int) -> List['PaymentHeaderEntity']:
        query = f"SELECT * FROM {self._table_name} WHERE purchase_order_id = ? ORDER BY payment_date ASC"
        rows = self.db_manager.fetch_all(query, (purchase_order_id,))
        return [self._entity_from_row(dict(row)) for row in rows if row]

    # می‌توانید متدهای دیگری مانند get_by_date_range و غیره اضافه کنید