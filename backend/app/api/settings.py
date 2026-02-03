# backend/app/api/settings.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.schemas.schemas import ApiResponse, AppSettings

router = APIRouter()

# Mock settings (in production, store in database)
mock_settings = {
    "mode": "mock",
    "theme": "light",
    "default_intent_templates": [
        "Introduce our company and ask about their interest in backend roles",
        "Ask about availability for a frontend developer position",
        "Inquire about their notice period and salary expectations",
        "Follow up on previous conversation about the role"
    ]
}

@router.get("", response_model=ApiResponse)
async def get_settings():
    """Get app settings"""
    return ApiResponse(success=True, data=mock_settings)

@router.put("", response_model=ApiResponse)
async def update_settings(
    settings: AppSettings
):
    """Update app settings"""
    global mock_settings
    mock_settings = settings.dict()
    return ApiResponse(success=True, data=mock_settings)