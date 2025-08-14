"""
Publishing Service

This service handles publishing content to social media platforms
and managing the publishing workflow.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import structlog

from src.integrations.firestore import firestore_client
from src.integrations.linkedin import linkedin_client
from src.integrations.twitter import twitter_client
from src.models.content import ContentItem, ContentStatus, GeneratedPost, PlatformType, PublishingResult
from src.models.user import SocialMediaAccount


class PublishingService:
    """Service for publishing content to social media platforms."""
    
    def __init__(self):
        """Initialize publishing service."""
        self.logger = structlog.get_logger(__name__)
        self.linkedin = linkedin_client
        self.twitter = twitter_client
        self.db = firestore_client
    
    async def publish_content(
        self,
        content_id: str,
        user_id: str,
        platforms: List[PlatformType]
    ) -> ContentItem:
        """
        Publish content immediately to specified platforms.
        
        Args:
            content_id: Content item ID
            user_id: User ID
            platforms: Platforms to publish to
            
        Returns:
            Updated ContentItem with publishing results
        """
        self.logger.info(
            "Starting content publishing",
            content_id=content_id,
            user_id=user_id,
            platforms=platforms
        )
        
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            if content_item.user_id != user_id:
                raise ValueError("Content item does not belong to user")
            
            # Check if content is ready for publishing
            if content_item.status not in [ContentStatus.APPROVED, ContentStatus.SCHEDULED]:
                raise ValueError(f"Content cannot be published in status: {content_item.status}")
            
            # Get user's social media accounts
            user = await self.db.get_user(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Publish to each platform
            publishing_results = {}
            for platform in platforms:
                try:
                    result = await self._publish_to_platform(
                        content_item=content_item,
                        platform=platform,
                        user_account=user.social_accounts.get(platform)
                    )
                    publishing_results[platform] = result
                    
                except Exception as e:
                    self.logger.error(
                        "Platform publishing failed",
                        content_id=content_id,
                        platform=platform,
                        error=str(e)
                    )
                    # Create failed result
                    publishing_results[platform] = PublishingResult(
                        platform=platform,
                        success=False,
                        error_message=str(e)
                    )
            
            # Update content item with results
            updates = {
                "publishing_results": {
                    platform.value: result.dict() for platform, result in publishing_results.items()
                },
                "status": ContentStatus.PUBLISHED,
            }
            
            updated_content = await self.db.update_content_item(content_id, updates)
            
            successful_platforms = [p for p, r in publishing_results.items() if r.success]
            self.logger.info(
                "Content publishing completed",
                content_id=content_id,
                successful_platforms=len(successful_platforms),
                total_platforms=len(platforms)
            )
            
            return updated_content
            
        except Exception as e:
            self.logger.error(
                "Content publishing failed",
                content_id=content_id,
                user_id=user_id,
                error=str(e)
            )
            
            # Update status to failed
            await self.db.update_content_item(content_id, {"status": ContentStatus.FAILED})
            raise
    
    async def _publish_to_platform(
        self,
        content_item: ContentItem,
        platform: PlatformType,
        user_account: Optional[SocialMediaAccount]
    ) -> PublishingResult:
        """Publish content to a specific platform."""
        if not user_account or not user_account.is_active:
            return PublishingResult(
                platform=platform,
                success=False,
                error_message=f"No active {platform.value} account connected"
            )
        
        # Get generated post for platform
        if platform.value not in content_item.generated_posts:
            return PublishingResult(
                platform=platform,
                success=False,
                error_message=f"No generated post found for {platform.value}"
            )
        
        post_data = content_item.generated_posts[platform.value]
        generated_post = GeneratedPost(**post_data)
        
        # Publish based on platform
        if platform == PlatformType.LINKEDIN:
            return await self.linkedin.publish_post(
                access_token=user_account.access_token,
                generated_post=generated_post,
                user_id=user_account.account_id
            )
        elif platform == PlatformType.TWITTER:
            return await self.twitter.publish_post(
                access_token=user_account.access_token,
                generated_post=generated_post,
                user_id=user_account.account_id
            )
        else:
            return PublishingResult(
                platform=platform,
                success=False,
                error_message=f"Platform {platform.value} not supported yet"
            )
    
    async def schedule_content(
        self,
        content_id: str,
        user_id: str,
        scheduled_for: datetime,
        platforms: List[PlatformType]
    ) -> ContentItem:
        """
        Schedule content for future publishing.
        
        Args:
            content_id: Content item ID
            user_id: User ID
            scheduled_for: When to publish the content
            platforms: Platforms to publish to
            
        Returns:
            Updated ContentItem with scheduling info
        """
        self.logger.info(
            "Scheduling content",
            content_id=content_id,
            user_id=user_id,
            scheduled_for=scheduled_for,
            platforms=platforms
        )
        
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            if content_item.user_id != user_id:
                raise ValueError("Content item does not belong to user")
            
            # Check if content is ready for scheduling
            if content_item.status not in [ContentStatus.APPROVED, ContentStatus.GENERATED]:
                raise ValueError(f"Content cannot be scheduled in status: {content_item.status}")
            
            # Validate scheduled time is in the future
            if scheduled_for <= datetime.utcnow():
                raise ValueError("Scheduled time must be in the future")
            
            # Update content item with scheduling info
            updates = {
                "scheduled_for": scheduled_for,
                "status": ContentStatus.SCHEDULED,
            }
            
            # Store which platforms to publish to (in metadata)
            updates["scheduled_platforms"] = [platform.value for platform in platforms]
            
            updated_content = await self.db.update_content_item(content_id, updates)
            
            self.logger.info(
                "Content scheduled successfully",
                content_id=content_id,
                scheduled_for=scheduled_for
            )
            
            return updated_content
            
        except Exception as e:
            self.logger.error(
                "Content scheduling failed",
                content_id=content_id,
                error=str(e)
            )
            raise
    
    async def process_scheduled_content(self) -> Dict[str, int]:
        """
        Process content that is scheduled for publishing.
        
        Returns:
            Dictionary with processing statistics
        """
        self.logger.info("Processing scheduled content")
        
        try:
            # Get content scheduled for now or earlier
            current_time = datetime.utcnow()
            
            # This would need a proper query in Firestore
            # For now, simplified implementation
            scheduled_content = await self._get_scheduled_content(current_time)
            
            results = {
                "processed": 0,
                "successful": 0,
                "failed": 0
            }
            
            for content_item in scheduled_content:
                try:
                    results["processed"] += 1
                    
                    # Get scheduled platforms
                    platforms = []
                    if hasattr(content_item, 'scheduled_platforms'):
                        platforms = [PlatformType(p) for p in content_item.scheduled_platforms]
                    
                    if not platforms:
                        # Default to all platforms with generated posts
                        platforms = [PlatformType(p) for p in content_item.generated_posts.keys()]
                    
                    # Publish the content
                    await self.publish_content(
                        content_id=content_item.id,
                        user_id=content_item.user_id,
                        platforms=platforms
                    )
                    
                    results["successful"] += 1
                    
                except Exception as e:
                    self.logger.error(
                        "Scheduled content processing failed",
                        content_id=content_item.id,
                        error=str(e)
                    )
                    results["failed"] += 1
            
            self.logger.info(
                "Scheduled content processing completed",
                **results
            )
            
            return results
            
        except Exception as e:
            self.logger.error("Scheduled content processing failed", error=str(e))
            return {"processed": 0, "successful": 0, "failed": 0}
    
    async def _get_scheduled_content(self, current_time: datetime) -> List[ContentItem]:
        """Get content items that are scheduled for the current time or earlier."""
        # This would be a proper Firestore query in production
        # For now, return empty list as placeholder
        return []
    
    async def cancel_scheduled_content(self, content_id: str, user_id: str) -> ContentItem:
        """
        Cancel scheduled content publishing.
        
        Args:
            content_id: Content item ID
            user_id: User ID
            
        Returns:
            Updated ContentItem
        """
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            if content_item.user_id != user_id:
                raise ValueError("Content item does not belong to user")
            
            # Check if content is scheduled
            if content_item.status != ContentStatus.SCHEDULED:
                raise ValueError("Content is not scheduled")
            
            # Update content item
            updates = {
                "scheduled_for": None,
                "status": ContentStatus.APPROVED,
            }
            
            # Remove scheduled platforms
            if hasattr(content_item, 'scheduled_platforms'):
                updates["scheduled_platforms"] = None
            
            updated_content = await self.db.update_content_item(content_id, updates)
            
            self.logger.info(
                "Scheduled content cancelled",
                content_id=content_id,
                user_id=user_id
            )
            
            return updated_content
            
        except Exception as e:
            self.logger.error(
                "Content schedule cancellation failed",
                content_id=content_id,
                error=str(e)
            )
            raise
    
    async def retry_failed_publishing(self, content_id: str, user_id: str) -> ContentItem:
        """
        Retry publishing for content that failed.
        
        Args:
            content_id: Content item ID
            user_id: User ID
            
        Returns:
            Updated ContentItem
        """
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            if content_item.user_id != user_id:
                raise ValueError("Content item does not belong to user")
            
            # Check for failed publishing results
            failed_platforms = []
            if content_item.publishing_results:
                for platform_str, result_data in content_item.publishing_results.items():
                    result = PublishingResult(**result_data)
                    if not result.success:
                        failed_platforms.append(PlatformType(platform_str))
            
            if not failed_platforms:
                raise ValueError("No failed publishing attempts found")
            
            # Retry publishing to failed platforms
            updated_content = await self.publish_content(
                content_id=content_id,
                user_id=user_id,
                platforms=failed_platforms
            )
            
            self.logger.info(
                "Publishing retry completed",
                content_id=content_id,
                retry_platforms=len(failed_platforms)
            )
            
            return updated_content
            
        except Exception as e:
            self.logger.error(
                "Publishing retry failed",
                content_id=content_id,
                error=str(e)
            )
            raise
    
    async def get_publishing_status(self, content_id: str, user_id: str) -> Dict[str, any]:
        """
        Get detailed publishing status for content.
        
        Args:
            content_id: Content item ID
            user_id: User ID
            
        Returns:
            Publishing status information
        """
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            if content_item.user_id != user_id:
                raise ValueError("Content item does not belong to user")
            
            status_info = {
                "content_id": content_id,
                "status": content_item.status.value,
                "scheduled_for": content_item.scheduled_for.isoformat() if content_item.scheduled_for else None,
                "platforms": {}
            }
            
            # Add platform-specific status
            if content_item.publishing_results:
                for platform_str, result_data in content_item.publishing_results.items():
                    result = PublishingResult(**result_data)
                    status_info["platforms"][platform_str] = {
                        "success": result.success,
                        "published_at": result.published_at.isoformat() if result.published_at else None,
                        "post_url": str(result.post_url) if result.post_url else None,
                        "error_message": result.error_message
                    }
            
            return status_info
            
        except Exception as e:
            self.logger.error(
                "Failed to get publishing status",
                content_id=content_id,
                error=str(e)
            )
            return {}
    
    async def bulk_publish_content(
        self,
        content_ids: List[str],
        user_id: str,
        platforms: List[PlatformType]
    ) -> Dict[str, bool]:
        """
        Publish multiple content items in batch.
        
        Args:
            content_ids: List of content item IDs
            user_id: User ID
            platforms: Platforms to publish to
            
        Returns:
            Dictionary mapping content_id to success status
        """
        self.logger.info(
            "Starting bulk content publishing",
            content_count=len(content_ids),
            user_id=user_id,
            platforms=platforms
        )
        
        results = {}
        
        # Process content items with concurrency limit
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent publications
        
        async def publish_content_item(content_id: str) -> None:
            async with semaphore:
                try:
                    await self.publish_content(
                        content_id=content_id,
                        user_id=user_id,
                        platforms=platforms
                    )
                    results[content_id] = True
                except Exception as e:
                    self.logger.error(
                        "Bulk publishing failed for content",
                        content_id=content_id,
                        error=str(e)
                    )
                    results[content_id] = False
        
        # Execute publications in parallel
        await asyncio.gather(*[publish_content_item(content_id) for content_id in content_ids])
        
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(
            "Bulk content publishing completed",
            content_count=len(content_ids),
            successful_count=successful_count
        )
        
        return results