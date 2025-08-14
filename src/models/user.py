"""
User Data Models and Schemas

This module contains user-related data models, schemas, and validation logic.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserRole(str, Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class SubscriptionTier(str, Enum):
    """Subscription tier enumeration."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class SocialPlatform(str, Enum):
    """Social media platform enumeration."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


class ContentPreferences(BaseModel):
    """User content preferences and settings."""
    
    # Content topics of interest
    topics: List[str] = Field(
        default=["artificial-intelligence", "machine-learning", "startups"],
        description="List of content topics user is interested in"
    )
    
    # Posting frequency settings
    posts_per_day: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Number of posts per day"
    )
    
    # Content tone and style
    tone: str = Field(
        default="professional",
        description="Content tone (professional, casual, expert, etc.)"
    )
    
    # Platform-specific settings
    platforms: List[SocialPlatform] = Field(
        default=[SocialPlatform.LINKEDIN, SocialPlatform.TWITTER],
        description="Enabled social media platforms"
    )
    
    # Scheduling preferences
    posting_timezone: str = Field(
        default="UTC",
        description="User's preferred timezone for posting"
    )
    
    # Content approval settings
    require_approval: bool = Field(
        default=False,
        description="Whether posts require manual approval"
    )


class SocialMediaAccount(BaseModel):
    """Social media account credentials and settings."""
    
    platform: SocialPlatform
    username: str = Field(..., description="Platform username or handle")
    account_id: str = Field(..., description="Platform-specific account ID")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    is_active: bool = Field(default=True, description="Whether account is active")
    last_post_at: Optional[datetime] = Field(None, description="Last post timestamp")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserStats(BaseModel):
    """User statistics and metrics."""
    
    total_posts: int = Field(default=0, description="Total posts generated")
    total_impressions: int = Field(default=0, description="Total content impressions")
    total_engagements: int = Field(default=0, description="Total content engagements")
    avg_engagement_rate: float = Field(default=0.0, description="Average engagement rate")
    best_performing_topic: Optional[str] = Field(None, description="Best performing content topic")
    last_active_at: Optional[datetime] = Field(None, description="Last activity timestamp")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class User(BaseModel):
    """User model with comprehensive profile information."""
    
    # Basic user information
    id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., description="User's full name")
    avatar_url: Optional[str] = Field(None, description="URL to user's avatar image")
    password_hash: str = Field(..., description="Hashed password")
    
    # Professional information
    job_title: Optional[str] = Field(None, description="User's job title")
    company: Optional[str] = Field(None, description="User's company")
    industry: Optional[str] = Field(None, description="User's industry")
    bio: Optional[str] = Field(None, description="User's professional bio")
    
    # Account settings
    role: UserRole = Field(default=UserRole.USER, description="User role")
    subscription_tier: SubscriptionTier = Field(
        default=SubscriptionTier.FREE,
        description="User's subscription tier"
    )
    is_active: bool = Field(default=True, description="Whether user account is active")
    is_verified: bool = Field(default=False, description="Whether user is verified")
    
    # Preferences and settings
    content_preferences: ContentPreferences = Field(
        default_factory=ContentPreferences,
        description="User's content preferences"
    )
    
    # Connected social media accounts
    social_accounts: Dict[SocialPlatform, SocialMediaAccount] = Field(
        default_factory=dict,
        description="Connected social media accounts"
    )
    
    # User statistics
    stats: UserStats = Field(
        default_factory=UserStats,
        description="User statistics and metrics"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Account creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    last_login_at: Optional[datetime] = Field(
        None,
        description="Last login timestamp"
    )
    
    @validator('email')
    def validate_email(cls, v):
        """Validate email format."""
        return v.lower()
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate full name is not empty."""
        if not v or not v.strip():
            raise ValueError('Full name cannot be empty')
        return v.strip()
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Request/Response Schemas
class UserCreateRequest(BaseModel):
    """Request schema for creating a new user."""
    
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=8, description="User password")
    job_title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None


class UserUpdateRequest(BaseModel):
    """Request schema for updating user information."""
    
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    content_preferences: Optional[ContentPreferences] = None


class UserResponse(BaseModel):
    """Response schema for user data (excludes sensitive information)."""
    
    id: str
    email: EmailStr
    full_name: str
    avatar_url: Optional[str]
    job_title: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    bio: Optional[str]
    role: UserRole
    subscription_tier: SubscriptionTier
    is_active: bool
    is_verified: bool
    content_preferences: ContentPreferences
    stats: UserStats
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }