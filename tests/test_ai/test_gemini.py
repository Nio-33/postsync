"""
Tests for Google Gemini AI Integration

This module contains tests for the Gemini AI client
and content generation functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.gemini import GeminiClient
from src.models.content import ContentTopic, GeneratedPost, PlatformType, SourceContent
from src.models.user import ContentPreferences, User


class TestGeminiClient:
    """Test Gemini AI client functionality."""
    
    @pytest.fixture
    def client(self) -> GeminiClient:
        """Create Gemini client instance."""
        return GeminiClient()
    
    @pytest.fixture
    def mock_gemini_model(self):
        """Mock Gemini model instance."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"linkedin": {"content": "Test generated content", "hashtags": ["AI", "Technology"]}, "twitter": {"content": "Short tweet content", "hashtags": ["AI"]}}'
        mock_model.generate_content.return_value = mock_response
        return mock_model
    
    @pytest.mark.asyncio
    async def test_generate_posts_success(
        self,
        client: GeminiClient,
        mock_source_content,
        mock_user,
        mock_gemini_model
    ):
        """Test successful post generation."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            # Mock successful response
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "linkedin": {
                    "content": "🚀 Exciting AI breakthrough! This revolutionary technology will transform how we approach complex problems. What are your thoughts on the implications for the industry? #AI #Innovation #Technology",
                    "hashtags": ["AI", "Innovation", "Technology"],
                    "relevance_score": 0.92,
                    "engagement_prediction": 0.85
                },
                "twitter": {
                    "content": "🚀 Revolutionary AI breakthrough changes everything! What impact do you think this will have? #AI #Innovation",
                    "hashtags": ["AI", "Innovation"],
                    "relevance_score": 0.88,
                    "engagement_prediction": 0.78
                }
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            posts = await client.generate_posts(
                source_content=mock_source_content,
                user_preferences=mock_user.content_preferences,
                platforms=[PlatformType.LINKEDIN, PlatformType.TWITTER]
            )
            
            assert len(posts) == 2
            assert PlatformType.LINKEDIN in posts
            assert PlatformType.TWITTER in posts
            
            linkedin_post = posts[PlatformType.LINKEDIN]
            assert "AI breakthrough" in linkedin_post.content
            assert "AI" in linkedin_post.hashtags
            assert linkedin_post.relevance_score == 0.92
    
    @pytest.mark.asyncio
    async def test_generate_posts_single_platform(
        self,
        client: GeminiClient,
        mock_source_content,
        mock_user,
        mock_gemini_model
    ):
        """Test post generation for single platform."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "linkedin": {
                    "content": "Professional LinkedIn post about AI innovation",
                    "hashtags": ["AI", "Innovation", "LinkedIn"],
                    "relevance_score": 0.90,
                    "engagement_prediction": 0.82
                }
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            posts = await client.generate_posts(
                source_content=mock_source_content,
                user_preferences=mock_user.content_preferences,
                platforms=[PlatformType.LINKEDIN]
            )
            
            assert len(posts) == 1
            assert PlatformType.LINKEDIN in posts
            assert PlatformType.TWITTER not in posts
    
    @pytest.mark.asyncio
    async def test_generate_posts_api_error(
        self,
        client: GeminiClient,
        mock_source_content,
        mock_user,
        mock_gemini_model
    ):
        """Test handling of Gemini API errors."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            mock_gemini_model.generate_content.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                await client.generate_posts(
                    source_content=mock_source_content,
                    user_preferences=mock_user.content_preferences,
                    platforms=[PlatformType.LINKEDIN]
                )
    
    @pytest.mark.asyncio
    async def test_optimize_content_for_engagement(
        self,
        client: GeminiClient,
        mock_gemini_model
    ):
        """Test content optimization for engagement."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            original_post = GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Basic AI post without much engagement",
                hashtags=["AI"]
            )
            
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "content": "🚀 Transform your AI strategy with this game-changing breakthrough! What innovative applications can you envision for your industry? Share your thoughts below! #AI #Innovation #Strategy #FutureOfWork",
                "hashtags": ["AI", "Innovation", "Strategy", "FutureOfWork"],
                "engagement_prediction": 0.92,
                "improvements_made": ["Added emojis", "Included call-to-action", "Enhanced hashtags"]
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            optimized = await client.optimize_content(
                original_post=original_post,
                optimization_goals=["engagement", "reach"]
            )
            
            assert "game-changing breakthrough" in optimized.content
            assert optimized.engagement_prediction == 0.92
            assert len(optimized.hashtags) == 4
    
    @pytest.mark.asyncio
    async def test_create_content_variations(
        self,
        client: GeminiClient,
        mock_gemini_model
    ):
        """Test creating content variations for A/B testing."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            original_post = GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="Original AI content",
                hashtags=["AI"]
            )
            
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "variations": [
                    {
                        "content": "Variation A: Question-focused AI content - What do you think about this AI advancement?",
                        "hashtags": ["AI", "Question"],
                        "variation_type": "question_focused"
                    },
                    {
                        "content": "Variation B: Story-driven AI content - Here's how this AI breakthrough changed everything...",
                        "hashtags": ["AI", "Story"],
                        "variation_type": "story_driven"
                    },
                    {
                        "content": "Variation C: Data-driven AI content - 85% of experts agree this AI technology will...",
                        "hashtags": ["AI", "Data"],
                        "variation_type": "data_driven"
                    }
                ]
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            variations = await client.create_variations(
                original_post=original_post,
                variation_count=3,
                variation_types=["question_focused", "story_driven", "data_driven"]
            )
            
            assert len(variations) == 3
            assert "Question-focused" in variations[0].content
            assert "Story-driven" in variations[1].content
            assert "Data-driven" in variations[2].content
    
    @pytest.mark.asyncio
    async def test_analyze_content_quality(
        self,
        client: GeminiClient,
        mock_gemini_model
    ):
        """Test content quality analysis."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            content = "Test AI content for quality analysis"
            
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "readability_score": 0.85,
                "engagement_prediction": 0.78,
                "fact_check_score": 0.92,
                "sentiment": "positive",
                "topics_covered": ["artificial-intelligence", "technology"],
                "improvement_suggestions": [
                    "Add more specific examples",
                    "Include call-to-action",
                    "Enhance hashtag strategy"
                ],
                "compliance_check": {
                    "professional_tone": true,
                    "appropriate_length": true,
                    "platform_guidelines": true
                }
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            analysis = await client.analyze_content_quality(
                content=content,
                platform=PlatformType.LINKEDIN
            )
            
            assert analysis["readability_score"] == 0.85
            assert analysis["sentiment"] == "positive"
            assert len(analysis["improvement_suggestions"]) == 3
            assert analysis["compliance_check"]["professional_tone"] is True
    
    @pytest.mark.asyncio
    async def test_predict_performance(
        self,
        client: GeminiClient,
        mock_gemini_model
    ):
        """Test content performance prediction."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            post = GeneratedPost(
                platform=PlatformType.LINKEDIN,
                content="AI breakthrough content with hashtags",
                hashtags=["AI", "Innovation"]
            )
            
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "estimated_reach": 2500,
                "estimated_engagement": 180,
                "engagement_rate": 7.2,
                "estimated_shares": 15,
                "estimated_comments": 25,
                "optimal_posting_time": "2024-01-15T14:00:00Z",
                "confidence_score": 0.84,
                "factors": {
                    "content_quality": 0.88,
                    "hashtag_relevance": 0.92,
                    "timing_factor": 0.75,
                    "audience_match": 0.85
                }
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            prediction = await client.predict_performance(
                post=post,
                user_audience_data={"followers": 1000, "engagement_rate": 6.5}
            )
            
            assert prediction["estimated_reach"] == 2500
            assert prediction["engagement_rate"] == 7.2
            assert prediction["confidence_score"] == 0.84
            assert "content_quality" in prediction["factors"]
    
    @pytest.mark.asyncio
    async def test_generate_hashtags(
        self,
        client: GeminiClient,
        mock_gemini_model
    ):
        """Test hashtag generation."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            content = "Revolutionary AI breakthrough in natural language processing"
            
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "hashtags": [
                    {"tag": "AI", "relevance": 0.95, "popularity": 0.90},
                    {"tag": "NLP", "relevance": 0.92, "popularity": 0.75},
                    {"tag": "Innovation", "relevance": 0.88, "popularity": 0.85},
                    {"tag": "Technology", "relevance": 0.85, "popularity": 0.95},
                    {"tag": "MachineLearning", "relevance": 0.80, "popularity": 0.80}
                ],
                "trending_hashtags": ["AI", "Technology"],
                "recommended_count": 4
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            hashtags = await client.generate_hashtags(
                content=content,
                platform=PlatformType.LINKEDIN,
                max_count=5
            )
            
            assert len(hashtags) == 5
            assert hashtags[0]["tag"] == "AI"
            assert hashtags[0]["relevance"] == 0.95
            assert "trending_hashtags" in hashtags
    
    @pytest.mark.asyncio
    async def test_check_connection_success(
        self,
        client: GeminiClient,
        mock_gemini_model
    ):
        """Test successful Gemini connection check."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            mock_response = MagicMock()
            mock_response.text = "Connection test successful"
            mock_gemini_model.generate_content.return_value = mock_response
            
            is_connected = await client.check_connection()
            
            assert is_connected is True
    
    @pytest.mark.asyncio
    async def test_check_connection_failure(
        self,
        client: GeminiClient,
        mock_gemini_model
    ):
        """Test Gemini connection check failure."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            mock_gemini_model.generate_content.side_effect = Exception("API Error")
            
            is_connected = await client.check_connection()
            
            assert is_connected is False
    
    def test_build_generation_prompt(
        self,
        client: GeminiClient,
        mock_source_content,
        mock_user
    ):
        """Test building generation prompts."""
        prompt = client._build_generation_prompt(
            source_content=mock_source_content,
            user_preferences=mock_user.content_preferences,
            platforms=[PlatformType.LINKEDIN, PlatformType.TWITTER]
        )
        
        assert "Revolutionary AI Breakthrough" in prompt  # Source title
        assert "professional" in prompt.lower()  # User tone preference
        assert "linkedin" in prompt.lower()
        assert "twitter" in prompt.lower()
    
    def test_parse_generated_response(
        self,
        client: GeminiClient
    ):
        """Test parsing of Gemini response."""
        response_text = '''
        {
            "linkedin": {
                "content": "Test LinkedIn content",
                "hashtags": ["Test", "LinkedIn"],
                "relevance_score": 0.85
            },
            "twitter": {
                "content": "Test Twitter content",
                "hashtags": ["Test", "Twitter"],
                "relevance_score": 0.78
            }
        }
        '''
        
        parsed = client._parse_generated_response(response_text)
        
        assert "linkedin" in parsed
        assert "twitter" in parsed
        assert parsed["linkedin"]["content"] == "Test LinkedIn content"
        assert parsed["twitter"]["relevance_score"] == 0.78
    
    def test_parse_invalid_response(
        self,
        client: GeminiClient
    ):
        """Test handling of invalid JSON responses."""
        invalid_response = "Invalid JSON response from Gemini"
        
        with pytest.raises(ValueError, match="Invalid response format"):
            client._parse_generated_response(invalid_response)
    
    def test_validate_content_compliance(
        self,
        client: GeminiClient
    ):
        """Test content compliance validation."""
        # Valid professional content
        valid_content = "Exciting developments in AI technology are transforming industries worldwide."
        is_compliant, issues = client._validate_content_compliance(
            content=valid_content,
            platform=PlatformType.LINKEDIN
        )
        
        assert is_compliant is True
        assert len(issues) == 0
        
        # Content with potential issues
        problematic_content = "BUY NOW!!! URGENT AI DEAL!!! LIMITED TIME!!!"
        is_compliant, issues = client._validate_content_compliance(
            content=problematic_content,
            platform=PlatformType.LINKEDIN
        )
        
        assert is_compliant is False
        assert len(issues) > 0
    
    @pytest.mark.asyncio
    async def test_generate_content_series(
        self,
        client: GeminiClient,
        mock_source_content,
        mock_user,
        mock_gemini_model
    ):
        """Test generating a series of related posts."""
        with patch('src.ai.gemini.genai.GenerativeModel') as mock_model_class:
            mock_model_class.return_value = mock_gemini_model
            
            mock_response = MagicMock()
            mock_response.text = '''
            {
                "series": [
                    {
                        "post_number": 1,
                        "content": "Part 1: Introduction to the AI breakthrough",
                        "hashtags": ["AI", "Series", "Part1"],
                        "platform": "linkedin"
                    },
                    {
                        "post_number": 2,
                        "content": "Part 2: Technical details of the breakthrough",
                        "hashtags": ["AI", "Technical", "Part2"],
                        "platform": "linkedin"
                    },
                    {
                        "post_number": 3,
                        "content": "Part 3: Implications for the industry",
                        "hashtags": ["AI", "Industry", "Part3"],
                        "platform": "linkedin"
                    }
                ]
            }
            '''
            mock_gemini_model.generate_content.return_value = mock_response
            
            series = await client.generate_content_series(
                source_content=mock_source_content,
                user_preferences=mock_user.content_preferences,
                platform=PlatformType.LINKEDIN,
                series_length=3
            )
            
            assert len(series) == 3
            assert "Part 1:" in series[0].content
            assert "Part 2:" in series[1].content
            assert "Part 3:" in series[2].content