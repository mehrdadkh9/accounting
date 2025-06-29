# src/business_logic/fiscal_year_manager.py
from typing import List, Optional, Dict, Any,TYPE_CHECKING
from datetime import date

from src.business_logic.entities.fiscal_year_entity import FiscalYearEntity
from src.constants import FiscalYearStatus # برای وضعیت
import logging
if TYPE_CHECKING: # This block is only for type checkers
    from src.data_access.fiscal_years_repository import FiscalYearsRepository

logger = logging.getLogger(__name__)

class FiscalYearManager:
    def __init__(self, fiscal_years_repository: 'FiscalYearsRepository'):
        if fiscal_years_repository is None:
            raise ValueError("fiscal_years_repository cannot be None")
        self.fiscal_years_repository = fiscal_years_repository
        logger.info("FiscalYearManager initialized.")

    def create_fiscal_year(self, 
                           name: str, 
                           start_date: date, 
                           end_date: date, 
                           status: FiscalYearStatus = FiscalYearStatus.OPEN
                           ) -> Optional[FiscalYearEntity]:
        """Creates a new fiscal year."""
        logger.info(f"Attempting to create fiscal year: {name}")
        if not name or not start_date or not end_date:
            raise ValueError("Name, start date, and end date are required for a fiscal year.")
        if start_date >= end_date:
            raise ValueError("Start date must be before end date for a fiscal year.")

        # TODO: Add validation for overlapping fiscal years if needed

        fy_entity = FiscalYearEntity(
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=status
        )
        try:
            created_fy = self.fiscal_years_repository.add(fy_entity)
            logger.info(f"Fiscal year '{name}' (ID: {created_fy.id}) created successfully.")
            return created_fy
        except Exception as e:
            logger.error(f"Error creating fiscal year '{name}': {e}", exc_info=True)
            raise # یا None برگردانید

    def get_fiscal_year_by_id(self, fy_id: int) -> Optional[FiscalYearEntity]:
        logger.debug(f"Fetching fiscal year by ID: {fy_id}")
        if not isinstance(fy_id, int) or fy_id <= 0:
            logger.warning(f"Attempted to fetch fiscal year with invalid ID: {fy_id}")
            return None
        return self.fiscal_years_repository.get_by_id(fy_id)

    def get_all_fiscal_years(self) -> List[FiscalYearEntity]:
        logger.debug("Fetching all fiscal years.")
        return self.fiscal_years_repository.get_all()

    def get_active_fiscal_year(self) -> Optional[FiscalYearEntity]:
        """
        Attempts to find an active (OPEN) fiscal year.
        Simple implementation: returns the first open fiscal year found.
        A more robust system might have only one truly "active" fiscal year.
        """
        logger.debug("Attempting to find an active fiscal year.")
        all_fys = self.get_all_fiscal_years()
        for fy in all_fys:
            if fy.status == FiscalYearStatus.OPEN:
                logger.info(f"Active fiscal year found: '{fy.name}' (ID: {fy.id})")
                return fy
        logger.warning("No active (OPEN) fiscal year found.")
        return None

    def update_fiscal_year(self, 
                           fy_id: int, 
                           name: Optional[str] = None, 
                           start_date: Optional[date] = None, 
                           end_date: Optional[date] = None, 
                           status: Optional[FiscalYearStatus] = None
                           ) -> Optional[FiscalYearEntity]:
        """Updates an existing fiscal year."""
        logger.info(f"Attempting to update fiscal year ID: {fy_id}")
        fy_to_update = self.fiscal_years_repository.get_by_id(fy_id)
        if not fy_to_update:
            logger.warning(f"Fiscal year ID {fy_id} not found for update.")
            return None

        changed = False
        if name is not None and fy_to_update.name != name:
            fy_to_update.name = name
            changed = True
        if start_date is not None and fy_to_update.start_date != start_date:
            fy_to_update.start_date = start_date
            changed = True
        if end_date is not None and fy_to_update.end_date != end_date:
            fy_to_update.end_date = end_date
            changed = True
        if status is not None and fy_to_update.status != status:
            fy_to_update.status = status
            changed = True

        if fy_to_update.start_date >= fy_to_update.end_date:
             raise ValueError("Start date must be before end date.")

        if changed:
            try:
                updated_fy = self.fiscal_years_repository.update(fy_to_update)
                logger.info(f"Fiscal year ID {fy_id} updated successfully.")
                return updated_fy
            except Exception as e:
                logger.error(f"Error updating fiscal year ID {fy_id}: {e}", exc_info=True)
                raise
        else:
            logger.info(f"No changes to update for fiscal year ID {fy_id}.")
            return fy_to_update

    def delete_fiscal_year(self, fy_id: int) -> bool:
        """
        Deletes a fiscal year. 
        Caution: Ensure no transactions or documents are linked to it.
        Database constraints (ON DELETE RESTRICT) should prevent deletion if linked.
        """
        logger.warning(f"Attempting to delete fiscal year ID: {fy_id}. This is a sensitive operation.")
        # TODO: Add checks to see if this fiscal year is in use by any transactions/documents.
        # If in use, deletion should be prevented or handled with extreme care.
        try:
            self.fiscal_years_repository.delete(fy_id)
            logger.info(f"Fiscal year ID {fy_id} deleted.")
            return True
        except Exception as e: # Catching generic Exception, specific DB errors might be better
            logger.error(f"Error deleting fiscal year ID {fy_id}: {e}", exc_info=True)
            # This could be due to FOREIGN KEY constraints if the fiscal year is in use.
            # Re-raise or return False with a more specific message.
            raise ValueError(f"امکان حذف سال مالی با شناسه {fy_id} وجود ندارد. ممکن است در حال استفاده باشد: {e}")