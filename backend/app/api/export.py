# backend/app/api/export.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional
import io
import csv
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_recruiter_user
from app.schemas.schemas import ApiResponse, ExportOptions
from app.models.models import User, Candidate, CandidateSkill

router = APIRouter()

@router.post("/excel")
async def export_excel(
    options: ExportOptions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Export candidates to Excel"""
    query = db.query(Candidate).filter(
        Candidate.organization_id == current_user.organization_id
    )
    
    if options.candidate_ids and len(options.candidate_ids) > 0:
        query = query.filter(Candidate.id.in_(options.candidate_ids))
    
    candidates = query.all()
    
    # Prepare data
    data = []
    for candidate in candidates:
        skills = [skill.skill for skill in candidate.skills]
        
        row = {
            "Name": candidate.name,
            "Email": candidate.email,
            "Phone": candidate.phone or "",
            "Experience": candidate.years_experience or "",
            "Skills": ", ".join(skills),
            "Current Company": candidate.current_company or "",
            "Education": candidate.education or "",
            "Location": candidate.location or "",
            "Status": candidate.status,
            "Portfolio URL": candidate.portfolio_url or "",
            "Notice Period": candidate.notice_period or "",
            "Expected Salary": candidate.expected_salary or "",
            "Overall Confidence": candidate.overall_confidence,
            "Created At": candidate.created_at.isoformat(),
            "Last Updated": candidate.updated_at.isoformat() if candidate.updated_at else ""
        }
        data.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Candidates')
    
    output.seek(0)
    
    # Return as downloadable file
    filename = f"candidates_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/csv")
async def export_csv(
    options: ExportOptions,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Export candidates to CSV"""
    query = db.query(Candidate).filter(
        Candidate.organization_id == current_user.organization_id
    )
    
    if options.candidate_ids and len(options.candidate_ids) > 0:
        query = query.filter(Candidate.id.in_(options.candidate_ids))
    
    candidates = query.all()
    
    # Prepare CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    headers = ["Name", "Email", "Phone", "Experience", "Skills", "Company", "Location", "Status"]
    writer.writerow(headers)
    
    # Write data
    for candidate in candidates:
        skills = [skill.skill for skill in candidate.skills]
        writer.writerow([
            candidate.name,
            candidate.email,
            candidate.phone or "",
            candidate.years_experience or "",
            "; ".join(skills),
            candidate.current_company or "",
            candidate.location or "",
            candidate.status
        ])
    
    output.seek(0)
    
    # Return as downloadable file
    filename = f"candidates_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/google-sheets/sync", response_model=ApiResponse)
async def sync_google_sheets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_recruiter_user)
):
    """Mock Google Sheets sync"""
    # Count candidates
    count = db.query(Candidate).filter(
        Candidate.organization_id == current_user.organization_id
    ).count()
    
    # Mock 20% failure rate
    import random
    if random.random() < 0.2:
        return ApiResponse(
            success=False,
            error="Failed to connect to Google Sheets. Please check your credentials."
        )
    
    return ApiResponse(
        success=True,
        data={
            "syncedAt": datetime.utcnow().isoformat(),
            "rowCount": count
        }
    )