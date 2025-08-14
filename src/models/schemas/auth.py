"""
Authentication Schemas

Request and response schemas for authentication-related endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request schema for user login."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """Response schema for successful login."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: str = Field(..., description="User identifier")


class TokenResponse(BaseModel):
    """Response schema for token-related operations."""
    
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token."""
    
    refresh_token: str = Field(..., description="Valid refresh token")


class RegisterRequest(BaseModel):
    """Request schema for user registration."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., description="User's full name")
    job_title: Optional[str] = Field(None, description="User's job title")
    company: Optional[str] = Field(None, description="User's company")


class PasswordResetRequest(BaseModel):
    """Request schema for password reset."""
    
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirmRequest(BaseModel):
    """Request schema for confirming password reset."""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password."""
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class SocialAuthRequest(BaseModel):
    """Request schema for social media authentication."""
    
    platform: str = Field(..., description="Social platform (linkedin, twitter)")
    authorization_code: str = Field(..., description="OAuth authorization code")
    redirect_uri: str = Field(..., description="OAuth redirect URI")


class SocialAuthResponse(BaseModel):
    """Response schema for social media authentication."""
    
    platform: str = Field(..., description="Social platform")
    account_id: str = Field(..., description="Platform account ID")
    username: str = Field(..., description="Platform username")
    is_connected: bool = Field(..., description="Connection status")
    connected_at: datetime = Field(..., description="Connection timestamp")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }