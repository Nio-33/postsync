"""
Firestore Database Integration

This module provides database operations for PostSync using Firestore,
including CRUD operations for users, content, and analytics data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import structlog
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter, Query

from src.config.database import get_database
from src.models.analytics import PostAnalytics, UserAnalytics
from src.models.content import ContentItem, ContentStatus
from src.models.user import User


class FirestoreClient:
    """Firestore database client for PostSync operations."""
    
    def __init__(self):
        """Initialize Firestore client."""
        self.db = get_database()
        self.logger = structlog.get_logger(__name__)
        
        # Collection names
        self.users_collection = "users"
        self.content_collection = "content"
        self.analytics_collection = "analytics"
        self.posts_collection = "posts"
        self.jobs_collection = "jobs"
        
        # In-memory storage for development mode
        self._mock_storage = {
            "users": {},
            "content": {},
            "analytics": {},
            "posts": {},
            "jobs": {}
        }
    
    # User Operations
    async def create_user(self, user: User) -> User:
        """Create a new user in Firestore."""
        try:
            if self.db is None:
                # Development mode: use in-memory storage
                user_dict = user.dict()
                user_dict["created_at"] = datetime.utcnow().isoformat()
                user_dict["updated_at"] = datetime.utcnow().isoformat()
                
                self._mock_storage["users"][user.id] = user_dict
                self.logger.info("User created in mock storage", user_id=user.id)
                return user
            
            # Production mode: use Firestore
            user_dict = user.dict()
            user_dict["created_at"] = firestore.SERVER_TIMESTAMP
            user_dict["updated_at"] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(self.users_collection).document(user.id)
            doc_ref.set(user_dict)
            
            self.logger.info("User created in Firestore", user_id=user.id)
            return user
            
        except Exception as e:
            self.logger.error("Failed to create user", user_id=user.id, error=str(e))
            raise
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID from Firestore."""
        try:
            if self.db is None:
                # Development mode: use in-memory storage
                user_data = self._mock_storage["users"].get(user_id)
                if user_data:
                    return User(**user_data)
                return None
            
            # Production mode: use Firestore
            doc_ref = self.db.collection(self.users_collection).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                user_data = doc.to_dict()
                user_data["id"] = doc.id
                return User(**user_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error("Failed to get user", user_id=user_id, error=str(e))
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email from Firestore."""
        try:
            if self.db is None:
                # Development mode: use in-memory storage
                for user_data in self._mock_storage["users"].values():
                    if user_data.get("email") == email:
                        return User(**user_data)
                return None
            
            # Production mode: use Firestore
            query = self.db.collection(self.users_collection).where(
                filter=FieldFilter("email", "==", email)
            ).limit(1)
            
            docs = query.stream()
            for doc in docs:
                user_data = doc.to_dict()
                user_data["id"] = doc.id
                return User(**user_data)
            
            return None
            
        except Exception as e:
            self.logger.error("Failed to get user by email", email=email, error=str(e))
            return None
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update user in Firestore."""
        try:
            updates["updated_at"] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(self.users_collection).document(user_id)
            doc_ref.update(updates)
            
            # Return updated user
            return await self.get_user(user_id)
            
        except Exception as e:
            self.logger.error("Failed to update user", user_id=user_id, error=str(e))
            return None
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user from Firestore."""
        try:
            # Delete user document
            doc_ref = self.db.collection(self.users_collection).document(user_id)
            doc_ref.delete()
            
            # TODO: Also delete related content and analytics
            
            self.logger.info("User deleted from Firestore", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete user", user_id=user_id, error=str(e))
            return False
    
    # Content Operations
    async def create_content_item(self, content: ContentItem) -> ContentItem:
        """Create a new content item in Firestore."""
        try:
            content_dict = content.dict()
            content_dict["created_at"] = firestore.SERVER_TIMESTAMP
            content_dict["updated_at"] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(self.content_collection).document(content.id)
            doc_ref.set(content_dict)
            
            self.logger.info("Content item created in Firestore", content_id=content.id)
            return content
            
        except Exception as e:
            self.logger.error("Failed to create content item", content_id=content.id, error=str(e))
            raise
    
    async def get_content_item(self, content_id: str) -> Optional[ContentItem]:
        """Get content item by ID from Firestore."""
        try:
            doc_ref = self.db.collection(self.content_collection).document(content_id)
            doc = doc_ref.get()
            
            if doc.exists:
                content_data = doc.to_dict()
                content_data["id"] = doc.id
                return ContentItem(**content_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error("Failed to get content item", content_id=content_id, error=str(e))
            return None
    
    async def get_user_content(
        self,
        user_id: str,
        status: Optional[ContentStatus] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        descending: bool = True
    ) -> List[ContentItem]:
        """Get content items for a user with filtering and pagination."""
        try:
            query = self.db.collection(self.content_collection).where(
                filter=FieldFilter("user_id", "==", user_id)
            )
            
            if status:
                query = query.where(filter=FieldFilter("status", "==", status.value))
            
            # Add ordering
            direction = Query.DESCENDING if descending else Query.ASCENDING
            query = query.order_by(order_by, direction=direction)
            
            # Add pagination
            query = query.offset(offset).limit(limit)
            
            content_items = []
            for doc in query.stream():
                content_data = doc.to_dict()
                content_data["id"] = doc.id
                content_items.append(ContentItem(**content_data))
            
            return content_items
            
        except Exception as e:
            self.logger.error("Failed to get user content", user_id=user_id, error=str(e))
            return []
    
    async def update_content_item(
        self, content_id: str, updates: Dict[str, Any]
    ) -> Optional[ContentItem]:
        """Update content item in Firestore."""
        try:
            updates["updated_at"] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(self.content_collection).document(content_id)
            doc_ref.update(updates)
            
            # Return updated content
            return await self.get_content_item(content_id)
            
        except Exception as e:
            self.logger.error("Failed to update content item", content_id=content_id, error=str(e))
            return None
    
    async def delete_content_item(self, content_id: str) -> bool:
        """Delete content item from Firestore."""
        try:
            doc_ref = self.db.collection(self.content_collection).document(content_id)
            doc_ref.delete()
            
            self.logger.info("Content item deleted from Firestore", content_id=content_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete content item", content_id=content_id, error=str(e))
            return False
    
    async def get_content_by_source_id(self, source_id: str, source: str) -> Optional[ContentItem]:
        """Get content item by source ID to check for duplicates."""
        try:
            query = self.db.collection(self.content_collection).where(
                filter=FieldFilter("source_content.source_id", "==", source_id)
            ).where(
                filter=FieldFilter("source_content.source", "==", source)
            ).limit(1)
            
            docs = query.stream()
            for doc in docs:
                content_data = doc.to_dict()
                content_data["id"] = doc.id
                return ContentItem(**content_data)
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to get content by source ID",
                source_id=source_id,
                source=source,
                error=str(e)
            )
            return None
    
    # Analytics Operations
    async def create_post_analytics(self, analytics: PostAnalytics) -> PostAnalytics:
        """Create post analytics record in Firestore."""
        try:
            analytics_dict = analytics.dict()
            analytics_dict["created_at"] = firestore.SERVER_TIMESTAMP
            analytics_dict["updated_at"] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(self.analytics_collection).document(analytics.post_id)
            doc_ref.set(analytics_dict)
            
            self.logger.info("Post analytics created in Firestore", post_id=analytics.post_id)
            return analytics
            
        except Exception as e:
            self.logger.error(
                "Failed to create post analytics",
                post_id=analytics.post_id,
                error=str(e)
            )
            raise
    
    async def get_post_analytics(self, post_id: str) -> Optional[PostAnalytics]:
        """Get post analytics by post ID from Firestore."""
        try:
            doc_ref = self.db.collection(self.analytics_collection).document(post_id)
            doc = doc_ref.get()
            
            if doc.exists:
                analytics_data = doc.to_dict()
                return PostAnalytics(**analytics_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error("Failed to get post analytics", post_id=post_id, error=str(e))
            return None
    
    async def update_post_analytics(
        self, post_id: str, updates: Dict[str, Any]
    ) -> Optional[PostAnalytics]:
        """Update post analytics in Firestore."""
        try:
            updates["updated_at"] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(self.analytics_collection).document(post_id)
            doc_ref.update(updates)
            
            # Return updated analytics
            return await self.get_post_analytics(post_id)
            
        except Exception as e:
            self.logger.error("Failed to update post analytics", post_id=post_id, error=str(e))
            return None
    
    async def get_user_analytics_data(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[PostAnalytics]:
        """Get analytics data for a user within date range."""
        try:
            query = self.db.collection(self.analytics_collection).where(
                filter=FieldFilter("user_id", "==", user_id)
            ).where(
                filter=FieldFilter("first_tracked_at", ">=", start_date)
            ).where(
                filter=FieldFilter("first_tracked_at", "<=", end_date)
            )
            
            analytics_list = []
            for doc in query.stream():
                analytics_data = doc.to_dict()
                analytics_list.append(PostAnalytics(**analytics_data))
            
            return analytics_list
            
        except Exception as e:
            self.logger.error(
                "Failed to get user analytics data",
                user_id=user_id,
                error=str(e)
            )
            return []
    
    # Utility Operations
    async def batch_write(self, operations: List[Dict[str, Any]]) -> bool:
        """Perform batch write operations."""
        try:
            batch = self.db.batch()
            
            for operation in operations:
                op_type = operation["type"]
                collection = operation["collection"]
                document_id = operation["document_id"]
                data = operation.get("data", {})
                
                doc_ref = self.db.collection(collection).document(document_id)
                
                if op_type == "set":
                    batch.set(doc_ref, data)
                elif op_type == "update":
                    batch.update(doc_ref, data)
                elif op_type == "delete":
                    batch.delete(doc_ref)
            
            batch.commit()
            self.logger.info("Batch write completed", operations_count=len(operations))
            return True
            
        except Exception as e:
            self.logger.error("Batch write failed", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        """Check Firestore connection health."""
        try:
            # Try to read from a test collection
            test_ref = self.db.collection("health_check").limit(1)
            list(test_ref.stream())
            return True
            
        except Exception as e:
            self.logger.error("Firestore health check failed", error=str(e))
            return False
    
    async def cleanup_old_data(self, days: int = 90) -> int:
        """Clean up old data from Firestore."""
        try:
            cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
            
            # Clean up old content items
            query = self.db.collection(self.content_collection).where(
                filter=FieldFilter("created_at", "<", cutoff_date)
            ).where(
                filter=FieldFilter("status", "in", ["failed", "rejected"])
            )
            
            deleted_count = 0
            batch = self.db.batch()
            
            for doc in query.limit(500).stream():
                batch.delete(doc.reference)
                deleted_count += 1
            
            if deleted_count > 0:
                batch.commit()
                self.logger.info("Old data cleaned up", deleted_count=deleted_count)
            
            return deleted_count
            
        except Exception as e:
            self.logger.error("Data cleanup failed", error=str(e))
            return 0

    async def get_scheduled_content(self, current_time: datetime) -> List[ContentItem]:
        """Get content items that are scheduled for publishing at or before the current time."""
        try:
            if self.db is None:
                # Development mode: use in-memory storage
                scheduled_items = []
                for content_id, content_data in self._mock_storage["content"].items():
                    content = ContentItem(**content_data)
                    if (content.status == ContentStatus.SCHEDULED and 
                        content.scheduled_at and 
                        content.scheduled_at <= current_time):
                        scheduled_items.append(content)
                return scheduled_items
            
            # Production mode: query Firestore
            query = self.db.collection(self.content_collection).where(
                filter=FieldFilter("status", "==", ContentStatus.SCHEDULED.value)
            ).where(
                filter=FieldFilter("scheduled_at", "<=", current_time)
            ).order_by("scheduled_at", direction=firestore.Query.ASCENDING)
            
            content_items = []
            for doc in query.stream():
                content_data = doc.to_dict()
                content_data["id"] = doc.id
                
                # Convert Firestore timestamps to datetime
                if "created_at" in content_data and hasattr(content_data["created_at"], 'seconds'):
                    content_data["created_at"] = datetime.fromtimestamp(content_data["created_at"].seconds)
                if "scheduled_at" in content_data and hasattr(content_data["scheduled_at"], 'seconds'):
                    content_data["scheduled_at"] = datetime.fromtimestamp(content_data["scheduled_at"].seconds)
                
                content_items.append(ContentItem(**content_data))
            
            return content_items
            
        except Exception as e:
            self.logger.error(
                "Failed to get scheduled content",
                error=str(e),
                current_time=current_time
            )
            return []


# Global Firestore client instance
firestore_client = FirestoreClient()


# Convenience functions
async def create_user(user: User) -> User:
    """Create a new user."""
    return await firestore_client.create_user(user)


async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID."""
    return await firestore_client.get_user(user_id)


async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email."""
    return await firestore_client.get_user_by_email(email)


async def update_user(user_id: str, updates: Dict[str, Any]) -> Optional[User]:
    """Update user."""
    return await firestore_client.update_user(user_id, updates)


async def delete_user(user_id: str) -> bool:
    """Delete user."""
    return await firestore_client.delete_user(user_id)


async def create_content_item(content: ContentItem) -> ContentItem:
    """Create content item."""
    return await firestore_client.create_content_item(content)


async def get_content_item(content_id: str) -> Optional[ContentItem]:
    """Get content item by ID."""
    return await firestore_client.get_content_item(content_id)