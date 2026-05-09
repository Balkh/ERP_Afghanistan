"""
Example Usage of Exception Handling System
Shows how to use the custom exceptions in application code.
"""

from .base import (
    PharmacyERPException,
    ValidationException,
    DatabaseException,
    ServiceException,
    ConfigurationException
)

def validate_age(age: int) -> None:
    """Example function that uses ValidationException."""
    if age < 0:
        raise ValidationException(
            message="Age cannot be negative",
            field="age",
            details={"provided_value": age, "minimum_allowed": 0}
        )
    if age > 150:
        raise ValidationException(
            message="Age seems unrealistic",
            field="age",
            details={"provided_value": age, "maximum_reasonable": 150}
        )

def get_user_from_db(user_id: int) -> dict:
    """Example function that uses DatabaseException."""
    # Simulate a database error
    if user_id < 0:
        raise DatabaseException(
            message="Invalid user ID provided",
            error_code="INVALID_USER_ID",
            details={"user_id": user_id, "table": "users"}
        )
    # Simulate user not found
    if user_id == 999:
        raise DatabaseException(
            message="User not found",
            error_code="USER_NOT_FOUND",
            details={"user_id": user_id}
        )
    
    # Return a mock user
    return {"id": user_id, "name": f"User {user_id}"}

def process_user_data(user_data: dict) -> dict:
    """Example function that uses ServiceException."""
    if not user_data.get("name"):
        raise ServiceException(
            message="User data is incomplete",
            error_code="INCOMPLETE_USER_DATA",
            details={"missing_fields": ["name"], "provided_data": user_data}
        )
    
    # Process the data
    return {"processed": True, "data": user_data}

def load_app_config(config_path: str) -> dict:
    """Example function that uses ConfigurationException."""
    import os
    if not os.path.exists(config_path):
        raise ConfigurationException(
            message=f"Configuration file not found: {config_path}",
            error_code="CONFIG_FILE_NOT_FOUND",
            details={"config_path": config_path}
        )
    
    # In a real app, we would load and parse the config file here
    return {"loaded": True, "path": config_path}

# Example usage:
if __name__ == "__main__":
    try:
        validate_age(-5)
    except ValidationException as e:
        print(f"Validation error: {e}")
        print(f"Field: {e.field}")
        print(f"Details: {e.details}")
    
    try:
        get_user_from_db(-1)
    except DatabaseException as e:
        print(f"Database error: {e}")
        print(f"Error code: {e.error_code}")
        print(f"Details: {e.details}")
    
    try:
        process_user_data({"id": 1})
    except ServiceException as e:
        print(f"Service error: {e}")
        print(f"Error code: {e.error_code}")
        print(f"Details: {e.details}")
    
    try:
        load_app_config("/nonexistent/config.json")
    except ConfigurationException as e:
        print(f"Configuration error: {e}")
        print(f"Error code: {e.error_code}")
        print(f"Details: {e.details}")