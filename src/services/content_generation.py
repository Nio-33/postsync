"""
Content Generation Service

This service handles AI-powered content generation from source content
using Gemini AI and content optimization features.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import structlog

from src.ai.content_optimizer import content_optimizer
from src.ai.gemini import gemini_client
from src.integrations.firestore import firestore_client
from src.models.content import ContentItem, ContentStatus, GeneratedPost, PlatformType
from src.models.user import ContentPreferences


class ContentGenerationService:
    """Service for AI-powered content generation and optimization."""
    
    def __init__(self):
        """Initialize content generation service."""
        self.logger = structlog.get_logger(__name__)
        self.gemini = gemini_client
        self.optimizer = content_optimizer
        self.db = firestore_client
    
    async def generate_posts(
        self,
        content_id: str,
        platforms: List[PlatformType],
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> ContentItem:
        """
        Generate social media posts for a content item.
        
        Args:
            content_id: Content item ID
            platforms: Target platforms for generation
            user_preferences: User's content preferences
            custom_instructions: Optional custom generation instructions
            
        Returns:
            Updated ContentItem with generated posts
        """
        self.logger.info(
            "Starting content generation",
            content_id=content_id,
            platforms=platforms
        )
        
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            # Check if content is in correct state for generation
            if content_item.status not in [ContentStatus.DISCOVERED, ContentStatus.ANALYZED]:
                raise ValueError(f"Content cannot be generated in status: {content_item.status}")
            
            # Generate posts using Gemini AI
            generated_posts = await self.gemini.generate_posts(
                source_content=content_item.source_content,
                platforms=platforms,
                user_preferences=user_preferences,
                custom_instructions=custom_instructions
            )
            
            if not generated_posts:
                raise Exception("No posts were generated")
            
            # Optimize generated posts
            optimized_posts = await self._optimize_generated_posts(
                generated_posts=generated_posts,
                source_content=content_item.source_content,
                user_preferences=user_preferences
            )
            
            # Update content item with generated posts
            updates = {
                "generated_posts": {
                    platform.value: post.dict() for platform, post in optimized_posts.items()
                },
                "status": ContentStatus.GENERATED,
            }
            
            updated_content = await self.db.update_content_item(content_id, updates)
            
            self.logger.info(
                "Content generation completed",
                content_id=content_id,
                platforms_generated=len(optimized_posts)
            )
            
            return updated_content
            
        except Exception as e:
            self.logger.error(
                "Content generation failed",
                content_id=content_id,
                error=str(e)
            )
            
            # Update status to failed
            await self.db.update_content_item(content_id, {"status": ContentStatus.FAILED})
            raise
    
    async def _optimize_generated_posts(
        self,
        generated_posts: Dict[PlatformType, GeneratedPost],
        source_content,
        user_preferences: ContentPreferences
    ) -> Dict[PlatformType, GeneratedPost]:
        """Optimize generated posts for quality and performance."""
        optimized_posts = {}
        
        for platform, post in generated_posts.items():
            try:
                # Score content quality
                quality_scores = await self.optimizer.score_content_quality(
                    generated_post=post,
                    source_content=source_content,
                    user_preferences=user_preferences
                )
                
                # Update post with quality scores
                post.relevance_score = quality_scores.get("relevance", post.relevance_score)
                post.engagement_prediction = quality_scores.get("engagement_potential", post.engagement_prediction)
                post.fact_check_score = quality_scores.get("factual_accuracy", post.fact_check_score)
                
                # Optimize hashtags if needed
                if len(post.hashtags) == 0 or quality_scores.get("overall", 0) < 0.7:
                    optimized_hashtags = await self.gemini.optimize_hashtags(
                        content=post.content,
                        topics=source_content.topics,
                        platform=platform,
                        max_hashtags=5 if platform == PlatformType.LINKEDIN else 2
                    )
                    post.hashtags = optimized_hashtags
                
                optimized_posts[platform] = post
                
            except Exception as e:
                self.logger.error(
                    "Post optimization failed",
                    platform=platform,
                    error=str(e)
                )
                # Keep original post if optimization fails
                optimized_posts[platform] = post
        
        return optimized_posts
    
    async def regenerate_post(
        self,
        content_id: str,
        platform: PlatformType,
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> Optional[GeneratedPost]:
        """
        Regenerate a specific post for a platform.
        
        Args:
            content_id: Content item ID
            platform: Platform to regenerate for
            user_preferences: User's content preferences
            custom_instructions: Optional custom instructions
            
        Returns:
            New GeneratedPost or None if failed
        """
        self.logger.info(
            "Regenerating post",
            content_id=content_id,
            platform=platform
        )
        
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            # Generate new post
            generated_posts = await self.gemini.generate_posts(
                source_content=content_item.source_content,
                platforms=[platform],
                user_preferences=user_preferences,
                custom_instructions=custom_instructions
            )
            
            if platform not in generated_posts:
                return None
            
            new_post = generated_posts[platform]
            
            # Optimize the new post
            optimized_posts = await self._optimize_generated_posts(
                generated_posts={platform: new_post},
                source_content=content_item.source_content,
                user_preferences=user_preferences
            )
            
            optimized_post = optimized_posts.get(platform, new_post)
            
            # Update content item with new post
            updates = {
                f"generated_posts.{platform.value}": optimized_post.dict(),
                "status": ContentStatus.GENERATED,
            }
            
            await self.db.update_content_item(content_id, updates)
            
            self.logger.info(
                "Post regeneration completed",
                content_id=content_id,
                platform=platform
            )
            
            return optimized_post
            
        except Exception as e:
            self.logger.error(
                "Post regeneration failed",
                content_id=content_id,
                platform=platform,
                error=str(e)
            )
            return None
    
    async def create_content_variations(
        self,
        content_id: str,
        platform: PlatformType,
        variation_count: int = 2,
        user_preferences: Optional[ContentPreferences] = None
    ) -> List[GeneratedPost]:
        """
        Create multiple variations of content for A/B testing.
        
        Args:
            content_id: Content item ID
            platform: Platform to generate for
            variation_count: Number of variations to create
            user_preferences: User's content preferences
            
        Returns:
            List of content variations
        """
        self.logger.info(
            "Creating content variations",
            content_id=content_id,
            platform=platform,
            variation_count=variation_count
        )
        
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            # Get user preferences if not provided
            if not user_preferences:
                user = await self.db.get_user(content_item.user_id)
                user_preferences = user.content_preferences if user else ContentPreferences()
            
            variations = []
            
            # Create variations with different approaches
            variation_strategies = ["tone", "structure", "hook", "cta"]
            
            for i in range(variation_count):
                strategy = variation_strategies[i % len(variation_strategies)]
                
                # Modify instructions for variation
                variation_instructions = f"Create a variation with different {strategy} approach"
                
                generated_posts = await self.gemini.generate_posts(
                    source_content=content_item.source_content,
                    platforms=[platform],
                    user_preferences=user_preferences,
                    custom_instructions=variation_instructions
                )
                
                if platform in generated_posts:
                    post = generated_posts[platform]
                    
                    # Optimize the variation
                    optimized_posts = await self._optimize_generated_posts(
                        generated_posts={platform: post},
                        source_content=content_item.source_content,
                        user_preferences=user_preferences
                    )
                    
                    variations.append(optimized_posts.get(platform, post))
            
            self.logger.info(
                "Content variations created",
                content_id=content_id,
                platform=platform,
                variations_created=len(variations)
            )
            
            return variations
            
        except Exception as e:
            self.logger.error(
                "Content variation creation failed",
                content_id=content_id,
                platform=platform,
                error=str(e)
            )
            return []
    
    async def analyze_content_quality(
        self,
        content_id: str,
        platform: PlatformType,
        user_preferences: ContentPreferences
    ) -> Dict[str, any]:
        """
        Analyze the quality of generated content.
        
        Args:
            content_id: Content item ID
            platform: Platform to analyze
            user_preferences: User's content preferences
            
        Returns:
            Quality analysis results
        """
        try:
            # Get content item
            content_item = await self.db.get_content_item(content_id)
            if not content_item:
                raise ValueError("Content item not found")
            
            # Get generated post for platform
            if platform.value not in content_item.generated_posts:
                raise ValueError(f"No generated post found for {platform.value}")
            
            post_data = content_item.generated_posts[platform.value]
            generated_post = GeneratedPost(**post_data)
            
            # Score content quality
            quality_scores = await self.optimizer.score_content_quality(
                generated_post=generated_post,
                source_content=content_item.source_content,
                user_preferences=user_preferences
            )
            
            # Get improvement suggestions
            suggestions = await self.optimizer.suggest_improvements(
                generated_post=generated_post,
                quality_scores=quality_scores,
                user_preferences=user_preferences
            )
            
            analysis = {
                "content_id": content_id,
                "platform": platform.value,
                "quality_scores": quality_scores,
                "improvement_suggestions": suggestions,
                "overall_rating": self._calculate_overall_rating(quality_scores),
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(
                "Content quality analysis failed",
                content_id=content_id,
                platform=platform,
                error=str(e)
            )
            return {}
    
    def _calculate_overall_rating(self, quality_scores: Dict[str, float]) -> str:
        """Calculate overall content rating from quality scores."""
        overall_score = quality_scores.get("overall", 0)
        
        if overall_score >= 0.8:
            return "excellent"
        elif overall_score >= 0.7:
            return "good"
        elif overall_score >= 0.6:
            return "fair"
        else:
            return "needs_improvement"
    
    async def get_content_item(self, content_id: str, user_id: str) -> Optional[ContentItem]:
        """
        Get content item by ID with user authorization.
        
        Args:
            content_id: Content item ID
            user_id: User ID for authorization
            
        Returns:
            ContentItem if found and authorized
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
    
    async def batch_generate_content(
        self,
        content_ids: List[str],
        platforms: List[PlatformType],
        user_preferences: ContentPreferences
    ) -> Dict[str, bool]:
        """
        Generate content for multiple content items in batch.
        
        Args:
            content_ids: List of content item IDs
            platforms: Target platforms
            user_preferences: User's content preferences
            
        Returns:
            Dictionary mapping content_id to success status
        """
        self.logger.info(
            "Starting batch content generation",
            content_count=len(content_ids),
            platforms=platforms
        )
        
        results = {}
        
        # Process content items with concurrency limit
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent generations
        
        async def generate_for_content(content_id: str) -> None:
            async with semaphore:
                try:
                    await self.generate_posts(
                        content_id=content_id,
                        platforms=platforms,
                        user_preferences=user_preferences
                    )
                    results[content_id] = True
                except Exception as e:
                    self.logger.error(
                        "Batch generation failed for content",
                        content_id=content_id,
                        error=str(e)
                    )
                    results[content_id] = False
        
        # Execute generations in parallel
        await asyncio.gather(*[generate_for_content(content_id) for content_id in content_ids])
        
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(
            "Batch content generation completed",
            content_count=len(content_ids),
            successful_count=successful_count
        )
        
        return results
    
    async def generate_direct_content(
        self,
        user_id: str,
        platforms: List[PlatformType],
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> ContentItem:
        """
        Generate content directly using AI without existing source content.
        
        Args:
            user_id: User ID
            platforms: Target platforms for generation
            user_preferences: User's content preferences
            custom_instructions: Optional custom generation instructions
            
        Returns:
            New ContentItem with generated posts
        """
        self.logger.info(
            "Starting direct content generation",
            user_id=user_id,
            platforms=platforms
        )
        
        try:
            # Create a new content item
            content_id = f"direct_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
            
            # Generate content using AI with custom prompt for direct generation
            ai_prompt = self._build_direct_generation_prompt(
                platforms=platforms,
                user_preferences=user_preferences,
                custom_instructions=custom_instructions
            )
            
            # Generate posts for each platform
            generated_posts = {}
            for platform in platforms:
                platform_prompt = f"{ai_prompt}\n\nCreate content optimized for {platform.value}."
                
                response = await self.gemini.generate_content(platform_prompt)
                
                generated_posts[platform] = GeneratedPost(
                    platform=platform,
                    text=response.get('text', ''),
                    hashtags=response.get('hashtags', []),
                    mentions=response.get('mentions', []),
                    media_urls=response.get('media_urls', []),
                    call_to_action=response.get('call_to_action'),
                    generated_at=datetime.now()
                )
            
            # Create content item
            content_item = ContentItem(
                id=content_id,
                user_id=user_id,
                title="AI Generated Content",
                source_content="Direct AI generation",
                source_url="",
                source_type="ai_generated",
                topic=user_preferences.preferred_topics[0] if user_preferences.preferred_topics else "technology",
                platforms=platforms,
                generated_posts=generated_posts,
                status=ContentStatus.GENERATED,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store in database
            await self.db.create_content_item(content_item.dict())
            
            self.logger.info(
                "Direct content generation completed",
                user_id=user_id,
                content_id=content_id
            )
            
            return content_item
            
        except Exception as e:
            self.logger.error(
                "Direct content generation failed",
                user_id=user_id,
                error=str(e)
            )
            raise
    
    def _build_direct_generation_prompt(
        self,
        platforms: List[PlatformType],
        user_preferences: ContentPreferences,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build AI prompt for direct content generation."""
        prompt_parts = [
            "Generate engaging social media content for AI professionals and tech enthusiasts.",
            f"Target platforms: {', '.join([p.value for p in platforms])}",
        ]
        
        if user_preferences.preferred_topics:
            prompt_parts.append(f"Focus on topics: {', '.join(user_preferences.preferred_topics)}")
        
        if user_preferences.tone:
            prompt_parts.append(f"Use a {user_preferences.tone} tone")
        
        if custom_instructions:
            prompt_parts.append(f"Additional instructions: {custom_instructions}")
        
        prompt_parts.extend([
            "Create original, valuable content that would interest AI and tech professionals.",
            "Include relevant hashtags and engaging call-to-action.",
            "Make it informative and actionable."
        ])
        
        return "\n".join(prompt_parts)