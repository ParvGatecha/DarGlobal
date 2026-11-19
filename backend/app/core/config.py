import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "DarGlobal Intelligence"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # LLM Settings (OpenRouter)
    OPENROUTER_API_KEY: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="google/gemma-4-31b-it:free", validation_alias="OPENROUTER_MODEL")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    AUTO_SELECT_FREE_MODEL: bool = Field(default=True, validation_alias="AUTO_SELECT_FREE_MODEL")

    # Storage Paths
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./data/chroma_db", validation_alias="CHROMA_PERSIST_DIRECTORY")
    BM25_INDEX_PATH: str = Field(default="./data/bm25_index.pkl", validation_alias="BM25_INDEX_PATH")
    RAW_DATA_DIRECTORY: str = Field(default="./data/raw_scraped", validation_alias="RAW_DATA_DIRECTORY")
    SEED_DATA_DIRECTORY: str = Field(default="./data/seed", validation_alias="SEED_DATA_DIRECTORY")

    # Retrieval Engine Settings
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2", validation_alias="EMBEDDING_MODEL_NAME")
    MAX_RETRIEVAL_RESULTS: int = Field(default=6, validation_alias="MAX_RETRIEVAL_RESULTS")
    RRF_K: int = 60
    DENSE_WEIGHT: float = 0.6
    BM25_WEIGHT: float = 0.4

    # Security & CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Target Web URLs
    DARGLOBAL_BASE_URL: str = "https://www.darglobal.co.uk"
    WASALT_BASE_URL: str = "https://wasalt.sa"

settings = Settings()
