# backend/app/api/auth.py
"""
Production-Grade Authentication Module
- Secure login with password hashing and verification
- Account lockout and brute force protection
- Session management with JWT tokens
- Comprehensive logging and audit trails
- Rate limiting for security
"""

import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    create_access_token, 
    get_password_hash,
    create_refresh_token,
    verify_token,
    generate_password_reset_token,
    verify_password_reset_token
)
from app.schemas.schemas import (
    Token, 
    UserLogin, 
    ApiResponse,
    TokenRefresh,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserCreate,
    UserResponse
)
from app.models.models import User, Organization, LoginAttempt, AuditLog
from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.core.email import send_password_reset_email, send_welcome_email
from app.utils.validators import validate_email_format, validate_password_strength
from app.utils.logging import audit_log

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# In-memory cache for login attempts (use Redis in production)
_failed_attempts_cache: Dict[str, List[datetime]] = {}
_account_lock_cache: Dict[str, datetime] = {}

class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass

def check_account_lock(email: str) -> Tuple[bool, Optional[timedelta]]:
    """
    Check if account is locked due to too many failed attempts
    Returns: (is_locked, time_remaining)
    """
    if email in _account_lock_cache:
        lock_time = _account_lock_cache[email]
        if datetime.utcnow() < lock_time:
            time_remaining = lock_time - datetime.utcnow()
            return True, time_remaining
        else:
            # Lock expired, remove from cache
            del _account_lock_cache[email]
            if email in _failed_attempts_cache:
                del _failed_attempts_cache[email]
    
    return False, None

def track_failed_attempt(email: str, db: Session, ip_address: str, user_agent: str) -> None:
    """
    Track failed login attempt and lock account if threshold exceeded
    """
    now = datetime.utcnow()
    
    # Add to in-memory cache
    if email not in _failed_attempts_cache:
        _failed_attempts_cache[email] = []
    
    _failed_attempts_cache[email].append(now)
    
    # Keep only attempts within the lock window
    window_start = now - timedelta(minutes=settings.ACCOUNT_LOCK_WINDOW_MINUTES)
    _failed_attempts_cache[email] = [
        attempt for attempt in _failed_attempts_cache[email] 
        if attempt > window_start
    ]
    
    # Store in database for audit
    login_attempt = LoginAttempt(
        id=uuid.uuid4(),
        email=email,
        success=False,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=now
    )
    db.add(login_attempt)
    db.commit()
    
    # Check if threshold exceeded
    if len(_failed_attempts_cache[email]) >= settings.MAX_LOGIN_ATTEMPTS:
        lock_until = now + timedelta(minutes=settings.ACCOUNT_LOCK_DURATION_MINUTES)
        _account_lock_cache[email] = lock_until
        
        # Log account lock event
        audit_log(
            db=db,
            user_id=None,
            action="ACCOUNT_LOCKED",
            resource_type="USER",
            resource_id=None,
            details={
                "email": email,
                "reason": "too_many_failed_attempts",
                "lock_until": lock_until.isoformat(),
                "failed_attempts": len(_failed_attempts_cache[email])
            },
            ip_address=ip_address
        )

def clear_failed_attempts(email: str) -> None:
    """Clear failed attempts after successful login"""
    if email in _failed_attempts_cache:
        del _failed_attempts_cache[email]
    if email in _account_lock_cache:
        del _account_lock_cache[email]

