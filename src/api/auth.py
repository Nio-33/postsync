"""
Authentication API Endpoints

This module contains all authentication-related endpoints including:
- User registration and login
- JWT token management
- Social media OAuth integration
- Password reset functionality
"""

from datetime import timedelta
from typing import Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from src.models.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SocialAuthRequest,
    SocialAuthResponse,
    TokenResponse,
)
from src.models.schemas.common import ErrorResponse, SuccessResponse
from src.models.user import User, UserCreateRequest, UserResponse
from src.services.auth import AuthService
from src.services.user import UserService
from src.utils.auth import get_current_user

# Initialize router and logger
router = APIRouter()
security = HTTPBearer()
logger = structlog.get_logger(__name__)

# Dependency injection
def get_auth_service() -> AuthService:
    """Get authentication service instance."""
    return AuthService()

def get_user_service() -> UserService:
    """Get user service instance."""
    return UserService()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid registration data"},
        409: {"model": ErrorResponse, "description": "User already exists"},
    }
)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Register a new user account.
    
    Creates a new user account with the provided email and password.
    The user will need to verify their email before accessing all features.
    """
    logger.info("User registration attempt", email=request.email)
    
    try:
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(request.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Create new user
        user_data = UserCreateRequest(
            email=request.email,
            full_name=request.full_name,
            password=request.password,
            job_title=request.job_title,
            company=request.company,
        )
        
        user = await user_service.create_user(user_data)
        logger.info("User registered successfully", user_id=user.id, email=user.email)
        
        return UserResponse.from_orm(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration failed", error=str(e), email=request.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        423: {"model": ErrorResponse, "description": "Account locked"},
    }
)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
) -> LoginResponse:
    """
    Authenticate user and return access tokens.
    
    Validates user credentials and returns JWT access and refresh tokens
    for authenticated API access.
    """
    logger.info("User login attempt", email=request.email)
    
    try:
        # Authenticate user
        user = await auth_service.authenticate_user(request.email, request.password)
        if not user:
            logger.warning("Failed login attempt", email=request.email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            logger.warning("Login attempt for inactive user", email=request.email)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is deactivated"
            )
        
        # Generate tokens
        access_token, refresh_token = await auth_service.create_tokens(user.id)
        
        # Update last login timestamp
        await user_service.update_last_login(user.id)
        
        logger.info("User logged in successfully", user_id=user.id, email=user.email)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60,  # 30 minutes
            user_id=user.id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login failed", error=str(e), email=request.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
    }
)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Validates the refresh token and returns a new access token.
    """
    logger.info("Token refresh attempt")
    
    try:
        # Validate refresh token and get new access token
        access_token = await auth_service.refresh_access_token(request.refresh_token)
        
        logger.info("Token refreshed successfully")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=30 * 60,  # 30 minutes
        )
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post(
    "/logout",
    response_model=SuccessResponse,
    dependencies=[Depends(security)]
)
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Logout user and invalidate tokens.
    
    Adds the current access token to a blacklist to prevent further use.
    """
    logger.info("User logout", user_id=current_user.id)
    
    try:
        # Invalidate user tokens
        await auth_service.logout_user(current_user.id)
        
        logger.info("User logged out successfully", user_id=current_user.id)
        
        return SuccessResponse(
            success=True,
            message="Logged out successfully"
        )
        
    except Exception as e:
        logger.error("Logout failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed. Please try again."
        )


@router.post(
    "/password-reset",
    response_model=SuccessResponse,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
    }
)
async def request_password_reset(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Request password reset for user email.
    
    Sends a password reset email with a secure token if the email exists.
    """
    logger.info("Password reset requested", email=request.email)
    
    try:
        # Generate password reset token and send email
        await auth_service.request_password_reset(request.email)
        
        logger.info("Password reset email sent", email=request.email)
        
        return SuccessResponse(
            success=True,
            message="Password reset email sent if account exists"
        )
        
    except Exception as e:
        logger.error("Password reset request failed", error=str(e), email=request.email)
        # Always return success to prevent email enumeration
        return SuccessResponse(
            success=True,
            message="Password reset email sent if account exists"
        )


@router.post(
    "/password-reset/confirm",
    response_model=SuccessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or expired token"},
    }
)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Confirm password reset with token.
    
    Validates the reset token and updates the user's password.
    """
    logger.info("Password reset confirmation attempt")
    
    try:
        # Validate token and reset password
        await auth_service.confirm_password_reset(request.token, request.new_password)
        
        logger.info("Password reset completed successfully")
        
        return SuccessResponse(
            success=True,
            message="Password reset successfully"
        )
        
    except Exception as e:
        logger.error("Password reset confirmation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.post(
    "/change-password",
    response_model=SuccessResponse,
    dependencies=[Depends(security)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid current password"},
    }
)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Change user password.
    
    Validates the current password and updates to the new password.
    """
    logger.info("Password change attempt", user_id=current_user.id)
    
    try:
        # Validate current password and update
        await auth_service.change_password(
            current_user.id,
            request.current_password,
            request.new_password
        )
        
        logger.info("Password changed successfully", user_id=current_user.id)
        
        return SuccessResponse(
            success=True,
            message="Password changed successfully"
        )
        
    except ValueError as e:
        logger.warning("Invalid current password", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    except Exception as e:
        logger.error("Password change failed", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed. Please try again."
        )


@router.post(
    "/social/connect",
    response_model=SocialAuthResponse,
    dependencies=[Depends(security)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid authorization code"},
    }
)
async def connect_social_account(
    request: SocialAuthRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> SocialAuthResponse:
    """
    Connect social media account to user profile.
    
    Exchanges OAuth authorization code for access tokens and stores
    the connection for automated posting.
    """
    logger.info(
        "Social account connection attempt",
        user_id=current_user.id,
        platform=request.platform
    )
    
    try:
        # Exchange authorization code for tokens
        account_info = await auth_service.connect_social_account(
            current_user.id,
            request.platform,
            request.authorization_code,
            request.redirect_uri
        )
        
        logger.info(
            "Social account connected successfully",
            user_id=current_user.id,
            platform=request.platform,
            account_id=account_info["account_id"]
        )
        
        return SocialAuthResponse(
            platform=request.platform,
            account_id=account_info["account_id"],
            username=account_info["username"],
            is_connected=True,
            connected_at=account_info["connected_at"]
        )
        
    except Exception as e:
        logger.error(
            "Social account connection failed",
            error=str(e),
            user_id=current_user.id,
            platform=request.platform
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect {request.platform} account"
        )


@router.delete(
    "/social/{platform}/disconnect",
    response_model=SuccessResponse,
    dependencies=[Depends(security)]
)
async def disconnect_social_account(
    platform: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Disconnect social media account from user profile.
    
    Removes the social media account connection and revokes stored tokens.
    """
    logger.info(
        "Social account disconnection attempt",
        user_id=current_user.id,
        platform=platform
    )
    
    try:
        # Disconnect social account
        await auth_service.disconnect_social_account(current_user.id, platform)
        
        logger.info(
            "Social account disconnected successfully",
            user_id=current_user.id,
            platform=platform
        )
        
        return SuccessResponse(
            success=True,
            message=f"{platform.title()} account disconnected successfully"
        )
        
    except Exception as e:
        logger.error(
            "Social account disconnection failed",
            error=str(e),
            user_id=current_user.id,
            platform=platform
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect {platform} account"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[Depends(security)]
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user information.
    
    Returns the authenticated user's profile information.
    """
    return UserResponse.from_orm(current_user)