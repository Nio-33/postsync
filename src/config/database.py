"""
Database Configuration and Connection Management

This module handles Firestore database connections and provides
database session management for the PostSync application.
"""

from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as firestore_client

from src.config.settings import get_settings


class DatabaseManager:
    """Singleton database manager for Firestore connections."""
    
    _instance: Optional["DatabaseManager"] = None
    _db: Optional[firestore_client.Client] = None
    
    def __new__(cls) -> "DatabaseManager":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database manager."""
        if self._db is None:
            self._initialize_firestore()
    
    def _initialize_firestore(self) -> None:
        """Initialize Firestore database connection."""
        settings = get_settings()
        
        try:
            # Check if Firebase app is already initialized
            firebase_admin.get_app()
        except ValueError:
            # Initialize Firebase app if not already done
            if settings.google_application_credentials:
                cred = credentials.Certificate(settings.google_application_credentials)
                firebase_admin.initialize_app(cred, {
                    'projectId': settings.google_cloud_project,
                })
            else:
                # For development, use a mock/test mode
                try:
                    firebase_admin.initialize_app()
                except Exception:
                    # If no credentials available, initialize with test credentials
                    firebase_admin.initialize_app(options={
                        'projectId': settings.google_cloud_project,
                    })
        
        try:
            # Initialize Firestore client
            self._db = firestore.client(database_id=settings.firestore_database_id)
        except Exception as e:
            # If Firestore initialization fails, set to None for graceful handling
            print(f"Warning: Firestore initialization failed: {e}")
            print("Running in development mode without Firestore")
            self._db = None
    
    @property
    def db(self) -> Optional[firestore_client.Client]:
        """Get Firestore database client."""
        if self._db is None:
            self._initialize_firestore()
        return self._db
    
    def get_collection(self, collection_name: str) -> firestore_client.CollectionReference:
        """Get a Firestore collection reference."""
        return self.db.collection(collection_name)
    
    def get_document(self, collection_name: str, document_id: str) -> firestore_client.DocumentReference:
        """Get a Firestore document reference."""
        return self.db.collection(collection_name).document(document_id)
    
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            # Try to read from a test collection
            test_ref = self.db.collection('health_check').limit(1)
            list(test_ref.stream())
            return True
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()


def get_database() -> firestore_client.Client:
    """Get the Firestore database client."""
    return db_manager.db


def get_collection(collection_name: str) -> firestore_client.CollectionReference:
    """Get a Firestore collection reference."""
    return db_manager.get_collection(collection_name)


def get_document(collection_name: str, document_id: str) -> firestore_client.DocumentReference:
    """Get a Firestore document reference."""
    return db_manager.get_document(collection_name, document_id)