def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client information from request"""
    return {
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_real_ip": request.headers.get("x-real-ip")
    }

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token
    """
    try:
        payload = verify_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token is blacklisted (for logout functionality)
        # In production, you might want to check Redis or database
        
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to check if current user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency to check if current user is admin"""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user

@router.post("/login", response_model=ApiResponse)
@rate_limiter(limit=5, window=60)  # 5 attempts per minute per IP
async def login(
    request: Request,
    user_data: UserLogin,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Authenticate user and return JWT tokens
    """
    client_info = get_client_info(request)
    ip_address = client_info["ip_address"]
    
    try:
        # Validate input
        # if not validate_email_format(user_data.email):
        #     raise HTTPException(
        #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        #         detail="Invalid email format"
        #     )
        
        # Check account lock
        is_locked, time_remaining = check_account_lock(user_data.email)
        if is_locked:
            remaining_minutes = int(time_remaining.total_seconds() / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked. Try again in {remaining_minutes} minutes."
            )
        
        # Find user in database
        user = db.query(User).filter(
            User.email == user_data.email
        ).first()
        
        if not user:
            # Don't reveal that user doesn't exist (security best practice)
            track_failed_attempt(user_data.email, db, ip_address, client_info["user_agent"])
            time.sleep(1)  # Add delay to prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        # Verify password
        if not verify_password(user_data.password, user.hashed_password):
            track_failed_attempt(user_data.email, db, ip_address, client_info["user_agent"])
            
            # Log failed attempt
            audit_log(
                db=db,
                user_id=user.id,
                action="LOGIN_FAILED",
                resource_type="USER",
                resource_id=user.id,
                details={
                    "reason": "invalid_password",
                    "ip_address": ip_address
                },
                ip_address=ip_address
            )
            
            time.sleep(1)  # Add delay to prevent timing attacks
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Clear failed attempts on successful login
        clear_failed_attempts(user_data.email)
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role},
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )
        
        # Update last login time
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Log successful login attempt
        login_attempt = LoginAttempt(
            id=uuid.uuid4(),
            email=user.email,
            success=True,
            ip_address=ip_address,
            user_agent=client_info["user_agent"],
            created_at=datetime.utcnow()
        )
        db.add(login_attempt)
        
        # Audit log for successful login
        audit_log(
            db=db,
            user_id=user.id,
            action="LOGIN_SUCCESS",
            resource_type="USER",
            resource_id=user.id,
            details={
                "ip_address": ip_address,
                "user_agent": client_info["user_agent"]
            },
            ip_address=ip_address
        )
        
        # Prepare response
        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            organization_id=str(user.organization_id),
            organization_name=user.organization.name,
            role=user.role,
            is_active=user.is_active,
            last_login=user.last_login
        )
        
        response_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds()),
            "user": user_response.dict()
        }
        
        return ApiResponse(
            success=True,
            data=response_data,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log unexpected errors but don't expose details to client
        print(f"Login error: {str(e)}")  # Replace with proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during authentication"
        )

