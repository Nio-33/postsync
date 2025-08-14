"""
Content Management API Endpoints

This module contains content-related endpoints including:
- Content discovery and management
- AI content generation
- Post scheduling and publishing
- Content approval workflows
"""

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from src.models.content import (
    ContentApprovalRequest,
    ContentGenerationRequest,
    ContentItem,
    ContentListResponse,
    ContentResponse,
    ContentSchedulingRequest,
    ContentStatus,
    ContentTopic,
    PlatformType,
)
from src.models.schemas.common import (
    ErrorResponse,
    FilterParams,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from src.models.user import User
from src.services.content_discovery import ContentDiscoveryService
from src.services.content_generation import ContentGenerationService
from src.services.publishing import PublishingService
from src.utils.auth import get_current_user

# Initialize router and dependencies
router = APIRouter()
security = HTTPBearer()
logger = structlog.get_logger(__name__)


def get_content_discovery_service() -> ContentDiscoveryService:
    """Get content discovery service instance."""
    return ContentDiscoveryService()


def get_content_generation_service() -> ContentGenerationService:
    """Get content generation service instance."""
    return ContentGenerationService()


def get_publishing_service() -> PublishingService:
    """Get publishing service instance."""
    return PublishingService()


@router.get(
    "",
    response_model=ContentListResponse,
    dependencies=[Depends(security)]
)
async def get_content_list(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[ContentStatus] = Query(None, alias="status"),
    topic_filter: Optional[ContentTopic] = Query(None, alias="topic"),
    platform_filter: Optional[PlatformType] = Query(None, alias="platform"),
    current_user: User = Depends(get_current_user),
    content_discovery: ContentDiscoveryService = Depends(get_content_discovery_service),
) -> ContentListResponse:
    """
    Get paginated list of content items.
    
    Returns a paginated list of content items with optional filtering
    by status, topic, and platform.
    """
    logger.info(
        "Content list requested",
        user_id=current_user.id,
        page=pagination.page,
        page_size=pagination.page_size
    )
    
    try:
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        if topic_filter:
            filters["topic"] = topic_filter
        if platform_filter:
            filters["platform"] = platform_filter
        
        content_list = await content_discovery.get_user_content(
            user_id=current_user.id,
            page=pagination.page,
            page_size=pagination.page_size,
            filters=filters,
            sort_by=pagination.sort_by,
            sort_order=pagination.sort_order,
        )
        
        return content_list
        
    except Exception as e:
        logger.error("Failed to fetch content list", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch content. Please try again."
        )


@router.get(
    "/{content_id}",
    response_model=ContentResponse,
    dependencies=[Depends(security)],
    responses={
        404: {"model": ErrorResponse, "description": "Content not found"},
    }
)
async def get_content_item(
    content_id: str,
    current_user: User = Depends(get_current_user),
    content_discovery: ContentDiscoveryService = Depends(get_content_discovery_service),
) -> ContentResponse:
    """
    Get specific content item by ID.
    
    Returns detailed information about a specific content item
    including source content, generated posts, and publishing results.
    """
    logger.info("Content item requested", user_id=current_user.id, content_id=content_id)
    
    try:
        content_item = await content_discovery.get_content_item(content_id, current_user.id)
        if not content_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content item not found"
            )
        
        return ContentResponse.from_orm(content_item)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch content item",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch content item. Please try again."
        )


@router.post(
    "/discover",
    response_model=SuccessResponse,
    dependencies=[Depends(security)]
)
async def trigger_content_discovery(
    current_user: User = Depends(get_current_user),
    content_discovery: ContentDiscoveryService = Depends(get_content_discovery_service),
) -> SuccessResponse:
    """
    Manually trigger content discovery.
    
    Initiates content discovery process to find new relevant content
    from configured sources.
    """
    logger.info("Manual content discovery triggered", user_id=current_user.id)
    
    try:
        await content_discovery.discover_content_for_user(current_user.id)
        
        return SuccessResponse(
            success=True,
            message="Content discovery initiated successfully"
        )
        
    except Exception as e:
        logger.error(
            "Content discovery failed",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Content discovery failed. Please try again."
        )


@router.post(
    "/{content_id}/generate",
    response_model=ContentResponse,
    dependencies=[Depends(security)],
    responses={
        404: {"model": ErrorResponse, "description": "Content not found"},
        400: {"model": ErrorResponse, "description": "Content already generated"},
    }
)
async def generate_content_posts(
    content_id: str,
    request: ContentGenerationRequest,
    current_user: User = Depends(get_current_user),
    content_generation: ContentGenerationService = Depends(get_content_generation_service),
) -> ContentResponse:
    """
    Generate social media posts from content.
    
    Uses AI to generate platform-optimized posts from the source content
    for the specified platforms.
    """
    logger.info(
        "Content generation requested",
        user_id=current_user.id,
        content_id=content_id,
        platforms=request.platforms
    )
    
    try:
        # Validate content belongs to user
        content_item = await content_generation.get_content_item(content_id, current_user.id)
        if not content_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content item not found"
            )
        
        # Generate posts for specified platforms
        updated_content = await content_generation.generate_posts(
            content_id=content_id,
            platforms=request.platforms,
            custom_instructions=request.custom_instructions,
            user_preferences=current_user.content_preferences,
        )
        
        logger.info(
            "Content generation completed",
            user_id=current_user.id,
            content_id=content_id,
            platforms=request.platforms
        )
        
        return ContentResponse.from_orm(updated_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Content generation failed",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Content generation failed. Please try again."
        )


