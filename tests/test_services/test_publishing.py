"""
Tests for Publishing Service

This module contains tests for content publishing functionality
across different social media platforms.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.content import ContentItem, ContentStatus, GeneratedPost, PlatformType, PublishingResult
from src.services.publishing import PublishingService


class TestPublishingService:
    """Test publishing service functionality."""
    
    @pytest.fixture
    def service(self) -> PublishingService:
        """Create publishing service instance."""
        return PublishingService()
    
    @pytest.mark.asyncio
    async def test_publish_content_success(
        self,
        service: PublishingService,
        mock_content_item,
        mock_linkedin_client,
        mock_firestore_client
    ):
        """Test successful content publishing to LinkedIn."""
        # Set up content item
        mock_content_item.status = ContentStatus.APPROVED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Test LinkedIn post content",
                hashtags=["AI", "Technology"]
            )
        }
        
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        # Mock successful publishing
        mock_result = PublishingResult(
            platform=PlatformType.LINKEDIN,
            post_id="linkedin-123",
            post_url="https://linkedin.com/posts/test",
            success=True,
            published_at=datetime.utcnow()
        )
        mock_linkedin_client.publish_post.return_value = mock_result
        
        result = await service.publish_content(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN
        )
        
        assert result.success is True
        assert result.post_id == "linkedin-123"
        mock_linkedin_client.publish_post.assert_called_once()
        mock_firestore_client.update_content_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_content_wrong_status(
        self,
        service: PublishingService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test publishing with wrong content status."""
        mock_content_item.status = ContentStatus.DISCOVERED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        
        with pytest.raises(ValueError, match="cannot be published"):
            await service.publish_content(
                content_id=mock_content_item.id,
                user_id=mock_content_item.user_id,
                platform=PlatformType.LINKEDIN
            )
    
    @pytest.mark.asyncio
    async def test_publish_content_no_generated_post(
        self,
        service: PublishingService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test publishing when no generated post exists for platform."""
        mock_content_item.status = ContentStatus.APPROVED
        mock_content_item.generated_posts = {}  # No posts generated
        mock_firestore_client.get_content_item.return_value = mock_content_item
        
        with pytest.raises(ValueError, match="No generated post found"):
            await service.publish_content(
                content_id=mock_content_item.id,
                user_id=mock_content_item.user_id,
                platform=PlatformType.LINKEDIN
            )
    
    @pytest.mark.asyncio
    async def test_publish_content_platform_error(
        self,
        service: PublishingService,
        mock_content_item,
        mock_linkedin_client,
        mock_firestore_client
    ):
        """Test handling platform publishing errors."""
        mock_content_item.status = ContentStatus.APPROVED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Test content",
                hashtags=["Test"]
            )
        }
        
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        # Mock publishing failure
        mock_result = PublishingResult(
            platform=PlatformType.LINKEDIN,
            success=False,
            error_message="API rate limit exceeded",
            published_at=datetime.utcnow()
        )
        mock_linkedin_client.publish_post.return_value = mock_result
        
        result = await service.publish_content(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN
        )
        
        assert result.success is False
        assert "rate limit" in result.error_message
        # Should still update content item with failure info
        mock_firestore_client.update_content_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_publication(
        self,
        service: PublishingService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test scheduling content for future publication."""
        mock_content_item.status = ContentStatus.APPROVED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.create_scheduled_task.return_value = MagicMock(id="task-123")
        
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        
        result = await service.schedule_publication(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN,
            scheduled_time=scheduled_time
        )
        
        assert result["task_id"] == "task-123"
        assert result["scheduled_time"] == scheduled_time
        mock_firestore_client.create_scheduled_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_scheduled_publication(
        self,
        service: PublishingService,
        mock_firestore_client
    ):
        """Test canceling a scheduled publication."""
        task_id = "task-123"
        mock_firestore_client.get_scheduled_task.return_value = MagicMock(
            id=task_id,
            status="scheduled"
        )
        mock_firestore_client.update_scheduled_task.return_value = True
        
        result = await service.cancel_scheduled_publication(
            task_id=task_id,
            user_id="user-123"
        )
        
        assert result is True
        mock_firestore_client.update_scheduled_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_to_multiple_platforms(
        self,
        service: PublishingService,
        mock_content_item,
        mock_linkedin_client,
        mock_twitter_client,
        mock_firestore_client
    ):
        """Test publishing to multiple platforms simultaneously."""
        # Set up content for multiple platforms
        mock_content_item.status = ContentStatus.APPROVED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="LinkedIn post content",
                hashtags=["AI", "Technology"]
            ),
            PlatformType.TWITTER: GeneratedPost(
                platform=PlatformType.TWITTER,
                content="Twitter post content",
                hashtags=["AI", "Tech"]
            )
        }
        
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        # Mock successful publishing for both platforms
        mock_linkedin_result = PublishingResult(
            platform=PlatformType.LINKEDIN,
            post_id="linkedin-123",
            success=True,
            published_at=datetime.utcnow()
        )
        mock_twitter_result = PublishingResult(
            platform=PlatformType.TWITTER,
            post_id="twitter-456",
            success=True,
            published_at=datetime.utcnow()
        )
        
        mock_linkedin_client.publish_post.return_value = mock_linkedin_result
        mock_twitter_client.publish_post.return_value = mock_twitter_result
        
        results = await service.publish_to_multiple_platforms(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platforms=[PlatformType.LINKEDIN, PlatformType.TWITTER]
        )
        
        assert len(results) == 2
        assert all(result.success for result in results)
        assert mock_linkedin_client.publish_post.call_count == 1
        assert mock_twitter_client.publish_post.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_failed_publication(
        self,
        service: PublishingService,
        mock_content_item,
        mock_linkedin_client,
        mock_firestore_client
    ):
        """Test retrying a failed publication."""
        mock_content_item.status = ContentStatus.PUBLISH_FAILED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Retry this content",
                hashtags=["Retry"]
            )
        }
        
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        # Mock successful retry
        mock_result = PublishingResult(
            platform=PlatformType.LINKEDIN,
            post_id="linkedin-retry-123",
            success=True,
            published_at=datetime.utcnow()
        )
        mock_linkedin_client.publish_post.return_value = mock_result
        
        result = await service.retry_failed_publication(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN
        )
        
        assert result.success is True
        assert result.post_id == "linkedin-retry-123"
    
    @pytest.mark.asyncio
    async def test_get_publication_status(
        self,
        service: PublishingService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test getting publication status for content."""
        mock_content_item.publishing_results = {
            PlatformType.LINKEDIN: PublishingResult(
                platform=PlatformType.LINKEDIN,
                post_id="linkedin-123",
                success=True,
                published_at=datetime.utcnow()
            )
        }
        
        mock_firestore_client.get_content_item.return_value = mock_content_item
        
        status = await service.get_publication_status(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id
        )
        
        assert PlatformType.LINKEDIN in status
        assert status[PlatformType.LINKEDIN]["success"] is True
        assert status[PlatformType.LINKEDIN]["post_id"] == "linkedin-123"
    
    @pytest.mark.asyncio
    async def test_bulk_publish_content(
        self,
        service: PublishingService
    ):
        """Test bulk publishing multiple content items."""
        content_ids = ["content-1", "content-2", "content-3"]
        user_id = "user-123"
        platform = PlatformType.LINKEDIN
        
        # Mock the publish_content method
        with patch.object(service, 'publish_content') as mock_publish:
            mock_results = [
                PublishingResult(platform=platform, success=True, post_id="post-1"),
                PublishingResult(platform=platform, success=True, post_id="post-2"),
                PublishingResult(platform=platform, success=False, error_message="Error")
            ]
            mock_publish.side_effect = mock_results
            
            results = await service.bulk_publish_content(
                content_ids=content_ids,
                user_id=user_id,
                platform=platform
            )
            
            assert results["successful"] == 2
            assert results["failed"] == 1
            assert len(results["results"]) == 3
            assert mock_publish.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_user_publishing_statistics(
        self,
        service: PublishingService,
        mock_firestore_client
    ):
        """Test getting publishing statistics for a user."""
        user_id = "user-123"
        
        # Mock statistics data
        mock_stats = {
            "total_published": 25,
            "successful_publications": 23,
            "failed_publications": 2,
            "success_rate": 92.0,
            "platforms": {
                "linkedin": {"published": 15, "failed": 1},
                "twitter": {"published": 8, "failed": 1}
            },
            "last_30_days": 8
        }
        
        mock_firestore_client.get_publishing_statistics.return_value = mock_stats
        
        stats = await service.get_user_publishing_statistics(
            user_id=user_id,
            days=30
        )
        
        assert stats["total_published"] == 25
        assert stats["success_rate"] == 92.0
        assert "linkedin" in stats["platforms"]
    
    @pytest.mark.asyncio
    async def test_delete_published_content(
        self,
        service: PublishingService,
        mock_content_item,
        mock_linkedin_client,
        mock_firestore_client
    ):
        """Test deleting published content from platform."""
        mock_content_item.status = ContentStatus.PUBLISHED
        mock_content_item.publishing_results = {
            PlatformType.LINKEDIN: PublishingResult(
                platform=PlatformType.LINKEDIN,
                post_id="linkedin-123",
                success=True,
                published_at=datetime.utcnow()
            )
        }
        
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        mock_linkedin_client.delete_post.return_value = True
        
        result = await service.delete_published_content(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN
        )
        
        assert result is True
        mock_linkedin_client.delete_post.assert_called_once_with("linkedin-123")
        mock_firestore_client.update_content_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_optimal_posting_times(
        self,
        service: PublishingService,
        mock_firestore_client
    ):
        """Test getting optimal posting times based on user's audience."""
        user_id = "user-123"
        platform = PlatformType.LINKEDIN
        
        # Mock optimal times data
        mock_times = {
            "weekdays": ["09:00", "13:00", "17:00"],
            "weekends": ["10:00", "15:00"],
            "timezone": "UTC",
            "confidence": 0.85,
            "based_on_posts": 50
        }
        
        mock_firestore_client.get_optimal_posting_times.return_value = mock_times
        
        times = await service.get_optimal_posting_times(
            user_id=user_id,
            platform=platform
        )
        
        assert len(times["weekdays"]) == 3
        assert times["confidence"] == 0.85
        mock_firestore_client.get_optimal_posting_times.assert_called_once()
    
    def test_validate_publishing_prerequisites(
        self,
        service: PublishingService,
        mock_content_item,
        mock_user
    ):
        """Test validation of publishing prerequisites."""
        # Test valid content
        mock_content_item.status = ContentStatus.APPROVED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Valid content",
                hashtags=["Valid"]
            )
        }
        
        # User has connected LinkedIn
        mock_user.social_accounts = {
            "linkedin": {
                "account_id": "linkedin-123",
                "access_token": "token-123",
                "is_active": True
            }
        }
        
        is_valid, errors = service._validate_publishing_prerequisites(
            mock_content_item,
            mock_user,
            PlatformType.LINKEDIN
        )
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_publishing_prerequisites_missing_account(
        self,
        service: PublishingService,
        mock_content_item,
        mock_user
    ):
        """Test validation when social account is not connected."""
        mock_content_item.status = ContentStatus.APPROVED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Valid content",
                hashtags=["Valid"]
            )
        }
        
        # User has no connected accounts
        mock_user.social_accounts = {}
        
        is_valid, errors = service._validate_publishing_prerequisites(
            mock_content_item,
            mock_user,
            PlatformType.LINKEDIN
        )
        
        assert is_valid is False
        assert "not connected" in errors[0].lower()