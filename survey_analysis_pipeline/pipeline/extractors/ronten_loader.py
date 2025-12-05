"""Loader for ronten (issue points) files."""

from pathlib import Path
from typing import Optional
from config.settings import Settings, get_settings

class RontenLoader:
    """Loads ronten (issue points) context from files."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize loader."""
        self.settings = settings or get_settings()
        
    def load_ronten_content(self, survey_slug: str) -> str:
        """Load ronten content for a specific survey slug.
        
        Args:
            survey_slug: The slug of the survey (e.g. 'bill-of-lading')
            
        Returns:
            Content of the ronten file or empty string if not found
        """
        filename = self.settings.ronten_file_mapping.get(survey_slug)
        if not filename:
            return ""
            
        file_path = self.settings.data_dir / filename
        
        try:
            if file_path.exists():
                return file_path.read_text(encoding='utf-8')
            return ""
        except Exception as e:
            print(f"Error loading ronten file {file_path}: {e}")
            return ""

