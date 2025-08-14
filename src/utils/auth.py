"""
Authentication Utilities

This module provides authentication and authorization utilities
including JWT token handling and user verification.
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from passlib.context import CryptContext

from src.config.settings import get_settings
from src.integrations.firestore import get_user_by_id
from src.models.user import User

# Initialize password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize HTTP Bearer token scheme
security = HTTPBearer()

# Logger
logger = structlog.get_logger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User ID to encode in token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT refresh token
    """
    settings = get_settings()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=30)  # Refresh tokens last 30 days
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload or None if invalid
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        return payload
    except jwt.PyJWTError as e:
        logger.warning("Token verification failed", error=str(e))
        return None


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        User ID or None if token is invalid
    """
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None


async def get_current_user(token: str = Depends(security)) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: HTTP Bearer token
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract token from Bearer scheme
        token_str = token.credentials
        
        # Verify token and get payload
        payload = verify_token(token_str)
        if payload is None:
            raise credentials_exception
        
        # Extract user ID
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Get user from database
        user = await get_user_by_id(user_id)
        if user is None:
            raise credentials_exception
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
            )
        
        return user
        
    except jwt.PyJWTError:
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (alias for get_current_user since we already check active status).
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Active user object
    """
    return current_user


def create_password_reset_token(user_id: str) -> str:
    """
    Create a password reset token.
    
    Args:
        user_id: User ID
        
    Returns:
        Password reset token
    """
    settings = get_settings()
    
    expire = datetime.utcnow() + timedelta(hours=1)  # Reset tokens expire in 1 hour
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "type": "password_reset"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token and return user ID.
    
    Args:
        token: Password reset token
        
    Returns:
        User ID if token is valid, None otherwise
    """
    payload = verify_token(token)
    
    if payload and payload.get("type") == "password_reset":
        return payload.get("sub")
    
    return None


def create_email_verification_token(user_id: str, email: str) -> str:
    """
    Create an email verification token.
    
    Args:
        user_id: User ID
        email: Email address to verify
        
    Returns:
        Email verification token
    """
    settings = get_settings()
    
    expire = datetime.utcnow() + timedelta(days=7)  # Verification tokens expire in 7 days
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": "email_verification"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    return encoded_jwt


def verify_email_verification_token(token: str) -> Optional[dict]:
    """
    Verify email verification token.
    
    Args:
        token: Email verification token
        
    Returns:
        Token payload with user_id and email if valid, None otherwise
    """
    payload = verify_token(token)
    
    if payload and payload.get("type") == "email_verification":
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email")
        }
    
    return None


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token is blacklisted, False otherwise
    """
    # This would typically check against a blacklist stored in Redis or database
    # For now, return False (no blacklisting implemented)
    return False


def blacklist_token(token: str) -> bool:
    """
    Add a token to the blacklist.
    
    Args:
        token: JWT token to blacklist
        
    Returns:
        True if successfully blacklisted
    """
    # This would typically add the token to a blacklist in Redis or database
    # For now, return True (blacklisting not implemented)
    return True


def check_permission(user: User, required_permission: str) -> bool:
    """
    Check if user has required permission.
    
    Args:
        user: User object
        required_permission: Required permission string
        
    Returns:
        True if user has permission
    """
    # Basic role-based permission checking
    if user.role.value == "admin":
        return True  # Admins have all permissions
    
    # Define role permissions
    role_permissions = {
        "user": [
            "read_own_content",
            "create_content",
            "update_own_content",
            "delete_own_content",
            "read_own_analytics"
        ],
        "moderator": [
            "read_own_content",
            "create_content", 
            "update_own_content",
            "delete_own_content",
            "read_own_analytics",
            "moderate_content",
            "read_user_content"
        ]
    }
    
    user_permissions = role_permissions.get(user.role.value, [])
    return required_permission in user_permissions


def require_permission(required_permission: str):
    """
    Decorator to require specific permission for endpoint access.
    
    Args:
        required_permission: Required permission string
        
    Returns:
        Dependency function for FastAPI
    """
    def permission_dependency(current_user: User = Depends(get_current_user)) -> User:
        if not check_permission(current_user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    return permission_dependency


def rate_limit_key(user_id: str, endpoint: str) -> str:
    """
    Generate rate limiting key for user and endpoint.
    
    Args:
        user_id: User ID
        endpoint: API endpoint
        
    Returns:
        Rate limit key
    """
    return f"rate_limit:{user_id}:{endpoint}"


def generate_api_key() -> str:
    """
    Generate API key for programmatic access.
    
    Returns:
        Generated API key
    """
    import secrets
    return f"pk_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(32))}"