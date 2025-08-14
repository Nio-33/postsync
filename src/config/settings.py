"""
Application Settings and Configuration

This module contains all configuration settings for PostSync, including:
- Environment variables management
- API credentials and secrets
- Feature flags and application settings
- Database and cloud service configuration
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Settings
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    
    # Google Cloud Configuration
    google_cloud_project: str = Field(..., description="Google Cloud Project ID")
    google_application_credentials: str = Field(
        default="",
        description="Path to Google Cloud service account credentials"
    )
    firestore_database_id: str = Field(
        default="(default)",
        description="Firestore database ID"
    )
    
    # AI Configuration
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    gemini_model: str = Field(
        default="gemini-1.5-pro-latest",
        description="Gemini model to use for content generation"
    )
    
    # Reddit API Configuration
    reddit_client_id: str = Field(..., description="Reddit API client ID")
    reddit_client_secret: str = Field(..., description="Reddit API client secret")
    reddit_user_agent: str = Field(
        default="PostSync:v1.0.0 (by /u/postsync)",
        description="Reddit API user agent"
    )
    
    # LinkedIn API Configuration
    linkedin_client_id: str = Field(..., description="LinkedIn API client ID")
    linkedin_client_secret: str = Field(..., description="LinkedIn API client secret")
    linkedin_redirect_uri: str = Field(
        default="https://api.postsync.com/auth/linkedin/callback",
        description="LinkedIn OAuth redirect URI"
    )
    
    # Twitter API Configuration
    twitter_api_key: str = Field(..., description="Twitter API key")
    twitter_api_secret: str = Field(..., description="Twitter API secret")
    twitter_bearer_token: str = Field(..., description="Twitter Bearer token")
    twitter_access_token: str = Field(default="", description="Twitter access token")
    twitter_access_token_secret: str = Field(
        default="",
        description="Twitter access token secret"
    )
    
    # Database Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Security Configuration
    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30,
        description="JWT access token expiration in minutes"
    )
    
    # Content Configuration
    max_daily_posts: int = Field(
        default=5,
        description="Maximum posts per user per day"
    )
    content_discovery_interval_minutes: int = Field(
        default=30,
        description="Content discovery interval in minutes"
    )
    post_scheduling_timezone: str = Field(
        default="UTC",
        description="Timezone for post scheduling"
    )
    
    # Monitoring and Logging
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")
    google_cloud_logging_enabled: bool = Field(
        default=True,
        description="Enable Google Cloud Logging"
    )
    
    # Rate Limiting
    reddit_rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Reddit API rate limit"
    )
    linkedin_rate_limit_requests_per_minute: int = Field(
        default=100,
        description="LinkedIn API rate limit"
    )
    twitter_rate_limit_requests_per_minute: int = Field(
        default=300,
        description="Twitter API rate limit"
    )
    
    # Feature Flags
    enable_auto_posting: bool = Field(
        default=True,
        description="Enable automatic posting"
    )
    enable_content_approval: bool = Field(
        default=False,
        description="Require manual content approval"
    )
    enable_analytics: bool = Field(
        default=True,
        description="Enable analytics tracking"
    )
    enable_a_b_testing: bool = Field(
        default=False,
        description="Enable A/B testing features"
    )
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()