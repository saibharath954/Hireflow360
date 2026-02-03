# backend/app/services/export_service.py
"""
Export Service
Handles all business logic related to data export and synchronization.
"""

import io
import csv
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, BinaryIO
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from app.models.models import Candidate, CandidateSkill, Message, Resume, Organization
from app.schemas.schemas import ExportOptions, GoogleSheetsSyncConfig
from app.core.logging import logger


class ExportService:
    """Service for export-related operations"""
    
    @staticmethod
    def export_candidates_to_excel(
        db: Session,
        organization_id: uuid.UUID,
        options: ExportOptions
    ) -> BinaryIO:
        """
        Export candidates to Excel format.
        
        Args:
            db: Database session
            organization_id: Organization ID
            options: Export options
            
        Returns:
            Binary Excel file
        """
        try:
            # Get candidates with filtering
            candidates = ExportService._get_candidates_for_export(db, organization_id, options)
            
            # Prepare data for export
            data = ExportService._prepare_export_data(candidates, options)
            
            # Create Excel workbook
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Main candidates sheet
                df_main = pd.DataFrame(data['candidates'])
                df_main.to_excel(writer, sheet_name='Candidates', index=False)
                
                # Format the worksheet
                worksheet = writer.sheets['Candidates']
                ExportService._format_excel_worksheet(worksheet, df_main)
                
                # Skills sheet
                if any('skills' in candidate for candidate in data['candidates']):
                    skills_data = []
                    for candidate in candidates:
                        skills = [skill.skill for skill in candidate.skills]
                        if skills:
                            skills_data.append({
                                'Candidate': candidate.name,
                                'Candidate Email': candidate.email,
                                'Skills': ', '.join(skills)
                            })
                    
                    if skills_data:
                        df_skills = pd.DataFrame(skills_data)
                        df_skills.to_excel(writer, sheet_name='Skills', index=False)
                
                # Messages sheet (if requested)
                if options.include_messages:
                    messages_data = ExportService._prepare_messages_data(candidates)
                    if messages_data:
                        df_messages = pd.DataFrame(messages_data)
                        df_messages.to_excel(writer, sheet_name='Messages', index=False)
            
            output.seek(0)
            logger.info(f"Exported {len(candidates)} candidates to Excel")
            return output
            
        except Exception as e:
            logger.error(f"Failed to export to Excel: {str(e)}")
            raise
    
    @staticmethod
    def export_candidates_to_csv(
        db: Session,
        organization_id: uuid.UUID,
        options: ExportOptions
    ) -> BinaryIO:
        """
        Export candidates to CSV format.
        
        Args:
            db: Database session
            organization_id: Organization ID
            options: Export options
            
        Returns:
            Binary CSV file
        """
        try:
            # Get candidates with filtering
            candidates = ExportService._get_candidates_for_export(db, organization_id, options)
            
            # Prepare data for export
            data = ExportService._prepare_export_data(candidates, options)
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            if data['candidates']:
                headers = data['candidates'][0].keys()
                writer.writerow(headers)
                
                # Write data
                for row in data['candidates']:
                    writer.writerow(row.values())
            
            csv_data = output.getvalue().encode('utf-8')
            output.close()
            
            logger.info(f"Exported {len(candidates)} candidates to CSV")
            return io.BytesIO(csv_data)
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {str(e)}")
            raise
    
    @staticmethod
    def export_candidates_to_json(
        db: Session,
        organization_id: uuid.UUID,
        options: ExportOptions
    ) -> Dict[str, Any]:
        """
        Export candidates to JSON format.
        
        Args:
            db: Database session
            organization_id: Organization ID
            options: Export options
            
        Returns:
            JSON data structure
        """
        try:
            # Get candidates with filtering
            candidates = ExportService._get_candidates_for_export(db, organization_id, options)
            
            # Prepare comprehensive data
            export_data = {
                "metadata": {
                    "exported_at": datetime.utcnow().isoformat(),
                    "total_candidates": len(candidates),
                    "format": "json",
                    "organization_id": str(organization_id)
                },
                "candidates": []
            }
            
            for candidate in candidates:
                candidate_data = {
                    "id": str(candidate.id),
                    "name": candidate.name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                    "years_experience": candidate.years_experience,
                    "skills": [skill.skill for skill in candidate.skills],
                    "current_company": candidate.current_company,
                    "education": candidate.education,
                    "location": candidate.location,
                    "portfolio_url": candidate.portfolio_url,
                    "notice_period": candidate.notice_period,
                    "expected_salary": candidate.expected_salary,
                    "status": candidate.status,
                    "overall_confidence": candidate.overall_confidence,
                    "created_at": candidate.created_at.isoformat(),
                    "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
                    "last_message_at": candidate.last_message_at.isoformat() if candidate.last_message_at else None,
                    "conversation_state": candidate.conversation_state
                }
                
                # Include parsed fields
                if options.fields:
                    candidate_data["parsed_fields"] = [
                        {
                            "name": pf.name,
                            "value": pf.value,
                            "confidence": pf.confidence,
                            "source": pf.source
                        }
                        for pf in candidate.parsed_fields
                    ]
                
                # Include messages if requested
                if options.include_messages:
                    candidate_data["messages"] = [
                        {
                            "id": str(msg.id),
                            "direction": msg.direction,
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat(),
                            "status": msg.status,
                            "classification": msg.classification,
                            "requires_hr_review": msg.requires_hr_review
                        }
                        for msg in candidate.messages
                    ]
                
                export_data["candidates"].append(candidate_data)
            
            logger.info(f"Exported {len(candidates)} candidates to JSON")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export to JSON: {str(e)}")
            raise
    
    @staticmethod
    def sync_to_google_sheets(
        db: Session,
        organization_id: uuid.UUID,
        config: GoogleSheetsSyncConfig
    ) -> Dict[str, Any]:
        """
        Sync candidates to Google Sheets.
        
        Args:
            db: Database session
            organization_id: Organization ID
            config: Google Sheets configuration
            
        Returns:
            Sync result
        """
        try:
            # Get candidates
            candidates = db.query(Candidate).options(
                joinedload(Candidate.skills)
            ).filter(
                Candidate.organization_id == organization_id,
                Candidate.is_active == True
            ).all()
            
            # Prepare data for Google Sheets
            sheet_data = []
            
            # Headers
            headers = [
                "Name", "Email", "Phone", "Experience", "Skills",
                "Current Company", "Education", "Location", "Status",
                "Overall Confidence", "Last Updated"
            ]
            sheet_data.append(headers)
            
            # Data rows
            for candidate in candidates:
                skills = ', '.join([skill.skill for skill in candidate.skills])
                
                row = [
                    candidate.name,
                    candidate.email,
                    candidate.phone or "",
                    str(candidate.years_experience) if candidate.years_experience else "",
                    skills,
                    candidate.current_company or "",
                    candidate.education or "",
                    candidate.location or "",
                    candidate.status,
                    str(round(candidate.overall_confidence, 2)) if candidate.overall_confidence else "0",
                    candidate.updated_at.strftime("%Y-%m-%d %H:%M") if candidate.updated_at else ""
                ]
                sheet_data.append(row)
            
            # In a real implementation, this would call Google Sheets API
            # For now, mock the response
            
            sync_result = {
                "success": True,
                "synced_at": datetime.utcnow().isoformat(),
                "sheet_id": config.sheet_id,
                "sheet_name": config.sheet_name,
                "rows_synced": len(candidates),
                "data_preview": sheet_data[:3] if len(sheet_data) > 3 else sheet_data
            }
            
            logger.info(f"Synced {len(candidates)} candidates to Google Sheets: {config.sheet_id}")
            return sync_result
            
        except Exception as e:
            logger.error(f"Failed to sync to Google Sheets: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "synced_at": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def generate_export_filename(format_type: str) -> str:
        """Generate filename for export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "xlsx":
            return f"candidates_export_{timestamp}.xlsx"
        elif format_type == "csv":
            return f"candidates_export_{timestamp}.csv"
        elif format_type == "json":
            return f"candidates_export_{timestamp}.json"
        else:
            return f"candidates_export_{timestamp}.{format_type}"
    
    # Helper Methods
    
    @staticmethod
    def _get_candidates_for_export(
        db: Session,
        organization_id: uuid.UUID,
        options: ExportOptions
    ) -> List[Candidate]:
        """Get candidates for export with appropriate filtering and loading."""
        query = db.query(Candidate).options(
            joinedload(Candidate.skills),
            joinedload(Candidate.parsed_fields)
        ).filter(
            Candidate.organization_id == organization_id,
            Candidate.is_active == True
        )
        
        # Filter by candidate IDs if specified
        if options.candidate_ids and len(options.candidate_ids) > 0:
            query = query.filter(Candidate.id.in_(options.candidate_ids))
        
        # Load messages if requested
        if options.include_messages:
            query = query.options(joinedload(Candidate.messages))
        
        return query.order_by(Candidate.created_at.desc()).all()
    
    @staticmethod
    def _prepare_export_data(
        candidates: List[Candidate],
        options: ExportOptions
    ) -> Dict[str, Any]:
        """Prepare data for export."""
        candidates_data = []
        
        # Default fields if not specified
        if not options.fields:
            options.fields = [
                "name", "email", "phone", "years_experience", "skills",
                "current_company", "education", "location", "status",
                "overall_confidence", "created_at"
            ]
        
        for candidate in candidates:
            candidate_dict = {}
            
            # Map field names to candidate attributes
            field_mapping = {
                "name": ("Name", candidate.name),
                "email": ("Email", candidate.email),
                "phone": ("Phone", candidate.phone or ""),
                "years_experience": ("Experience", 
                    str(candidate.years_experience) if candidate.years_experience else ""),
                "skills": ("Skills", 
                    ", ".join([skill.skill for skill in candidate.skills])),
                "current_company": ("Current Company", candidate.current_company or ""),
                "education": ("Education", candidate.education or ""),
                "location": ("Location", candidate.location or ""),
                "status": ("Status", candidate.status),
                "overall_confidence": ("Confidence", 
                    str(round(candidate.overall_confidence, 2)) if candidate.overall_confidence else "0"),
                "created_at": ("Created At", 
                    candidate.created_at.strftime("%Y-%m-%d %H:%M")),
                "updated_at": ("Updated At",
                    candidate.updated_at.strftime("%Y-%m-%d %H:%M") if candidate.updated_at else ""),
                "last_message_at": ("Last Message",
                    candidate.last_message_at.strftime("%Y-%m-%d %H:%M") if candidate.last_message_at else ""),
                "portfolio_url": ("Portfolio URL", candidate.portfolio_url or ""),
                "notice_period": ("Notice Period", candidate.notice_period or ""),
                "expected_salary": ("Expected Salary", candidate.expected_salary or "")
            }
            
            # Add fields based on options
            for field in options.fields:
                if field in field_mapping:
                    column_name, value = field_mapping[field]
                    candidate_dict[column_name] = value
            
            # Add parsed fields if requested
            if "parsed_fields" in options.fields:
                parsed_info = []
                for pf in candidate.parsed_fields:
                    parsed_info.append(f"{pf.name}: {pf.value} ({pf.confidence}%)")
                candidate_dict["Parsed Fields"] = "; ".join(parsed_info)
            
            candidates_data.append(candidate_dict)
        
        return {"candidates": candidates_data}
    
    @staticmethod
    def _prepare_messages_data(candidates: List[Candidate]) -> List[Dict[str, Any]]:
        """Prepare messages data for export."""
        messages_data = []
        
        for candidate in candidates:
            for message in candidate.messages:
                messages_data.append({
                    "Candidate": candidate.name,
                    "Candidate Email": candidate.email,
                    "Direction": message.direction,
                    "Timestamp": message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "Content": message.content[:500],  # Limit content length
                    "Status": message.status,
                    "Classification": message.classification or "",
                    "Requires HR Review": "Yes" if message.requires_hr_review else "No"
                })
        
        return messages_data
    
    @staticmethod
    def _format_excel_worksheet(worksheet, df):
        """Format Excel worksheet for better readability."""
        # Set column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Style header row
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        # Freeze header row
        worksheet.freeze_panes = "A2"
        
        # Add filters
        worksheet.auto_filter.ref = worksheet.dimensions