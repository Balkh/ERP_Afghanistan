from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any
from django.db import models
from django.core.exceptions import ValidationError, ObjectDoesNotExist

# Generic type variables
ModelType = TypeVar("ModelType", bound=models.Model)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseService(ABC, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Abstract base service class that defines the interface for all services.
    Implements the Service Layer pattern to encapsulate business logic.
    """
    
    def __init__(self, model: type[ModelType]):
        """
        Initialize the service with a Django model.
        
        Args:
            model: The Django model class this service operates on
        """
        self.model = model
    
    @abstractmethod
    def get(self, id: Any) -> Optional[ModelType]:
        """
        Retrieve a single object by ID.
        
        Args:
            id: The ID of the object to retrieve
            
        Returns:
            The object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Retrieve multiple objects with pagination and filtering.
        
        Args:
            skip: Number of objects to skip
            limit: Maximum number of objects to return
            filters: Dictionary of field-value pairs to filter by
            
        Returns:
            List of objects matching the criteria
        """
        pass
    
    @abstractmethod
    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new object.
        
        Args:
            obj_in: The object data to create
            
        Returns:
            The created object
            
        Raises:
            ValidationError: If the data is invalid
        """
        pass
    
    @abstractmethod
    def update(
        self, 
        id: Any, 
        obj_in: UpdateSchemaType
    ) -> Optional[ModelType]:
        """
        Update an existing object.
        
        Args:
            id: The ID of the object to update
            obj_in: The updated object data
            
        Returns:
            The updated object if found, None otherwise
            
        Raises:
            ValidationError: If the data is invalid
        """
        pass
    
    @abstractmethod
    def delete(self, id: Any) -> bool:
        """
        Delete an object by ID.
        
        Args:
            id: The ID of the object to delete
            
        Returns:
            True if the object was deleted, False if not found
        """
        pass
    
    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count objects matching the given filters.
        
        Args:
            filters: Dictionary of field-value pairs to filter by
            
        Returns:
            The number of objects matching the criteria
        """
        pass


class BaseRepository(ABC, Generic[ModelType]):
    """
    Abstract base repository class that defines the interface for data access.
    Implements the Repository pattern to abstract data persistence logic.
    """
    
    def __init__(self, model: type[ModelType]):
        """
        Initialize the repository with a Django model.
        
        Args:
            model: The Django model class this repository operates on
        """
        self.model = model
    
    @abstractmethod
    def get(self, id: Any) -> Optional[ModelType]:
        """
        Retrieve a single object by ID.
        
        Args:
            id: The ID of the object to retrieve
            
        Returns:
            The object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Retrieve multiple objects with pagination and filtering.
        
        Args:
            skip: Number of objects to skip
            limit: Maximum number of objects to return
            filters: Dictionary of field-value pairs to filter by
            
        Returns:
            List of objects matching the criteria
        """
        pass
    
    @abstractmethod
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create a new object.
        
        Args:
            obj_in: Dictionary of field values for the new object
            
        Returns:
            The created object
            
        Raises:
            ValidationError: If the data is invalid
        """
        pass
    
    @abstractmethod
    def update(
        self, 
        id: Any, 
        obj_in: Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        Update an existing object.
        
        Args:
            id: The ID of the object to update
            obj_in: Dictionary of field values to update
            
        Returns:
            The updated object if found, None otherwise
            
        Raises:
            ValidationError: If the data is invalid
        """
        pass
    
    @abstractmethod
    def delete(self, id: Any) -> bool:
        """
        Delete an object by ID.
        
        Args:
            id: The ID of the object to delete
            
        Returns:
            True if the object was deleted, False if not found
        """
        pass
    
    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count objects matching the given filters.
        
        Args:
            filters: Dictionary of field-value pairs to filter by
            
        Returns:
            The number of objects matching the criteria
        """
        pass