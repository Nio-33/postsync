"""
Tests for Reddit Integration

This module contains tests for Reddit API integration
and content discovery functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.reddit import RedditClient
from src.models.content import ContentTopic, SourceContent


class TestRedditClient:
    """Test Reddit API client functionality."""
    
    @pytest.fixture
    def client(self) -> RedditClient:
        """Create Reddit client instance."""
        return RedditClient()
    
    @pytest.fixture
    def mock_reddit_instance(self):
        """Mock PRAW Reddit instance."""
        mock_reddit = MagicMock()
        mock_subreddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        return mock_reddit, mock_subreddit
    
    @pytest.mark.asyncio
    async def test_discover_content_success(
        self,
        client: RedditClient,
        sample_reddit_data
    ):
        """Test successful content discovery from Reddit."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit, mock_subreddit = self.setup_mock_reddit(sample_reddit_data)
            mock_reddit_class.return_value = mock_reddit
            
            # Mock subreddit posts
            mock_posts = []
            for data in sample_reddit_data:
                mock_post = MagicMock()
                mock_post.id = data["id"]
                mock_post.title = data["title"]
                mock_post.selftext = data["selftext"]
                mock_post.url = data["url"]
                mock_post.score = data["score"]
                mock_post.num_comments = data["num_comments"]
                mock_post.created_utc = data["created_utc"]
                mock_post.author.name = data["author"]
                mock_post.subreddit.display_name = data["subreddit"]
                mock_posts.append(mock_post)
            
            mock_subreddit.hot.return_value = mock_posts
            
            content = await client.discover_content(
                subreddits=["AIBusiness"],
                limit=10,
                time_filter="day"
            )
            
            assert len(content) == 2
            assert content[0].title == "OpenAI Announces GPT-5"
            assert content[0].source_id == "test1"
            assert ContentTopic.ARTIFICIAL_INTELLIGENCE in content[0].topics
    
    def setup_mock_reddit(self, sample_data):
        """Helper to set up mock Reddit instance."""
        mock_reddit = MagicMock()
        mock_subreddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        return mock_reddit, mock_subreddit
    
    @pytest.mark.asyncio
    async def test_discover_content_multiple_subreddits(
        self,
        client: RedditClient,
        sample_reddit_data
    ):
        """Test content discovery from multiple subreddits."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit, mock_subreddit = self.setup_mock_reddit(sample_reddit_data)
            mock_reddit_class.return_value = mock_reddit
            
            # Mock different subreddits returning different content
            def mock_subreddit_side_effect(name):
                mock_sub = MagicMock()
                if name == "MachineLearning":
                    mock_post = MagicMock()
                    mock_post.id = "ml_post_1"
                    mock_post.title = "New ML Algorithm Breakthrough"
                    mock_post.selftext = "Researchers develop new algorithm..."
                    mock_post.url = "https://arxiv.org/ml-paper"
                    mock_post.score = 200
                    mock_post.num_comments = 30
                    mock_post.created_utc = 1640995200
                    mock_post.author.name = "ml_researcher"
                    mock_post.subreddit.display_name = "MachineLearning"
                    mock_sub.hot.return_value = [mock_post]
                else:
                    mock_sub.hot.return_value = []
                return mock_sub
            
            mock_reddit.subreddit.side_effect = mock_subreddit_side_effect
            
            content = await client.discover_content(
                subreddits=["AIBusiness", "MachineLearning"],
                limit=5
            )
            
            assert len(content) >= 1
            ml_posts = [c for c in content if c.source_id == "ml_post_1"]
            assert len(ml_posts) == 1
            assert ml_posts[0].title == "New ML Algorithm Breakthrough"
    
    @pytest.mark.asyncio
    async def test_discover_content_with_filtering(
        self,
        client: RedditClient
    ):
        """Test content discovery with quality filtering."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit = MagicMock()
            mock_subreddit = MagicMock()
            mock_reddit.subreddit.return_value = mock_subreddit
            mock_reddit_class.return_value = mock_reddit
            
            # Create posts with varying quality scores
            mock_posts = []
            for i, score in enumerate([5, 50, 150]):  # Low, medium, high engagement
                mock_post = MagicMock()
                mock_post.id = f"post_{i}"
                mock_post.title = f"Test Post {i}"
                mock_post.selftext = f"Content for post {i}"
                mock_post.url = f"https://example.com/post{i}"
                mock_post.score = score
                mock_post.num_comments = score // 5
                mock_post.created_utc = 1640995200
                mock_post.author.name = f"author_{i}"
                mock_post.subreddit.display_name = "AIBusiness"
                mock_posts.append(mock_post)
            
            mock_subreddit.hot.return_value = mock_posts
            
            content = await client.discover_content(
                subreddits=["AIBusiness"],
                min_score=25,  # Filter out low-scoring posts
                limit=10
            )
            
            # Should only return posts with score >= 25
            assert len(content) == 2
            assert all(c.upvotes >= 25 for c in content)
    
    @pytest.mark.asyncio
    async def test_discover_content_empty_result(
        self,
        client: RedditClient
    ):
        """Test content discovery when no posts are found."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit = MagicMock()
            mock_subreddit = MagicMock()
            mock_reddit.subreddit.return_value = mock_subreddit
            mock_reddit_class.return_value = mock_reddit
            
            # Mock empty subreddit
            mock_subreddit.hot.return_value = []
            
            content = await client.discover_content(
                subreddits=["EmptySubreddit"],
                limit=10
            )
            
            assert len(content) == 0
    
    @pytest.mark.asyncio 
    async def test_discover_content_api_error(
        self,
        client: RedditClient
    ):
        """Test handling of Reddit API errors."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit = MagicMock()
            mock_reddit.subreddit.side_effect = Exception("Reddit API Error")
            mock_reddit_class.return_value = mock_reddit
            
            with pytest.raises(Exception, match="Reddit API Error"):
                await client.discover_content(
                    subreddits=["AIBusiness"],
                    limit=10
                )
    
    def test_classify_content_topics(
        self,
        client: RedditClient
    ):
        """Test content topic classification."""
        # Test AI-related content
        ai_title = "OpenAI Releases New Language Model"
        ai_content = "The latest advancement in artificial intelligence..."
        ai_topics = client._classify_content_topics(ai_title, ai_content)
        
        assert ContentTopic.ARTIFICIAL_INTELLIGENCE in ai_topics
        
        # Test business-related content
        biz_title = "AI Startup Raises $50M in Series B Funding"
        biz_content = "The company plans to expand its AI platform..."
        biz_topics = client._classify_content_topics(biz_title, biz_content)
        
        assert ContentTopic.AI_BUSINESS in biz_topics
        
        # Test research content
        research_title = "New Research on Neural Network Architecture"
        research_content = "Researchers at MIT have developed..."
        research_topics = client._classify_content_topics(research_title, research_content)
        
        assert ContentTopic.AI_RESEARCH in research_topics
    
    def test_calculate_engagement_score(
        self,
        client: RedditClient
    ):
        """Test engagement score calculation."""
        # High engagement post
        high_score = client._calculate_engagement_score(
            upvotes=200,
            comments=50,
            created_timestamp=1640995200,  # Recent
            subreddit_name="AIBusiness"
        )
        
        assert 0.0 <= high_score <= 1.0
        assert high_score > 0.5
        
        # Low engagement post
        low_score = client._calculate_engagement_score(
            upvotes=5,
            comments=1,
            created_timestamp=1640908800,  # Older
            subreddit_name="AIBusiness"
        )
        
        assert 0.0 <= low_score <= 1.0
        assert low_score < high_score
    
    def test_analyze_sentiment(
        self,
        client: RedditClient
    ):
        """Test sentiment analysis of content."""
        # Positive content
        positive_text = "Amazing breakthrough in AI! This is revolutionary and will change everything for the better."
        positive_sentiment = client._analyze_sentiment(positive_text)
        assert positive_sentiment in ["positive", "neutral"]
        
        # Negative content
        negative_text = "This AI development is concerning and could lead to serious problems."
        negative_sentiment = client._analyze_sentiment(negative_text)
        assert negative_sentiment in ["negative", "neutral"]
        
        # Neutral content
        neutral_text = "The company announced a new AI model with standard features."
        neutral_sentiment = client._analyze_sentiment(neutral_text)
        assert neutral_sentiment in ["positive", "negative", "neutral"]
    
    @pytest.mark.asyncio
    async def test_check_connection_success(
        self,
        client: RedditClient
    ):
        """Test successful Reddit connection check."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit = MagicMock()
            mock_reddit.user.me.return_value = MagicMock(name="test_bot")
            mock_reddit_class.return_value = mock_reddit
            
            is_connected = await client.check_connection()
            
            assert is_connected is True
    
    @pytest.mark.asyncio
    async def test_check_connection_failure(
        self,
        client: RedditClient
    ):
        """Test Reddit connection check failure."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit = MagicMock()
            mock_reddit.user.me.side_effect = Exception("Authentication failed")
            mock_reddit_class.return_value = mock_reddit
            
            is_connected = await client.check_connection()
            
            assert is_connected is False
    
    def test_filter_duplicate_content(
        self,
        client: RedditClient
    ):
        """Test filtering of duplicate content."""
        # Create content items with some duplicates
        content_items = []
        
        # Original post
        original = SourceContent(
            source_id="original_post",
            source="reddit",
            url="https://reddit.com/original",
            title="AI Breakthrough Announced",
            description="Original description",
            author="author1",
            published_at=datetime.utcnow()
        )
        content_items.append(original)
        
        # Near-duplicate post (similar title)
        duplicate = SourceContent(
            source_id="duplicate_post", 
            source="reddit",
            url="https://reddit.com/duplicate",
            title="AI Breakthrough is Announced",  # Very similar
            description="Different description",
            author="author2",
            published_at=datetime.utcnow()
        )
        content_items.append(duplicate)
        
        # Unique post
        unique = SourceContent(
            source_id="unique_post",
            source="reddit", 
            url="https://reddit.com/unique",
            title="Completely Different AI News",
            description="Unique description",
            author="author3",
            published_at=datetime.utcnow()
        )
        content_items.append(unique)
        
        filtered_content = client._filter_duplicate_content(content_items)
        
        # Should remove the duplicate but keep original and unique
        assert len(filtered_content) == 2
        source_ids = [c.source_id for c in filtered_content]
        assert "original_post" in source_ids
        assert "unique_post" in source_ids
        assert "duplicate_post" not in source_ids
    
    @pytest.mark.asyncio
    async def test_get_trending_topics(
        self,
        client: RedditClient
    ):
        """Test getting trending topics from multiple subreddits."""
        with patch('src.integrations.reddit.praw.Reddit') as mock_reddit_class:
            mock_reddit = MagicMock()
            mock_reddit_class.return_value = mock_reddit
            
            # Mock trending posts
            def mock_subreddit_side_effect(name):
                mock_sub = MagicMock()
                mock_posts = []
                
                # Create posts with different trending topics
                topics = ["GPT-4", "autonomous vehicles", "AI safety"] 
                for i, topic in enumerate(topics):
                    mock_post = MagicMock()
                    mock_post.title = f"Breaking: {topic} news update"
                    mock_post.score = 100 + i * 50
                    mock_post.num_comments = 20 + i * 10
                    mock_post.created_utc = 1640995200
                    mock_posts.append(mock_post)
                
                mock_sub.hot.return_value = mock_posts
                return mock_sub
            
            mock_reddit.subreddit.side_effect = mock_subreddit_side_effect
            
            trending = await client.get_trending_topics(
                subreddits=["AIBusiness", "MachineLearning"],
                limit=10
            )
            
            assert len(trending) > 0
            assert all(isinstance(topic, dict) for topic in trending)
            assert all("topic" in topic and "score" in topic for topic in trending)
    
    def test_content_age_filtering(
        self,
        client: RedditClient
    ):
        """Test filtering content by age."""
        now = datetime.utcnow()
        
        # Recent content (should pass)
        recent_content = SourceContent(
            source_id="recent",
            source="reddit",
            url="https://reddit.com/recent",
            title="Recent AI News",
            description="Recent description",
            author="author1",
            published_at=now - timedelta(hours=2)
        )
        
        # Old content (should be filtered)
        old_content = SourceContent(
            source_id="old",
            source="reddit", 
            url="https://reddit.com/old",
            title="Old AI News",
            description="Old description", 
            author="author2",
            published_at=now - timedelta(days=5)
        )
        
        content_items = [recent_content, old_content]
        
        # Filter content older than 3 days
        filtered = client._filter_by_age(content_items, max_age_days=3)
        
        assert len(filtered) == 1
        assert filtered[0].source_id == "recent"