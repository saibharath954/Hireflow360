"""
Security utilities for authentication and authorization
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Union, Any, Dict

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import secrets

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT secret keys (store in environment variables in production)
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
REFRESH_SECRET_KEY = settings.REFRESH_SECRET_KEY

# For password reset tokens (use Fernet symmetric encryption)
fernet_key = settings.FERNET_KEY.encode() if settings.FERNET_KEY else Fernet.generate_key()
cipher_suite = Fernet(fernet_key)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify an access token.
    Wrapper around verify_token for access tokens.
    """
    return verify_token(token, is_refresh=False)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, is_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token and return payload if valid
    """
    try:
        secret_key = REFRESH_SECRET_KEY if is_refresh else SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        
        # Check token type
        token_type = payload.get("type")
        if is_refresh and token_type != "refresh":
            return None
        elif not is_refresh and token_type != "access":
            return None
            
        return payload
    except JWTError:
        return None

def generate_password_reset_token(email: str) -> str:
    """Generate a secure password reset token"""
    # Create a token with timestamp
    data = f"{email}:{datetime.utcnow().timestamp()}"
    token = cipher_suite.encrypt(data.encode())
    return token.decode()

def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify and extract email from password reset token"""
    try:
        data = cipher_suite.decrypt(token.encode()).decode()
        email, timestamp_str = data.split(":")
        timestamp = float(timestamp_str)
        
        # Check if token is expired (1 hour)
        token_age = datetime.utcnow().timestamp() - timestamp
        if token_age > 3600:  # 1 hour in seconds
            return None
            
        return email
    except Exception:
        return None

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)