@router.post(
    "/{content_id}/approve",
    response_model=ContentResponse,
    dependencies=[Depends(security)],
    responses={
        404: {"model": ErrorResponse, "description": "Content not found"},
        400: {"model": ErrorResponse, "description": "Content not ready for approval"},
    }
)
async def approve_content(
    content_id: str,
    request: ContentApprovalRequest,
    current_user: User = Depends(get_current_user),
    content_discovery: ContentDiscoveryService = Depends(get_content_discovery_service),
) -> ContentResponse:
    """
    Approve or reject generated content.
    
    Approves generated content for publishing or rejects it with
    a reason for regeneration.
    """
    logger.info(
        "Content approval requested",
        user_id=current_user.id,
        content_id=content_id,
        approved=request.approved
    )
    
    try:
        updated_content = await content_discovery.approve_content(
            content_id=content_id,
            user_id=current_user.id,
            approved=request.approved,
            rejection_reason=request.rejection_reason,
        )
        
        logger.info(
            "Content approval processed",
            user_id=current_user.id,
            content_id=content_id,
            approved=request.approved
        )
        
        return ContentResponse.from_orm(updated_content)
        
    except ValueError as e:
        logger.warning(
            "Invalid content approval request",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Content approval failed",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Content approval failed. Please try again."
        )


@router.post(
    "/{content_id}/schedule",
    response_model=ContentResponse,
    dependencies=[Depends(security)],
    responses={
        404: {"model": ErrorResponse, "description": "Content not found"},
        400: {"model": ErrorResponse, "description": "Content not ready for scheduling"},
    }
)
async def schedule_content(
    content_id: str,
    request: ContentSchedulingRequest,
    current_user: User = Depends(get_current_user),
    publishing: PublishingService = Depends(get_publishing_service),
) -> ContentResponse:
    """
    Schedule content for publishing.
    
    Schedules approved content for publishing at the specified time
    on the selected platforms.
    """
    logger.info(
        "Content scheduling requested",
        user_id=current_user.id,
        content_id=content_id,
        scheduled_for=request.scheduled_for,
        platforms=request.platforms
    )
    
    try:
        updated_content = await publishing.schedule_content(
            content_id=content_id,
            user_id=current_user.id,
            scheduled_for=request.scheduled_for,
            platforms=request.platforms,
        )
        
        logger.info(
            "Content scheduled successfully",
            user_id=current_user.id,
            content_id=content_id,
            scheduled_for=request.scheduled_for
        )
        
        return ContentResponse.from_orm(updated_content)
        
    except ValueError as e:
        logger.warning(
            "Invalid content scheduling request",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Content scheduling failed",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Content scheduling failed. Please try again."
        )


@router.post(
    "/{content_id}/publish",
    response_model=ContentResponse,
    dependencies=[Depends(security)],
    responses={
        404: {"model": ErrorResponse, "description": "Content not found"},
        400: {"model": ErrorResponse, "description": "Content not ready for publishing"},
    }
)
async def publish_content_now(
    content_id: str,
    platforms: List[PlatformType] = Query(..., description="Platforms to publish to"),
    current_user: User = Depends(get_current_user),
    publishing: PublishingService = Depends(get_publishing_service),
) -> ContentResponse:
    """
    Publish content immediately.
    
    Publishes approved content immediately to the specified platforms
    without scheduling.
    """
    logger.info(
        "Immediate content publishing requested",
        user_id=current_user.id,
        content_id=content_id,
        platforms=platforms
    )
    
    try:
        updated_content = await publishing.publish_content(
            content_id=content_id,
            user_id=current_user.id,
            platforms=platforms,
        )
        
        logger.info(
            "Content published successfully",
            user_id=current_user.id,
            content_id=content_id,
            platforms=platforms
        )
        
        return ContentResponse.from_orm(updated_content)
        
    except ValueError as e:
        logger.warning(
            "Invalid content publishing request",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Content publishing failed",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Content publishing failed. Please try again."
        )


@router.delete(
    "/{content_id}",
    response_model=SuccessResponse,
    dependencies=[Depends(security)],
    responses={
        404: {"model": ErrorResponse, "description": "Content not found"},
    }
)
async def delete_content_item(
    content_id: str,
    current_user: User = Depends(get_current_user),
    content_discovery: ContentDiscoveryService = Depends(get_content_discovery_service),
) -> SuccessResponse:
    """
    Delete content item.
    
    Permanently deletes a content item and all associated data.
    """
    logger.info("Content deletion requested", user_id=current_user.id, content_id=content_id)
    
    try:
        await content_discovery.delete_content_item(content_id, current_user.id)
        
        logger.info("Content deleted successfully", user_id=current_user.id, content_id=content_id)
        
        return SuccessResponse(
            success=True,
            message="Content item deleted successfully"
        )
        
    except ValueError as e:
        logger.warning(
            "Content deletion denied",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content item not found"
        )
    except Exception as e:
        logger.error(
            "Content deletion failed",
            user_id=current_user.id,
            content_id=content_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Content deletion failed. Please try again."
        )