"""
Tests for Authentication API Endpoints

This module contains tests for user authentication, registration,
and authorization functionality.
"""

import pytest
from fastapi import status
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from src.models.user import User


class TestAuthenticationEndpoints:
    """Test authentication-related endpoints."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient, mock_firestore_client):
        """Test successful user registration."""
        # Mock that user doesn't exist
        mock_firestore_client.get_user_by_email.return_value = None
        mock_firestore_client.create_user.return_value = User(
            id="new-user-123",
            email="newuser@example.com",
            full_name="New User"
        )
        
        response = await async_client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User",
            "job_title": "AI Engineer",
            "company": "Tech Corp"
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_register_existing_user(self, async_client: AsyncClient, mock_firestore_client, mock_user):
        """Test registration with existing email."""
        # Mock that user already exists
        mock_firestore_client.get_user_by_email.return_value = mock_user
        
        response = await async_client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "securepassword123",
            "full_name": "Test User"
        })
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_invalid_data(self, async_client: AsyncClient):
        """Test registration with invalid data."""
        response = await async_client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "short",
            "full_name": ""
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, mock_user):
        """Test successful login."""
        with patch("src.services.auth.AuthService.authenticate_user") as mock_auth:
            with patch("src.services.user.UserService.update_last_login") as mock_update:
                mock_auth.return_value = mock_user
                mock_update.return_value = None
                
                response = await async_client.post("/api/v1/auth/login", json={
                    "email": "test@example.com",
                    "password": "correctpassword"
                })
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"
                assert data["user_id"] == mock_user.id
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client: AsyncClient):
        """Test login with invalid credentials."""
        with patch("src.services.auth.AuthService.authenticate_user") as mock_auth:
            mock_auth.return_value = None
            
            response = await async_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid email or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, async_client: AsyncClient, mock_user):
        """Test login with inactive user account."""
        mock_user.is_active = False
        
        with patch("src.services.auth.AuthService.authenticate_user") as mock_auth:
            mock_auth.return_value = mock_user
            
            response = await async_client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "correctpassword"
            })
            
            assert response.status_code == status.HTTP_423_LOCKED
            assert "deactivated" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient):
        """Test successful token refresh."""
        with patch("src.services.auth.AuthService.refresh_access_token") as mock_refresh:
            mock_refresh.return_value = "new-access-token"
            
            response = await async_client.post("/api/v1/auth/refresh", json={
                "refresh_token": "valid-refresh-token"
            })
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "new-access-token"
            assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test token refresh with invalid token."""
        with patch("src.services.auth.AuthService.refresh_access_token") as mock_refresh:
            mock_refresh.side_effect = Exception("Invalid token")
            
            response = await async_client.post("/api/v1/auth/refresh", json={
                "refresh_token": "invalid-refresh-token"
            })
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_logout_success(self, async_client: AsyncClient, auth_headers):
        """Test successful logout."""
        with patch("src.services.auth.AuthService.logout_user") as mock_logout:
            mock_logout.return_value = None
            
            response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True
    
    @pytest.mark.asyncio
    async def test_logout_unauthorized(self, async_client: AsyncClient):
        """Test logout without authentication."""
        response = await async_client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_password_reset_request(self, async_client: AsyncClient):
        """Test password reset request."""
        with patch("src.services.auth.AuthService.request_password_reset") as mock_reset:
            mock_reset.return_value = None
            
            response = await async_client.post("/api/v1/auth/password-reset", json={
                "email": "test@example.com"
            })
            
            assert response.status_code == status.HTTP_200_OK
            assert "sent" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_password_reset_confirm_success(self, async_client: AsyncClient):
        """Test successful password reset confirmation."""
        with patch("src.services.auth.AuthService.confirm_password_reset") as mock_confirm:
            mock_confirm.return_value = None
            
            response = await async_client.post("/api/v1/auth/password-reset/confirm", json={
                "token": "valid-reset-token",
                "new_password": "newpassword123"
            })
            
            assert response.status_code == status.HTTP_200_OK
            assert "successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_password_reset_confirm_invalid_token(self, async_client: AsyncClient):
        """Test password reset confirmation with invalid token."""
        with patch("src.services.auth.AuthService.confirm_password_reset") as mock_confirm:
            mock_confirm.side_effect = Exception("Invalid token")
            
            response = await async_client.post("/api/v1/auth/password-reset/confirm", json={
                "token": "invalid-reset-token",
                "new_password": "newpassword123"
            })
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_change_password_success(self, async_client: AsyncClient, auth_headers):
        """Test successful password change."""
        with patch("src.services.auth.AuthService.change_password") as mock_change:
            mock_change.return_value = None
            
            response = await async_client.post("/api/v1/auth/change-password", 
                headers=auth_headers,
                json={
                    "current_password": "currentpassword",
                    "new_password": "newpassword123"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert "successfully" in response.json()["message"]
    
    @pytest.mark.asyncio
    async def test_change_password_invalid_current(self, async_client: AsyncClient, auth_headers):
        """Test password change with invalid current password."""
        with patch("src.services.auth.AuthService.change_password") as mock_change:
            mock_change.side_effect = ValueError("Invalid current password")
            
            response = await async_client.post("/api/v1/auth/change-password",
                headers=auth_headers,
                json={
                    "current_password": "wrongpassword",
                    "new_password": "newpassword123"
                }
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, async_client: AsyncClient, auth_headers, mock_user):
        """Test getting current user information."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == mock_user.id
        assert data["email"] == mock_user.email
    
    @pytest.mark.asyncio
    async def test_social_connect_linkedin(self, async_client: AsyncClient, auth_headers):
        """Test connecting LinkedIn account."""
        with patch("src.services.auth.AuthService.connect_social_account") as mock_connect:
            mock_connect.return_value = {
                "account_id": "linkedin-123",
                "username": "testuser",
                "connected_at": "2024-01-01T12:00:00Z"
            }
            
            response = await async_client.post("/api/v1/auth/social/connect",
                headers=auth_headers,
                json={
                    "platform": "linkedin",
                    "authorization_code": "auth-code-123",
                    "redirect_uri": "https://app.postsync.com/callback"
                }
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["platform"] == "linkedin"
            assert data["is_connected"] is True
    
    @pytest.mark.asyncio
    async def test_social_disconnect(self, async_client: AsyncClient, auth_headers):
        """Test disconnecting social media account."""
        with patch("src.services.auth.AuthService.disconnect_social_account") as mock_disconnect:
            mock_disconnect.return_value = None
            
            response = await async_client.delete("/api/v1/auth/social/linkedin/disconnect",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert "disconnected" in response.json()["message"]


class TestAuthenticationHelpers:
    """Test authentication helper functions."""
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        from src.utils.auth import hash_password, verify_password
        
        password = "testpassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    def test_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        from src.utils.auth import create_access_token, verify_token
        
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
    
    def test_invalid_token_verification(self):
        """Test verification of invalid tokens."""
        from src.utils.auth import verify_token
        
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_permission_checking(self, mock_user, mock_admin_user):
        """Test permission checking functionality."""
        from src.utils.auth import check_permission
        
        # Regular user permissions
        assert check_permission(mock_user, "read_own_content") is True
        assert check_permission(mock_user, "moderate_content") is False
        
        # Admin permissions
        assert check_permission(mock_admin_user, "read_own_content") is True
        assert check_permission(mock_admin_user, "moderate_content") is True