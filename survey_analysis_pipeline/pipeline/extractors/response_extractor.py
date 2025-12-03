"""Extract and process user responses from survey data."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

import pandas as pd

from config.settings import Settings, get_settings
from .data_loader import SurveyDataLoader


@dataclass
class UserResponse:
    """A single user response with context."""
    session_id: str
    content: str
    timestamp: Optional[str]
    preceding_question: str
    response_length: int
    session_status: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "content": self.content,
            "timestamp": self.timestamp,
            "preceding_question": self.preceding_question,
            "response_length": self.response_length,
            "session_status": self.session_status,
        }


@dataclass
class ExtractionResult:
    """Result of response extraction."""
    survey_slug: str
    survey_title: str
    responses: List[UserResponse]
    total_sessions: int
    completed_sessions: int
    filtered_count: int
    date_range: tuple[str, str]
    
    @property
    def response_count(self) -> int:
        """Number of extracted responses."""
        return len(self.responses)


class ResponseExtractor:
    """Extract user responses from survey messages."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize extractor.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self.data_loader = SurveyDataLoader(settings)
        self.min_length = self.settings.min_response_length
    
    def extract_responses(
        self,
        survey_slug: str,
        completed_only: bool = True,
    ) -> ExtractionResult:
        """Extract user responses from a survey.
        
        Args:
            survey_slug: Survey identifier
            completed_only: Only include responses from completed sessions
            
        Returns:
            ExtractionResult with extracted responses
        """
        # Load data
        messages_df, sessions_df = self.data_loader.load_survey(survey_slug)
        metadata = self.data_loader.get_survey_metadata(survey_slug)
        
        # Filter sessions
        if completed_only:
            valid_sessions = self.data_loader.get_completed_sessions(sessions_df)
        else:
            valid_sessions = sessions_df
        
        valid_session_ids = set(valid_sessions['id'].tolist())
        
        # Create session status lookup
        session_status = dict(zip(sessions_df['id'], sessions_df['status']))
        
        # Extract responses
        responses = []
        filtered_count = 0
        
        # Group messages by session
        for session_id, group in messages_df.groupby('session_id'):
            if session_id not in valid_session_ids:
                continue
            
            # Sort by timestamp
            group = group.sort_values('timestamp')
            messages = group.to_dict('records')
            
            # Find user responses with preceding questions
            for i, msg in enumerate(messages):
                if msg.get('role') != 'user':
                    continue
                
                content = str(msg.get('content', '')).strip()
                
                # Apply minimum length filter
                if len(content) < self.min_length:
                    filtered_count += 1
                    continue
                
                # Find preceding question
                preceding_q = ""
                for j in range(i - 1, -1, -1):
                    if messages[j].get('role') == 'assistant':
                        preceding_q = str(messages[j].get('content', '')).strip()
                        # Truncate long questions
                        if len(preceding_q) > 500:
                            preceding_q = preceding_q[:500] + "..."
                        break
                
                # Get timestamp
                timestamp = None
                if pd.notna(msg.get('timestamp')):
                    ts = msg['timestamp']
                    if hasattr(ts, 'isoformat'):
                        timestamp = ts.isoformat()
                    else:
                        timestamp = str(ts)
                
                responses.append(UserResponse(
                    session_id=session_id,
                    content=content,
                    timestamp=timestamp,
                    preceding_question=preceding_q,
                    response_length=len(content),
                    session_status=session_status.get(session_id, "unknown"),
                ))
        
        return ExtractionResult(
            survey_slug=survey_slug,
            survey_title=metadata.title,
            responses=responses,
            total_sessions=metadata.total_sessions,
            completed_sessions=metadata.completed_sessions,
            filtered_count=filtered_count,
            date_range=metadata.date_range,
        )
    
    def get_response_texts(self, extraction_result: ExtractionResult) -> List[str]:
        """Get just the response text content.
        
        Args:
            extraction_result: Extraction result
            
        Returns:
            List of response text strings
        """
        return [r.content for r in extraction_result.responses]
    
    def get_qa_pairs(
        self,
        extraction_result: ExtractionResult
    ) -> List[Dict[str, str]]:
        """Get question-answer pairs.
        
        Args:
            extraction_result: Extraction result
            
        Returns:
            List of dicts with 'question' and 'answer' keys
        """
        pairs = []
        for r in extraction_result.responses:
            if r.preceding_question:
                pairs.append({
                    "question": r.preceding_question,
                    "answer": r.content,
                    "session_id": r.session_id,
                })
        return pairs
    
    def get_statistics(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        """Get statistics about extracted responses.
        
        Args:
            extraction_result: Extraction result
            
        Returns:
            Dictionary of statistics
        """
        lengths = [r.response_length for r in extraction_result.responses]
        
        if not lengths:
            return {
                "total_responses": 0,
                "avg_length": 0,
                "median_length": 0,
                "min_length": 0,
                "max_length": 0,
                "total_characters": 0,
            }
        
        import statistics
        
        return {
            "total_responses": len(lengths),
            "avg_length": statistics.mean(lengths),
            "median_length": statistics.median(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "total_characters": sum(lengths),
            "total_sessions": extraction_result.total_sessions,
            "completed_sessions": extraction_result.completed_sessions,
            "filtered_count": extraction_result.filtered_count,
            "date_range": extraction_result.date_range,
        }

