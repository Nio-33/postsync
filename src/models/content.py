"""
Content Data Models and Schemas

This module contains content-related data models, schemas, and validation logic
for discovered content, generated posts, and publishing information.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, validator


class ContentStatus(str, Enum):
    """Content processing status enumeration."""
    DISCOVERED = "discovered"
    ANALYZED = "analyzed"
    GENERATED = "generated"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"


class ContentSource(str, Enum):
    """Content source enumeration."""
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    TWITTER = "twitter"
    RSS_FEED = "rss_feed"
    MANUAL = "manual"


class ContentTopic(str, Enum):
    """Content topic categorization."""
    ARTIFICIAL_INTELLIGENCE = "artificial-intelligence"
    MACHINE_LEARNING = "machine-learning"
    DEEP_LEARNING = "deep-learning"
    GENERATIVE_AI = "generative-ai"
    AI_STARTUPS = "ai-startups"
    AI_FUNDING = "ai-funding"
    AI_RESEARCH = "ai-research"
    AI_ETHICS = "ai-ethics"
    AI_POLICY = "ai-policy"
    AI_CAREERS = "ai-careers"
    DATA_SCIENCE = "data-science"
    ROBOTICS = "robotics"
    COMPUTER_VISION = "computer-vision"
    NATURAL_LANGUAGE_PROCESSING = "nlp"
    AI_TOOLS = "ai-tools"
    AI_NEWS = "ai-news"


class PlatformType(str, Enum):
    """Social media platform enumeration."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class SourceContent(BaseModel):
    """Original source content that was discovered."""
    
    # Source identification
    source_id: str = Field(..., description="Unique identifier from source platform")
    source: ContentSource = Field(..., description="Content source platform")
    url: HttpUrl = Field(..., description="Original content URL")
    
    # Content metadata
    title: str = Field(..., description="Original content title")
    description: Optional[str] = Field(None, description="Content description or excerpt")
    author: Optional[str] = Field(None, description="Content author")
    published_at: datetime = Field(..., description="Original publication timestamp")
    
    # Content analysis
    upvotes: Optional[int] = Field(None, description="Number of upvotes/likes")
    comments_count: Optional[int] = Field(None, description="Number of comments")
    engagement_score: Optional[float] = Field(None, description="Calculated engagement score")
    
    # Classification
    topics: List[ContentTopic] = Field(
        default_factory=list,
        description="Identified content topics"
    )
    sentiment: Optional[str] = Field(None, description="Content sentiment (positive/negative/neutral)")
    
    # Processing metadata
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When content was discovered"
    )
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GeneratedPost(BaseModel):
    """AI-generated post content for a specific platform."""
    
    platform: PlatformType = Field(..., description="Target social media platform")
    content: str = Field(..., description="Generated post content")
    hashtags: List[str] = Field(default_factory=list, description="Relevant hashtags")
    mentions: List[str] = Field(default_factory=list, description="User mentions")
    
    # Content metrics
    character_count: int = Field(..., description="Character count of the post")
    estimated_reading_time: int = Field(..., description="Estimated reading time in seconds")
    
    # Quality scores
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    engagement_prediction: float = Field(..., ge=0.0, le=1.0, description="Predicted engagement (0-1)")
    fact_check_score: float = Field(..., ge=0.0, le=1.0, description="Fact-checking confidence (0-1)")
    
    # Generation metadata
    ai_model: str = Field(..., description="AI model used for generation")
    generation_prompt: str = Field(..., description="Prompt used for generation")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Generation timestamp"
    )
    
    @validator('character_count', always=True)
    def calculate_character_count(cls, v, values):
        """Calculate character count from content."""
        if 'content' in values:
            return len(values['content'])
        return v
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PublishingResult(BaseModel):
    """Result of publishing a post to a social media platform."""
    
    platform: PlatformType = Field(..., description="Platform where post was published")
    post_id: Optional[str] = Field(None, description="Platform-specific post ID")
    post_url: Optional[HttpUrl] = Field(None, description="URL to the published post")
    
    # Publishing status
    success: bool = Field(..., description="Whether publishing was successful")
    error_message: Optional[str] = Field(None, description="Error message if publishing failed")
    
    # Publishing metadata
    published_at: Optional[datetime] = Field(None, description="Actual publishing timestamp")
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled publishing time")
    
    # Performance tracking
    initial_impressions: Optional[int] = Field(None, description="Initial impression count")
    initial_engagements: Optional[int] = Field(None, description="Initial engagement count")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContentItem(BaseModel):
    """Complete content item including source, generated posts, and publishing results."""
    
    # Unique identifier
    id: str = Field(..., description="Unique content item identifier")
    
    # User and status
    user_id: str = Field(..., description="ID of user who owns this content")
    status: ContentStatus = Field(..., description="Current processing status")
    
    # Source content
    source_content: SourceContent = Field(..., description="Original source content")
    
    # Generated posts for different platforms
    generated_posts: Dict[PlatformType, GeneratedPost] = Field(
        default_factory=dict,
        description="Generated posts for each platform"
    )
    
    # Publishing results
    publishing_results: Dict[PlatformType, PublishingResult] = Field(
        default_factory=dict,
        description="Publishing results for each platform"
    )
    
    # Content approval
    approved_by: Optional[str] = Field(None, description="ID of user who approved content")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")
    
    # Scheduling
    scheduled_for: Optional[datetime] = Field(None, description="Scheduled publishing time")
    priority: int = Field(default=0, description="Content priority (higher = more important)")
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Content creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Request/Response Schemas
class ContentDiscoveryRequest(BaseModel):
    """Request schema for manual content discovery."""
    
    url: HttpUrl = Field(..., description="URL to discover content from")
    source: ContentSource = Field(..., description="Content source platform")
    topics: Optional[List[ContentTopic]] = Field(None, description="Suggested topics")


class ContentGenerationRequest(BaseModel):
    """Request schema for generating posts from content."""
    
    content_id: str = Field(..., description="Content item ID")
    platforms: List[PlatformType] = Field(..., description="Target platforms")
    custom_instructions: Optional[str] = Field(None, description="Custom generation instructions")


class ContentApprovalRequest(BaseModel):
    """Request schema for approving/rejecting content."""
    
    approved: bool = Field(..., description="Whether content is approved")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")


class ContentSchedulingRequest(BaseModel):
    """Request schema for scheduling content publication."""
    
    scheduled_for: datetime = Field(..., description="Scheduled publication time")
    platforms: List[PlatformType] = Field(..., description="Platforms to publish to")


class ContentResponse(BaseModel):
    """Response schema for content data."""
    
    id: str
    user_id: str
    status: ContentStatus
    source_content: SourceContent
    generated_posts: Dict[PlatformType, GeneratedPost]
    publishing_results: Dict[PlatformType, PublishingResult]
    scheduled_for: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContentListResponse(BaseModel):
    """Response schema for paginated content list."""
    
    items: List[ContentResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool