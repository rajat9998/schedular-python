"""
Custom exceptions for the scheduler microservice
Following proper exception hierarchy and error handling patterns
"""

class SchedulerError(Exception):
    """Base exception for scheduler-related errors"""
    pass

class JobNotFoundError(SchedulerError):
    """Raised when a job is not found"""
    def __init__(self, message="Job not found"):
        self.message = message
        super().__init__(self.message)

class InvalidJobConfigurationError(SchedulerError):
    """Raised when job configuration is invalid"""
    def __init__(self, message="Invalid job configuration"):
        self.message = message
        super().__init__(self.message)

class JobExecutionError(SchedulerError):
    """Raised when job execution fails"""
    def __init__(self, message="Job execution failed", job_id=None):
        self.message = message
        self.job_id = job_id
        super().__init__(self.message)

class SchedulerNotAvailableError(SchedulerError):
    """Raised when scheduler service is not available"""
    def __init__(self, message="Scheduler service not available"):
        self.message = message
        super().__init__(self.message)

class ValidationError(SchedulerError):
    """Raised when input validation fails"""
    def __init__(self, message="Validation error", field=None):
        self.message = message
        self.field = field
        super().__init__(self.message)

class RateLimitExceededError(SchedulerError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message="Rate limit exceeded", retry_after=None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)