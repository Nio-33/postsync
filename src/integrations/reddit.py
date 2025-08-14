"""
Reddit API Integration

This module handles Reddit API interactions for content discovery
from r/AIBusiness and other AI-related subreddits.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import praw
import structlog
from praw.models import Submission

from src.config.settings import get_settings
from src.models.content import ContentSource, ContentTopic, SourceContent


class RedditClient:
    """Reddit API client for content discovery."""
    
    def __init__(self):
        """Initialize Reddit client with API credentials."""
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize PRAW client
        self._client = praw.Reddit(
            client_id=self.settings.reddit_client_id,
            client_secret=self.settings.reddit_client_secret,
            user_agent=self.settings.reddit_user_agent,
        )
        
        # Subreddit configurations
        self.subreddits = {
            "AIBusiness": {
                "name": "AIBusiness",
                "topics": [ContentTopic.AI_STARTUPS, ContentTopic.AI_FUNDING, ContentTopic.AI_NEWS],
                "min_score": 10,
            },
            "MachineLearning": {
                "name": "MachineLearning", 
                "topics": [ContentTopic.MACHINE_LEARNING, ContentTopic.AI_RESEARCH],
                "min_score": 20,
            },
            "artificial": {
                "name": "artificial",
                "topics": [ContentTopic.ARTIFICIAL_INTELLIGENCE, ContentTopic.AI_NEWS],
                "min_score": 15,
            },
            "OpenAI": {
                "name": "OpenAI",
                "topics": [ContentTopic.GENERATIVE_AI, ContentTopic.AI_TOOLS],
                "min_score": 10,
            },
            "singularity": {
                "name": "singularity",
                "topics": [ContentTopic.AI_RESEARCH, ContentTopic.AI_ETHICS],
                "min_score": 5,
            },
        }
    
    async def discover_content(
        self,
        hours_back: int = 24,
        min_score: int = 10,
        limit: int = 100
    ) -> List[SourceContent]:
        """
        Discover new content from configured subreddits.
        
        Args:
            hours_back: How many hours back to look for content
            min_score: Minimum score threshold for posts
            limit: Maximum number of posts per subreddit
            
        Returns:
            List of SourceContent objects
        """
        self.logger.info(
            "Starting Reddit content discovery",
            hours_back=hours_back,
            min_score=min_score,
            limit=limit
        )
        
        discovered_content = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        for subreddit_config in self.subreddits.values():
            try:
                subreddit_content = await self._discover_from_subreddit(
                    subreddit_config=subreddit_config,
                    cutoff_time=cutoff_time,
                    min_score=max(min_score, subreddit_config["min_score"]),
                    limit=limit
                )
                discovered_content.extend(subreddit_content)
                
            except Exception as e:
                self.logger.error(
                    "Failed to discover content from subreddit",
                    subreddit=subreddit_config["name"],
                    error=str(e)
                )
                continue
        
        # Remove duplicates based on URL
        unique_content = self._deduplicate_content(discovered_content)
        
        self.logger.info(
            "Reddit content discovery completed",
            total_discovered=len(discovered_content),
            unique_content=len(unique_content)
        )
        
        return unique_content
    
    async def _discover_from_subreddit(
        self,
        subreddit_config: Dict,
        cutoff_time: datetime,
        min_score: int,
        limit: int
    ) -> List[SourceContent]:
        """Discover content from a specific subreddit."""
        subreddit_name = subreddit_config["name"]
        topics = subreddit_config["topics"]
        
        self.logger.debug(
            "Discovering content from subreddit",
            subreddit=subreddit_name,
            min_score=min_score
        )
        
        try:
            # Get subreddit instance
            subreddit = self._client.subreddit(subreddit_name)
            
            # Get hot and new posts
            content_items = []
            
            # Process hot posts
            for submission in subreddit.hot(limit=limit // 2):
                if await self._should_include_submission(submission, cutoff_time, min_score):
                    content_item = await self._submission_to_content(submission, topics)
                    if content_item:
                        content_items.append(content_item)
            
            # Process new posts
            for submission in subreddit.new(limit=limit // 2):
                if await self._should_include_submission(submission, cutoff_time, min_score):
                    content_item = await self._submission_to_content(submission, topics)
                    if content_item:
                        content_items.append(content_item)
            
            self.logger.debug(
                "Content discovered from subreddit",
                subreddit=subreddit_name,
                count=len(content_items)
            )
            
            return content_items
            
        except Exception as e:
            self.logger.error(
                "Error discovering content from subreddit",
                subreddit=subreddit_name,
                error=str(e)
            )
            return []
    
    async def _should_include_submission(
        self,
        submission: Submission,
        cutoff_time: datetime,
        min_score: int
    ) -> bool:
        """Check if submission should be included in discovery."""
        # Check if post is recent enough
        post_time = datetime.utcfromtimestamp(submission.created_utc)
        if post_time < cutoff_time:
            return False
        
        # Check minimum score
        if submission.score < min_score:
            return False
        
        # Skip removed or deleted posts
        if submission.removed_by_category or submission.selftext == "[deleted]":
            return False
        
        # Skip self posts without external links
        if submission.is_self and not submission.url.startswith("http"):
            return False
        
        # Filter out common non-content domains
        excluded_domains = {
            "reddit.com",
            "redd.it", 
            "imgur.com",
            "youtube.com",  # Will handle separately in future
            "youtu.be"
        }
        
        if any(domain in submission.url for domain in excluded_domains):
            return False
        
        return True
    
    async def _submission_to_content(
        self,
        submission: Submission,
        default_topics: List[ContentTopic]
    ) -> Optional[SourceContent]:
        """Convert Reddit submission to SourceContent object."""
        try:
            # Extract topics from title and content
            topics = await self._extract_topics(submission.title, submission.selftext)
            if not topics:
                topics = default_topics
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(submission)
            
            # Determine sentiment (basic implementation)
            sentiment = self._analyze_sentiment(submission.title)
            
            content = SourceContent(
                source_id=submission.id,
                source=ContentSource.REDDIT,
                url=submission.url,
                title=submission.title,
                description=submission.selftext[:500] if submission.selftext else None,
                author=str(submission.author) if submission.author else None,
                published_at=datetime.utcfromtimestamp(submission.created_utc),
                upvotes=submission.score,
                comments_count=submission.num_comments,
                engagement_score=engagement_score,
                topics=topics,
                sentiment=sentiment,
            )
            
            return content
            
        except Exception as e:
            self.logger.error(
                "Failed to convert submission to content",
                submission_id=submission.id,
                error=str(e)
            )
            return None
    
    async def _extract_topics(self, title: str, content: str) -> List[ContentTopic]:
        """Extract relevant topics from title and content."""
        title_lower = title.lower()
        content_lower = content.lower() if content else ""
        text = f"{title_lower} {content_lower}"
        
        topics = []
        
        # Topic keyword mapping
        topic_keywords = {
            ContentTopic.ARTIFICIAL_INTELLIGENCE: [
                "artificial intelligence", "ai", "agi", "superintelligence"
            ],
            ContentTopic.MACHINE_LEARNING: [
                "machine learning", "ml", "neural network", "deep learning"
            ],
            ContentTopic.GENERATIVE_AI: [
                "generative ai", "gpt", "llm", "language model", "chatgpt", "claude"
            ],
            ContentTopic.AI_STARTUPS: [
                "startup", "company", "business", "enterprise", "saas"
            ],
            ContentTopic.AI_FUNDING: [
                "funding", "investment", "venture", "series", "raised", "valuation"
            ],
            ContentTopic.AI_RESEARCH: [
                "research", "paper", "study", "breakthrough", "discovery"
            ],
            ContentTopic.AI_ETHICS: [
                "ethics", "bias", "fairness", "responsible", "alignment"
            ],
            ContentTopic.AI_POLICY: [
                "policy", "regulation", "government", "law", "legal"
            ],
            ContentTopic.AI_CAREERS: [
                "job", "career", "hiring", "salary", "interview"
            ],
            ContentTopic.AI_TOOLS: [
                "tool", "platform", "software", "api", "framework"
            ],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)
        
        # Default to AI news if no specific topics found
        if not topics:
            topics.append(ContentTopic.AI_NEWS)
        
        return topics[:3]  # Limit to top 3 topics
    
    def _calculate_engagement_score(self, submission: Submission) -> float:
        """Calculate engagement score based on Reddit metrics."""
        # Basic engagement score calculation
        score_weight = 0.6
        comment_weight = 0.3
        ratio_weight = 0.1
        
        # Normalize scores (rough estimation)
        normalized_score = min(submission.score / 100.0, 1.0)
        normalized_comments = min(submission.num_comments / 50.0, 1.0)
        upvote_ratio = getattr(submission, 'upvote_ratio', 0.5)
        
        engagement_score = (
            normalized_score * score_weight +
            normalized_comments * comment_weight +
            upvote_ratio * ratio_weight
        )
        
        return min(engagement_score, 1.0)
    
    def _analyze_sentiment(self, title: str) -> str:
        """Basic sentiment analysis of title."""
        positive_words = [
            "breakthrough", "success", "amazing", "incredible", "revolutionary",
            "advance", "progress", "achievement", "winner", "best"
        ]
        negative_words = [
            "failed", "problem", "issue", "concern", "danger", "risk",
            "threat", "warning", "crisis", "disaster"
        ]
        
        title_lower = title.lower()
        
        positive_count = sum(1 for word in positive_words if word in title_lower)
        negative_count = sum(1 for word in negative_words if word in title_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _deduplicate_content(self, content_list: List[SourceContent]) -> List[SourceContent]:
        """Remove duplicate content based on URL."""
        seen_urls = set()
        unique_content = []
        
        for content in content_list:
            if content.url not in seen_urls:
                seen_urls.add(content.url)
                unique_content.append(content)
        
        return unique_content
    
    async def get_submission_details(self, submission_id: str) -> Optional[Dict]:
        """Get detailed information about a specific submission."""
        try:
            submission = self._client.submission(id=submission_id)
            
            return {
                "id": submission.id,
                "title": submission.title,
                "url": submission.url,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "created_utc": submission.created_utc,
                "author": str(submission.author) if submission.author else None,
                "subreddit": str(submission.subreddit),
                "selftext": submission.selftext,
                "upvote_ratio": getattr(submission, 'upvote_ratio', None),
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get submission details",
                submission_id=submission_id,
                error=str(e)
            )
            return None
    
    async def check_connection(self) -> bool:
        """Check if Reddit API connection is working."""
        try:
            # Try to access a public subreddit
            subreddit = self._client.subreddit("test")
            next(subreddit.hot(limit=1))
            return True
            
        except Exception as e:
            self.logger.error("Reddit connection check failed", error=str(e))
            return False


# Global Reddit client instance
reddit_client = RedditClient()


async def discover_reddit_content(
    hours_back: int = 24,
    min_score: int = 10,
    limit: int = 100
) -> List[SourceContent]:
    """Convenience function to discover content from Reddit."""
    return await reddit_client.discover_content(
        hours_back=hours_back,
        min_score=min_score,
        limit=limit
    )