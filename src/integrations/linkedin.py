"""
LinkedIn API Integration

This module handles LinkedIn API interactions for posting content
and retrieving analytics data.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
import structlog
from linkedin_api import Linkedin

from src.config.settings import get_settings
from src.models.content import GeneratedPost, PlatformType, PublishingResult


class LinkedInClient:
    """LinkedIn API client for content publishing and analytics."""
    
    def __init__(self):
        """Initialize LinkedIn client."""
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # LinkedIn API endpoints
        self.base_url = "https://api.linkedin.com/v2"
        self.posts_endpoint = f"{self.base_url}/ugcPosts"
        self.people_endpoint = f"{self.base_url}/people"
        self.shares_endpoint = f"{self.base_url}/shares"
        
        # Rate limiting
        self.rate_limit = self.settings.linkedin_rate_limit_requests_per_minute
    
    async def authenticate_user(self, authorization_code: str, redirect_uri: str) -> Dict:
        """
        Exchange authorization code for access token.
        
        Args:
            authorization_code: OAuth authorization code from LinkedIn
            redirect_uri: Redirect URI used in OAuth flow
            
        Returns:
            Dictionary containing access token and user info
        """
        self.logger.info("Authenticating LinkedIn user")
        
        try:
            # Exchange authorization code for access token
            token_data = await self._exchange_code_for_token(
                authorization_code, redirect_uri
            )
            
            # Get user profile information
            user_info = await self._get_user_profile(token_data["access_token"])
            
            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data["expires_in"],
                "user_info": user_info,
            }
            
        except Exception as e:
            self.logger.error("LinkedIn authentication failed", error=str(e))
            raise
    
    async def _exchange_code_for_token(
        self, authorization_code: str, redirect_uri: str
    ) -> Dict:
        """Exchange authorization code for access token."""
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": self.settings.linkedin_client_id,
            "client_secret": self.settings.linkedin_client_secret,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def _get_user_profile(self, access_token: str) -> Dict:
        """Get user profile information."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.people_endpoint}/(id~)",
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def publish_post(
        self,
        access_token: str,
        generated_post: GeneratedPost,
        user_id: str
    ) -> PublishingResult:
        """
        Publish a post to LinkedIn.
        
        Args:
            access_token: User's LinkedIn access token
            generated_post: Generated post content
            user_id: LinkedIn user ID
            
        Returns:
            PublishingResult with publishing status and details
        """
        self.logger.info("Publishing post to LinkedIn", user_id=user_id)
        
        try:
            # Prepare post data
            post_data = self._prepare_post_data(generated_post, user_id)
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.posts_endpoint,
                    json=post_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    # Extract post ID from response
                    post_id = self._extract_post_id(response.headers)
                    post_url = f"https://www.linkedin.com/feed/update/{post_id}"
                    
                    self.logger.info(
                        "LinkedIn post published successfully",
                        user_id=user_id,
                        post_id=post_id
                    )
                    
                    return PublishingResult(
                        platform=PlatformType.LINKEDIN,
                        post_id=post_id,
                        post_url=post_url,
                        success=True,
                        published_at=datetime.utcnow(),
                    )
                else:
                    error_message = f"LinkedIn API error: {response.status_code}"
                    self.logger.error(
                        "LinkedIn post publishing failed",
                        user_id=user_id,
                        status_code=response.status_code,
                        response=response.text
                    )
                    
                    return PublishingResult(
                        platform=PlatformType.LINKEDIN,
                        success=False,
                        error_message=error_message,
                    )
                    
        except Exception as e:
            self.logger.error(
                "LinkedIn post publishing error",
                user_id=user_id,
                error=str(e)
            )
            
            return PublishingResult(
                platform=PlatformType.LINKEDIN,
                success=False,
                error_message=str(e),
            )
    
    def _prepare_post_data(self, generated_post: GeneratedPost, user_id: str) -> Dict:
        """Prepare post data for LinkedIn API."""
        # Format content with hashtags
        content_text = generated_post.content
        if generated_post.hashtags:
            hashtags_text = " ".join(f"#{tag}" for tag in generated_post.hashtags)
            content_text = f"{content_text}\n\n{hashtags_text}"
        
        post_data = {
            "author": f"urn:li:person:{user_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content_text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        return post_data
    
    def _extract_post_id(self, headers: Dict) -> str:
        """Extract post ID from response headers."""
        # LinkedIn returns the post ID in the Location header
        location = headers.get("Location", "")
        if location:
            # Extract ID from URL like: /v2/ugcPosts/urn:li:ugcPost:1234567890
            parts = location.split(":")
            if len(parts) >= 3:
                return parts[-1]
        
        # Fallback to timestamp-based ID if extraction fails
        return f"linkedin_{int(datetime.utcnow().timestamp())}"
    
    async def get_post_analytics(
        self,
        access_token: str,
        post_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get analytics data for a specific LinkedIn post.
        
        Args:
            access_token: User's LinkedIn access token
            post_id: LinkedIn post ID
            user_id: LinkedIn user ID
            
        Returns:
            Dictionary containing analytics data
        """
        self.logger.info("Fetching LinkedIn post analytics", post_id=post_id)
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # Get post statistics
            stats_url = f"{self.base_url}/socialActions/{post_id}/statistics"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(stats_url, headers=headers)
                
                if response.status_code == 200:
                    stats_data = response.json()
                    
                    return {
                        "post_id": post_id,
                        "likes": stats_data.get("numLikes", 0),
                        "comments": stats_data.get("numComments", 0),
                        "shares": stats_data.get("numShares", 0),
                        "impressions": stats_data.get("numViews", 0),
                        "engagement_rate": self._calculate_engagement_rate(stats_data),
                        "retrieved_at": datetime.utcnow().isoformat(),
                    }
                else:
                    self.logger.warning(
                        "Failed to fetch LinkedIn post analytics",
                        post_id=post_id,
                        status_code=response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.logger.error(
                "Error fetching LinkedIn post analytics",
                post_id=post_id,
                error=str(e)
            )
            return None
    
    def _calculate_engagement_rate(self, stats_data: Dict) -> float:
        """Calculate engagement rate from LinkedIn statistics."""
        impressions = stats_data.get("numViews", 0)
        if impressions == 0:
            return 0.0
        
        total_engagements = (
            stats_data.get("numLikes", 0) +
            stats_data.get("numComments", 0) +
            stats_data.get("numShares", 0)
        )
        
        return (total_engagements / impressions) * 100
    
    async def get_user_analytics(
        self,
        access_token: str,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict]:
        """
        Get user-level analytics from LinkedIn.
        
        Args:
            access_token: User's LinkedIn access token
            user_id: LinkedIn user ID
            start_date: Start date for analytics
            end_date: End date for analytics
            
        Returns:
            Dictionary containing user analytics
        """
        self.logger.info("Fetching LinkedIn user analytics", user_id=user_id)
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # Get follower statistics
            followers_url = f"{self.base_url}/networkSizes/{user_id}?edgeType=CompanyFollowedByMember"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(followers_url, headers=headers)
                
                if response.status_code == 200:
                    followers_data = response.json()
                    
                    return {
                        "user_id": user_id,
                        "follower_count": followers_data.get("firstDegreeSize", 0),
                        "connection_count": followers_data.get("secondDegreeSize", 0),
                        "retrieved_at": datetime.utcnow().isoformat(),
                    }
                else:
                    self.logger.warning(
                        "Failed to fetch LinkedIn user analytics",
                        user_id=user_id,
                        status_code=response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.logger.error(
                "Error fetching LinkedIn user analytics",
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def validate_access_token(self, access_token: str) -> bool:
        """
        Validate LinkedIn access token.
        
        Args:
            access_token: Access token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.people_endpoint}/(id~)",
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            self.logger.error("LinkedIn token validation failed", error=str(e))
            return False
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        Refresh LinkedIn access token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary containing new token data
        """
        self.logger.info("Refreshing LinkedIn access token")
        
        try:
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.settings.linkedin_client_id,
                "client_secret": self.settings.linkedin_client_secret,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    self.logger.error(
                        "LinkedIn token refresh failed",
                        status_code=response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.logger.error("LinkedIn token refresh error", error=str(e))
            return None
    
    async def check_connection(self) -> bool:
        """Check if LinkedIn API connection is working."""
        try:
            # Test with a basic API call (this would need a valid token in practice)
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.linkedin.com/v2/")
                # LinkedIn returns 401 for unauthenticated requests, which is expected
                return response.status_code in [200, 401]
                
        except Exception as e:
            self.logger.error("LinkedIn connection check failed", error=str(e))
            return False


# Global LinkedIn client instance
linkedin_client = LinkedInClient()


async def publish_to_linkedin(
    access_token: str,
    generated_post: GeneratedPost,
    user_id: str
) -> PublishingResult:
    """Convenience function to publish content to LinkedIn."""
    return await linkedin_client.publish_post(access_token, generated_post, user_id)