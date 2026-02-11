"""
Configuration management using Pydantic Settings.
Loads configuration from .env file with validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ===========================================
    # Database Configuration
    # ===========================================
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_user: str = Field(default="bose_admin")
    postgres_password: str = Field(default="local_dev_pass")
    postgres_db: str = Field(default="bose_products")
    
    # Connection pool settings
    max_db_connections: int = Field(default=10, ge=1, le=100)
    min_db_connections: int = Field(default=2, ge=1, le=10)
    
    # ===========================================
    # Ollama Configuration
    # ===========================================
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_embedding_model: str = Field(default="bge-m3")
    ollama_llm_model: str = Field(default="llama3.2:3b")
    embedding_dimension: int = Field(default=1024)
    
    # ===========================================
    # ETL Settings
    # ===========================================
    max_pdf_pages: int = Field(default=50, ge=1)
    batch_size: int = Field(default=10, ge=1, le=100)
    cache_embeddings: bool = Field(default=True)
    
    # ===========================================
    # Performance Settings
    # ===========================================
    query_timeout_seconds: int = Field(default=3, ge=1, le=30)
    
    # ===========================================
    # Path Configuration
    # ===========================================
    raw_pdfs_dir: str = Field(default="data/raw_pdfs")
    processed_dir: str = Field(default="data/processed")
    
    # ===========================================
    # Logging Configuration
    # ===========================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # ===========================================
    # Computed Properties
    # ===========================================
    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL for asyncpg."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def raw_pdfs_path(self) -> Path:
        """Absolute path to raw PDFs directory."""
        return Path(self.raw_pdfs_dir).resolve()
    
    @property
    def processed_path(self) -> Path:
        """Absolute path to processed data directory."""
        return Path(self.processed_dir).resolve()
    
    @property
    def raw_tables_cache(self) -> Path:
        """Path to raw tables JSON cache."""
        return self.processed_path / "raw_tables.json"
    
    @property
    def normalized_cache(self) -> Path:
        """Path to normalized products JSON cache."""
        return self.processed_path / "normalized_products.json"
    
    @property
    def embeddings_cache(self) -> Path:
        """Path to embeddings JSON cache."""
        return self.processed_path / "embeddings_cache.json"
    
    # ===========================================
    # Validators
    # ===========================================
    @field_validator("postgres_host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Ensure host is not empty."""
        if not v or not v.strip():
            raise ValueError("postgres_host cannot be empty")
        return v.strip()
    
    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_url(cls, v: str) -> str:
        """Ensure Ollama URL is valid."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("ollama_base_url must start with http:// or https://")
        return v.rstrip("/")
    
    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        self.raw_pdfs_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    settings = Settings()
    settings.ensure_directories()
    return settings


# Convenience alias
settings = get_settings()
