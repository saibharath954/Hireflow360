# backend/app/api/api.py
from fastapi import APIRouter
from app.api import (
    auth, candidates, resumes, messaging,
    jobs, export, dashboard, settings
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(messaging.router, prefix="/messaging", tags=["messaging"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(export.router, prefix="/export", tags=["export"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])