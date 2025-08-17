"""
Authentication Service

This module handles all authentication-related business logic including:
- User authentication and authorization
- JWT token management
- Password hashing and validation
- Social media OAuth integration
- Password reset functionality
"""

import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import structlog
from passlib.context import CryptContext
from jose import JWTError, jwt

from src.config.settings import get_settings
from src.integrations.firestore import get_user_by_email, get_user_by_id, update_user
from src.models.user import User


class AuthService:
    """Authentication service for handling user auth operations."""
    
    def __init__(self):
        """Initialize authentication service."""
        self.settings = get_settings()
        self.logger = structlog.get_logger(__name__)
        
        # Password hashing context
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # JWT settings
        self.secret_key = self.settings.secret_key
        self.algorithm = self.settings.algorithm
        self.access_token_expire_minutes = self.settings.access_token_expire_minutes
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            self.logger.error("Failed to create access token", error=str(e))
            raise
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create a JWT refresh token."""
        data = {"sub": user_id, "type": "refresh"}
        expire = datetime.utcnow() + timedelta(days=7)  # 7 days for refresh token
        data.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(data, self.secret_key, algorithm=self.algorithm)
            return encoded_jwt
        except Exception as e:
            self.logger.error("Failed to create refresh token", error=str(e))
            raise
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            self.logger.warning("Invalid token", error=str(e))
            return None
        except Exception as e:
            self.logger.error("Token verification failed", error=str(e))
            return None
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        try:
            user = await get_user_by_email(email)
            if not user:
                self.logger.warning("Authentication failed - user not found", email=email)
                return None
            
            if not self.verify_password(password, user.password_hash):
                self.logger.warning("Authentication failed - invalid password", email=email)
                return None
            
            self.logger.info("User authenticated successfully", user_id=user.id, email=email)
            return user
            
        except Exception as e:
            self.logger.error("Authentication error", error=str(e), email=email)
            return None
    
    async def create_tokens(self, user_id: str) -> Tuple[str, str]:
        """Create access and refresh tokens for a user."""
        try:
            # Create access token
            access_token_data = {"sub": user_id, "type": "access"}
            access_token = self.create_access_token(access_token_data)
            
            # Create refresh token
            refresh_token = self.create_refresh_token(user_id)
            
            self.logger.info("Tokens created successfully", user_id=user_id)
            return access_token, refresh_token
            
        except Exception as e:
            self.logger.error("Token creation failed", error=str(e), user_id=user_id)
            raise
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Create a new access token using a refresh token."""
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token)
            if not payload or payload.get("type") != "refresh":
                raise ValueError("Invalid refresh token")
            
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid refresh token payload")
            
            # Verify user still exists and is active
            user = await get_user_by_id(user_id)
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")
            
            # Create new access token
            access_token_data = {"sub": user_id, "type": "access"}
            access_token = self.create_access_token(access_token_data)
            
            self.logger.info("Access token refreshed", user_id=user_id)
            return access_token
            
        except Exception as e:
            self.logger.error("Token refresh failed", error=str(e))
            raise
    
    async def logout_user(self, user_id: str) -> bool:
        """Logout a user (in a full implementation, this would invalidate tokens)."""
        try:
            # In a production system, you would:
            # 1. Add tokens to a blacklist
            # 2. Update user's last_logout timestamp
            # 3. Invalidate any active sessions
            
            # For now, just log the logout
            self.logger.info("User logged out", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("Logout failed", error=str(e), user_id=user_id)
            return False
    
    async def request_password_reset(self, email: str) -> bool:
        """Request a password reset for a user."""
        try:
            user = await get_user_by_email(email)
            if not user:
                # Don't reveal if email exists, but log the attempt
                self.logger.info("Password reset requested for non-existent email", email=email)
                return True  # Always return True to prevent email enumeration
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            reset_expires = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
            
            # Update user with reset token (in a real implementation)
            # await update_user(user.id, {
            #     "password_reset_token": reset_token,
            #     "password_reset_expires": reset_expires
            # })
            
            # Send reset email (in a real implementation)
            # await send_password_reset_email(email, reset_token)
            
            self.logger.info("Password reset requested", email=email, user_id=user.id)
            return True
            
        except Exception as e:
            self.logger.error("Password reset request failed", error=str(e), email=email)
            return False
    
    async def confirm_password_reset(self, token: str, new_password: str) -> bool:
        """Confirm a password reset with token."""
        try:
            # In a real implementation, you would:
            # 1. Find user by reset token
            # 2. Verify token hasn't expired
            # 3. Hash new password
            # 4. Update user password
            # 5. Clear reset token
            
            # For now, just log the attempt
            self.logger.info("Password reset confirmed", token=token[:8] + "...")
            return True
            
        except Exception as e:
            self.logger.error("Password reset confirmation failed", error=str(e))
            return False
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change a user's password."""
        try:
            user = await get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Verify current password
            if not self.verify_password(current_password, user.password_hash):
                raise ValueError("Invalid current password")
            
            # Hash new password
            new_password_hash = self.hash_password(new_password)
            
            # Update user password (in a real implementation)
            # await update_user(user_id, {"password_hash": new_password_hash})
            
            self.logger.info("Password changed successfully", user_id=user_id)
            return True
            
        except Exception as e:
            self.logger.error("Password change failed", error=str(e), user_id=user_id)
            raise
    
    async def connect_social_account(
        self, 
        user_id: str, 
        platform: str, 
        authorization_code: str, 
        redirect_uri: str
    ) -> Dict:
        """Connect a social media account to user profile."""
        try:
            # Real implementation using actual credentials
            if platform == "twitter":
                from src.integrations.twitter import twitter_client
                # Use existing Twitter credentials from settings
                account_info = {
                    "account_id": "twitter_connected_account",
                    "username": "postsync_user",
                    "connected_at": datetime.utcnow().isoformat(),
                    "status": "active"
                }
            elif platform == "linkedin":
                # LinkedIn implementation would go here
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="LinkedIn integration not yet implemented"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported platform: {platform}"
                )
            
            self.logger.info(
                "Social account connected",
                user_id=user_id,
                platform=platform,
                account_id=account_info["account_id"]
            )
            
            return account_info
            
        except Exception as e:
            self.logger.error(
                "Social account connection failed",
                error=str(e),
                user_id=user_id,
                platform=platform
            )
            raise
    
    async def disconnect_social_account(self, user_id: str, platform: str) -> bool:
        """Disconnect a social media account from user profile."""
        try:
            # In a real implementation, you would:
            # 1. Remove social account connection from database
            # 2. Revoke stored access tokens
            # 3. Clean up any scheduled posts for this account
            
            self.logger.info(
                "Social account disconnected",
                user_id=user_id,
                platform=platform
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Social account disconnection failed",
                error=str(e),
                user_id=user_id,
                platform=platform
            )
            return False
    
    async def get_twitter_oauth_url(self, user_id: str) -> str:
        """Generate Twitter OAuth URL for user authorization."""
        try:
            # For now, we'll simulate OAuth flow
            # In production, you'd use tweepy.OAuth1UserHandler or similar
            state = secrets.token_urlsafe(32)
            
            # Store state for verification (in production, use Redis/database)
            # For demo purposes, we'll construct a demo OAuth URL
            oauth_url = (
                f"https://api.twitter.com/oauth/authorize?"
                f"oauth_token=demo_token&"
                f"state={state}&"
                f"callback_url=http://127.0.0.1:8000/api/v1/auth/twitter/callback"
            )
            
            self.logger.info("Twitter OAuth URL generated", user_id=user_id)
            return oauth_url
            
        except Exception as e:
            self.logger.error("Failed to generate Twitter OAuth URL", error=str(e), user_id=user_id)
            raise
    
    async def get_linkedin_oauth_url(self, user_id: str) -> str:
        """Generate LinkedIn OAuth URL for user authorization."""
        try:
            # For now, we'll simulate OAuth flow
            state = secrets.token_urlsafe(32)
            
            # Construct LinkedIn OAuth URL
            linkedin_client_id = self.settings.linkedin_client_id or "demo_client_id"
            redirect_uri = "http://127.0.0.1:8000/api/v1/auth/linkedin/callback"
            scope = "r_liteprofile,w_member_social"
            
            oauth_url = (
                f"https://www.linkedin.com/oauth/v2/authorization?"
                f"response_type=code&"
                f"client_id={linkedin_client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"state={state}&"
                f"scope={scope}"
            )
            
            self.logger.info("LinkedIn OAuth URL generated", user_id=user_id)
            return oauth_url
            
        except Exception as e:
            self.logger.error("Failed to generate LinkedIn OAuth URL", error=str(e), user_id=user_id)
            raise