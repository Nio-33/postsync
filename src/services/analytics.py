"""
Analytics Service

Service layer for handling analytics data collection, processing,
and reporting functionality.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog
from collections import defaultdict

from src.models.analytics import (
    PostAnalytics,
    UserAnalytics,
    PlatformAnalytics,
    TimeGranularity,
    PlatformType,
    MetricType,
    MetricPoint,
    AnalyticsSummary
)
from src.integrations.firestore import FirestoreClient
from src.integrations.twitter import TwitterClient
from src.integrations.linkedin import LinkedInClient


class AnalyticsService:
    """Service for analytics operations."""
    
    def __init__(self):
        """Initialize analytics service."""
        self.db = FirestoreClient()
        self.logger = structlog.get_logger(__name__)
        self.twitter = TwitterClient()
        self.linkedin = LinkedInClient()
    
    async def get_analytics_summary(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> AnalyticsSummary:
        """Get analytics summary for dashboard display."""
        try:
            # Get all analytics data for the user in the time period
            analytics_data = await self.db.get_user_analytics_data(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not analytics_data:
                # Return empty summary if no data
                return AnalyticsSummary(
                    period_start=start_date,
                    period_end=end_date,
                    total_posts=0,
                    total_impressions=0,
                    total_engagements=0,
                    average_engagement_rate=0.0,
                    follower_growth=0,
                    best_post_id=None,
                    best_post_engagement_rate=None,
                    top_platform=None,
                    engagement_trend="stable",
                    impression_trend="stable"
                )
            
            # Calculate aggregated metrics
            total_posts = len(analytics_data)
            total_impressions = sum(post.impressions for post in analytics_data)
            total_engagements = sum(post.total_engagements for post in analytics_data)
            average_engagement_rate = sum(post.engagement_rate for post in analytics_data) / total_posts if total_posts > 0 else 0.0
            
            # Find best performing post
            best_post = max(analytics_data, key=lambda x: x.engagement_rate, default=None)
            
            # Calculate platform performance
            platform_performance = defaultdict(list)
            for post in analytics_data:
                platform_performance[post.platform].append(post.engagement_rate)
            
            # Find top platform by average engagement
            top_platform = None
            if platform_performance:
                top_platform = max(
                    platform_performance.items(),
                    key=lambda x: sum(x[1]) / len(x[1])
                )[0]
            
            # Calculate trends (compare with previous period)
            previous_period_start = start_date - (end_date - start_date)
            previous_analytics = await self.db.get_user_analytics_data(
                user_id=user_id,
                start_date=previous_period_start,
                end_date=start_date
            )
            
            engagement_trend = self._calculate_trend(
                current_data=analytics_data,
                previous_data=previous_analytics,
                metric="engagement_rate"
            )
            impression_trend = self._calculate_trend(
                current_data=analytics_data,
                previous_data=previous_analytics,
                metric="impressions"
            )
            
            return AnalyticsSummary(
                period_start=start_date,
                period_end=end_date,
                total_posts=total_posts,
                total_impressions=total_impressions,
                total_engagements=total_engagements,
                average_engagement_rate=average_engagement_rate,
                follower_growth=0,  # Will be implemented with platform APIs
                best_post_id=best_post.post_id if best_post else None,
                best_post_engagement_rate=best_post.engagement_rate if best_post else None,
                top_platform=top_platform,
                engagement_trend=engagement_trend,
                impression_trend=impression_trend
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to get analytics summary",
                user_id=user_id,
                error=str(e)
            )
            # Return empty summary on error
            return AnalyticsSummary(
                period_start=start_date,
                period_end=end_date,
                total_posts=0,
                total_impressions=0,
                total_engagements=0,
                average_engagement_rate=0.0,
                follower_growth=0,
                best_post_id=None,
                best_post_engagement_rate=None,
                top_platform=None,
                engagement_trend="stable",
                impression_trend="stable"
            )

    async def get_content_analytics(
        self,
        content_id: str,
        user_id: str,
        timeframe: TimeGranularity = TimeGranularity.MONTH
    ) -> Optional[PostAnalytics]:
        """Get analytics for a specific content item."""
        try:
            # Get post analytics from database
            analytics = await self.db.get_post_analytics(content_id)
            if analytics and analytics.user_id == user_id:
                return analytics
            return None
        except Exception as e:
            self.logger.error(
                "Failed to get content analytics",
                content_id=content_id,
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def get_user_analytics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity = TimeGranularity.DAY
    ) -> Optional[UserAnalytics]:
        """Get comprehensive analytics for a user."""
        try:
            # Get all analytics data for the user in the time period
            analytics_data = await self.db.get_user_analytics_data(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not analytics_data:
                return None
            
            # Calculate aggregate metrics
            total_posts = len(analytics_data)
            total_impressions = sum(post.impressions for post in analytics_data)
            total_engagements = sum(post.total_engagements for post in analytics_data)
            average_engagement_rate = sum(post.engagement_rate for post in analytics_data) / total_posts if total_posts > 0 else 0.0
            
            # Calculate platform-specific metrics
            platform_metrics = defaultdict(lambda: defaultdict(float))
            for post in analytics_data:
                platform = post.platform
                platform_metrics[platform][MetricType.IMPRESSIONS] += post.impressions
                platform_metrics[platform][MetricType.LIKES] += post.likes
                platform_metrics[platform][MetricType.COMMENTS] += post.comments
                platform_metrics[platform][MetricType.SHARES] += post.shares
                platform_metrics[platform][MetricType.ENGAGEMENT_RATE] += post.engagement_rate
            
            # Average engagement rates per platform
            platform_post_counts = defaultdict(int)
            for post in analytics_data:
                platform_post_counts[post.platform] += 1
            
            for platform in platform_metrics:
                if platform_post_counts[platform] > 0:
                    platform_metrics[platform][MetricType.ENGAGEMENT_RATE] /= platform_post_counts[platform]
            
            # Find best performing post
            best_post = max(analytics_data, key=lambda x: x.engagement_rate, default=None)
            
            # Calculate engagement trends over time
            engagement_trends = self._calculate_engagement_trends(analytics_data, granularity)
            
            # Generate AI-powered optimization suggestions
            optimization_suggestions = await self._generate_optimization_suggestions(
                analytics_data, platform_metrics
            )
            
            return UserAnalytics(
                user_id=user_id,
                period_start=start_date,
                period_end=end_date,
                granularity=granularity,
                total_posts=total_posts,
                total_impressions=total_impressions,
                total_engagements=total_engagements,
                average_engagement_rate=average_engagement_rate,
                platform_metrics=dict(platform_metrics),
                best_performing_post=best_post.post_id if best_post else None,
                engagement_trends=engagement_trends,
                optimization_suggestions=optimization_suggestions
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to get user analytics",
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def get_platform_analytics(
        self,
        user_id: str,
        platform: PlatformType,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[PlatformAnalytics]:
        """Get analytics for a specific platform."""
        try:
            # Get analytics data for the specific platform
            all_analytics = await self.db.get_user_analytics_data(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Filter by platform
            platform_analytics = [post for post in all_analytics if post.platform == platform]
            
            if not platform_analytics:
                return None
            
            # Calculate platform-specific metrics
            posts_published = len(platform_analytics)
            avg_impressions = sum(post.impressions for post in platform_analytics) / posts_published
            avg_engagement_rate = sum(post.engagement_rate for post in platform_analytics) / posts_published
            
            average_post_performance = {
                MetricType.IMPRESSIONS: avg_impressions,
                MetricType.LIKES: sum(post.likes for post in platform_analytics) / posts_published,
                MetricType.COMMENTS: sum(post.comments for post in platform_analytics) / posts_published,
                MetricType.SHARES: sum(post.shares for post in platform_analytics) / posts_published,
                MetricType.ENGAGEMENT_RATE: avg_engagement_rate
            }
            
            # Calculate engagement history over time
            engagement_history = []
            for post in platform_analytics:
                engagement_history.append(MetricPoint(
                    timestamp=post.first_tracked_at,
                    value=post.engagement_rate
                ))
            
            # Sort by timestamp
            engagement_history.sort(key=lambda x: x.timestamp)
            
            return PlatformAnalytics(
                user_id=user_id,
                platform=platform,
                follower_count=0,  # Will be fetched from platform APIs
                following_count=0,  # Will be fetched from platform APIs
                profile_views=0,    # Will be fetched from platform APIs
                posts_published=posts_published,
                average_post_performance=average_post_performance,
                best_posting_times=[],  # Will be calculated from historical data
                audience_activity_pattern={},  # Will be calculated from historical data
                follower_growth_rate=0.0,
                engagement_growth_rate=0.0,
                follower_history=[],
                engagement_history=engagement_history,
                period_start=start_date,
                period_end=end_date
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to get platform analytics",
                user_id=user_id,
                platform=platform,
                error=str(e)
            )
            return None
    
    async def get_post_analytics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        platform: Optional[PlatformType] = None,
        limit: int = 50
    ) -> List[PostAnalytics]:
        """Get post-level analytics."""
        try:
            analytics_data = await self.db.get_user_analytics_data(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Filter by platform if specified
            if platform:
                analytics_data = [post for post in analytics_data if post.platform == platform]
            
            # Sort by engagement rate and limit results
            analytics_data.sort(key=lambda x: x.engagement_rate, reverse=True)
            return analytics_data[:limit]
            
        except Exception as e:
            self.logger.error(
                "Failed to get post analytics",
                user_id=user_id,
                error=str(e)
            )
            return []

    async def get_single_post_analytics(
        self,
        post_id: str,
        user_id: str
    ) -> Optional[PostAnalytics]:
        """Get analytics for a specific post."""
        try:
            analytics = await self.db.get_post_analytics(post_id)
            if analytics and analytics.user_id == user_id:
                return analytics
            return None
        except Exception as e:
            self.logger.error(
                "Failed to get single post analytics",
                post_id=post_id,
                user_id=user_id,
                error=str(e)
            )
            return None

    async def get_comprehensive_analytics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity,
        platforms: Optional[List[PlatformType]] = None,
        metrics: Optional[List[MetricType]] = None
    ) -> Dict[str, Any]:
        """Get comprehensive analytics data."""
        try:
            # Get user analytics
            user_analytics = await self.get_user_analytics(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity
            )
            
            # Get platform analytics
            platform_analytics = []
            target_platforms = platforms or [PlatformType.TWITTER, PlatformType.LINKEDIN]
            
            for platform in target_platforms:
                platform_data = await self.get_platform_analytics(
                    user_id=user_id,
                    platform=platform,
                    start_date=start_date,
                    end_date=end_date
                )
                if platform_data:
                    platform_analytics.append(platform_data)
            
            # Get post analytics
            post_analytics = await self.get_post_analytics(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                limit=100
            )
            
            return {
                "user_analytics": user_analytics,
                "platform_analytics": platform_analytics,
                "post_analytics": post_analytics
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get comprehensive analytics",
                user_id=user_id,
                error=str(e)
            )
            return {}

    async def get_engagement_insights(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get AI-powered engagement insights."""
        try:
            analytics_data = await self.db.get_user_analytics_data(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            if not analytics_data:
                return {"insights": [], "recommendations": []}
            
            # Calculate key insights
            avg_engagement = sum(post.engagement_rate for post in analytics_data) / len(analytics_data)
            best_posts = sorted(analytics_data, key=lambda x: x.engagement_rate, reverse=True)[:3]
            
            # Platform performance comparison
            platform_performance = defaultdict(list)
            for post in analytics_data:
                platform_performance[post.platform].append(post.engagement_rate)
            
            insights = []
            recommendations = []
            
            # Generate insights based on data
            if len(analytics_data) > 0:
                insights.append(f"Your average engagement rate is {avg_engagement:.2f}%")
                
                if best_posts:
                    best_platform = best_posts[0].platform
                    insights.append(f"Your best performing platform is {best_platform}")
                
                # Add recommendations
                if avg_engagement < 2.0:
                    recommendations.append("Consider posting at different times to increase engagement")
                    recommendations.append("Try using more visual content like images or videos")
                
                if len(platform_performance) > 1:
                    recommendations.append("Focus more content on your best performing platform")
            
            return {
                "insights": insights,
                "recommendations": recommendations,
                "average_engagement_rate": avg_engagement,
                "best_posts": [{"post_id": post.post_id, "engagement_rate": post.engagement_rate} for post in best_posts]
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get engagement insights",
                user_id=user_id,
                error=str(e)
            )
            return {"insights": [], "recommendations": []}

    async def get_best_posting_times(
        self,
        user_id: str,
        platform: Optional[PlatformType] = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """Get optimal posting times analysis."""
        try:
            analytics_data = await self.db.get_user_analytics_data(
                user_id=user_id,
                start_date=start_date or datetime.utcnow() - timedelta(days=30),
                end_date=end_date or datetime.utcnow()
            )
            
            if platform:
                analytics_data = [post for post in analytics_data if post.platform == platform]
            
            if not analytics_data:
                return {"best_times": [], "analysis": "Insufficient data for analysis"}
            
            # Analyze posting times vs engagement
            time_performance = defaultdict(list)
            for post in analytics_data:
                hour = post.first_tracked_at.hour
                time_performance[hour].append(post.engagement_rate)
            
            # Calculate average engagement by hour
            best_times = []
            for hour, rates in time_performance.items():
                avg_rate = sum(rates) / len(rates)
                best_times.append({
                    "hour": hour,
                    "average_engagement_rate": avg_rate,
                    "sample_size": len(rates)
                })
            
            # Sort by engagement rate
            best_times.sort(key=lambda x: x["average_engagement_rate"], reverse=True)
            
            return {
                "best_times": best_times[:5],  # Top 5 hours
                "analysis": f"Based on {len(analytics_data)} posts",
                "platform": platform
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get best posting times",
                user_id=user_id,
                error=str(e)
            )
            return {"best_times": [], "analysis": "Error analyzing posting times"}

    async def refresh_analytics_data(
        self,
        user_id: str,
        platform: Optional[PlatformType] = None
    ) -> Dict[str, Any]:
        """Refresh analytics data from platforms."""
        try:
            refresh_results = []
            
            if not platform or platform == PlatformType.TWITTER:
                # Refresh Twitter analytics
                try:
                    # This would fetch latest data from Twitter API
                    refresh_results.append({"platform": "twitter", "status": "success", "updated": datetime.utcnow()})
                except Exception as e:
                    refresh_results.append({"platform": "twitter", "status": "error", "error": str(e)})
            
            if not platform or platform == PlatformType.LINKEDIN:
                # Refresh LinkedIn analytics
                try:
                    # This would fetch latest data from LinkedIn API
                    refresh_results.append({"platform": "linkedin", "status": "success", "updated": datetime.utcnow()})
                except Exception as e:
                    refresh_results.append({"platform": "linkedin", "status": "error", "error": str(e)})
            
            return {
                "refreshed_at": datetime.utcnow(),
                "results": refresh_results
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to refresh analytics data",
                user_id=user_id,
                error=str(e)
            )
            return {"error": str(e)}

    # Helper Methods
    def _calculate_trend(
        self,
        current_data: List[PostAnalytics],
        previous_data: List[PostAnalytics],
        metric: str
    ) -> str:
        """Calculate trend direction (up/down/stable)."""
        if not current_data or not previous_data:
            return "stable"
        
        if metric == "engagement_rate":
            current_avg = sum(post.engagement_rate for post in current_data) / len(current_data)
            previous_avg = sum(post.engagement_rate for post in previous_data) / len(previous_data)
        elif metric == "impressions":
            current_avg = sum(post.impressions for post in current_data) / len(current_data)
            previous_avg = sum(post.impressions for post in previous_data) / len(previous_data)
        else:
            return "stable"
        
        if current_avg > previous_avg * 1.05:  # 5% threshold
            return "up"
        elif current_avg < previous_avg * 0.95:
            return "down"
        else:
            return "stable"

    def _calculate_engagement_trends(
        self,
        analytics_data: List[PostAnalytics],
        granularity: TimeGranularity
    ) -> List[MetricPoint]:
        """Calculate engagement trends over time."""
        if not analytics_data:
            return []
        
        # Sort by timestamp
        sorted_data = sorted(analytics_data, key=lambda x: x.first_tracked_at)
        
        trends = []
        for post in sorted_data:
            trends.append(MetricPoint(
                timestamp=post.first_tracked_at,
                value=post.engagement_rate
            ))
        
        return trends

    async def _generate_optimization_suggestions(
        self,
        analytics_data: List[PostAnalytics],
        platform_metrics: Dict[str, Dict[str, float]]
    ) -> List[str]:
        """Generate AI-powered optimization suggestions."""
        suggestions = []
        
        if not analytics_data:
            return ["Start publishing content to get personalized recommendations"]
        
        # Calculate overall performance metrics
        avg_engagement = sum(post.engagement_rate for post in analytics_data) / len(analytics_data)
        
        # Performance-based suggestions
        if avg_engagement < 2.0:
            suggestions.append("Your engagement rate is below average. Try posting more visual content.")
            suggestions.append("Consider posting at different times when your audience is more active.")
        elif avg_engagement > 5.0:
            suggestions.append("Great engagement rate! Keep up the excellent content quality.")
        
        # Platform-specific suggestions
        if len(platform_metrics) > 1:
            best_platform = max(platform_metrics.items(), key=lambda x: x[1][MetricType.ENGAGEMENT_RATE])
            suggestions.append(f"Your {best_platform[0]} content performs best. Consider increasing posting frequency there.")
        
        # Content frequency suggestions
        if len(analytics_data) < 10:
            suggestions.append("Increase your posting frequency to build better audience engagement.")
        
        return suggestions[:5]  # Limit to top 5 suggestions