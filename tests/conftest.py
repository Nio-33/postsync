"""
Test Configuration and Fixtures

This module contains pytest fixtures and configuration for the test suite.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["REDDIT_CLIENT_ID"] = "test-reddit-id"
os.environ["REDDIT_CLIENT_SECRET"] = "test-reddit-secret"
os.environ["LINKEDIN_CLIENT_ID"] = "test-linkedin-id"
os.environ["LINKEDIN_CLIENT_SECRET"] = "test-linkedin-secret"
os.environ["TWITTER_API_KEY"] = "test-twitter-key"
os.environ["TWITTER_API_SECRET"] = "test-twitter-secret"
os.environ["TWITTER_BEARER_TOKEN"] = "test-twitter-bearer"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"

from src.main import app
from src.models.content import ContentItem, ContentStatus, ContentTopic, PlatformType, SourceContent
from src.models.user import ContentPreferences, User, UserRole


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_user() -> User:
    """Create a mock user for testing."""
    return User(
        id="test-user-123",
        email="test@example.com",
        full_name="Test User",
        job_title="AI Engineer",
        company="Test Company",
        role=UserRole.USER,
        content_preferences=ContentPreferences(
            topics=["artificial-intelligence", "machine-learning"],
            posts_per_day=2,
            tone="professional",
            platforms=[PlatformType.LINKEDIN, PlatformType.TWITTER]
        )
    )


@pytest.fixture
def mock_admin_user() -> User:
    """Create a mock admin user for testing."""
    return User(
        id="test-admin-123",
        email="admin@example.com",
        full_name="Admin User",
        role=UserRole.ADMIN,
        content_preferences=ContentPreferences()
    )


@pytest.fixture
def mock_source_content() -> SourceContent:
    """Create mock source content for testing."""
    from datetime import datetime
    from src.models.content import ContentSource
    
    return SourceContent(
        source_id="test-reddit-123",
        source=ContentSource.REDDIT,
        url="https://reddit.com/r/AIBusiness/test-post",
        title="Revolutionary AI Breakthrough Changes Everything",
        description="This groundbreaking AI technology is set to transform the industry...",
        author="ai_researcher",
        published_at=datetime.utcnow(),
        upvotes=150,
        comments_count=45,
        engagement_score=0.8,
        topics=[ContentTopic.ARTIFICIAL_INTELLIGENCE, ContentTopic.AI_RESEARCH],
        sentiment="positive"
    )


@pytest.fixture
def mock_content_item(mock_user: User, mock_source_content: SourceContent) -> ContentItem:
    """Create a mock content item for testing."""
    return ContentItem(
        id="test-content-123",
        user_id=mock_user.id,
        status=ContentStatus.DISCOVERED,
        source_content=mock_source_content
    )


@pytest.fixture
def mock_firestore_client() -> MagicMock:
    """Create a mock Firestore client."""
    mock_client = MagicMock()
    
    # Mock common database operations
    mock_client.get_user = AsyncMock(return_value=None)
    mock_client.get_user_by_email = AsyncMock(return_value=None)
    mock_client.create_user = AsyncMock()
    mock_client.update_user = AsyncMock()
    mock_client.get_content_item = AsyncMock(return_value=None)
    mock_client.create_content_item = AsyncMock()
    mock_client.update_content_item = AsyncMock()
    mock_client.get_user_content = AsyncMock(return_value=[])
    
    return mock_client


@pytest.fixture
def mock_reddit_client() -> MagicMock:
    """Create a mock Reddit client."""
    mock_client = MagicMock()
    mock_client.discover_content = AsyncMock(return_value=[])
    mock_client.check_connection = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
def mock_gemini_client() -> MagicMock:
    """Create a mock Gemini AI client."""
    mock_client = MagicMock()
    
    # Mock content generation
    mock_generated_post = MagicMock()
    mock_generated_post.platform = PlatformType.LINKEDIN
    mock_generated_post.content = "Test generated content"
    mock_generated_post.hashtags = ["AI", "Technology"]
    mock_generated_post.relevance_score = 0.9
    mock_generated_post.engagement_prediction = 0.8
    mock_generated_post.fact_check_score = 0.95
    
    mock_client.generate_posts = AsyncMock(return_value={
        PlatformType.LINKEDIN: mock_generated_post
    })
    mock_client.check_connection = AsyncMock(return_value=True)
    
    return mock_client


@pytest.fixture
def mock_linkedin_client() -> MagicMock:
    """Create a mock LinkedIn client."""
    mock_client = MagicMock()
    
    # Mock authentication
    mock_client.authenticate_user = AsyncMock(return_value={
        "access_token": "test-linkedin-token",
        "user_info": {"id": "linkedin-user-123", "name": "Test User"}
    })
    
    # Mock publishing
    from src.models.content import PublishingResult
    mock_client.publish_post = AsyncMock(return_value=PublishingResult(
        platform=PlatformType.LINKEDIN,
        post_id="linkedin-post-123",
        post_url="https://linkedin.com/posts/test",
        success=True,
        published_at=datetime.utcnow()
    ))
    
    mock_client.check_connection = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
def mock_twitter_client() -> MagicMock:
    """Create a mock Twitter client."""
    mock_client = MagicMock()
    
    # Mock authentication
    mock_client.authenticate_user = AsyncMock(return_value={
        "access_token": "test-twitter-token",
        "user_info": {"id": "twitter-user-123", "username": "testuser"}
    })
    
    # Mock publishing
    from src.models.content import PublishingResult
    mock_client.publish_post = AsyncMock(return_value=PublishingResult(
        platform=PlatformType.TWITTER,
        post_id="twitter-post-123",
        post_url="https://twitter.com/user/status/123",
        success=True,
        published_at=datetime.utcnow()
    ))
    
    mock_client.check_connection = AsyncMock(return_value=True)
    return mock_client


@pytest.fixture
def auth_headers(mock_user: User) -> dict:
    """Create authentication headers for API requests."""
    from src.utils.auth import create_access_token
    
    token = create_access_token(data={"sub": mock_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(mock_admin_user: User) -> dict:
    """Create admin authentication headers for API requests."""
    from src.utils.auth import create_access_token
    
    token = create_access_token(data={"sub": mock_admin_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_dependencies(
    monkeypatch,
    mock_firestore_client,
    mock_reddit_client, 
    mock_gemini_client,
    mock_linkedin_client,
    mock_twitter_client
):
    """Mock external dependencies for all tests."""
    # Mock database client
    monkeypatch.setattr("src.integrations.firestore.firestore_client", mock_firestore_client)
    
    # Mock API clients
    monkeypatch.setattr("src.integrations.reddit.reddit_client", mock_reddit_client)
    monkeypatch.setattr("src.ai.gemini.gemini_client", mock_gemini_client)
    monkeypatch.setattr("src.integrations.linkedin.linkedin_client", mock_linkedin_client)
    monkeypatch.setattr("src.integrations.twitter.twitter_client", mock_twitter_client)


@pytest.fixture
def sample_reddit_data() -> list:
    """Sample Reddit data for testing content discovery."""
    return [
        {
            "id": "test1",
            "title": "OpenAI Announces GPT-5",
            "selftext": "OpenAI has announced the next version of their language model...",
            "url": "https://openai.com/gpt5",
            "score": 150,
            "num_comments": 45,
            "created_utc": 1640995200,  # 2022-01-01 00:00:00 UTC
            "author": "ai_news",
            "subreddit": "AIBusiness"
        },
        {
            "id": "test2",
            "title": "AI Startup Raises $100M Series B",
            "selftext": "A promising AI startup focused on autonomous vehicles...",
            "url": "https://techcrunch.com/ai-startup-funding",
            "score": 85,
            "num_comments": 23,
            "created_utc": 1640995200,
            "author": "startup_news",
            "subreddit": "AIBusiness"
        }
    ]


@pytest.fixture
def sample_generated_content() -> dict:
    """Sample generated content for testing."""
    return {
        "linkedin": {
            "content": "🚀 Exciting developments in AI! OpenAI's latest announcement shows the rapid pace of innovation in artificial intelligence. This breakthrough could revolutionize how we approach complex problem-solving across industries.\n\nWhat implications do you see for your field? How are you preparing for the next wave of AI advancement?\n\n#AI #Innovation #Technology #FutureOfWork",
            "hashtags": ["AI", "Innovation", "Technology", "FutureOfWork"],
            "mentions": []
        },
        "twitter": {
            "content": "🚀 OpenAI's latest AI breakthrough is game-changing! The pace of innovation continues to accelerate. What impact do you think this will have on your industry? #AI #Innovation",
            "hashtags": ["AI", "Innovation"],
            "mentions": []
        }
    }


@pytest.fixture
def sample_analytics_data() -> dict:
    """Sample analytics data for testing."""
    return {
        "post_id": "test-post-123",
        "platform": "linkedin",
        "impressions": 1500,
        "likes": 45,
        "comments": 8,
        "shares": 12,
        "clicks": 67,
        "engagement_rate": 8.8,
        "created_at": "2024-01-01T12:00:00Z"
    }


# Async test utilities
class AsyncContextManager:
    """Helper for testing async context managers."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Test data factories
