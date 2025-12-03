"""
Configuration file for survey analysis pipeline.

This module centralizes all configuration settings including file paths,
API keys, and processing parameters.
"""

import os
from pathlib import Path
from typing import Optional


# ============================================================================
# File Paths
# ============================================================================

# Base directory
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

# Input files
BACKUP_JSON_FILE = PROJECT_ROOT / "backup-2025-11-14T03-19-14.json"

# Output directories
SURVEY_CHUNKS_DIR = BASE_DIR / "survey_chunks"
SURVEY_SUMMARIES_DIR = BASE_DIR / "survey_summaries"

# LLM-specific output directories
CLAUDE_OUTPUT_DIR = SURVEY_SUMMARIES_DIR / "claude" / "summaries"
GEMINI_OUTPUT_DIR = SURVEY_SUMMARIES_DIR / "gemini" / "summaries"
OLLAMA_OUTPUT_DIR = SURVEY_SUMMARIES_DIR / "ollama" / "summaries"


# ============================================================================
# API Configuration
# ============================================================================

# API Keys (loaded from environment variables)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# LLM Model names
CLAUDE_MODEL = "claude-sonnet-4-20250514"
GEMINI_MODEL = "gemini-1.5-pro"
OLLAMA_MODEL = "gpt-oss20b"
OLLAMA_BASE_URL = "http://localhost:11434"

# API request settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 120  # seconds


# ============================================================================
# Processing Parameters
# ============================================================================

# Batch sizes for processing
BATCH_SIZE_SMALL = 10   # For initial batch summarization
BATCH_SIZE_MEDIUM = 20  # For larger batches
BATCH_SIZE_LARGE = 50   # For very large datasets

# Default batch size to use
DEFAULT_BATCH_SIZE = BATCH_SIZE_SMALL

# Summarization settings
SUMMARY_MAX_TOKENS = 4096
SUMMARY_TEMPERATURE = 0.7

# Maximum number of responses to process per question (for testing)
MAX_RESPONSES_PER_QUESTION: Optional[int] = None  # Set to None for no limit


# ============================================================================
# Output Format Settings
# ============================================================================

# Markdown settings
MD_INCLUDE_STATS = True
MD_INCLUDE_TIMESTAMP = True

# HTML settings
HTML_INCLUDE_TOC = True
HTML_THEME = "modern"  # Options: "modern", "classic", "minimal"

# PDF settings
PDF_PAGE_SIZE = "A4"
PDF_FONT_SIZE = 12
PDF_MARGIN = "2cm"


# ============================================================================
# Logging and Progress
# ============================================================================

# Logging level
LOG_LEVEL = "INFO"  # Options: "DEBUG", "INFO", "WARNING", "ERROR"

# Progress bar settings
SHOW_PROGRESS_BARS = True
PROGRESS_BAR_COLOR = "green"


# ============================================================================
# Validation
# ============================================================================

def validate_config() -> bool:
    """
    Validate configuration settings.
    
    Returns:
        bool: True if configuration is valid, False otherwise.
    """
    errors = []
    
    # Check API keys
    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY environment variable is not set")
    
    if not GOOGLE_API_KEY:
        errors.append("GOOGLE_API_KEY environment variable is not set")
    
    # Check input file
    if not BACKUP_JSON_FILE.exists():
        errors.append(f"Backup JSON file not found: {BACKUP_JSON_FILE}")
    
    if errors:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    return True


def ensure_output_directories():
    """Create output directories if they don't exist."""
    directories = [
        SURVEY_CHUNKS_DIR,
        SURVEY_SUMMARIES_DIR,
        CLAUDE_OUTPUT_DIR,
        GEMINI_OUTPUT_DIR,
        OLLAMA_OUTPUT_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def get_output_dir(llm_provider: str) -> Path:
    """
    Get output directory for specific LLM provider.
    
    Args:
        llm_provider: Name of LLM provider ("claude", "gemini", or "ollama")
    
    Returns:
        Path to output directory
    """
    if llm_provider.lower() == "claude":
        return CLAUDE_OUTPUT_DIR
    elif llm_provider.lower() == "gemini":
        return GEMINI_OUTPUT_DIR
    elif llm_provider.lower() == "ollama":
        return OLLAMA_OUTPUT_DIR
    else:
        raise ValueError(f"Unknown LLM provider: {llm_provider}")


def print_config():
    """Print current configuration for debugging."""
    print("\n" + "="*70)
    print("CONFIGURATION")
    print("="*70)
    print(f"Base directory: {BASE_DIR}")
    print(f"Backup file: {BACKUP_JSON_FILE}")
    print(f"Survey chunks: {SURVEY_CHUNKS_DIR}")
    print(f"Claude output: {CLAUDE_OUTPUT_DIR}")
    print(f"Gemini output: {GEMINI_OUTPUT_DIR}")
    print(f"Ollama output: {OLLAMA_OUTPUT_DIR}")
    print(f"\nClaude model: {CLAUDE_MODEL}")
    print(f"Gemini model: {GEMINI_MODEL}")
    print(f"Ollama model: {OLLAMA_MODEL}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Batch size: {DEFAULT_BATCH_SIZE}")
    print(f"\nAPI keys:")
    print(f"  - ANTHROPIC_API_KEY: {'✅ Set' if ANTHROPIC_API_KEY else '❌ Not set'}")
    print(f"  - GOOGLE_API_KEY: {'✅ Set' if GOOGLE_API_KEY else '❌ Not set'}")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Test configuration
    print_config()
    
    if validate_config():
        print("✅ Configuration is valid")
        ensure_output_directories()
        print("✅ Output directories created/verified")
    else:
        print("❌ Configuration validation failed")

