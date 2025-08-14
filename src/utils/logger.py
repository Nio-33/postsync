"""
Logging Configuration

This module provides structured logging configuration for PostSync
using structlog for better observability and debugging.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor

from src.config.settings import get_settings


def setup_logging() -> None:
    """Set up structured logging for the application."""
    settings = get_settings()
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    
    # Define processors for structlog
    processors: list[Processor] = [
        # Add timestamp
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add development-friendly formatting for local development
    if settings.environment == "development":
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    else:
        # Production: JSON formatting for better log aggregation
        processors.extend([
            # Add context information
            add_app_context,
            structlog.processors.JSONRenderer(),
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def add_app_context(logger: Any, name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add application context to log entries."""
    settings = get_settings()
    
    # Add application metadata
    event_dict["app"] = "postsync"
    event_dict["version"] = "1.0.0"
    event_dict["environment"] = settings.environment
    
    # Add request ID if available (would be set by middleware)
    # This is a placeholder for request tracking
    if hasattr(logger, "_context") and "request_id" in logger._context:
        event_dict["request_id"] = logger._context["request_id"]
    
    return event_dict


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name."""
    return structlog.get_logger(name)


# Logging utilities for common patterns
class LoggingMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger instance for this class."""
        return structlog.get_logger(self.__class__.__name__)


def log_function_call(func_name: str, **kwargs) -> None:
    """Log function call with parameters."""
    logger = structlog.get_logger("function_call")
    logger.info(f"Calling {func_name}", **kwargs)


def log_api_request(method: str, path: str, user_id: str = None, **kwargs) -> None:
    """Log API request details."""
    logger = structlog.get_logger("api_request")
    logger.info(
        "API request",
        method=method,
        path=path,
        user_id=user_id,
        **kwargs
    )


def log_api_response(method: str, path: str, status_code: int, duration_ms: float, **kwargs) -> None:
    """Log API response details."""
    logger = structlog.get_logger("api_response")
    logger.info(
        "API response",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


def log_external_api_call(service: str, operation: str, success: bool, duration_ms: float = None, **kwargs) -> None:
    """Log external API call details."""
    logger = structlog.get_logger("external_api")
    log_data = {
        "service": service,
        "operation": operation,
        "success": success,
        **kwargs
    }
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    
    if success:
        logger.info("External API call successful", **log_data)
    else:
        logger.error("External API call failed", **log_data)


def log_user_action(user_id: str, action: str, resource_type: str = None, resource_id: str = None, **kwargs) -> None:
    """Log user action for audit trail."""
    logger = structlog.get_logger("user_action")
    logger.info(
        "User action",
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        **kwargs
    )


def log_business_event(event_type: str, **kwargs) -> None:
    """Log business events for analytics and monitoring."""
    logger = structlog.get_logger("business_event")
    logger.info(
        "Business event",
        event_type=event_type,
        **kwargs
    )


def log_performance_metric(metric_name: str, value: float, unit: str = None, **kwargs) -> None:
    """Log performance metrics."""
    logger = structlog.get_logger("performance")
    log_data = {
        "metric": metric_name,
        "value": value,
        **kwargs
    }
    
    if unit:
        log_data["unit"] = unit
    
    logger.info("Performance metric", **log_data)


def log_security_event(event_type: str, severity: str = "info", user_id: str = None, **kwargs) -> None:
    """Log security-related events."""
    logger = structlog.get_logger("security")
    
    log_data = {
        "security_event": event_type,
        "severity": severity,
        **kwargs
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    if severity == "critical":
        logger.critical("Security event", **log_data)
    elif severity == "error":
        logger.error("Security event", **log_data)
    elif severity == "warning":
        logger.warning("Security event", **log_data)
    else:
        logger.info("Security event", **log_data)