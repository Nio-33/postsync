"""
Content Discovery Service

This service handles discovering new content from various sources
and managing the content discovery pipeline.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import structlog

from src.integrations.firestore import firestore_client
from src.integrations.reddit import reddit_client
from src.models.content import ContentItem, ContentListResponse, ContentStatus, SourceContent
from src.models.user import User
from src.utils.error_handling import (
    with_retry, with_error_handling, ErrorContext, ExternalServiceError, 
    ContentGenerationError, error_handler
)


class ContentDiscoveryService:
    """Service for discovering and managing content from external sources."""
    
    def __init__(self):
        """Initialize content discovery service."""
        self.logger = structlog.get_logger(__name__)
        self.reddit = reddit_client
        self.db = firestore_client
    
    @with_error_handling("content_discovery", "discover_content_for_user", "retry_with_backoff")
    @with_retry(max_attempts=3, retryable_errors=[ExternalServiceError])
    async def discover_content_for_user(self, user_id: str) -> List[ContentItem]:
        """
        Discover new content for a specific user based on their preferences.
        
        Args:
            user_id: User ID to discover content for
            
        Returns:
            List of discovered content items
        """
        self.logger.info("Starting content discovery for user", user_id=user_id)
        
        try:
            # Get user preferences
            user = await self.db.get_user(user_id)
            if not user:
                self.logger.error("User not found for content discovery", user_id=user_id)
                return []
            
            # Discover content from Reddit
            discovered_content = await self._discover_from_reddit(user)
            
            # Filter and score content based on user preferences
            filtered_content = await self._filter_and_score_content(discovered_content, user)
            
            # Create content items in database
            content_items = []
            for source_content in filtered_content:
                try:
                    # Check for duplicates
                    existing = await self.db.get_content_by_source_id(
                        source_content.source_id, 
                        source_content.source.value
                    )
                    
                    if existing:
                        self.logger.debug(
                            "Skipping duplicate content",
                            source_id=source_content.source_id
                        )
                        continue
                    
                    # Create new content item
                    content_item = ContentItem(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        status=ContentStatus.DISCOVERED,
                        source_content=source_content,
                    )
                    
                    # Save to database
                    created_item = await self.db.create_content_item(content_item)
                    content_items.append(created_item)
                    
                except Exception as item_error:
                    # Log individual item error but continue processing
                    self.logger.warning(
                        "Failed to process content item",
                        source_id=source_content.source_id,
                        error=str(item_error)
                    )
                    continue
            
            self.logger.info(
                "Content discovery completed",
                user_id=user_id,
                discovered_count=len(discovered_content),
                filtered_count=len(filtered_content),
                created_count=len(content_items)
            )
            
            return content_items
            
        except Exception as e:
            # Create error context
            context = ErrorContext(
                service="content_discovery",
                operation="discover_content_for_user",
                user_id=user_id
            )
            
            # Handle the error
            await error_handler.handle_error(e, context)
            
            self.logger.error(
                "Content discovery failed",
                user_id=user_id,
                error=str(e)
            )
            
            # Return empty list instead of raising to maintain service availability
            return []
    
    async def _discover_from_reddit(self, user: User) -> List[SourceContent]:
        """Discover content from Reddit based on user preferences."""
        try:
            # Calculate discovery parameters based on user preferences
            hours_back = 24  # Look back 24 hours
            min_score = 10   # Minimum Reddit score
            limit = 50       # Maximum posts per source
            
            # Discover content from Reddit
            reddit_content = await self.reddit.discover_content(
                hours_back=hours_back,
                min_score=min_score,
                limit=limit
            )
            
            self.logger.debug(
                "Reddit content discovered",
                user_id=user.id,
                count=len(reddit_content)
            )
            
            return reddit_content
            
        except Exception as e:
            self.logger.error(
                "Reddit content discovery failed",
                user_id=user.id,
                error=str(e)
            )
            return []
    
    async def _filter_and_score_content(
        self, 
        content_list: List[SourceContent], 
        user: User
    ) -> List[SourceContent]:
        """Filter and score content based on user preferences."""
        try:
            filtered_content = []
            user_topics = set(user.content_preferences.topics)
            
            for content in content_list:
                # Check if content topics match user interests
                content_topics = set([topic.value for topic in content.topics])
                topic_overlap = len(user_topics.intersection(content_topics))
                
                if topic_overlap == 0:
                    continue  # Skip content with no topic overlap
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance_score(content, user)
                
                # Filter by minimum relevance threshold
                if relevance_score < 0.3:
                    continue
                
                # Update content with enhanced scoring
                content.engagement_score = relevance_score
                filtered_content.append(content)
            
            # Sort by relevance score (descending)
            filtered_content.sort(key=lambda x: x.engagement_score, reverse=True)
            
            # Limit to top content based on user's daily post limit
            max_content = user.content_preferences.posts_per_day * 3  # 3x buffer
            filtered_content = filtered_content[:max_content]
            
            self.logger.debug(
                "Content filtered and scored",
                user_id=user.id,
                original_count=len(content_list),
                filtered_count=len(filtered_content)
            )
            
            return filtered_content
            
        except Exception as e:
            self.logger.error(
                "Content filtering failed",
                user_id=user.id,
                error=str(e)
            )
            return content_list  # Return unfiltered if filtering fails
    
    def _calculate_relevance_score(self, content: SourceContent, user: User) -> float:
        """Calculate enhanced relevance score for content based on user preferences."""
        # Base engagement score (normalized 0-1)
        base_score = min(content.engagement_score, 1.0)
        
        # Weighted scoring components
        topic_score = self._calculate_topic_relevance(content, user)
        business_impact_score = self._calculate_business_impact(content)
        recency_score = self._calculate_recency_score(content)
        engagement_score = self._calculate_engagement_score(content)
        quality_score = self._calculate_content_quality_score(content)
        
        # Weighted combination based on PRD priorities
        final_score = (
            base_score * 0.2 +          # Base engagement
            topic_score * 0.25 +        # Topic relevance (highest weight)
            business_impact_score * 0.2 +  # Business impact
            recency_score * 0.15 +      # Recency
            engagement_score * 0.15 +   # Social engagement
            quality_score * 0.05        # Content quality indicators
        )
        
        return min(final_score, 1.0)  # Cap at 1.0
    
    def _calculate_topic_relevance(self, content: SourceContent, user: User) -> float:
        """Calculate topic relevance score with priority keywords."""
        score = 0.0
        
        # User topic preferences
        user_topics = set(user.content_preferences.topics)
        content_topics = set([topic.value for topic in content.topics])
        topic_overlap = len(user_topics.intersection(content_topics))
        
        if topic_overlap > 0:
            score += 0.4 * (topic_overlap / max(len(user_topics), 1))
        
        # Priority keyword boost (from PRD)
        priority_keywords = {
            "funding", "acquisition", "ipo", "investment", "venture capital",
            "breakthrough", "launch", "partnership", "startup", "unicorn",
            "series a", "series b", "series c", "valuation", "revenue",
            "ai model", "gpt", "llm", "machine learning", "deep learning"
        }
        
        text_content = f"{content.title} {content.description or ''}".lower()
        keyword_matches = sum(1 for keyword in priority_keywords if keyword in text_content)
        
        if keyword_matches > 0:
            score += 0.3 * min(keyword_matches / 5, 1.0)  # Boost up to 0.3
        
        # AI industry specific terms
        ai_terms = {
            "artificial intelligence", "machine learning", "neural network",
            "generative ai", "chatgpt", "openai", "anthropic", "google ai"
        }
        ai_matches = sum(1 for term in ai_terms if term in text_content)
        if ai_matches > 0:
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_business_impact(self, content: SourceContent) -> float:
        """Calculate business impact score based on content type and significance."""
        score = 0.0
        
        title_lower = content.title.lower()
        description_lower = (content.description or "").lower()
        full_text = f"{title_lower} {description_lower}"
        
        # High impact business events
        high_impact_terms = {
            "billion": 0.3, "million": 0.2, "acquisition": 0.25, "merger": 0.25,
            "ipo": 0.3, "public": 0.2, "investment": 0.2, "funding": 0.2,
            "partnership": 0.15, "collaboration": 0.15, "breakthrough": 0.25,
            "record": 0.2, "first": 0.15, "largest": 0.2, "leader": 0.1
        }
        
        for term, weight in high_impact_terms.items():
            if term in full_text:
                score += weight
        
        # Company significance indicators
        major_companies = {
            "openai", "google", "microsoft", "meta", "apple", "amazon",
            "nvidia", "tesla", "anthropic", "deepmind", "facebook"
        }
        
        company_mentions = sum(1 for company in major_companies if company in full_text)
        if company_mentions > 0:
            score += 0.15 * min(company_mentions, 2)  # Max 0.3 boost
        
        return min(score, 1.0)
    
    def _calculate_recency_score(self, content: SourceContent) -> float:
        """Calculate recency score with decay function."""
        hours_old = (datetime.utcnow() - content.published_at).total_seconds() / 3600
        
        # Exponential decay for recency (optimal posting within 6 hours)
        if hours_old <= 1:
            return 1.0  # Breaking news
        elif hours_old <= 6:
            return 0.8  # Very recent
        elif hours_old <= 12:
            return 0.6  # Recent
        elif hours_old <= 24:
            return 0.4  # Same day
        else:
            return max(0.1, 0.4 * (48 - hours_old) / 24)  # Decay over 48 hours
    
    def _calculate_engagement_score(self, content: SourceContent) -> float:
        """Calculate normalized engagement score."""
        score = 0.0
        
        # Reddit-specific engagement metrics
        if content.upvotes:
            # Normalize upvotes (logarithmic scale for better distribution)
            import math
            normalized_upvotes = min(math.log10(content.upvotes + 1) / 3, 1.0)
            score += normalized_upvotes * 0.6
        
        if content.comments_count:
            # Normalize comments
            normalized_comments = min(content.comments_count / 50, 1.0)
            score += normalized_comments * 0.4
        
        return score
    
    def _calculate_content_quality_score(self, content: SourceContent) -> float:
        """Calculate content quality indicators."""
        score = 0.5  # Base quality score
        
        # Title quality indicators
        title_words = len(content.title.split())
        if 8 <= title_words <= 15:  # Optimal title length
            score += 0.2
        
        # Description quality
        if content.description:
            desc_words = len(content.description.split())
            if desc_words >= 20:  # Substantial description
                score += 0.2
        
        # URL quality (prefer established domains)
        quality_domains = {
            "techcrunch.com", "venturebeat.com", "wired.com", "arstechnica.com",
            "bloomberg.com", "reuters.com", "wsj.com", "ft.com", "cnbc.com"
        }
        
        if any(domain in content.url for domain in quality_domains):
            score += 0.3
        
        return min(score, 1.0)
    
    async def get_user_content(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc"
    ) -> ContentListResponse:
        """
        Get paginated list of content for a user with filtering and sorting.
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            filters: Optional filters to apply
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            ContentListResponse with paginated content
        """
        try:
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Apply filters
            status_filter = None
            if filters and "status" in filters:
                status_filter = filters["status"]
            
            # Get content from database
            content_items = await self.db.get_user_content(
                user_id=user_id,
                status=status_filter,
                limit=page_size,
                offset=offset,
                order_by=sort_by or "created_at",
                descending=sort_order.lower() == "desc"
            )
            
            # Get total count (simplified - in production would need proper count query)
            total_items = await self._get_user_content_count(user_id, filters)
            
            # Calculate pagination info
            total_pages = (total_items + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1
            
            # Convert to response format
            from src.models.content import ContentResponse
            items = [ContentResponse.from_orm(item) for item in content_items]
            
            return ContentListResponse(
                items=items,
                total=total_items,
                page=page,
                page_size=page_size,
                has_next=has_next,
                has_previous=has_previous
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to get user content",
                user_id=user_id,
                error=str(e)
            )
            return ContentListResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                has_next=False,
                has_previous=False
            )
    
    async def _get_user_content_count(self, user_id: str, filters: Optional[Dict] = None) -> int:
        """Get total count of user content (simplified implementation)."""
        # In production, this would be a proper count query
        # For now, return estimated count
        return 100  # Placeholder
    
    async def get_content_item(self, content_id: str, user_id: str) -> Optional[ContentItem]:
        """
        Get a specific content item by ID.
        
        Args:
            content_id: Content item ID
            user_id: User ID (for authorization)
            
        Returns:
            ContentItem if found and belongs to user, None otherwise
        """
        try:
            content_item = await self.db.get_content_item(content_id)
            
            if content_item and content_item.user_id == user_id:
                return content_item
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get content item",
                content_id=content_id,
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def approve_content(
        self,
        content_id: str,
        user_id: str,
        approved: bool,
        rejection_reason: Optional[str] = None
    ) -> Optional[ContentItem]:
        """
        Approve or reject content for publishing.
        
        Args:
            content_id: Content item ID
            user_id: User ID
            approved: Whether content is approved
            rejection_reason: Reason for rejection (if not approved)
            
        Returns:
            Updated ContentItem
        """
        try:
            # Get and validate content item
            content_item = await self.get_content_item(content_id, user_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            # Check if content is in correct state for approval
            if content_item.status not in [ContentStatus.GENERATED, ContentStatus.REJECTED]:
                raise ValueError(f"Content cannot be approved in status: {content_item.status}")
            
            # Update content status
            updates = {
                "status": ContentStatus.APPROVED if approved else ContentStatus.REJECTED,
                "approved_by": user_id if approved else None,
                "approved_at": datetime.utcnow() if approved else None,
                "rejection_reason": rejection_reason if not approved else None,
            }
            
            updated_content = await self.db.update_content_item(content_id, updates)
            
            self.logger.info(
                "Content approval processed",
                content_id=content_id,
                user_id=user_id,
                approved=approved
            )
            
            return updated_content
            
        except Exception as e:
            self.logger.error(
                "Content approval failed",
                content_id=content_id,
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def delete_content_item(self, content_id: str, user_id: str) -> bool:
        """
        Delete a content item.
        
        Args:
            content_id: Content item ID
            user_id: User ID (for authorization)
            
        Returns:
            True if deleted successfully
        """
        try:
            # Verify content belongs to user
            content_item = await self.get_content_item(content_id, user_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            # Delete from database
            success = await self.db.delete_content_item(content_id)
            
            if success:
                self.logger.info(
                    "Content item deleted",
                    content_id=content_id,
                    user_id=user_id
                )
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Content deletion failed",
                content_id=content_id,
                user_id=user_id,
                error=str(e)
            )
            return False
    
    async def bulk_discover_content(self, user_ids: List[str]) -> Dict[str, int]:
        """
        Discover content for multiple users in batch.
        
        Args:
            user_ids: List of user IDs
            
        Returns:
            Dictionary mapping user_id to number of content items discovered
        """
        self.logger.info("Starting bulk content discovery", user_count=len(user_ids))
        
        results = {}
        
        # Process users in parallel (with concurrency limit)
        semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent discoveries
        
        async def discover_for_user(user_id: str) -> None:
            async with semaphore:
                try:
                    content_items = await self.discover_content_for_user(user_id)
                    results[user_id] = len(content_items)
                except Exception as e:
                    self.logger.error(
                        "Bulk discovery failed for user",
                        user_id=user_id,
                        error=str(e)
                    )
                    results[user_id] = 0
        
        # Execute discoveries in parallel
        await asyncio.gather(*[discover_for_user(user_id) for user_id in user_ids])
        
        total_discovered = sum(results.values())
        self.logger.info(
            "Bulk content discovery completed",
            user_count=len(user_ids),
            total_discovered=total_discovered
        )
        
        return results
    
    async def cleanup_old_content(self, days_old: int = 30) -> int:
        """
        Clean up old content items.
        
        Args:
            days_old: Delete content older than this many days
            
        Returns:
            Number of items cleaned up
        """
        try:
            cleanup_count = await self.db.cleanup_old_data(days=days_old)
            
            self.logger.info(
                "Content cleanup completed",
                days_old=days_old,
                cleanup_count=cleanup_count
            )
            
            return cleanup_count
            
        except Exception as e:
            self.logger.error("Content cleanup failed", error=str(e))
            return 0