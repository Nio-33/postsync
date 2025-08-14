"""
User Management API Endpoints

This module contains user profile management endpoints including:
- User profile operations
- Account settings management
- Subscription and billing
- User statistics and analytics
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from src.models.schemas.common import ErrorResponse, PaginatedResponse, PaginationParams, SuccessResponse
from src.models.user import (
    ContentPreferences,
    SubscriptionTier,
    User,
    UserResponse,
    UserStats,
    UserUpdateRequest,
)
from src.services.user import UserService
from src.utils.auth import get_current_user

# Initialize router and dependencies
router = APIRouter()
security = HTTPBearer()
logger = structlog.get_logger(__name__)


def get_user_service() -> UserService:
    """Get user service instance."""
    return UserService()


@router.get(
    "/profile",
    response_model=UserResponse,
    dependencies=[Depends(security)]
)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user's profile information.
    
    Returns comprehensive user profile data including preferences,
    statistics, and connected social accounts.
    """
    logger.info("User profile requested", user_id=current_user.id)
    return UserResponse.from_orm(current_user)


@router.put(
    "/profile",
    response_model=UserResponse,
    dependencies=[Depends(security)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid profile data"},
    }
)
async def update_user_profile(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """
    Update user profile information.
    
    Updates user profile fields including name, job title, company,
    bio, and other professional information.
    """
    logger.info("User profile update", user_id=current_user.id)
    
    try:
        updated_user = await user_service.update_user(current_user.id, request)
        logger.info("User profile updated successfully", user_id=current_user.id)
        return UserResponse.from_orm(updated_user)
        
    except ValueError as e:
        logger.warning("Invalid profile update data", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Profile update failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed. Please try again."
        )


@router.get(
    "/preferences",
    response_model=ContentPreferences,
    dependencies=[Depends(security)]
)
async def get_content_preferences(
    current_user: User = Depends(get_current_user),
) -> ContentPreferences:
    """
    Get user's content preferences.
    
    Returns content generation preferences including topics,
    posting frequency, tone, and platform settings.
    """
    logger.info("Content preferences requested", user_id=current_user.id)
    return current_user.content_preferences


@router.put(
    "/preferences",
    response_model=ContentPreferences,
    dependencies=[Depends(security)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid preferences data"},
    }
)
async def update_content_preferences(
    preferences: ContentPreferences,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> ContentPreferences:
    """
    Update user's content preferences.
    
    Updates content generation settings including topics of interest,
    posting frequency, tone, and enabled platforms.
    """
    logger.info("Content preferences update", user_id=current_user.id)
    
    try:
        updated_user = await user_service.update_content_preferences(
            current_user.id, preferences
        )
        logger.info("Content preferences updated successfully", user_id=current_user.id)
        return updated_user.content_preferences
        
    except ValueError as e:
        logger.warning("Invalid preferences data", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Preferences update failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Preferences update failed. Please try again."
        )


@router.get(
    "/stats",
    response_model=UserStats,
    dependencies=[Depends(security)]
)
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> UserStats:
    """
    Get user's statistics and metrics.
    
    Returns comprehensive statistics including total posts,
    engagement metrics, and performance insights.
    """
    logger.info("User statistics requested", user_id=current_user.id)
    
    try:
        stats = await user_service.get_user_statistics(current_user.id)
        return stats
        
    except Exception as e:
        logger.error("Failed to fetch user statistics", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch statistics. Please try again."
        )


@router.get(
    "/subscription",
    response_model=dict,
    dependencies=[Depends(security)]
)
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> dict:
    """
    Get user's subscription information.
    
    Returns current subscription tier, usage limits, and billing information.
    """
    logger.info("Subscription info requested", user_id=current_user.id)
    
    try:
        subscription_info = await user_service.get_subscription_info(current_user.id)
        return subscription_info
        
    except Exception as e:
        logger.error("Failed to fetch subscription info", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch subscription information. Please try again."
        )


@router.post(
    "/subscription/upgrade",
    response_model=SuccessResponse,
    dependencies=[Depends(security)],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid subscription tier"},
        402: {"model": ErrorResponse, "description": "Payment required"},
    }
)
async def upgrade_subscription(
    tier: SubscriptionTier,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> SuccessResponse:
    """
    Upgrade user's subscription tier.
    
    Upgrades the user to a higher subscription tier with immediate
    access to additional features and higher usage limits.
    """
    logger.info("Subscription upgrade request", user_id=current_user.id, tier=tier)
    
    try:
        await user_service.upgrade_subscription(current_user.id, tier)
        logger.info("Subscription upgraded successfully", user_id=current_user.id, tier=tier)
        
        return SuccessResponse(
            success=True,
            message=f"Successfully upgraded to {tier.value} plan"
        )
        
    except ValueError as e:
        logger.warning("Invalid subscription upgrade", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Subscription upgrade failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subscription upgrade failed. Please try again."
        )


@router.delete(
    "/account",
    response_model=SuccessResponse,
    dependencies=[Depends(security)],
    responses={
        400: {"model": ErrorResponse, "description": "Account deletion not allowed"},
    }
)
async def delete_account(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> SuccessResponse:
    """
    Delete user account.
    
    Permanently deletes the user account and all associated data.
    This action cannot be undone.
    """
    logger.info("Account deletion request", user_id=current_user.id)
    
    try:
        await user_service.delete_user(current_user.id)
        logger.info("Account deleted successfully", user_id=current_user.id)
        
        return SuccessResponse(
            success=True,
            message="Account deleted successfully"
        )
        
    except ValueError as e:
        logger.warning("Account deletion denied", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Account deletion failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed. Please try again."
        )


@router.post(
    "/account/deactivate",
    response_model=SuccessResponse,
    dependencies=[Depends(security)]
)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> SuccessResponse:
    """
    Deactivate user account.
    
    Temporarily deactivates the account. The user can reactivate
    by logging in again.
    """
    logger.info("Account deactivation request", user_id=current_user.id)
    
    try:
        await user_service.deactivate_user(current_user.id)
        logger.info("Account deactivated successfully", user_id=current_user.id)
        
        return SuccessResponse(
            success=True,
            message="Account deactivated successfully"
        )
        
    except Exception as e:
        logger.error("Account deactivation failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deactivation failed. Please try again."
        )


@router.post(
    "/account/reactivate",
    response_model=SuccessResponse,
    dependencies=[Depends(security)]
)
async def reactivate_account(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> SuccessResponse:
    """
    Reactivate user account.
    
    Reactivates a previously deactivated account and restores
    full functionality.
    """
    logger.info("Account reactivation request", user_id=current_user.id)
    
    try:
        await user_service.reactivate_user(current_user.id)
        logger.info("Account reactivated successfully", user_id=current_user.id)
        
        return SuccessResponse(
            success=True,
            message="Account reactivated successfully"
        )
        
    except Exception as e:
        logger.error("Account reactivation failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account reactivation failed. Please try again."
        )


@router.get(
    "/social-accounts",
    response_model=dict,
    dependencies=[Depends(security)]
)
async def get_connected_social_accounts(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get list of connected social media accounts.
    
    Returns information about all connected social media accounts
    including connection status and last activity.
    """
    logger.info("Social accounts requested", user_id=current_user.id)
    
    # Convert social accounts to serializable format
    social_accounts = {}
    for platform, account in current_user.social_accounts.items():
        social_accounts[platform.value] = {
            "username": account.username,
            "account_id": account.account_id,
            "is_active": account.is_active,
            "last_post_at": account.last_post_at.isoformat() if account.last_post_at else None,
            "connected_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
        }
    
    return {
        "connected_accounts": social_accounts,
        "total_connected": len([acc for acc in current_user.social_accounts.values() if acc.is_active])
    }