"""
Analytics API Endpoints

This module contains analytics and reporting endpoints including:
- User performance analytics
- Content performance metrics
- Platform-specific analytics
- Engagement insights and trends
"""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from src.models.analytics import (
    AnalyticsRequest,
    AnalyticsResponse,
    AnalyticsSummary,
    MetricType,
    PlatformAnalytics,
    PlatformType,
    PostAnalytics,
    TimeGranularity,
    UserAnalytics,
)
from src.models.schemas.common import ErrorResponse
from src.models.user import User
from src.services.analytics import AnalyticsService
from src.utils.auth import get_current_user

# Initialize router and dependencies
router = APIRouter()
security = HTTPBearer()
logger = structlog.get_logger(__name__)


def get_analytics_service() -> AnalyticsService:
    """Get analytics service instance."""
    return AnalyticsService()


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    dependencies=[Depends(security)]
)
async def get_analytics_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsSummary:
    """
    Get analytics summary for dashboard.
    
    Returns a high-level summary of user's content performance
    over the specified time period.
    """
    logger.info("Analytics summary requested", user_id=current_user.id, days=days)
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        summary = await analytics_service.get_analytics_summary(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )
        
        return summary
        
    except Exception as e:
        logger.error("Failed to fetch analytics summary", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analytics summary. Please try again."
        )


@router.post(
    "",
    response_model=AnalyticsResponse,
    dependencies=[Depends(security)]
)
async def get_analytics(
    request: AnalyticsRequest,
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsResponse:
    """
    Get comprehensive analytics data.
    
    Returns detailed analytics including user metrics, platform-specific
    data, and individual post performance.
    """
    logger.info(
        "Comprehensive analytics requested",
        user_id=current_user.id,
        start_date=request.start_date,
        end_date=request.end_date,
        granularity=request.granularity
    )
    
    try:
        # Validate date range
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Check if date range is not too large
        max_days = 365
        if (request.end_date - request.start_date).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Date range cannot exceed {max_days} days"
            )
        
        analytics_data = await analytics_service.get_comprehensive_analytics(
            user_id=current_user.id,
            start_date=request.start_date,
            end_date=request.end_date,
            granularity=request.granularity,
            platforms=request.platforms,
            metrics=request.metrics,
        )
        
        return analytics_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch analytics", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch analytics. Please try again."
        )


