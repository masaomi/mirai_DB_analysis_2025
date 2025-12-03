"""Load and parse survey data from CSV files."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import pandas as pd

from config.settings import Settings, get_settings


@dataclass
class SurveyMetadata:
    """Metadata about a survey."""
    slug: str
    title: str
    total_sessions: int
    completed_sessions: int
    total_messages: int
    date_range: tuple[str, str]


class SurveyDataLoader:
    """Load survey data from CSV files."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize data loader.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self.data_dir = Path(self.settings.data_dir)
    
    def get_available_surveys(self) -> List[str]:
        """Get list of available survey slugs.
        
        Returns:
            List of survey slug names
        """
        surveys = set()
        for f in self.data_dir.glob("*_messages.csv"):
            slug = f.name.replace("_messages.csv", "")
            # Check if sessions file also exists
            sessions_file = self.data_dir / f"{slug}_interview_sessions.csv"
            if sessions_file.exists():
                surveys.add(slug)
        return sorted(surveys)
    
    def load_messages(self, survey_slug: str) -> pd.DataFrame:
        """Load messages CSV for a survey.
        
        Args:
            survey_slug: Survey identifier
            
        Returns:
            DataFrame with messages
        """
        file_path = self.data_dir / f"{survey_slug}_messages.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Messages file not found: {file_path}")
        
        df = pd.read_csv(file_path)
        
        # Parse timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        return df
    
    def load_sessions(self, survey_slug: str) -> pd.DataFrame:
        """Load interview sessions CSV for a survey.
        
        Args:
            survey_slug: Survey identifier
            
        Returns:
            DataFrame with sessions
        """
        file_path = self.data_dir / f"{survey_slug}_interview_sessions.csv"
        if not file_path.exists():
            raise FileNotFoundError(f"Sessions file not found: {file_path}")
        
        df = pd.read_csv(file_path)
        
        # Parse timestamps
        for col in ['start_time', 'end_time', 'created_at', 'updated_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    
    def load_survey(self, survey_slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load both messages and sessions for a survey.
        
        Args:
            survey_slug: Survey identifier
            
        Returns:
            Tuple of (messages_df, sessions_df)
        """
        messages = self.load_messages(survey_slug)
        sessions = self.load_sessions(survey_slug)
        return messages, sessions
    
    def get_completed_sessions(self, sessions_df: pd.DataFrame) -> pd.DataFrame:
        """Filter to completed sessions only.
        
        Args:
            sessions_df: Sessions DataFrame
            
        Returns:
            Filtered DataFrame with completed sessions
        """
        return sessions_df[sessions_df['status'] == 'completed'].copy()
    
    def get_survey_metadata(self, survey_slug: str) -> SurveyMetadata:
        """Get metadata about a survey.
        
        Args:
            survey_slug: Survey identifier
            
        Returns:
            SurveyMetadata object
        """
        messages_df, sessions_df = self.load_survey(survey_slug)
        
        # Get title from first session
        title = "Unknown Survey"
        if 'config_title' in sessions_df.columns and len(sessions_df) > 0:
            title = sessions_df['config_title'].iloc[0]
            if pd.isna(title):
                title = survey_slug
        
        # Count sessions
        total_sessions = len(sessions_df)
        completed_sessions = len(self.get_completed_sessions(sessions_df))
        
        # Count messages
        total_messages = len(messages_df)
        
        # Get date range
        date_range = ("Unknown", "Unknown")
        if 'timestamp' in messages_df.columns:
            valid_dates = messages_df['timestamp'].dropna()
            if len(valid_dates) > 0:
                date_range = (
                    valid_dates.min().strftime("%Y-%m-%d"),
                    valid_dates.max().strftime("%Y-%m-%d")
                )
        
        return SurveyMetadata(
            slug=survey_slug,
            title=title,
            total_sessions=total_sessions,
            completed_sessions=completed_sessions,
            total_messages=total_messages,
            date_range=date_range,
        )

