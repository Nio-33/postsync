"""
Common Schemas

Shared schemas used across multiple API endpoints for consistent
request/response formatting and validation.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

# Type variable for generic responses
T = TypeVar('T')


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page"
    )
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)"
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    
    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    trace_id: Optional[str] = Field(
        None,
        description="Request trace ID for debugging"
    )


class SuccessResponse(BaseModel):
    """Standard success response format."""
    
    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional response data"
    )


class HealthCheckResponse(BaseModel):
    """Health check response format."""
    
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Current timestamp")
    checks: Dict[str, str] = Field(
        default_factory=dict,
        description="Individual service check results"
    )


class BulkOperationRequest(BaseModel):
    """Request schema for bulk operations."""
    
    operation: str = Field(..., description="Operation type")
    items: List[str] = Field(..., description="List of item IDs")
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Operation-specific parameters"
    )


class BulkOperationResponse(BaseModel):
    """Response schema for bulk operations."""
    
    operation: str = Field(..., description="Operation type")
    total_items: int = Field(..., description="Total items processed")
    successful_items: int = Field(..., description="Successfully processed items")
    failed_items: int = Field(..., description="Failed items")
    errors: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of errors for failed items"
    )


class FilterParams(BaseModel):
    """Standard filtering parameters."""
    
    search: Optional[str] = Field(None, description="Search query")
    status: Optional[str] = Field(None, description="Filter by status")
    platform: Optional[str] = Field(None, description="Filter by platform")
    topic: Optional[str] = Field(None, description="Filter by topic")
    date_from: Optional[str] = Field(None, description="Filter from date (ISO format)")
    date_to: Optional[str] = Field(None, description="Filter to date (ISO format)")


class MetricsResponse(BaseModel):
    """Response schema for metrics data."""
    
    metric_name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Metric unit")
    timestamp: str = Field(..., description="Metric timestamp")
    tags: Optional[Dict[str, str]] = Field(
        None,
        description="Metric tags for grouping"
    )


class ConfigurationResponse(BaseModel):
    """Response schema for configuration data."""
    
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    is_public: bool = Field(default=True, description="Whether config is public")


class NotificationResponse(BaseModel):
    """Response schema for notifications."""
    
    id: str = Field(..., description="Notification ID")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    read: bool = Field(default=False, description="Whether notification is read")
    created_at: str = Field(..., description="Creation timestamp")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional notification data"
    )