@router.get(
    "/user",
    response_model=UserAnalytics,
    dependencies=[Depends(security)]
)
async def get_user_analytics(
    start_date: datetime = Query(..., description="Start date for analytics"),
    end_date: datetime = Query(..., description="End date for analytics"),
    granularity: TimeGranularity = Query(TimeGranularity.DAY, description="Data granularity"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> UserAnalytics:
    """
    Get user-level analytics.
    
    Returns aggregated analytics data for the user across all platforms
    and content within the specified time period.
    """
    logger.info(
        "User analytics requested",
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity
    )
    
    try:
        user_analytics = await analytics_service.get_user_analytics(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )
        
        return user_analytics
        
    except Exception as e:
        logger.error("Failed to fetch user analytics", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user analytics. Please try again."
        )


@router.get(
    "/platform/{platform}",
    response_model=PlatformAnalytics,
    dependencies=[Depends(security)]
)
async def get_platform_analytics(
    platform: PlatformType,
    start_date: datetime = Query(..., description="Start date for analytics"),
    end_date: datetime = Query(..., description="End date for analytics"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> PlatformAnalytics:
    """
    Get platform-specific analytics.
    
    Returns detailed analytics for a specific social media platform
    including account metrics and content performance.
    """
    logger.info(
        "Platform analytics requested",
        user_id=current_user.id,
        platform=platform,
        start_date=start_date,
        end_date=end_date
    )
    
    try:
        platform_analytics = await analytics_service.get_platform_analytics(
            user_id=current_user.id,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
        )
        
        return platform_analytics
        
    except Exception as e:
        logger.error(
            "Failed to fetch platform analytics",
            user_id=current_user.id,
            platform=platform,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch platform analytics. Please try again."
        )


@router.get(
    "/posts",
    response_model=List[PostAnalytics],
    dependencies=[Depends(security)]
)
async def get_post_analytics(
    start_date: datetime = Query(..., description="Start date for analytics"),
    end_date: datetime = Query(..., description="End date for analytics"),
    platform: Optional[PlatformType] = Query(None, description="Filter by platform"),
    limit: int = Query(50, ge=1, le=100, description="Number of posts to return"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> List[PostAnalytics]:
    """
    Get post-level analytics.
    
    Returns analytics data for individual posts within the specified
    time period, optionally filtered by platform.
    """
    logger.info(
        "Post analytics requested",
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
        limit=limit
    )
    
    try:
        post_analytics = await analytics_service.get_post_analytics(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            platform=platform,
            limit=limit,
        )
        
        return post_analytics
        
    except Exception as e:
        logger.error("Failed to fetch post analytics", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post analytics. Please try again."
        )


@router.get(
    "/posts/{post_id}",
    response_model=PostAnalytics,
    dependencies=[Depends(security)],
    responses={
        404: {"model": ErrorResponse, "description": "Post not found"},
    }
)
async def get_single_post_analytics(
    post_id: str,
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> PostAnalytics:
    """
    Get analytics for a specific post.
    
    Returns detailed analytics data for a single post including
    engagement metrics, audience insights, and performance trends.
    """
    logger.info("Single post analytics requested", user_id=current_user.id, post_id=post_id)
    
    try:
        post_analytics = await analytics_service.get_single_post_analytics(
            post_id=post_id,
            user_id=current_user.id,
        )
        
        if not post_analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post analytics not found"
            )
        
        return post_analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch single post analytics",
            user_id=current_user.id,
            post_id=post_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch post analytics. Please try again."
        )


@router.get(
    "/insights/engagement",
    response_model=dict,
    dependencies=[Depends(security)]
)
async def get_engagement_insights(
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    """
    Get engagement insights and recommendations.
    
    Returns AI-powered insights about user's content performance
    and recommendations for optimization.
    """
    logger.info("Engagement insights requested", user_id=current_user.id, days=days)
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        insights = await analytics_service.get_engagement_insights(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
        )
        
        return insights
        
    except Exception as e:
        logger.error("Failed to fetch engagement insights", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch engagement insights. Please try again."
        )


@router.get(
    "/insights/best-times",
    response_model=dict,
    dependencies=[Depends(security)]
)
async def get_best_posting_times(
    platform: Optional[PlatformType] = Query(None, description="Platform to analyze"),
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    """
    Get optimal posting times analysis.
    
    Returns analysis of best posting times based on historical
    engagement data, optionally filtered by platform.
    """
    logger.info(
        "Best posting times requested",
        user_id=current_user.id,
        platform=platform,
        days=days
    )
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        best_times = await analytics_service.get_best_posting_times(
            user_id=current_user.id,
            platform=platform,
            start_date=start_date,
            end_date=end_date,
        )
        
        return best_times
        
    except Exception as e:
        logger.error("Failed to fetch best posting times", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch best posting times. Please try again."
        )


@router.post(
    "/refresh",
    response_model=dict,
    dependencies=[Depends(security)]
)
async def refresh_analytics_data(
    platform: Optional[PlatformType] = Query(None, description="Platform to refresh"),
    current_user: User = Depends(get_current_user),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    """
    Refresh analytics data from platforms.
    
    Triggers a refresh of analytics data from social media platforms
    to get the latest metrics and insights.
    """
    logger.info("Analytics refresh requested", user_id=current_user.id, platform=platform)
    
    try:
        refresh_result = await analytics_service.refresh_analytics_data(
            user_id=current_user.id,
            platform=platform,
        )
        
        return {
            "success": True,
            "message": "Analytics data refresh initiated",
            "details": refresh_result
        }
        
    except Exception as e:
        logger.error("Failed to refresh analytics data", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh analytics data. Please try again."
        )