@router.post("/refresh", response_model=ApiResponse)
async def refresh_token(
    refresh_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        payload = verify_token(refresh_data.refresh_token, is_refresh=True)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role},
            expires_delta=access_token_expires
        )
        
        response_data = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds())
        }
        
        return ApiResponse(
            success=True,
            data=response_data,
            message="Token refreshed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )

@router.post("/logout", response_model=ApiResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout user (add token to blacklist in production)
    """
    client_info = get_client_info(request)
    
    # In production, add token to blacklist (Redis/database)
    # token = request.headers.get("Authorization").replace("Bearer ", "")
    # add_to_blacklist(token, current_user.id)
    
    # Log logout action
    audit_log(
        db=db,
        user_id=current_user.id,
        action="LOGOUT",
        resource_type="USER",
        resource_id=current_user.id,
        details={
            "ip_address": client_info["ip_address"],
            "user_agent": client_info["user_agent"]
        },
        ip_address=client_info["ip_address"]
    )
    
    return ApiResponse(
        success=True,
        message="Successfully logged out"
    )

@router.post("/password-reset-request", response_model=ApiResponse)
@rate_limiter(limit=3, window=3600)  # 3 requests per hour per IP
async def password_reset_request(
    request: Request,
    reset_data: PasswordResetRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Request password reset (sends email with reset link)
    """
    client_info = get_client_info(request)
    
    # Find user by email
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if user and user.is_active:
        # Generate reset token (valid for 1 hour)
        reset_token = generate_password_reset_token(user.email)
        
        # Store token in database (or Redis in production)
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # Send reset email (in background)
        if background_tasks and settings.SMTP_ENABLED:
            background_tasks.add_task(
                send_password_reset_email,
                email=user.email,
                name=user.name,
                reset_token=reset_token
            )
        
        # Log reset request
        audit_log(
            db=db,
            user_id=user.id,
            action="PASSWORD_RESET_REQUEST",
            resource_type="USER",
            resource_id=user.id,
            details={
                "ip_address": client_info["ip_address"]
            },
            ip_address=client_info["ip_address"]
        )
    
    # Always return success (don't reveal if email exists)
    return ApiResponse(
        success=True,
        message="If an account exists with this email, you will receive password reset instructions."
    )

@router.post("/password-reset-confirm", response_model=ApiResponse)
@rate_limiter(limit=5, window=3600)  # 5 attempts per hour per IP
async def password_reset_confirm(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token and new password
    """
    # Verify reset token
    email = verify_password_reset_token(reset_data.reset_token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find user
    user = db.query(User).filter(
        User.email == email,
        User.password_reset_token == reset_data.reset_token,
        User.password_reset_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Validate new password
    if not validate_password_strength(reset_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password does not meet strength requirements"
        )
    
    # Update password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.updated_at = datetime.utcnow()
    db.commit()
    
    # Clear any failed login attempts for this user
    clear_failed_attempts(user.email)
    
    # Log password reset
    audit_log(
        db=db,
        user_id=user.id,
        action="PASSWORD_RESET_SUCCESS",
        resource_type="USER",
        resource_id=user.id,
        details={},
        ip_address=None
    )
    
    return ApiResponse(
        success=True,
        message="Password has been reset successfully"
    )

@router.get("/me", response_model=ApiResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    """
    user_response = UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        organization_id=str(current_user.organization_id),
        organization_name=current_user.organization.name,
        role=current_user.role,
        is_active=current_user.is_active,
        last_login=current_user.last_login
    )
    
    return ApiResponse(
        success=True,
        data=user_response.dict()
    )

@router.post("/register", response_model=ApiResponse)
async def register_user(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Register a new user (typically for admin use)
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Validate email
    # if not validate_email_format(user_data.email):
    #     raise HTTPException(
    #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #         detail="Invalid email format"
    #     )
    
    # Validate password
    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password does not meet strength requirements"
        )
    
    # Find or create organization
    organization = db.query(Organization).filter(
        Organization.name == user_data.organization_name
    ).first()
    
    if not organization:
        organization = Organization(
            id=uuid.uuid4(),
            name=user_data.organization_name
        )
        db.add(organization)
        db.commit()
        db.refresh(organization)
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        id=uuid.uuid4(),
        email=user_data.email,
        name=user_data.name,
        hashed_password=hashed_password,
        organization_id=organization.id,
        role=user_data.role,
        is_active=True,
        created_at=datetime.utcnow()
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Send welcome email
    if background_tasks and settings.SMTP_ENABLED:
        background_tasks.add_task(
            send_welcome_email,
            email=user.email,
            name=user.name,
            organization_name=organization.name
        )
    
    # Audit log
    client_info = get_client_info(request)
    audit_log(
        db=db,
        user_id=user.id,
        action="USER_REGISTERED",
        resource_type="USER",
        resource_id=user.id,
        details={
            "registered_by": "self" if not request.user else str(request.user.id),
            "ip_address": client_info["ip_address"]
        },
        ip_address=client_info["ip_address"]
    )
    
    user_response = UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        organization_id=str(user.organization_id),
        organization_name=organization.name,
        role=user.role,
        is_active=user.is_active,
        last_login=user.last_login
    )
    
    return ApiResponse(
        success=True,
        data=user_response.dict(),
        message="User registered successfully"
    )

@router.get("/validate-token", response_model=ApiResponse)
async def validate_token(
    token: str = Depends(oauth2_scheme)
):
    """
    Validate JWT token
    """
    try:
        payload = verify_token(token)
        if payload:
            return ApiResponse(
                success=True,
                data={"valid": True, "exp": payload.get("exp")},
                message="Token is valid"
            )
        else:
            return ApiResponse(
                success=False,
                data={"valid": False},
                message="Token is invalid or expired"
            )
    except Exception:
        return ApiResponse(
            success=False,
            data={"valid": False},
            message="Token validation failed"
        )