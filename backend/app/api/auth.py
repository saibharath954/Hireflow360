# backend/app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.schemas.schemas import Token, UserLogin, ApiResponse
from app.models.models import User, Organization
from app.core.config import settings
import uuid

router = APIRouter()

@router.post("/login", response_model=ApiResponse)
async def login(
    form_data: UserLogin,
    db: Session = Depends(get_db)
):
    # Mock login for demo - in production, validate against database
    user = db.query(User).filter(User.email == form_data.email).first()
    
    if not user:
        # For demo, create a mock user
        org = db.query(Organization).first()
        if not org:
            org = Organization(
                id=uuid.uuid4(),
                name="Alfaleus Technology"
            )
            db.add(org)
            db.commit()
            db.refresh(org)
        
        # Check if admin (mock logic)
        is_admin = "admin" in form_data.email.lower()
        
        user = User(
            id=uuid.uuid4(),
            email=form_data.email,
            name=form_data.email.split("@")[0].replace(".", " ").title(),
            organization_id=org.id,
            role="ADMIN" if is_admin else "RECRUITER",
            hashed_password=get_password_hash("password")  # Default password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # For demo purposes, accept any password
    # In production: if not verify_password(form_data.password, user.hashed_password):
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return ApiResponse(
        success=True,
        data={
            "token": access_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "organization_id": str(user.organization_id),
                "organization_name": user.organization.name,
                "role": user.role,
                "avatar_url": user.avatar_url
            }
        }
    )

@router.post("/logout")
async def logout():
    # In production, you might want to add token to a blacklist
    return {"message": "Successfully logged out"}