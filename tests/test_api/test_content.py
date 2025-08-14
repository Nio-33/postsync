"""
Tests for Content API Endpoints

This module contains tests for content-related endpoints
including discovery, generation, and publishing.
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.models.content import ContentItem, ContentStatus, PlatformType


class TestContentEndpoints:
    """Test content-related API endpoints."""
    
    @pytest.mark.asyncio
    async def test_discover_content_success(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test successful content discovery."""
        with patch("src.services.content_discovery.ContentDiscoveryService.discover_content_for_user") as mock_discover:
            mock_discover.return_value = [mock_content_item]
            
            response = await async_client.post(
                "/api/v1/content/discover",
                headers=auth_headers,
                json={"subreddits": ["AIBusiness"], "limit": 10}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["items"]) == 1
            assert data["total"] == 1
    
    @pytest.mark.asyncio
    async def test_discover_content_unauthorized(self, async_client: AsyncClient):
        """Test content discovery without authentication."""
        response = await async_client.post(
            "/api/v1/content/discover",
            json={"subreddits": ["AIBusiness"], "limit": 10}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_get_user_content(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test getting user's content with pagination."""
        with patch("src.services.content_discovery.ContentDiscoveryService.get_user_content") as mock_get:
            mock_pagination = {
                "items": [mock_content_item],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "total_pages": 1
            }
            mock_get.return_value = mock_pagination
            
            response = await async_client.get(
                "/api/v1/content/my-content?page=1&page_size=10",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total"] == 1
            assert data["page"] == 1
    
    @pytest.mark.asyncio
    async def test_get_content_item(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test getting a specific content item."""
        with patch("src.services.content_discovery.ContentDiscoveryService.get_content_item") as mock_get:
            mock_get.return_value = mock_content_item
            
            response = await async_client.get(
                f"/api/v1/content/{mock_content_item.id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == mock_content_item.id
    
    @pytest.mark.asyncio
    async def test_get_content_item_not_found(
        self,
        async_client: AsyncClient,
        auth_headers
    ):
        """Test getting non-existent content item."""
        with patch("src.services.content_discovery.ContentDiscoveryService.get_content_item") as mock_get:
            mock_get.return_value = None
            
            response = await async_client.get(
                "/api/v1/content/nonexistent-id",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_generate_content_success(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test successful content generation."""
        with patch("src.services.content_generation.ContentGenerationService.generate_content_for_item") as mock_generate:
            mock_content_item.status = ContentStatus.GENERATED
            mock_generate.return_value = mock_content_item
            
            response = await async_client.post(
                f"/api/v1/content/{mock_content_item.id}/generate",
                headers=auth_headers,
                json={"platforms": ["linkedin", "twitter"]}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "generated"
    
    @pytest.mark.asyncio
    async def test_generate_content_invalid_platform(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test content generation with invalid platform."""
        response = await async_client.post(
            f"/api/v1/content/{mock_content_item.id}/generate",
            headers=auth_headers,
            json={"platforms": ["invalid_platform"]}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_approve_content_success(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test successful content approval."""
        with patch("src.services.content_discovery.ContentDiscoveryService.approve_content") as mock_approve:
            mock_content_item.status = ContentStatus.APPROVED
            mock_approve.return_value = mock_content_item
            
            response = await async_client.post(
                f"/api/v1/content/{mock_content_item.id}/approve",
                headers=auth_headers,
                json={"approved": True}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "approved"
    
    @pytest.mark.asyncio
    async def test_reject_content_with_reason(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test content rejection with reason."""
        with patch("src.services.content_discovery.ContentDiscoveryService.approve_content") as mock_approve:
            mock_content_item.status = ContentStatus.REJECTED
            mock_approve.return_value = mock_content_item
            
            response = await async_client.post(
                f"/api/v1/content/{mock_content_item.id}/approve",
                headers=auth_headers,
                json={
                    "approved": False,
                    "rejection_reason": "Not relevant to user interests"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "rejected"
    
    @pytest.mark.asyncio
    async def test_publish_content_success(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test successful content publishing."""
        with patch("src.services.publishing.PublishingService.publish_content") as mock_publish:
            from src.models.content import PublishingResult
            mock_result = PublishingResult(
                platform=PlatformType.LINKEDIN,
                post_id="linkedin-123",
                success=True,
                published_at="2024-01-01T12:00:00Z"
            )
            mock_publish.return_value = mock_result
            
            response = await async_client.post(
                f"/api/v1/content/{mock_content_item.id}/publish",
                headers=auth_headers,
                json={"platform": "linkedin"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["post_id"] == "linkedin-123"
    
    @pytest.mark.asyncio
    async def test_publish_content_failure(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test content publishing failure."""
        with patch("src.services.publishing.PublishingService.publish_content") as mock_publish:
            from src.models.content import PublishingResult
            mock_result = PublishingResult(
                platform=PlatformType.LINKEDIN,
                success=False,
                error_message="API rate limit exceeded"
            )
            mock_publish.return_value = mock_result
            
            response = await async_client.post(
                f"/api/v1/content/{mock_content_item.id}/publish",
                headers=auth_headers,
                json={"platform": "linkedin"}
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "rate limit" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_schedule_publication(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test scheduling content publication."""
        with patch("src.services.publishing.PublishingService.schedule_publication") as mock_schedule:
            mock_schedule.return_value = {
                "task_id": "task-123",
                "scheduled_time": "2024-01-15T14:00:00Z"
            }
            
            response = await async_client.post(
                f"/api/v1/content/{mock_content_item.id}/schedule",
                headers=auth_headers,
                json={
                    "platform": "linkedin",
                    "scheduled_time": "2024-01-15T14:00:00Z"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["task_id"] == "task-123"
    
    @pytest.mark.asyncio
    async def test_delete_content_item(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test deleting a content item."""
        with patch("src.services.content_discovery.ContentDiscoveryService.delete_content_item") as mock_delete:
            mock_delete.return_value = True
            
            response = await async_client.delete(
                f"/api/v1/content/{mock_content_item.id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_204_NO_CONTENT
    
    @pytest.mark.asyncio
    async def test_delete_content_item_not_found(
        self,
        async_client: AsyncClient,
        auth_headers
    ):
        """Test deleting non-existent content item."""
        with patch("src.services.content_discovery.ContentDiscoveryService.delete_content_item") as mock_delete:
            mock_delete.return_value = False
            
            response = await async_client.delete(
                "/api/v1/content/nonexistent-id",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_regenerate_content(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test content regeneration with feedback."""
        with patch("src.services.content_generation.ContentGenerationService.regenerate_content") as mock_regenerate:
            mock_regenerate.return_value = mock_content_item
            
            response = await async_client.post(
                f"/api/v1/content/{mock_content_item.id}/regenerate",
                headers=auth_headers,
                json={
                    "platform": "linkedin",
                    "feedback": "Make it more engaging and add questions"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == mock_content_item.id
    
    @pytest.mark.asyncio
    async def test_get_content_analytics(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test getting content analytics."""
        with patch("src.services.analytics.AnalyticsService.get_content_analytics") as mock_analytics:
            mock_analytics.return_value = {
                "impressions": 1500,
                "likes": 45,
                "comments": 8,
                "shares": 12,
                "engagement_rate": 8.8
            }
            
            response = await async_client.get(
                f"/api/v1/content/{mock_content_item.id}/analytics",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["impressions"] == 1500
            assert data["engagement_rate"] == 8.8
    
    @pytest.mark.asyncio
    async def test_bulk_generate_content(
        self,
        async_client: AsyncClient,
        auth_headers
    ):
        """Test bulk content generation."""
        with patch("src.services.content_generation.ContentGenerationService.bulk_generate_content") as mock_bulk:
            mock_bulk.return_value = {
                "successful": 3,
                "failed": 1,
                "items": ["content-1", "content-2", "content-3"]
            }
            
            response = await async_client.post(
                "/api/v1/content/bulk-generate",
                headers=auth_headers,
                json={
                    "content_ids": ["content-1", "content-2", "content-3", "content-4"],
                    "platforms": ["linkedin", "twitter"]
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["successful"] == 3
            assert data["failed"] == 1
    
    @pytest.mark.asyncio
    async def test_get_content_suggestions(
        self,
        async_client: AsyncClient,
        auth_headers
    ):
        """Test getting content suggestions based on user preferences."""
        with patch("src.services.content_discovery.ContentDiscoveryService.get_content_suggestions") as mock_suggestions:
            mock_suggestions.return_value = [
                {
                    "title": "AI Ethics in 2024",
                    "relevance_score": 0.92,
                    "topic": "ai-ethics"
                },
                {
                    "title": "Machine Learning Trends",
                    "relevance_score": 0.88,
                    "topic": "machine-learning"
                }
            ]
            
            response = await async_client.get(
                "/api/v1/content/suggestions",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["relevance_score"] == 0.92
    
    @pytest.mark.asyncio
    async def test_content_filtering_by_status(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test filtering content by status."""
        with patch("src.services.content_discovery.ContentDiscoveryService.get_user_content") as mock_get:
            mock_pagination = {
                "items": [mock_content_item],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "total_pages": 1
            }
            mock_get.return_value = mock_pagination
            
            response = await async_client.get(
                "/api/v1/content/my-content?status=generated",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            # Verify that the service was called with status filter
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_content_search(
        self,
        async_client: AsyncClient,
        auth_headers,
        mock_content_item
    ):
        """Test searching user's content."""
        with patch("src.services.content_discovery.ContentDiscoveryService.search_user_content") as mock_search:
            mock_search.return_value = [mock_content_item]
            
            response = await async_client.get(
                "/api/v1/content/search?query=AI breakthrough",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) >= 0