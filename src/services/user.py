"""
User Service

This module handles all user-related business logic including:
- User creation and management
- Profile updates and settings
- Social account management
- User statistics tracking
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

import structlog
from passlib.context import CryptContext

from src.integrations.firestore import (
    create_user as firestore_create_user,
    get_user_by_email,
    get_user_by_id,
    update_user as firestore_update_user,
    delete_user as firestore_delete_user,
)
from src.models.user import (
    User,
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
    UserStats,
    ContentPreferences,
    SocialMediaAccount,
    SocialPlatform,
    SubscriptionTier,
    UserRole,
)


class UserService:
    """Service for handling user-related operations."""
    
    def __init__(self):
        """Initialize user service."""
        self.logger = structlog.get_logger(__name__)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self.pwd_context.hash(password)
    
    async def create_user(self, user_data: UserCreateRequest) -> User:
        """Create a new user account."""
        try:
            # Check if user already exists
            existing_user = await get_user_by_email(user_data.email)
            if existing_user:
                raise ValueError(f"User with email {user_data.email} already exists")
            
            # Generate user ID
            user_id = str(uuid.uuid4())
            
            # Hash password
            password_hash = self._hash_password(user_data.password)
            
            # Create user model
            user = User(
                id=user_id,
                email=user_data.email,
                full_name=user_data.full_name,
                job_title=user_data.job_title,
                company=user_data.company,
                industry=user_data.industry,
                password_hash=password_hash,  # This field might need to be added to the User model
                role=UserRole.USER,
                subscription_tier=SubscriptionTier.FREE,
                is_active=True,
                is_verified=False,
                content_preferences=ContentPreferences(),
                stats=UserStats(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Store user in Firestore
            await firestore_create_user(user)
            
            self.logger.info("User created successfully", user_id=user.id, email=user.email)
            return user
            
        except Exception as e:
            self.logger.error("User creation failed", error=str(e), email=user_data.email)
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            user = await get_user_by_id(user_id)
            if user:
                self.logger.debug("User retrieved by ID", user_id=user_id)
            return user
        except Exception as e:
            self.logger.error("Failed to get user by ID", error=str(e), user_id=user_id)
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            user = await get_user_by_email(email)
            if user:
                self.logger.debug("User retrieved by email", email=email)
            return user
        except Exception as e:
            self.logger.error("Failed to get user by email", error=str(e), email=email)
            return None
    
    async def update_user(self, user_id: str, update_data: UserUpdateRequest) -> Optional[User]:
        """Update user information."""
        try:
            # Get current user
            user = await get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Prepare update data
            update_fields = {}
            if update_data.full_name is not None:
                update_fields["full_name"] = update_data.full_name
            if update_data.job_title is not None:
                update_fields["job_title"] = update_data.job_title
            if update_data.company is not None:
                update_fields["company"] = update_data.company
            if update_data.industry is not None:
                update_fields["industry"] = update_data.industry
            if update_data.bio is not None:
                update_fields["bio"] = update_data.bio
            if update_data.avatar_url is not None:
                update_fields["avatar_url"] = update_data.avatar_url
            if update_data.content_preferences is not None:
                update_fields["content_preferences"] = update_data.content_preferences.dict()
            
            # Always update the updated_at timestamp
            update_fields["updated_at"] = datetime.utcnow()
            
            # Update user in Firestore
            updated_user = await firestore_update_user(user_id, update_fields)
            
            self.logger.info("User updated successfully", user_id=user_id)
            return updated_user
            
        except Exception as e:
            self.logger.error("User update failed", error=str(e), user_id=user_id)
            raise
    
    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            update_fields = {
                "last_login_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.debug("Last login updated", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to update last login", error=str(e), user_id=user_id)
            return False
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        try:
            update_fields = {
                "is_active": False,
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.info("User deactivated", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("User deactivation failed", error=str(e), user_id=user_id)
            return False
    
    async def activate_user(self, user_id: str) -> bool:
        """Activate a user account."""
        try:
            update_fields = {
                "is_active": True,
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.info("User activated", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("User activation failed", error=str(e), user_id=user_id)
            return False
    
    async def verify_user(self, user_id: str) -> bool:
        """Mark user as verified."""
        try:
            update_fields = {
                "is_verified": True,
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.info("User verified", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("User verification failed", error=str(e), user_id=user_id)
            return False
    
    async def update_subscription_tier(self, user_id: str, tier: SubscriptionTier) -> bool:
        """Update user's subscription tier."""
        try:
            update_fields = {
                "subscription_tier": tier.value,
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.info("Subscription tier updated", user_id=user_id, tier=tier.value)
            return True
            
        except Exception as e:
            self.logger.error("Subscription tier update failed", error=str(e), user_id=user_id)
            return False
    
    async def add_social_account(
        self, 
        user_id: str, 
        platform: SocialPlatform, 
        account: SocialMediaAccount
    ) -> bool:
        """Add a social media account to user profile."""
        try:
            user = await get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Update social accounts
            social_accounts = user.social_accounts.copy()
            social_accounts[platform] = account
            
            update_fields = {
                "social_accounts": {k.value: v.dict() for k, v in social_accounts.items()},
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.info("Social account added", user_id=user_id, platform=platform.value)
            return True
            
        except Exception as e:
            self.logger.error("Failed to add social account", error=str(e), user_id=user_id)
            return False
    
    async def remove_social_account(self, user_id: str, platform: SocialPlatform) -> bool:
        """Remove a social media account from user profile."""
        try:
            user = await get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Remove social account
            social_accounts = user.social_accounts.copy()
            if platform in social_accounts:
                del social_accounts[platform]
            
            update_fields = {
                "social_accounts": {k.value: v.dict() for k, v in social_accounts.items()},
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.info("Social account removed", user_id=user_id, platform=platform.value)
            return True
            
        except Exception as e:
            self.logger.error("Failed to remove social account", error=str(e), user_id=user_id)
            return False
    
    async def update_user_stats(self, user_id: str, stats: UserStats) -> bool:
        """Update user statistics."""
        try:
            update_fields = {
                "stats": stats.dict(),
                "updated_at": datetime.utcnow()
            }
            
            await firestore_update_user(user_id, update_fields)
            self.logger.debug("User stats updated", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to update user stats", error=str(e), user_id=user_id)
            return False
    
    async def get_user_statistics(self, user_id: str) -> UserStats:
        """Get user statistics and metrics."""
        try:
            user = await get_user_by_id(user_id)
            if not user:
                self.logger.warning("User not found for stats", user_id=user_id)
                # Return default stats for non-existent user
                return UserStats()
            
            # Return user's stats, or default stats if not set
            if hasattr(user, 'stats') and user.stats:
                return user.stats
            else:
                # Return default stats with at least some demo data
                return UserStats(
                    total_posts=0,
                    total_impressions=0,
                    total_engagements=0,
                    avg_engagement_rate=0.0,
                    best_performing_topic="AI & Technology",
                    last_active_at=datetime.utcnow()
                )
                
        except Exception as e:
            self.logger.error("Failed to get user statistics", error=str(e), user_id=user_id)
            # Return default stats on error
            return UserStats()
    
    async def increment_post_count(self, user_id: str) -> bool:
        """Increment user's total post count."""
        try:
            user = await get_user_by_id(user_id)
            if not user:
                return False
            
            updated_stats = user.stats.copy()
            updated_stats.total_posts += 1
            updated_stats.last_active_at = datetime.utcnow()
            
            return await self.update_user_stats(user_id, updated_stats)
            
        except Exception as e:
            self.logger.error("Failed to increment post count", error=str(e), user_id=user_id)
            return False
    
    async def update_engagement_metrics(
        self, 
        user_id: str, 
        impressions: int, 
        engagements: int
    ) -> bool:
        """Update user's engagement metrics."""
        try:
            user = await get_user_by_id(user_id)
            if not user:
                return False
            
            updated_stats = user.stats.copy()
            updated_stats.total_impressions += impressions
            updated_stats.total_engagements += engagements
            
            # Recalculate average engagement rate
            if updated_stats.total_impressions > 0:
                updated_stats.avg_engagement_rate = (
                    updated_stats.total_engagements / updated_stats.total_impressions
                ) * 100
            
            updated_stats.last_active_at = datetime.utcnow()
            
            return await self.update_user_stats(user_id, updated_stats)
            
        except Exception as e:
            self.logger.error("Failed to update engagement metrics", error=str(e), user_id=user_id)
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user account (soft delete by deactivating)."""
        try:
            # For now, just deactivate instead of hard delete
            success = await self.deactivate_user(user_id)
            if success:
                self.logger.info("User deleted (deactivated)", user_id=user_id)
            return success
            
        except Exception as e:
            self.logger.error("User deletion failed", error=str(e), user_id=user_id)
            return False
    
    async def get_users_by_subscription_tier(self, tier: SubscriptionTier) -> List[User]:
        """Get all users by subscription tier."""
        try:
            # This would require implementing a query in the Firestore integration
            # For now, return empty list
            self.logger.debug("Getting users by subscription tier", tier=tier.value)
            return []
            
        except Exception as e:
            self.logger.error("Failed to get users by subscription tier", error=str(e))
            return []
    
    async def search_users(self, query: str, limit: int = 50) -> List[User]:
        """Search for users by name or email."""
        try:
            # This would require implementing a search query in the Firestore integration
            # For now, return empty list
            self.logger.debug("Searching users", query=query, limit=limit)
            return []
            
        except Exception as e:
            self.logger.error("User search failed", error=str(e), query=query)
            return []