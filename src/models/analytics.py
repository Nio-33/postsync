"""
Analytics Data Models and Schemas

This module contains analytics-related data models for tracking content performance,
user engagement metrics, and platform-specific analytics.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Analytics metric type enumeration."""
    IMPRESSIONS = "impressions"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    CLICKS = "clicks"
    SAVES = "saves"
    FOLLOWS = "follows"
    REACH = "reach"
    ENGAGEMENT_RATE = "engagement_rate"
    CLICK_THROUGH_RATE = "click_through_rate"


class TimeGranularity(str, Enum):
    """Time-based aggregation granularity."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class PlatformType(str, Enum):
    """Social media platform enumeration."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class MetricPoint(BaseModel):
    """Single metric data point with timestamp."""
    
    timestamp: datetime = Field(..., description="Metric timestamp")
    value: float = Field(..., description="Metric value")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PostAnalytics(BaseModel):
    """Analytics data for a single post."""
    
    # Post identification
    post_id: str = Field(..., description="Unique post identifier")
    content_id: str = Field(..., description="Related content item ID")
    platform: PlatformType = Field(..., description="Social media platform")
    platform_post_id: str = Field(..., description="Platform-specific post ID")
    
    # Basic metrics
    impressions: int = Field(default=0, description="Total impressions")
    likes: int = Field(default=0, description="Total likes")
    comments: int = Field(default=0, description="Total comments")
    shares: int = Field(default=0, description="Total shares")
    clicks: int = Field(default=0, description="Total clicks")
    saves: int = Field(default=0, description="Total saves/bookmarks")
    
    # Calculated metrics
    engagement_rate: float = Field(default=0.0, description="Engagement rate percentage")
    click_through_rate: float = Field(default=0.0, description="Click-through rate percentage")
    
    # Time-series data
    metrics_history: Dict[MetricType, List[MetricPoint]] = Field(
        default_factory=dict,
        description="Historical metrics data"
    )
    
    # Audience insights
    top_countries: List[Dict[str, int]] = Field(
        default_factory=list,
        description="Top countries by engagement"
    )
    age_demographics: Dict[str, int] = Field(
        default_factory=dict,
        description="Age group distribution"
    )
    gender_demographics: Dict[str, int] = Field(
        default_factory=dict,
        description="Gender distribution"
    )
    
    # Performance benchmarks
    industry_percentile: Optional[float] = Field(
        None,
        description="Performance percentile within industry"
    )
    user_percentile: Optional[float] = Field(
        None,
        description="Performance percentile for the user"
    )
    
    # Timestamps
    first_tracked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="First analytics tracking timestamp"
    )
    last_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last analytics update timestamp"
    )
    
    @property
    def total_engagements(self) -> int:
        """Calculate total engagements."""
        return self.likes + self.comments + self.shares + self.saves
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserAnalytics(BaseModel):
    """Aggregated analytics data for a user."""
    
    # User identification
    user_id: str = Field(..., description="User identifier")
    
    # Time period
    period_start: datetime = Field(..., description="Analytics period start")
    period_end: datetime = Field(..., description="Analytics period end")
    granularity: TimeGranularity = Field(..., description="Data aggregation granularity")
    
    # Aggregate metrics across all platforms
    total_posts: int = Field(default=0, description="Total posts published")
    total_impressions: int = Field(default=0, description="Total impressions")
    total_engagements: int = Field(default=0, description="Total engagements")
    average_engagement_rate: float = Field(default=0.0, description="Average engagement rate")
    
    # Platform-specific metrics
    platform_metrics: Dict[PlatformType, Dict[MetricType, float]] = Field(
        default_factory=dict,
        description="Metrics broken down by platform"
    )
    
    # Content performance
    best_performing_post: Optional[str] = Field(
        None,
        description="ID of best performing post"
    )
    top_topics: List[Dict[str, Union[str, float]]] = Field(
        default_factory=list,
        description="Top performing content topics"
    )
    
    # Trends and insights
    growth_metrics: Dict[MetricType, float] = Field(
        default_factory=dict,
        description="Growth percentages for each metric"
    )
    engagement_trends: List[MetricPoint] = Field(
        default_factory=list,
        description="Engagement rate trends over time"
    )
    
    # Comparative analysis
    industry_benchmark: Dict[MetricType, float] = Field(
        default_factory=dict,
        description="Industry benchmark comparisons"
    )
    percentile_ranks: Dict[MetricType, float] = Field(
        default_factory=dict,
        description="User's percentile rank for each metric"
    )
    
    # Recommendations
    optimization_suggestions: List[str] = Field(
        default_factory=list,
        description="AI-generated optimization suggestions"
    )
    
    # Timestamps
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Analytics generation timestamp"
    )
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlatformAnalytics(BaseModel):
    """Platform-specific analytics for a user."""
    
    # Identification
    user_id: str = Field(..., description="User identifier")
    platform: PlatformType = Field(..., description="Social media platform")
    
    # Account metrics
    follower_count: int = Field(default=0, description="Current follower count")
    following_count: int = Field(default=0, description="Current following count")
    profile_views: int = Field(default=0, description="Profile views in period")
    
    # Content metrics
    posts_published: int = Field(default=0, description="Posts published in period")
    average_post_performance: Dict[MetricType, float] = Field(
        default_factory=dict,
        description="Average performance per post"
    )
    
    # Engagement patterns
    best_posting_times: List[Dict[str, Union[str, float]]] = Field(
        default_factory=list,
        description="Optimal posting times with engagement rates"
    )
    audience_activity_pattern: Dict[str, float] = Field(
        default_factory=dict,
        description="Hourly audience activity patterns"
    )
    
    # Growth tracking
    follower_growth_rate: float = Field(
        default=0.0,
        description="Follower growth rate percentage"
    )
    engagement_growth_rate: float = Field(
        default=0.0,
        description="Engagement growth rate percentage"
    )
    
    # Historical data
    follower_history: List[MetricPoint] = Field(
        default_factory=list,
        description="Historical follower count data"
    )
    engagement_history: List[MetricPoint] = Field(
        default_factory=list,
        description="Historical engagement rate data"
    )
    
    # Timestamps
    period_start: datetime = Field(..., description="Analytics period start")
    period_end: datetime = Field(..., description="Analytics period end")
    last_updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Request/Response Schemas
class AnalyticsRequest(BaseModel):
    """Request schema for analytics data."""
    
    start_date: datetime = Field(..., description="Analytics period start date")
    end_date: datetime = Field(..., description="Analytics period end date")
    granularity: TimeGranularity = Field(
        default=TimeGranularity.DAY,
        description="Data aggregation granularity"
    )
    platforms: Optional[List[PlatformType]] = Field(
        None,
        description="Specific platforms to include (all if None)"
    )
    metrics: Optional[List[MetricType]] = Field(
        None,
        description="Specific metrics to include (all if None)"
    )


class AnalyticsResponse(BaseModel):
    """Response schema for analytics data."""
    
    user_analytics: UserAnalytics
    platform_analytics: List[PlatformAnalytics]
    post_analytics: List[PostAnalytics]
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnalyticsSummary(BaseModel):
    """Summary analytics for dashboard display."""
    
    # Period information
    period_start: datetime
    period_end: datetime
    
    # Key metrics
    total_posts: int
    total_impressions: int
    total_engagements: int
    average_engagement_rate: float
    follower_growth: int
    
    # Top performers
    best_post_id: Optional[str]
    best_post_engagement_rate: Optional[float]
    top_platform: Optional[PlatformType]
    
    # Trends
    engagement_trend: str = Field(description="up/down/stable")
    impression_trend: str = Field(description="up/down/stable")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }