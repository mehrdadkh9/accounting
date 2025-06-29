# src/business_logic/person_manager.py

from typing import Optional, List
from src.business_logic.entities.person_entity import PersonEntity
from src.data_access.persons_repository import PersonsRepository
from src.constants import PersonType
import logging

logger = logging.getLogger(__name__)

class PersonManager:
    def __init__(self, persons_repository: PersonsRepository):
        """
        Initializes the PersonManager with a PersonsRepository.
        :param persons_repository: An instance of PersonsRepository.
        """
        if persons_repository is None:
            raise ValueError("persons_repository cannot be None")
        self.persons_repository = persons_repository

    def add_person(self, name: str, person_type: PersonType, contact_info: Optional[str] = None) -> PersonEntity:
        """
        Adds a new person to the system.
        Validates input and then uses the repository to save the person.
        """
        if not name or not isinstance(name, str):
            logger.error("Person name cannot be empty.")
            raise ValueError("نام شخص نمی‌تواند خالی باشد.")
        if not isinstance(person_type, PersonType):
            logger.error(f"Invalid person_type: {person_type}")
            raise ValueError("نوع شخص نامعتبر است.")

        # Check if person with the same name and type already exists (optional business rule)
        # existing_persons = self.persons_repository.get_by_name(name, exact=True)
        # for p in existing_persons:
        #     if p.person_type == person_type:
        #         logger.warning(f"Person '{name}' with type '{person_type.value}' already exists with ID {p.id}.")
        #         raise ValueError(f"شخصی با نام '{name}' و نوع '{person_type.value}' از قبل موجود است.")

        person_entity = PersonEntity(
            name=name,
            person_type=person_type,
            contact_info=contact_info
        )
        
        try:
            created_person = self.persons_repository.add(person_entity)
            logger.info(f"Person '{created_person.name}' (ID: {created_person.id}) added successfully.")
            return created_person
        except Exception as e:
            logger.error(f"Error adding person '{name}': {e}", exc_info=True)
            # Depending on the exception, you might want to raise a more specific business-level exception
            raise # Re-raise the original exception or a custom one

    def get_person_by_id(self, person_id: int) -> Optional[PersonEntity]:
        """Retrieves a person by their ID."""
        if not isinstance(person_id, int) or person_id <= 0:
            logger.error(f"Invalid person_id: {person_id}")
            return None # Or raise ValueError
            
        person = self.persons_repository.get_by_id(person_id)
        if person:
            logger.debug(f"Person with ID {person_id} found: {person.name}")
        else:
            logger.debug(f"Person with ID {person_id} not found.")
        return person

    def get_all_persons(self) -> List[PersonEntity]:
        """Retrieves all persons."""
        logger.debug("Fetching all persons.")
        return self.persons_repository.get_all()

    def get_persons_by_type(self, person_type: PersonType) -> List[PersonEntity]:
        """Retrieves all persons of a specific type."""
        if not isinstance(person_type, PersonType):
            logger.error(f"Invalid person_type: {person_type}")
            return [] # Or raise ValueError
            
        logger.debug(f"Fetching persons of type: {person_type.value}")
        return self.persons_repository.get_by_type(person_type)
        
    def find_persons_by_name(self, name_query: str, exact_match: bool = False) -> List[PersonEntity]:
        """Finds persons by name (exact or partial match)."""
        if not name_query:
            return []
        logger.debug(f"Searching for persons with name query: '{name_query}', exact: {exact_match}")
        return self.persons_repository.get_by_name(name_query, exact=exact_match)

    def update_person(self, 
                      person_id: int, 
                      name: Optional[str] = None, 
                      person_type: Optional[PersonType] = None, 
                      contact_info: Optional[str] = None) -> Optional[PersonEntity]:
        """
        Updates an existing person's details.
        Only provided fields are updated.
        """
        if not isinstance(person_id, int) or person_id <= 0:
            logger.error(f"Invalid person_id for update: {person_id}")
            raise ValueError("شناسه شخص نامعتبر است.")

        person_to_update = self.persons_repository.get_by_id(person_id)
        if not person_to_update:
            logger.warning(f"Person with ID {person_id} not found for update.")
            return None

        updated = False
        if name is not None:
            if not name:
                raise ValueError("نام شخص برای به‌روزرسانی نمی‌تواند خالی باشد.")
            person_to_update.name = name
            updated = True
        
        if person_type is not None:
            if not isinstance(person_type, PersonType):
                raise ValueError("نوع شخص برای به‌روزرسانی نامعتبر است.")
            person_to_update.person_type = person_type
            updated = True
            
        if contact_info is not None: # Allow empty string for contact_info to clear it
            person_to_update.contact_info = contact_info
            updated = True

        if updated:
            try:
                updated_person = self.persons_repository.update(person_to_update)
                logger.info(f"Person '{updated_person.name}' (ID: {updated_person.id}) updated successfully.")
                return updated_person
            except Exception as e:
                logger.error(f"Error updating person ID {person_id}: {e}", exc_info=True)
                raise
        else:
            logger.info(f"No updates provided for person ID {person_id}.")
            return person_to_update # Return the original if no changes were made

    def delete_person(self, person_id: int) -> bool:
        """
        Deletes a person by their ID.
        Returns True if deletion was successful, False otherwise.
        Note: If a Person is an Employee, the database schema's ON DELETE CASCADE
        should handle deletion of the corresponding Employee record.
        """
        if not isinstance(person_id, int) or person_id <= 0:
            logger.error(f"Invalid person_id for delete: {person_id}")
            # raise ValueError("شناسه شخص نامعتبر است.")
            return False

        person_to_delete = self.persons_repository.get_by_id(person_id)
        if not person_to_delete:
            logger.warning(f"Person with ID {person_id} not found for deletion.")
            return False
            
        try:
            self.persons_repository.delete(person_id)
            logger.info(f"Person with ID {person_id} (Name: {person_to_delete.name}) deleted successfully.")
            return True
        except Exception as e:
            logger.error(f"Error deleting person ID {person_id}: {e}", exc_info=True)
            return False