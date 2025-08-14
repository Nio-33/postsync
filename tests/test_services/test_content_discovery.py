"""
Tests for Content Discovery Service

This module contains tests for the content discovery functionality
including Reddit integration and content filtering.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.content import ContentItem, ContentStatus, ContentTopic, SourceContent
from src.services.content_discovery import ContentDiscoveryService


class TestContentDiscoveryService:
    """Test content discovery service functionality."""
    
    @pytest.fixture
    def service(self) -> ContentDiscoveryService:
        """Create content discovery service instance."""
        return ContentDiscoveryService()
    
    @pytest.mark.asyncio
    async def test_discover_content_for_user_success(
        self, 
        service: ContentDiscoveryService,
        mock_user,
        mock_source_content,
        mock_firestore_client,
        mock_reddit_client
    ):
        """Test successful content discovery for a user."""
        # Mock database calls
        mock_firestore_client.get_user.return_value = mock_user
        mock_firestore_client.get_content_by_source_id.return_value = None
        mock_firestore_client.create_content_item.return_value = MagicMock()
        
        # Mock Reddit discovery
        mock_reddit_client.discover_content.return_value = [mock_source_content]
        
        result = await service.discover_content_for_user(mock_user.id)
        
        assert len(result) == 1
        mock_firestore_client.get_user.assert_called_once_with(mock_user.id)
        mock_reddit_client.discover_content.assert_called_once()
        mock_firestore_client.create_content_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_discover_content_user_not_found(
        self,
        service: ContentDiscoveryService,
        mock_firestore_client
    ):
        """Test content discovery with non-existent user."""
        mock_firestore_client.get_user.return_value = None
        
        result = await service.discover_content_for_user("nonexistent-user")
        
        assert result == []
        mock_firestore_client.get_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_discover_content_duplicate_filtering(
        self,
        service: ContentDiscoveryService,
        mock_user,
        mock_source_content,
        mock_firestore_client,
        mock_reddit_client
    ):
        """Test that duplicate content is filtered out."""
        # Mock database calls
        mock_firestore_client.get_user.return_value = mock_user
        # Mock that content already exists
        mock_firestore_client.get_content_by_source_id.return_value = MagicMock()
        
        # Mock Reddit discovery
        mock_reddit_client.discover_content.return_value = [mock_source_content]
        
        result = await service.discover_content_for_user(mock_user.id)
        
        assert len(result) == 0  # Should be filtered out
        mock_firestore_client.create_content_item.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_filter_and_score_content(
        self,
        service: ContentDiscoveryService,
        mock_user,
        mock_source_content
    ):
        """Test content filtering and scoring logic."""
        # Create content with matching topics
        mock_source_content.topics = [ContentTopic.ARTIFICIAL_INTELLIGENCE]
        content_list = [mock_source_content]
        
        # User preferences include AI topics
        mock_user.content_preferences.topics = ["artificial-intelligence"]
        
        filtered_content = await service._filter_and_score_content(content_list, mock_user)
        
        assert len(filtered_content) == 1
        assert filtered_content[0].engagement_score > 0
    
    @pytest.mark.asyncio
    async def test_filter_content_no_topic_match(
        self,
        service: ContentDiscoveryService,
        mock_user,
        mock_source_content
    ):
        """Test filtering out content with no topic matches."""
        # Create content with different topics
        mock_source_content.topics = [ContentTopic.AI_POLICY]
        content_list = [mock_source_content]
        
        # User preferences don't include policy topics
        mock_user.content_preferences.topics = ["artificial-intelligence", "machine-learning"]
        
        filtered_content = await service._filter_and_score_content(content_list, mock_user)
        
        assert len(filtered_content) == 0
    
    def test_calculate_relevance_score(
        self,
        service: ContentDiscoveryService,
        mock_user,
        mock_source_content
    ):
        """Test relevance score calculation."""
        # Set up content with high engagement
        mock_source_content.upvotes = 100
        mock_source_content.comments_count = 50
        mock_source_content.sentiment = "positive"
        mock_source_content.published_at = datetime.utcnow() - timedelta(hours=2)
        mock_source_content.topics = [ContentTopic.ARTIFICIAL_INTELLIGENCE]
        
        # User interested in AI
        mock_user.content_preferences.topics = ["artificial-intelligence"]
        
        score = service._calculate_relevance_score(mock_source_content, mock_user)
        
        assert score > 0.5  # Should get a good score
        assert score <= 1.0  # Should be capped at 1.0
    
    @pytest.mark.asyncio
    async def test_get_user_content_with_pagination(
        self,
        service: ContentDiscoveryService,
        mock_firestore_client
    ):
        """Test getting user content with pagination."""
        # Mock database response
        mock_content_items = [MagicMock() for _ in range(5)]
        mock_firestore_client.get_user_content.return_value = mock_content_items
        
        result = await service.get_user_content(
            user_id="test-user",
            page=1,
            page_size=5
        )
        
        assert result.page == 1
        assert result.page_size == 5
        assert len(result.items) == 5
        mock_firestore_client.get_user_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_content_item_success(
        self,
        service: ContentDiscoveryService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test getting a specific content item."""
        mock_firestore_client.get_content_item.return_value = mock_content_item
        
        result = await service.get_content_item(mock_content_item.id, mock_content_item.user_id)
        
        assert result == mock_content_item
        mock_firestore_client.get_content_item.assert_called_once_with(mock_content_item.id)
    
    @pytest.mark.asyncio
    async def test_get_content_item_wrong_user(
        self,
        service: ContentDiscoveryService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test getting content item with wrong user ID."""
        mock_firestore_client.get_content_item.return_value = mock_content_item
        
        result = await service.get_content_item(mock_content_item.id, "wrong-user")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_approve_content_success(
        self,
        service: ContentDiscoveryService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test successful content approval."""
        mock_content_item.status = ContentStatus.GENERATED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        result = await service.approve_content(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            approved=True
        )
        
        assert result == mock_content_item
        mock_firestore_client.update_content_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_approve_content_wrong_status(
        self,
        service: ContentDiscoveryService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test content approval with wrong status."""
        mock_content_item.status = ContentStatus.DISCOVERED  # Wrong status
        mock_firestore_client.get_content_item.return_value = mock_content_item
        
        with pytest.raises(ValueError, match="cannot be approved"):
            await service.approve_content(
                content_id=mock_content_item.id,
                user_id=mock_content_item.user_id,
                approved=True
            )
    
    @pytest.mark.asyncio
    async def test_reject_content_with_reason(
        self,
        service: ContentDiscoveryService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test content rejection with reason."""
        mock_content_item.status = ContentStatus.GENERATED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        result = await service.approve_content(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            approved=False,
            rejection_reason="Not relevant to user interests"
        )
        
        assert result == mock_content_item
        # Check that rejection reason was passed in update call
        call_args = mock_firestore_client.update_content_item.call_args
        assert call_args[0][1]["rejection_reason"] == "Not relevant to user interests"
        assert call_args[0][1]["status"] == ContentStatus.REJECTED
    
    @pytest.mark.asyncio
    async def test_delete_content_item_success(
        self,
        service: ContentDiscoveryService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test successful content deletion."""
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.delete_content_item.return_value = True
        
        result = await service.delete_content_item(mock_content_item.id, mock_content_item.user_id)
        
        assert result is True
        mock_firestore_client.delete_content_item.assert_called_once_with(mock_content_item.id)
    
    @pytest.mark.asyncio
    async def test_delete_content_item_not_found(
        self,
        service: ContentDiscoveryService,
        mock_firestore_client
    ):
        """Test deleting non-existent content item."""
        mock_firestore_client.get_content_item.return_value = None
        
        result = await service.delete_content_item("nonexistent", "user-123")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_bulk_discover_content(
        self,
        service: ContentDiscoveryService
    ):
        """Test bulk content discovery for multiple users."""
        user_ids = ["user1", "user2", "user3"]
        
        # Mock the discover_content_for_user method
        with patch.object(service, 'discover_content_for_user') as mock_discover:
            mock_discover.side_effect = [
                [MagicMock(), MagicMock()],  # 2 items for user1
                [MagicMock()],               # 1 item for user2
                []                           # 0 items for user3
            ]
            
            results = await service.bulk_discover_content(user_ids)
            
            assert results["user1"] == 2
            assert results["user2"] == 1
            assert results["user3"] == 0
            assert mock_discover.call_count == 3
    
    @pytest.mark.asyncio
    async def test_cleanup_old_content(
        self,
        service: ContentDiscoveryService,
        mock_firestore_client
    ):
        """Test cleanup of old content."""
        mock_firestore_client.cleanup_old_data.return_value = 15
        
        result = await service.cleanup_old_content(days_old=30)
        
        assert result == 15
        mock_firestore_client.cleanup_old_data.assert_called_once_with(days=30)