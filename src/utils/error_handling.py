"""
Centralized Error Handling and Recovery System

This module provides comprehensive error handling capabilities:
- Custom exception classes
- Retry mechanisms with exponential backoff
- Circuit breaker pattern
- Error classification and recovery strategies
- Graceful degradation patterns
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from functools import wraps

import structlog

from src.utils.monitoring import performance_monitor, AlertSeverity


class ErrorCategory(Enum):
    """Categories of errors for classification."""
    TRANSIENT = "transient"  # Temporary errors that may resolve
    PERMANENT = "permanent"  # Errors that won't resolve without intervention
    RATE_LIMIT = "rate_limit"  # API rate limiting errors
    AUTHENTICATION = "authentication"  # Auth/permission errors
    VALIDATION = "validation"  # Input validation errors
    EXTERNAL_SERVICE = "external_service"  # Third-party service errors
    SYSTEM = "system"  # Internal system errors


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for errors."""
    service: str
    operation: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PostSyncError(Exception):
    """Base exception class for PostSync errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        recoverable: bool = True
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context
        self.original_error = original_error
        self.recoverable = recoverable
        self.timestamp = datetime.utcnow()


class ContentGenerationError(PostSyncError):
    """Errors related to content generation."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class APIRateLimitError(PostSyncError):
    """API rate limiting errors."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            **kwargs
        )
        self.retry_after = retry_after


class AuthenticationError(PostSyncError):
    """Authentication and authorization errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class ValidationError(PostSyncError):
    """Input validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            recoverable=False,
            **kwargs
        )
        self.field = field


class ExternalServiceError(PostSyncError):
    """External service errors."""
    
    def __init__(self, message: str, service_name: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.service_name = service_name


class CircuitBreakerError(PostSyncError):
    """Circuit breaker open error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: List[Type[Exception]] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: Type[Exception] = Exception


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.logger = structlog.get_logger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info("Circuit breaker moving to half-open state")
            else:
                raise CircuitBreakerError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        
        except self.config.expected_exception as e:
            await self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (
            datetime.utcnow() - self.last_failure_time
        ).total_seconds() > self.config.recovery_timeout
    
    async def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.logger.info("Circuit breaker closed after successful call")
        
        self.failure_count = 0
    
    async def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                threshold=self.config.failure_threshold
            )


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Error classification rules
        self.error_classifiers = {
            "openai": self._classify_openai_error,
            "google": self._classify_google_error,
            "reddit": self._classify_reddit_error,
            "linkedin": self._classify_linkedin_error,
            "twitter": self._classify_twitter_error,
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        recovery_strategy: Optional[str] = None
    ) -> Optional[Any]:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            recovery_strategy: Optional recovery strategy to use
            
        Returns:
            Recovery result if applicable, None otherwise
        """
        try:
            # Classify the error
            postsync_error = self._classify_error(error, context)
            
            # Log the error
            await self._log_error(postsync_error)
            
            # Send to monitoring
            await self._track_error_metrics(postsync_error)
            
            # Attempt recovery if applicable
            if postsync_error.recoverable and recovery_strategy:
                return await self._attempt_recovery(postsync_error, recovery_strategy)
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Error in error handler",
                original_error=str(error),
                handler_error=str(e)
            )
            return None
    
    def _classify_error(self, error: Exception, context: ErrorContext) -> PostSyncError:
        """Classify an error into PostSync error taxonomy."""
        
        # If already a PostSync error, return as-is
        if isinstance(error, PostSyncError):
            return error
        
        # Try service-specific classification
        if context.service in self.error_classifiers:
            classified = self.error_classifiers[context.service](error)
            if classified:
                return classified
        
        # Generic classification based on error type
        error_str = str(error).lower()
        
        # Rate limiting
        if any(term in error_str for term in ["rate limit", "quota", "too many requests"]):
            return APIRateLimitError(
                f"Rate limit exceeded: {str(error)}",
                context=context,
                original_error=error
            )
        
        # Authentication
        if any(term in error_str for term in ["unauthorized", "forbidden", "invalid token", "auth"]):
            return AuthenticationError(
                f"Authentication error: {str(error)}",
                context=context,
                original_error=error
            )
        
        # Network/connectivity
        if any(term in error_str for term in ["connection", "timeout", "network", "dns"]):
            return ExternalServiceError(
                f"Network error: {str(error)}",
                service_name=context.service,
                context=context,
                original_error=error
            )
        
        # Default classification
        return PostSyncError(
            str(error),
            context=context,
            original_error=error
        )
    
    def _classify_openai_error(self, error: Exception) -> Optional[PostSyncError]:
        """Classify OpenAI-specific errors."""
        error_str = str(error).lower()
        
        if "rate limit" in error_str:
            return APIRateLimitError(
                f"OpenAI rate limit: {str(error)}",
                service_name="openai"
            )
        
        if "context length" in error_str or "token limit" in error_str:
            return ValidationError(
                f"OpenAI input too long: {str(error)}",
                field="prompt_length"
            )
        
        return None
    
    def _classify_google_error(self, error: Exception) -> Optional[PostSyncError]:
        """Classify Google API errors."""
        error_str = str(error).lower()
        
        if "quota" in error_str or "rate limit" in error_str:
            return APIRateLimitError(
                f"Google API quota exceeded: {str(error)}",
                service_name="google"
            )
        
        if "safety" in error_str or "blocked" in error_str:
            return ContentGenerationError(
                f"Content blocked by safety filter: {str(error)}"
            )
        
        return None
    
    def _classify_reddit_error(self, error: Exception) -> Optional[PostSyncError]:
        """Classify Reddit API errors."""
        error_str = str(error).lower()
        
        if "429" in error_str or "rate limit" in error_str:
            return APIRateLimitError(
                f"Reddit rate limit: {str(error)}",
                service_name="reddit"
            )
        
        return None
    
    def _classify_linkedin_error(self, error: Exception) -> Optional[PostSyncError]:
        """Classify LinkedIn API errors."""
        error_str = str(error).lower()
        
        if "throttle" in error_str or "rate limit" in error_str:
            return APIRateLimitError(
                f"LinkedIn rate limit: {str(error)}",
                service_name="linkedin"
            )
        
        return None
    
    def _classify_twitter_error(self, error: Exception) -> Optional[PostSyncError]:
        """Classify Twitter API errors."""
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "429" in error_str:
            return APIRateLimitError(
                f"Twitter rate limit: {str(error)}",
                service_name="twitter"
            )
        
        return None
    
    async def _log_error(self, error: PostSyncError):
        """Log error with appropriate level and context."""
        log_data = {
            "error_message": error.message,
            "error_category": error.category.value,
            "error_severity": error.severity.value,
            "recoverable": error.recoverable,
            "timestamp": error.timestamp.isoformat()
        }
        
        if error.context:
            log_data.update({
                "service": error.context.service,
                "operation": error.context.operation,
                "user_id": error.context.user_id,
                "request_id": error.context.request_id
            })
        
        if error.original_error:
            log_data["original_error"] = str(error.original_error)
        
        # Log with appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical("Critical error occurred", **log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error("High severity error occurred", **log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning("Medium severity error occurred", **log_data)
        else:
            self.logger.info("Low severity error occurred", **log_data)
    
    async def _track_error_metrics(self, error: PostSyncError):
        """Track error metrics for monitoring."""
        try:
            labels = {
                "category": error.category.value,
                "severity": error.severity.value,
                "service": error.context.service if error.context else "unknown"
            }
            
            # Track error count
            await performance_monitor.track_metric(
                "errors_total",
                1,
                performance_monitor.MetricType.COUNTER,
                labels,
                "Total errors by category and severity"
            )
            
            # Track error rate
            await performance_monitor.track_metric(
                "error_rate",
                1,
                performance_monitor.MetricType.RATE,
                labels,
                "Error rate by service"
            )
            
            # Trigger alert for critical errors
            if error.severity == ErrorSeverity.CRITICAL:
                await performance_monitor._trigger_alert(
                    performance_monitor.Alert(
                        id=f"critical_error_{int(time.time())}",
                        severity=AlertSeverity.CRITICAL,
                        title="Critical Error Occurred",
                        description=f"Critical error in {error.context.service if error.context else 'unknown'}: {error.message}",
                        metric_name="critical_error",
                        current_value=1,
                        threshold=0,
                        timestamp=datetime.utcnow()
                    )
                )
        
        except Exception as e:
            self.logger.error("Failed to track error metrics", error=str(e))
    
    async def _attempt_recovery(
        self,
        error: PostSyncError,
        strategy: str
    ) -> Optional[Any]:
        """Attempt error recovery using specified strategy."""
        try:
            if strategy == "retry_with_backoff":
                return await self._retry_with_backoff(error)
            elif strategy == "fallback_service":
                return await self._fallback_service(error)
            elif strategy == "graceful_degradation":
                return await self._graceful_degradation(error)
            else:
                self.logger.warning(f"Unknown recovery strategy: {strategy}")
                return None
        
        except Exception as e:
            self.logger.error(
                "Recovery attempt failed",
                strategy=strategy,
                error=str(e)
            )
            return None
    
    async def _retry_with_backoff(self, error: PostSyncError) -> Optional[Any]:
        """Implement retry with exponential backoff."""
        # This would retry the original operation
        # In practice, this needs to be integrated with the calling code
        self.logger.info("Retry recovery strategy triggered", error=error.message)
        return None
    
    async def _fallback_service(self, error: PostSyncError) -> Optional[Any]:
        """Implement fallback to alternative service."""
        self.logger.info("Fallback service recovery triggered", error=error.message)
        return None
    
    async def _graceful_degradation(self, error: PostSyncError) -> Optional[Any]:
        """Implement graceful degradation."""
        self.logger.info("Graceful degradation recovery triggered", error=error.message)
        return None
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or create circuit breaker for service."""
        if service_name not in self.circuit_breakers:
            config = CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                expected_exception=ExternalServiceError
            )
            self.circuit_breakers[service_name] = CircuitBreaker(config)
        
        return self.circuit_breakers[service_name]


# Global error handler instance
error_handler = ErrorHandler()


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_errors: Optional[List[Type[Exception]]] = None
):
    """Decorator for adding retry logic to functions."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                
                except Exception as e:
                    last_exception = e
                    
                    # Check if error is retryable
                    if retryable_errors and not any(isinstance(e, err_type) for err_type in retryable_errors):
                        raise e
                    
                    # Don't retry on last attempt
                    if attempt == max_attempts - 1:
                        raise e
                    
                    # Calculate delay
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    structlog.get_logger(__name__).warning(
                        "Retrying after error",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e)
                    )
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator


def with_circuit_breaker(service_name: str):
    """Decorator for adding circuit breaker protection."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = error_handler.get_circuit_breaker(service_name)
            return await circuit_breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


def with_error_handling(
    service_name: str,
    operation_name: str,
    recovery_strategy: Optional[str] = None
):
    """Decorator for comprehensive error handling."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = ErrorContext(
                service=service_name,
                operation=operation_name,
                # Would extract user_id and request_id from args/kwargs in practice
            )
            
            try:
                return await func(*args, **kwargs)
            
            except Exception as e:
                await error_handler.handle_error(e, context, recovery_strategy)
                raise e
        
        return wrapper
    return decorator