class TestDataFactory:
    """Factory for creating test data objects."""
    
    @staticmethod
    def create_user(**kwargs) -> User:
        """Create a test user with optional overrides."""
        defaults = {
            "id": "test-user-123",
            "email": "test@example.com",
            "full_name": "Test User",
            "role": UserRole.USER,
            "content_preferences": ContentPreferences()
        }
        defaults.update(kwargs)
        return User(**defaults)
    
    @staticmethod
    def create_content_item(**kwargs) -> ContentItem:
        """Create a test content item with optional overrides."""
        defaults = {
            "id": "test-content-123",
            "user_id": "test-user-123",
            "status": ContentStatus.DISCOVERED,
            "source_content": TestDataFactory.create_source_content()
        }
        defaults.update(kwargs)
        return ContentItem(**defaults)
    
    @staticmethod
    def create_source_content(**kwargs) -> SourceContent:
        """Create test source content with optional overrides."""
        from datetime import datetime
        from src.models.content import ContentSource
        
        defaults = {
            "source_id": "test-source-123",
            "source": ContentSource.REDDIT,
            "url": "https://reddit.com/r/test",
            "title": "Test Content Title",
            "description": "Test content description",
            "author": "test_author",
            "published_at": datetime.utcnow(),
            "upvotes": 100,
            "comments_count": 25,
            "engagement_score": 0.8,
            "topics": [ContentTopic.ARTIFICIAL_INTELLIGENCE],
            "sentiment": "positive"
        }
        defaults.update(kwargs)
        return SourceContent(**defaults)


# Export test factory for easy importing
test_factory = TestDataFactory()