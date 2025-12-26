"""Domain exceptions"""


class DomainException(Exception):
    """Base domain exception"""

    pass


class ValidationException(DomainException):
    """Validation error"""

    pass


class ExternalAPIException(DomainException):
    """External API error"""

    pass


class CircuitBreakerOpenException(DomainException):
    """Circuit breaker is open"""

    pass


class RateLimitException(DomainException):
    """Rate limit exceeded"""

    pass


class JobNotFoundException(DomainException):
    """Job not found"""

    pass
