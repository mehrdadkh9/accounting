# src/business_logic/employee_manager.py

from typing import Optional, List, Dict, Any, Tuple
from datetime import date

from src.business_logic.entities.person_entity import PersonEntity
from src.business_logic.entities.employee_entity import EmployeeEntity
from src.data_access.employees_repository import EmployeesRepository
from src.business_logic.person_manager import PersonManager # To manage the Person aspect
from src.constants import PersonType,DATE_FORMAT 
import logging

logger = logging.getLogger(__name__)

class EmployeeManager:
    def __init__(self,
                 employees_repository: EmployeesRepository,
                 person_manager: PersonManager):
        """
        Initializes the EmployeeManager.
        :param employees_repository: An instance of EmployeesRepository.
        :param person_manager: An instance of PersonManager.
        """
        if employees_repository is None: raise ValueError("employees_repository cannot be None")
        if person_manager is None: raise ValueError("person_manager cannot be None")

        self.employees_repository = employees_repository
        self.person_manager = person_manager

    def add_employee(self,
                     name: str,
                     base_salary: float,
                     hire_date: date,
                     contact_info: Optional[str] = None,
                     national_id: Optional[str] = None,
                     position: Optional[str] = None,
                     is_active: bool = True) -> Optional[Tuple[PersonEntity, EmployeeEntity]]:
        """
        Adds a new employee. This involves creating a Person record and then an Employee record.
        Returns a tuple of (PersonEntity, EmployeeEntity) if successful.
        """
        if not name: raise ValueError("نام کارمند نمی‌تواند خالی باشد.")
        if base_salary < 0: raise ValueError("حقوق پایه نمی‌تواند منفی باشد.")
        if not isinstance(hire_date, date): raise ValueError("تاریخ استخدام نامعتبر است.")

        # --- Start Transactional Block (Conceptual) ---
        person_entity = None
        employee_entity = None
        try:
            # 1. Create Person record
            person_entity = self.person_manager.add_person(
                name=name,
                person_type=PersonType.EMPLOYEE,
                contact_info=contact_info
            )
            if not person_entity or person_entity.id is None:
                raise Exception("خطا در ایجاد رکورد شخص برای کارمند.")
            
            logger.info(f"Person record created for employee '{name}' with Person ID: {person_entity.id}.")

            # 2. Create Employee record
            employee_entity_data = EmployeeEntity(
                person_id=person_entity.id,
                national_id=national_id,
                position=position,
                base_salary=base_salary,
                hire_date=hire_date,
                is_active=is_active
            )
            employee_entity = self.employees_repository.add(employee_entity_data)
            if not employee_entity or employee_entity.id is None:
                # Rollback person creation if employee creation fails
                logger.error(f"Failed to create employee-specific record for Person ID {person_entity.id}. Attempting to rollback person record.")
                try:
                    self.person_manager.delete_person(person_entity.id) # type: ignore
                    logger.info(f"Person record ID {person_entity.id} rolled back due to employee creation failure.")
                except Exception as rollback_e:
                    logger.critical(f"CRITICAL: Failed to rollback Person ID {person_entity.id} after employee creation failure: {rollback_e}")
                raise Exception("خطا در ایجاد رکورد اختصاصی کارمند.")

            logger.info(f"Employee record created (ID: {employee_entity.id}) for Person ID {person_entity.id} ('{name}').")
            return person_entity, employee_entity

        except Exception as e:
            logger.error(f"Error adding employee '{name}': {e}", exc_info=True)
            # If person_entity was created but employee_entity failed, person_entity might have been rolled back.
            # If person_entity creation itself failed, nothing more to do.
            # This conceptual transaction needs robust handling in a real system.
            raise # Re-raise or return None
        # --- End Transactional Block ---

    def get_employee_details_by_employee_id(self, employee_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieves combined details of an employee (Person + Employee info) by Employee ID.
        Returns a dictionary or None if not found.
        """
        if not isinstance(employee_id, int) or employee_id <= 0: return None
        
        employee_record = self.employees_repository.get_by_id(employee_id)
        if not employee_record:
            logger.debug(f"No employee-specific record found for Employee ID: {employee_id}")
            return None
        
        person_record = self.person_manager.get_person_by_id(employee_record.person_id)
        if not person_record:
            logger.error(f"CRITICAL: Employee record ID {employee_id} exists but corresponding Person record ID {employee_record.person_id} not found!")
            # This indicates a data integrity issue.
            return None 
            # Or return partial data with a warning:
            # return {"employee_data": employee_record.__dict__, "person_data": None, "error": "Person record missing"}


        # Combine data into a single dictionary for convenience
        combined_details = {
            "employee_id": employee_record.id,
            "person_id": person_record.id,
            "name": person_record.name,
            "contact_info": person_record.contact_info,
            "person_type": person_record.person_type.value, # Send enum value
            # Employee specific fields
            "national_id": employee_record.national_id,
            "position": employee_record.position,
            "base_salary": employee_record.base_salary,
            "hire_date": employee_record.hire_date.strftime(DATE_FORMAT) if employee_record.hire_date else None,
            "is_active": employee_record.is_active
        }
        return combined_details

    def get_employee_by_person_id(self, person_id: int) -> Optional[EmployeeEntity]:
        """Retrieves the employee-specific record using the person_id."""
        if not isinstance(person_id, int) or person_id <= 0: return None
        return self.employees_repository.get_by_person_id(person_id) # Assumes repo has this method

    def get_all_employee_details(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Retrieves details for all employees, optionally filtering for active ones."""
        all_employee_records = self.employees_repository.get_all()
        
        employee_details_list: List[Dict[str, Any]] = []
        for emp_record in all_employee_records:
            if active_only and not emp_record.is_active:
                continue
            
            details = self.get_employee_details_by_employee_id(emp_record.id) # type: ignore
            if details:
                employee_details_list.append(details)
            else:
                # This case implies an employee record exists but its person details couldn't be fetched,
                # which was logged by get_employee_details_by_employee_id.
                logger.warning(f"Could not fetch full details for Employee ID {emp_record.id} while getting all employees.")

        return employee_details_list

    def update_employee_details(self, 
                                employee_id: int,
                                name: Optional[str] = None,
                                contact_info: Optional[str] = None,
                                national_id: Optional[str] = None,
                                position: Optional[str] = None,
                                base_salary: Optional[float] = None,
                                hire_date: Optional[date] = None,
                                is_active: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """
        Updates details for an employee.
        Allows updating fields in both Person and Employee entities.
        """
        if not isinstance(employee_id, int) or employee_id <= 0: 
            raise ValueError("شناسه کارمند نامعتبر است.")

        employee_record = self.employees_repository.get_by_id(employee_id)
        if not employee_record or not employee_record.id:
            logger.warning(f"Employee with ID {employee_id} not found for update.")
            return None

        # --- Start Transactional Block (Conceptual) ---
        person_updated = False
        employee_specific_updated = False
        try:
            # 1. Update Person details if any are provided
            if name is not None or contact_info is not None:
                # Note: We don't allow changing person_type for an existing employee here.
                updated_person = self.person_manager.update_person(
                    person_id=employee_record.person_id,
                    name=name,
                    contact_info=contact_info
                )
                if updated_person:
                    person_updated = True
                else: # Should not happen if person_id is valid
                    logger.error(f"Failed to update person details for employee ID {employee_id}, person ID {employee_record.person_id}")
                    # Continue to update employee details if person update failed but person exists

            # 2. Update Employee-specific details
            if national_id is not None:
                employee_record.national_id = national_id
                employee_specific_updated = True
            if position is not None:
                employee_record.position = position
                employee_specific_updated = True
            if base_salary is not None:
                if base_salary < 0: raise ValueError("حقوق پایه نمی‌تواند منفی باشد.")
                employee_record.base_salary = base_salary
                employee_specific_updated = True
            if hire_date is not None:
                if not isinstance(hire_date, date): raise ValueError("تاریخ استخدام نامعتبر است.")
                employee_record.hire_date = hire_date
                employee_specific_updated = True
            if is_active is not None:
                employee_record.is_active = is_active
                employee_specific_updated = True
            
            if employee_specific_updated:
                self.employees_repository.update(employee_record)
            
            if person_updated or employee_specific_updated:
                logger.info(f"Details for employee ID {employee_id} (Person ID: {employee_record.person_id}) updated.")
                return self.get_employee_details_by_employee_id(employee_id) # Return fresh combined data
            else:
                logger.info(f"No updates provided for employee ID {employee_id}.")
                return self.get_employee_details_by_employee_id(employee_id) # Return current data

        except Exception as e:
            logger.error(f"Error updating employee ID {employee_id}: {e}", exc_info=True)
            # Rollback would be complex here.
            raise
        # --- End Transactional Block ---

    def set_employee_activity(self, employee_id: int, is_active: bool) -> Optional[Dict[str, Any]]:
        """Sets the active status of an employee."""
        return self.update_employee_details(employee_id=employee_id, is_active=is_active)

    def delete_employee_record(self, employee_id: int, delete_person_record_also: bool = False) -> bool:
        """
        Deletes the Employee-specific record.
        If delete_person_record_also is True, it will also attempt to delete the associated Person record.
        WARNING: Deleting person record will cascade to employee due to DB constraint.
        Usually, employees are marked as inactive rather than deleted.
        """
        logger.warning(f"Attempting to delete employee record ID: {employee_id}. Delete Person: {delete_person_record_also}")
        employee_record = self.employees_repository.get_by_id(employee_id)
        if not employee_record or not employee_record.id:
            logger.warning(f"Employee record ID {employee_id} not found for deletion.")
            return False # Or True if "not found" is ok

        try:
            if delete_person_record_also:
                # Deleting the person will cascade and delete the employee record too due to FK ON DELETE CASCADE
                logger.info(f"Attempting to delete associated Person record (ID: {employee_record.person_id}) which will cascade to Employee ID {employee_id}.")
                return self.person_manager.delete_person(employee_record.person_id)
            else:
                # Just delete the employee-specific part (person record remains as an ex-employee or other type)
                # This might be unusual if the PersonType is still EMPLOYEE.
                # Consider changing PersonType if only employee part is deleted.
                # For now, just delete employee record.
                self.employees_repository.delete(employee_record.id)
                logger.info(f"Employee-specific record ID {employee_id} deleted. Corresponding Person record (ID: {employee_record.person_id}) remains.")
                # If person_type was strictly EMPLOYEE, it might need to be updated to something else or the person deleted.
                # This logic depends on business rules for "ex-employees".
                return True
        except Exception as e:
            logger.error(f"Error deleting employee record ID {employee_id}: {e}", exc_info=True)
            return False