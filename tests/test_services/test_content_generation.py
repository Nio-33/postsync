"""
Tests for Content Generation Service

This module contains tests for AI-powered content generation
and optimization functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.content import ContentItem, ContentStatus, GeneratedPost, PlatformType
from src.services.content_generation import ContentGenerationService


class TestContentGenerationService:
    """Test content generation service functionality."""
    
    @pytest.fixture
    def service(self) -> ContentGenerationService:
        """Create content generation service instance."""
        return ContentGenerationService()
    
    @pytest.mark.asyncio
    async def test_generate_content_for_item_success(
        self, 
        service: ContentGenerationService,
        mock_content_item,
        mock_gemini_client,
        mock_firestore_client
    ):
        """Test successful content generation for a content item."""
        mock_content_item.status = ContentStatus.DISCOVERED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        # Mock Gemini response
        mock_generated_post = MagicMock()
        mock_generated_post.platform = PlatformType.LINKEDIN
        mock_generated_post.content = "AI breakthrough revolutionizes industry"
        mock_generated_post.hashtags = ["AI", "Technology"]
        mock_generated_post.relevance_score = 0.9
        
        mock_gemini_client.generate_posts.return_value = {
            PlatformType.LINKEDIN: mock_generated_post
        }
        
        result = await service.generate_content_for_item(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platforms=[PlatformType.LINKEDIN]
        )
        
        assert result == mock_content_item
        mock_gemini_client.generate_posts.assert_called_once()
        mock_firestore_client.update_content_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_content_wrong_status(
        self,
        service: ContentGenerationService,
        mock_content_item,
        mock_firestore_client
    ):
        """Test content generation with wrong status."""
        mock_content_item.status = ContentStatus.PUBLISHED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        
        with pytest.raises(ValueError, match="cannot be used for generation"):
            await service.generate_content_for_item(
                content_id=mock_content_item.id,
                user_id=mock_content_item.user_id,
                platforms=[PlatformType.LINKEDIN]
            )
    
    @pytest.mark.asyncio
    async def test_generate_content_item_not_found(
        self,
        service: ContentGenerationService,
        mock_firestore_client
    ):
        """Test content generation with non-existent item."""
        mock_firestore_client.get_content_item.return_value = None
        
        result = await service.generate_content_for_item(
            content_id="nonexistent",
            user_id="user-123",
            platforms=[PlatformType.LINKEDIN]
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_regenerate_content_success(
        self,
        service: ContentGenerationService,
        mock_content_item,
        mock_gemini_client,
        mock_firestore_client
    ):
        """Test successful content regeneration."""
        mock_content_item.status = ContentStatus.GENERATED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Old content",
                hashtags=["OldTag"]
            )
        }
        
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        # Mock new generation
        mock_generated_post = MagicMock()
        mock_generated_post.platform = PlatformType.LINKEDIN
        mock_generated_post.content = "New improved content"
        mock_generated_post.hashtags = ["NewTag", "AI"]
        
        mock_gemini_client.generate_posts.return_value = {
            PlatformType.LINKEDIN: mock_generated_post
        }
        
        result = await service.regenerate_content(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN,
            feedback="Make it more engaging"
        )
        
        assert result == mock_content_item
        mock_gemini_client.generate_posts.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_optimize_content_for_engagement(
        self,
        service: ContentGenerationService,
        mock_content_item,
        mock_gemini_client,
        mock_firestore_client
    ):
        """Test content optimization for engagement."""
        mock_content_item.status = ContentStatus.GENERATED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.update_content_item.return_value = mock_content_item
        
        # Mock optimization
        mock_optimized_post = MagicMock()
        mock_optimized_post.platform = PlatformType.LINKEDIN
        mock_optimized_post.content = "Optimized engaging content"
        mock_optimized_post.engagement_prediction = 0.95
        
        mock_gemini_client.optimize_content.return_value = mock_optimized_post
        
        result = await service.optimize_content_for_engagement(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN
        )
        
        assert result == mock_content_item
        mock_gemini_client.optimize_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_content_variations(
        self,
        service: ContentGenerationService,
        mock_content_item,
        mock_gemini_client,
        mock_firestore_client
    ):
        """Test creating content variations for A/B testing."""
        mock_content_item.status = ContentStatus.GENERATED
        mock_firestore_client.get_content_item.return_value = mock_content_item
        mock_firestore_client.create_content_item.return_value = MagicMock()
        
        # Mock variations
        mock_variations = [
            MagicMock(content="Variation A", hashtags=["A"]),
            MagicMock(content="Variation B", hashtags=["B"]),
            MagicMock(content="Variation C", hashtags=["C"])
        ]
        
        mock_gemini_client.create_variations.return_value = mock_variations
        
        result = await service.create_content_variations(
            content_id=mock_content_item.id,
            user_id=mock_content_item.user_id,
            platform=PlatformType.LINKEDIN,
            variation_count=3
        )
        
        assert len(result) == 3
        assert mock_firestore_client.create_content_item.call_count == 3
    
    @pytest.mark.asyncio
    async def test_analyze_content_quality(
        self,
        service: ContentGenerationService,
        mock_content_item,
        mock_gemini_client
    ):
        """Test content quality analysis."""
        mock_content_item.status = ContentStatus.GENERATED
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Test content for analysis",
                hashtags=["Test"]
            )
        }
        
        # Mock quality analysis
        mock_analysis = {
            "readability_score": 0.85,
            "engagement_prediction": 0.78,
            "fact_check_score": 0.92,
            "sentiment": "positive",
            "topics_covered": ["artificial-intelligence"],
            "improvement_suggestions": ["Add more specific examples"]
        }
        
        mock_gemini_client.analyze_content_quality.return_value = mock_analysis
        
        result = await service.analyze_content_quality(
            mock_content_item,
            PlatformType.LINKEDIN
        )
        
        assert result == mock_analysis
        mock_gemini_client.analyze_content_quality.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_generate_content(
        self,
        service: ContentGenerationService
    ):
        """Test bulk content generation for multiple items."""
        content_ids = ["content1", "content2", "content3"]
        user_id = "user-123"
        
        # Mock the generate_content_for_item method
        with patch.object(service, 'generate_content_for_item') as mock_generate:
            mock_generate.side_effect = [
                MagicMock(id="content1"),  # Success
                MagicMock(id="content2"),  # Success
                None                       # Failure
            ]
            
            results = await service.bulk_generate_content(
                content_ids=content_ids,
                user_id=user_id,
                platforms=[PlatformType.LINKEDIN, PlatformType.TWITTER]
            )
            
            assert results["successful"] == 2
            assert results["failed"] == 1
            assert len(results["items"]) == 2
            assert mock_generate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_content_performance_prediction(
        self,
        service: ContentGenerationService,
        mock_content_item,
        mock_gemini_client
    ):
        """Test content performance prediction."""
        mock_content_item.status = ContentStatus.GENERATED
        
        # Mock performance prediction
        mock_prediction = {
            "estimated_reach": 1500,
            "estimated_engagement": 120,
            "engagement_rate": 8.0,
            "optimal_posting_time": "2024-01-01T14:00:00Z",
            "confidence_score": 0.82
        }
        
        mock_gemini_client.predict_performance.return_value = mock_prediction
        
        result = await service.get_content_performance_prediction(
            mock_content_item,
            PlatformType.LINKEDIN
        )
        
        assert result == mock_prediction
        mock_gemini_client.predict_performance.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_content_generation(
        self,
        service: ContentGenerationService,
        mock_firestore_client
    ):
        """Test scheduling content generation."""
        user_id = "user-123"
        platforms = [PlatformType.LINKEDIN, PlatformType.TWITTER]
        schedule_time = datetime.utcnow() + timedelta(hours=2)
        
        mock_firestore_client.create_scheduled_task.return_value = MagicMock(
            id="task-123"
        )
        
        result = await service.schedule_content_generation(
            user_id=user_id,
            content_id="content-123",
            platforms=platforms,
            scheduled_time=schedule_time
        )
        
        assert result["task_id"] == "task-123"
        assert result["scheduled_time"] == schedule_time
        mock_firestore_client.create_scheduled_task.assert_called_once()
    
    def test_calculate_content_score(
        self,
        service: ContentGenerationService,
        mock_content_item
    ):
        """Test content scoring algorithm."""
        # Set up content with various metrics
        generated_post = GeneratedPost(
            platform=PlatformType.LINKEDIN,
            content="High quality AI content with engaging elements!",
            hashtags=["AI", "Technology", "Innovation"],
            relevance_score=0.9,
            engagement_prediction=0.85,
            fact_check_score=0.95
        )
        
        mock_content_item.generated_posts = {
            PlatformType.LINKEDIN: generated_post
        }
        
        score = service._calculate_content_score(
            mock_content_item,
            PlatformType.LINKEDIN
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Should be high due to good metrics
    
    @pytest.mark.asyncio
    async def test_update_generation_preferences(
        self,
        service: ContentGenerationService,
        mock_user,
        mock_firestore_client
    ):
        """Test updating user generation preferences."""
        new_preferences = {
            "tone": "casual",
            "length": "medium",
            "include_questions": True,
            "hashtag_count": 5,
            "emoji_usage": "moderate"
        }
        
        mock_firestore_client.get_user.return_value = mock_user
        mock_firestore_client.update_user.return_value = mock_user
        
        result = await service.update_generation_preferences(
            user_id=mock_user.id,
            preferences=new_preferences
        )
        
        assert result == mock_user
        mock_firestore_client.update_user.assert_called_once()
        
        # Check that preferences were merged
        call_args = mock_firestore_client.update_user.call_args
        updated_prefs = call_args[0][1]["content_preferences"]
        assert updated_prefs["tone"] == "casual"
        assert updated_prefs["include_questions"] is True
    
    @pytest.mark.asyncio
    async def test_get_generation_history(
        self,
        service: ContentGenerationService,
        mock_firestore_client
    ):
        """Test getting generation history for a user."""
        user_id = "user-123"
        
        # Mock history data
        mock_history = [
            {
                "content_id": "content-1",
                "generated_at": datetime.utcnow(),
                "platforms": ["linkedin"],
                "quality_score": 0.85
            },
            {
                "content_id": "content-2", 
                "generated_at": datetime.utcnow() - timedelta(hours=1),
                "platforms": ["twitter"],
                "quality_score": 0.78
            }
        ]
        
        mock_firestore_client.get_generation_history.return_value = mock_history
        
        result = await service.get_generation_history(
            user_id=user_id,
            limit=10,
            offset=0
        )
        
        assert len(result) == 2
        assert result[0]["quality_score"] == 0.85
        mock_firestore_client.get_generation_history.assert_called_once_with(
            user_id=user_id, limit=10, offset=0
        )