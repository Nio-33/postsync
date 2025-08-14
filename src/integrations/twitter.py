"""
Twitter API Integration

This module handles Twitter API v2 interactions for posting content
and retrieving analytics data.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
import structlog
import tweepy

from src.config.settings import get_settings
from src.models.content import GeneratedPost, PlatformType, PublishingResult


class TwitterClient:
    """Twitter API v2 client for content publishing and analytics."""
    
    def __init__(self):
        """Initialize Twitter client."""
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Initialize Tweepy client with API v2
        self._client = tweepy.Client(
            bearer_token=self.settings.twitter_bearer_token,
            consumer_key=self.settings.twitter_api_key,
            consumer_secret=self.settings.twitter_api_secret,
            access_token=self.settings.twitter_access_token,
            access_token_secret=self.settings.twitter_access_token_secret,
            wait_on_rate_limit=True,
        )
        
        # Twitter API endpoints for direct HTTP calls
        self.base_url = "https://api.twitter.com/2"
        self.tweets_endpoint = f"{self.base_url}/tweets"
        self.users_endpoint = f"{self.base_url}/users"
        
        # Rate limiting
        self.rate_limit = self.settings.twitter_rate_limit_requests_per_minute
    
    async def authenticate_user(self, authorization_code: str, redirect_uri: str) -> Dict:
        """
        Exchange authorization code for access token using OAuth 2.0.
        
        Args:
            authorization_code: OAuth authorization code from Twitter
            redirect_uri: Redirect URI used in OAuth flow
            
        Returns:
            Dictionary containing access token and user info
        """
        self.logger.info("Authenticating Twitter user")
        
        try:
            # Twitter OAuth 2.0 token exchange
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
            self.logger.error("Twitter authentication failed", error=str(e))
            raise
    
    async def _exchange_code_for_token(
        self, authorization_code: str, redirect_uri: str
    ) -> Dict:
        """Exchange authorization code for access token."""
        token_url = "https://api.twitter.com/2/oauth2/token"
        
        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "client_id": self.settings.twitter_api_key,
            "code_verifier": "challenge",  # Should be stored from OAuth flow
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
                f"{self.users_endpoint}/me",
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
        Publish a tweet to Twitter.
        
        Args:
            access_token: User's Twitter access token
            generated_post: Generated post content
            user_id: Twitter user ID
            
        Returns:
            PublishingResult with publishing status and details
        """
        self.logger.info("Publishing tweet to Twitter", user_id=user_id)
        
        try:
            # Check if content needs to be split into a thread
            if len(generated_post.content) > 280:
                return await self._publish_thread(access_token, generated_post, user_id)
            else:
                return await self._publish_single_tweet(access_token, generated_post, user_id)
                
        except Exception as e:
            self.logger.error(
                "Twitter post publishing error",
                user_id=user_id,
                error=str(e)
            )
            
            return PublishingResult(
                platform=PlatformType.TWITTER,
                success=False,
                error_message=str(e),
            )
    
    async def _publish_single_tweet(
        self,
        access_token: str,
        generated_post: GeneratedPost,
        user_id: str
    ) -> PublishingResult:
        """Publish a single tweet."""
        # Prepare tweet content
        tweet_text = self._prepare_tweet_text(generated_post)
        
        # Ensure tweet is within character limit
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
        
        # Make API request
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        tweet_data = {"text": tweet_text}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.tweets_endpoint,
                json=tweet_data,
                headers=headers
            )
            
            if response.status_code == 201:
                response_data = response.json()
                tweet_id = response_data["data"]["id"]
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                
                self.logger.info(
                    "Twitter post published successfully",
                    user_id=user_id,
                    tweet_id=tweet_id
                )
                
                return PublishingResult(
                    platform=PlatformType.TWITTER,
                    post_id=tweet_id,
                    post_url=tweet_url,
                    success=True,
                    published_at=datetime.utcnow(),
                )
            else:
                error_message = f"Twitter API error: {response.status_code}"
                self.logger.error(
                    "Twitter post publishing failed",
                    user_id=user_id,
                    status_code=response.status_code,
                    response=response.text
                )
                
                return PublishingResult(
                    platform=PlatformType.TWITTER,
                    success=False,
                    error_message=error_message,
                )
    
    async def _publish_thread(
        self,
        access_token: str,
        generated_post: GeneratedPost,
        user_id: str
    ) -> PublishingResult:
        """Publish a Twitter thread for longer content."""
        # Split content into thread tweets
        thread_tweets = self._split_into_thread(generated_post)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        tweet_ids = []
        reply_to_id = None
        
        async with httpx.AsyncClient() as client:
            for i, tweet_text in enumerate(thread_tweets):
                tweet_data = {"text": tweet_text}
                
                # Add reply reference for subsequent tweets
                if reply_to_id:
                    tweet_data["reply"] = {"in_reply_to_tweet_id": reply_to_id}
                
                response = await client.post(
                    self.tweets_endpoint,
                    json=tweet_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    response_data = response.json()
                    tweet_id = response_data["data"]["id"]
                    tweet_ids.append(tweet_id)
                    reply_to_id = tweet_id
                    
                    # Add delay between thread tweets
                    if i < len(thread_tweets) - 1:
                        await asyncio.sleep(1)
                else:
                    error_message = f"Twitter thread error: {response.status_code}"
                    self.logger.error(
                        "Twitter thread publishing failed",
                        user_id=user_id,
                        tweet_index=i,
                        status_code=response.status_code
                    )
                    
                    return PublishingResult(
                        platform=PlatformType.TWITTER,
                        success=False,
                        error_message=error_message,
                    )
        
        # Return result with first tweet ID
        first_tweet_id = tweet_ids[0] if tweet_ids else None
        tweet_url = f"https://twitter.com/user/status/{first_tweet_id}" if first_tweet_id else None
        
        self.logger.info(
            "Twitter thread published successfully",
            user_id=user_id,
            thread_length=len(tweet_ids),
            first_tweet_id=first_tweet_id
        )
        
        return PublishingResult(
            platform=PlatformType.TWITTER,
            post_id=first_tweet_id,
            post_url=tweet_url,
            success=True,
            published_at=datetime.utcnow(),
        )
    
    def _prepare_tweet_text(self, generated_post: GeneratedPost) -> str:
        """Prepare tweet text with hashtags."""
        tweet_text = generated_post.content
        
        # Add hashtags if they fit
        if generated_post.hashtags:
            hashtags_text = " ".join(f"#{tag}" for tag in generated_post.hashtags[:3])  # Limit hashtags
            potential_text = f"{tweet_text} {hashtags_text}"
            
            if len(potential_text) <= 280:
                tweet_text = potential_text
        
        return tweet_text
    
    def _split_into_thread(self, generated_post: GeneratedPost) -> List[str]:
        """Split long content into Twitter thread tweets."""
        content = generated_post.content
        tweets = []
        
        # Reserve space for thread numbering and hashtags
        max_length = 250
        
        # Split by sentences first
        sentences = content.split('. ')
        current_tweet = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Add period back if it's not the last sentence
            if not sentence.endswith('.'):
                sentence += '.'
            
            potential_tweet = f"{current_tweet} {sentence}".strip()
            
            if len(potential_tweet) <= max_length:
                current_tweet = potential_tweet
            else:
                # Save current tweet and start new one
                if current_tweet:
                    tweets.append(current_tweet)
                current_tweet = sentence
        
        # Add remaining content
        if current_tweet:
            tweets.append(current_tweet)
        
        # Add thread numbering and hashtags to last tweet
        if len(tweets) > 1:
            for i, tweet in enumerate(tweets):
                tweets[i] = f"{i + 1}/{len(tweets)} {tweet}"
            
            # Add hashtags to last tweet if they fit
            if generated_post.hashtags:
                hashtags_text = " ".join(f"#{tag}" for tag in generated_post.hashtags[:2])
                last_tweet = tweets[-1]
                
                if len(last_tweet) + len(hashtags_text) + 1 <= 280:
                    tweets[-1] = f"{last_tweet} {hashtags_text}"
        
        return tweets
    
    async def get_tweet_analytics(
        self,
        access_token: str,
        tweet_id: str,
        user_id: str
    ) -> Optional[Dict]:
        """
        Get analytics data for a specific tweet.
        
        Args:
            access_token: User's Twitter access token
            tweet_id: Twitter tweet ID
            user_id: Twitter user ID
            
        Returns:
            Dictionary containing analytics data
        """
        self.logger.info("Fetching Twitter tweet analytics", tweet_id=tweet_id)
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # Get tweet with public metrics
            params = {
                "tweet.fields": "public_metrics,created_at",
                "expansions": "author_id"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.tweets_endpoint}/{tweet_id}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    tweet_data = data["data"]
                    metrics = tweet_data.get("public_metrics", {})
                    
                    return {
                        "tweet_id": tweet_id,
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "replies": metrics.get("reply_count", 0),
                        "quotes": metrics.get("quote_count", 0),
                        "impressions": metrics.get("impression_count", 0),
                        "engagement_rate": self._calculate_engagement_rate(metrics),
                        "created_at": tweet_data.get("created_at"),
                        "retrieved_at": datetime.utcnow().isoformat(),
                    }
                else:
                    self.logger.warning(
                        "Failed to fetch Twitter tweet analytics",
                        tweet_id=tweet_id,
                        status_code=response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.logger.error(
                "Error fetching Twitter tweet analytics",
                tweet_id=tweet_id,
                error=str(e)
            )
            return None
    
    def _calculate_engagement_rate(self, metrics: Dict) -> float:
        """Calculate engagement rate from Twitter metrics."""
        impressions = metrics.get("impression_count", 0)
        if impressions == 0:
            return 0.0
        
        total_engagements = (
            metrics.get("like_count", 0) +
            metrics.get("retweet_count", 0) +
            metrics.get("reply_count", 0) +
            metrics.get("quote_count", 0)
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
        Get user-level analytics from Twitter.
        
        Args:
            access_token: User's Twitter access token
            user_id: Twitter user ID
            start_date: Start date for analytics
            end_date: End date for analytics
            
        Returns:
            Dictionary containing user analytics
        """
        self.logger.info("Fetching Twitter user analytics", user_id=user_id)
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # Get user information
            params = {"user.fields": "public_metrics,created_at"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.users_endpoint}/{user_id}",
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    user_data = data["data"]
                    metrics = user_data.get("public_metrics", {})
                    
                    return {
                        "user_id": user_id,
                        "follower_count": metrics.get("followers_count", 0),
                        "following_count": metrics.get("following_count", 0),
                        "tweet_count": metrics.get("tweet_count", 0),
                        "listed_count": metrics.get("listed_count", 0),
                        "retrieved_at": datetime.utcnow().isoformat(),
                    }
                else:
                    self.logger.warning(
                        "Failed to fetch Twitter user analytics",
                        user_id=user_id,
                        status_code=response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.logger.error(
                "Error fetching Twitter user analytics",
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def validate_access_token(self, access_token: str) -> bool:
        """
        Validate Twitter access token.
        
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
                    f"{self.users_endpoint}/me",
                    headers=headers
                )
                
                return response.status_code == 200
                
        except Exception as e:
            self.logger.error("Twitter token validation failed", error=str(e))
            return False
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        Refresh Twitter access token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary containing new token data
        """
        self.logger.info("Refreshing Twitter access token")
        
        try:
            token_url = "https://api.twitter.com/2/oauth2/token"
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.settings.twitter_api_key,
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
                        "Twitter token refresh failed",
                        status_code=response.status_code
                    )
                    return None
                    
        except Exception as e:
            self.logger.error("Twitter token refresh error", error=str(e))
            return None
    
    async def check_connection(self) -> bool:
        """Check if Twitter API connection is working."""
        try:
            # Test with a basic API call
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/tweets/search/recent?query=test&max_results=10",
                    headers={"Authorization": f"Bearer {self.settings.twitter_bearer_token}"}
                )
                return response.status_code in [200, 401]  # 401 is expected without proper auth
                
        except Exception as e:
            self.logger.error("Twitter connection check failed", error=str(e))
            return False


# Global Twitter client instance
twitter_client = TwitterClient()


async def publish_to_twitter(
    access_token: str,
    generated_post: GeneratedPost,
    user_id: str
) -> PublishingResult:
    """Convenience function to publish content to Twitter."""
    return await twitter_client.publish_post(access_token, generated_post, user_id)