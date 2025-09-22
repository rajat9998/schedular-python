"""
Input validation utilities
Implements proper validation patterns for API inputs
"""

from typing import Tuple
from src.common.exceptions import ValidationError

def validate_pagination(page: int, per_page: int, max_per_page: int = 100) -> Tuple[int, int]:
    """
    Validate pagination parameters
    
    Args:
        page: Page number
        per_page: Items per page
        max_per_page: Maximum allowed items per page
        
    Returns:
        Tuple[int, int]: Validated (page, per_page)
        
    Raises:
        ValidationError: If validation fails
    """
    if page < 1:
        raise ValidationError("Page number must be >= 1", field="page")
    
    if per_page < 1:
        raise ValidationError("Per page must be >= 1", field="per_page")
    
    if per_page > max_per_page:
        raise ValidationError(f"Per page cannot exceed {max_per_page}", field="per_page")
    
    return page, per_page

def validate_job_name(name: str) -> str:
    """
    Validate job name
    
    Args:
        name: Job name
        
    Returns:
        str: Validated name
        
    Raises:
        ValidationError: If validation fails
    """
    if not name or not name.strip():
        raise ValidationError("Job name is required", field="name")
    
    name = name.strip()
    
    if len(name) < 3:
        raise ValidationError("Job name must be at least 3 characters", field="name")
    
    if len(name) > 255:
        raise ValidationError("Job name cannot exceed 255 characters", field="name")
    
    # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
    import re
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValidationError(
            "Job name can only contain letters, numbers, spaces, hyphens, and underscores", 
            field="name"
        )
    
    return name

def validate_cron_expression(cron_expr: str) -> str:
    """
    Validate cron expression
    
    Args:
        cron_expr: Cron expression string
        
    Returns:
        str: Validated cron expression
        
    Raises:
        ValidationError: If validation fails
    """
    from croniter import croniter
    
    if not cron_expr or not cron_expr.strip():
        raise ValidationError("Cron expression cannot be empty", field="cron_expression")
    
    cron_expr = cron_expr.strip()
    
    try:
        # Test if cron expression is valid
        croniter(cron_expr)
        return cron_expr
    except Exception as e:
        raise ValidationError(f"Invalid cron expression: {str(e)}", field="cron_expression")

def validate_interval_seconds(interval: int) -> int:
    """
    Validate interval in seconds
    
    Args:
        interval: Interval in seconds
        
    Returns:
        int: Validated interval
        
    Raises:
        ValidationError: If validation fails
    """
    if interval <= 0:
        raise ValidationError("Interval must be positive", field="interval_seconds")
    
    # Minimum interval: 60 seconds (1 minute)
    if interval < 60:
        raise ValidationError("Minimum interval is 60 seconds", field="interval_seconds")
    
    # Maximum interval: 7 days
    max_interval = 7 * 24 * 3600  # 7 days in seconds
    if interval > max_interval:
        raise ValidationError("Maximum interval is 7 days", field="interval_seconds")
    
    return interval

def validate_priority(priority: int) -> int:
    """
    Validate job priority
    
    Args:
        priority: Job priority
        
    Returns:
        int: Validated priority
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(priority, int):
        raise ValidationError("Priority must be an integer", field="priority")
    
    if priority < 1 or priority > 10:
        raise ValidationError("Priority must be between 1 and 10", field="priority")
    
    return priority

def validate_timeout_seconds(timeout: int) -> int:
    """
    Validate timeout in seconds
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        int: Validated timeout
        
    Raises:
        ValidationError: If validation fails
    """
    if timeout <= 0:
        raise ValidationError("Timeout must be positive", field="timeout_seconds")
    
    # Minimum timeout: 30 seconds
    if timeout < 30:
        raise ValidationError("Minimum timeout is 30 seconds", field="timeout_seconds")
    
    # Maximum timeout: 24 hours
    max_timeout = 24 * 3600  # 24 hours in seconds
    if timeout > max_timeout:
        raise ValidationError("Maximum timeout is 24 hours", field="timeout_seconds")
    
    return timeout

def validate_max_retries(max_retries: int) -> int:
    """
    Validate maximum retry attempts
    
    Args:
        max_retries: Maximum retry attempts
        
    Returns:
        int: Validated max retries
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(max_retries, int):
        raise ValidationError("Max retries must be an integer", field="max_retries")
    
    if max_retries < 0:
        raise ValidationError("Max retries cannot be negative", field="max_retries")
    
    if max_retries > 10:
        raise ValidationError("Max retries cannot exceed 10", field="max_retries")
    
    return max_retries