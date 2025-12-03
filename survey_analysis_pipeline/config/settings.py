"""Configuration settings using pydantic-settings."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    BEDROCK = "bedrock"
    OPENROUTER = "openrouter"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Paths
    data_dir: Path = Field(
        default=Path("../data"),
        description="Directory containing survey CSV files"
    )
    output_dir: Path = Field(
        default=Path("outputs"),
        description="Directory for generated reports"
    )
    
    # LLM Provider Selection
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="LLM provider to use"
    )
    
    # Ollama Settings
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )
    ollama_model: str = Field(
        default="llama3.2",
        description="Ollama model name"
    )
    
    # Amazon Bedrock Settings
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock"
    )
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS access key ID"
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret access key"
    )
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Bedrock model ID"
    )
    
    # OpenRouter Settings
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key"
    )
    openrouter_model: str = Field(
        default="anthropic/claude-3.5-sonnet",
        description="OpenRouter model name"
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    
    # Analysis Settings
    min_response_length: int = Field(
        default=10,
        description="Minimum characters for valid response"
    )
    clustering_min_samples: int = Field(
        default=3,
        description="Minimum samples for HDBSCAN clustering"
    )
    minority_threshold: float = Field(
        default=0.1,
        description="Top percentage for minority detection"
    )
    minority_top_n: int = Field(
        default=10,
        description="Number of minority opinions to extract"
    )
    
    # Summarization Settings
    chunk_size: int = Field(
        default=30,
        description="Number of responses per chunk for summarization"
    )
    max_tokens: int = Field(
        default=2000,
        description="Maximum tokens for LLM response"
    )
    temperature: float = Field(
        default=0.3,
        description="LLM temperature for summarization"
    )
    
    # Embedding Settings
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-base",
        description="Sentence transformer model for embeddings"
    )
    
    # Multi LLM Orchestration
    multi_llm_enabled: bool = Field(
        default=False,
        description="Enable multi-LLM orchestration"
    )
    multi_llm_models: List[str] = Field(
        default=["anthropic/claude-3.5-sonnet", "openai/gpt-4o", "google/gemini-1.5-pro"],
        description="Models to use for multi-LLM orchestration"
    )
    
    # Persona Assembly
    persona_enabled: bool = Field(
        default=False,
        description="Enable persona assembly"
    )
    
    # Cache Settings
    cache_enabled: bool = Field(
        default=True,
        description="Enable LLM response caching"
    )
    cache_dir: Path = Field(
        default=Path(".cache"),
        description="Cache directory"
    )
    
    def get_llm_config(self) -> dict:
        """Get LLM configuration based on selected provider."""
        if self.llm_provider == LLMProvider.OLLAMA:
            return {
                "provider": "ollama",
                "model": f"ollama/{self.ollama_model}",
                "api_base": self.ollama_base_url,
            }
        elif self.llm_provider == LLMProvider.BEDROCK:
            return {
                "provider": "bedrock",
                "model": f"bedrock/{self.bedrock_model_id}",
                "aws_region_name": self.aws_region,
            }
        elif self.llm_provider == LLMProvider.OPENROUTER:
            return {
                "provider": "openrouter",
                "model": f"openrouter/{self.openrouter_model}",
                "api_key": self.openrouter_api_key,
                "api_base": self.openrouter_base_url,
            }
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

