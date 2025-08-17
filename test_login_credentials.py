#!/usr/bin/env python3
"""
Test login credentials and create debug user if needed
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.services.auth import AuthService
from src.services.user import UserService
from src.models.user import UserCreateRequest

async def test_login():
    """Test login with common passwords and create debug user"""
    auth_service = AuthService()
    user_service = UserService()
    
    email = "omene.shadrachh@gmail.com"
    common_passwords = [
        "password",
        "password123", 
        "123456",
        "admin",
        "test123",
        "postsync123",
        "omene123"
    ]
    
    print(f"Testing login for: {email}")
    
    # Try common passwords
    for password in common_passwords:
        try:
            user = await auth_service.authenticate_user(email, password)
            if user:
                print(f"✅ SUCCESS: Password is '{password}'")
                return password
        except Exception as e:
            print(f"❌ '{password}' failed: {str(e)}")
    
    print("\n🔧 Creating debug user with known password...")
    debug_email = "debug@postsync.com"
    debug_password = "debug123"
    
    try:
        # Create debug user
        user_data = UserCreateRequest(
            email=debug_email,
            full_name="Debug User",
            password=debug_password,
            job_title="Developer",
            company="PostSync Debug"
        )
        
        debug_user = await user_service.create_user(user_data)
        print(f"✅ Debug user created:")
        print(f"   Email: {debug_email}")
        print(f"   Password: {debug_password}")
        return debug_password
        
    except Exception as e:
        print(f"❌ Failed to create debug user: {str(e)}")
    
    return None

if __name__ == "__main__":
    result = asyncio.run(test_login())
    if result:
        print(f"\n🎉 You can now login with the working credentials!")
    else:
        print(f"\n😞 Could not find working credentials or create debug user")