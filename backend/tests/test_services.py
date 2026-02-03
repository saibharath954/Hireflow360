# backend/tests/test_services.py
"""
Test suite for service classes.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.services.candidate_service import CandidateService
from app.services.resume_service import ResumeService
from app.services.messaging_service import MessagingService
from app.services.job_service import JobService
from app.services.export_service import ExportService
from app.schemas.schemas import (
    CandidateCreate, CandidateUpdate, CandidateFilters,
    ExportOptions, ReplyCreate, MessageCreate
)


class TestCandidateService:
    """Test CandidateService."""
    
    def test_create_candidate(self):
        """Test creating a candidate."""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_candidate = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(return_value=mock_candidate)
        
        # Test data
        candidate_data = CandidateCreate(
            organization_id=uuid.uuid4(), 
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            years_experience=5,
            skills=["Python", "FastAPI"],
            current_company="TechCorp",
            education="BSc CS",
            location="San Francisco"
        )
        
        # Call service
        result = CandidateService.create_candidate(
            db=mock_db,
            candidate_data=candidate_data,
            organization_id=uuid.uuid4(),
            owner_id=uuid.uuid4()
        )
        
        # Verify
        assert result.email == "john@example.com"
        assert result.name == "John Doe"
        assert result.organization_id is not None
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called()
    
    def test_get_candidate_by_id(self):
        """Test getting a candidate by ID."""
        mock_db = Mock(spec=Session)
        mock_candidate = Mock()
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_candidate
        
        result = CandidateService.get_candidate_by_id(
            db=mock_db,
            candidate_id=uuid.uuid4(),
            organization_id=uuid.uuid4()
        )
        
        assert result == mock_candidate


class TestMessagingService:
    """Test MessagingService."""
    
    def test_generate_message_preview(self):
        """Test generating message preview."""
        mock_db = Mock(spec=Session)
        mock_candidate = Mock()
        mock_candidate.name = "John Doe"
        mock_candidate.current_company = "TechCorp"
        mock_candidate.skills = []
        mock_candidate.conversation_state = {"fields": {}}
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_candidate
        
        preview, error = MessagingService.generate_message_preview(
            db=mock_db,
            intent="Ask about availability",
            candidate_id=uuid.uuid4(),
            organization_id=uuid.uuid4()
        )
        
        assert error is None
        assert preview is not None
        assert "Hi John!" in preview.content
        assert "Ask about availability" in preview.content
    
    def test_classify_reply(self):
        """Test reply classification."""
        # Test interested reply
        result = MessagingService._classify_reply("Yes, I'm interested!")
        assert result["classification"] == "interested"
        assert not result["requires_hr_review"]
        
        # Test question reply
        result = MessagingService._classify_reply("What's the salary range?")
        assert result["classification"] == "question"
        assert result["requires_hr_review"]
        assert result["ai_suggested_reply"] is not None
        
        # Test not interested reply
        result = MessagingService._classify_reply("No thanks, not interested")
        assert result["classification"] == "not_interested"


class TestExportService:
    """Test ExportService."""
    
    def test_generate_export_filename(self):
        """Test filename generation."""
        filename = ExportService.generate_export_filename("xlsx")
        assert filename.endswith(".xlsx")
        assert "candidates_export" in filename
        
        filename = ExportService.generate_export_filename("csv")
        assert filename.endswith(".csv")
        
        filename = ExportService.generate_export_filename("json")
        assert filename.endswith(".json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])