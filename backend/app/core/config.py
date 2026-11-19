import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "DarGlobal Intelligence"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="production", validation_alias="ENVIRONMENT")
    PORT: int = Field(default=8000, validation_alias="PORT")

    # LLM Settings (OpenRouter)
    OPENROUTER_API_KEY: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="google/gemma-4-31b-it:free", validation_alias="OPENROUTER_MODEL")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    AUTO_SELECT_FREE_MODEL: bool = Field(default=True, validation_alias="AUTO_SELECT_FREE_MODEL")

    # Storage Paths
    CHROMA_PERSIST_DIRECTORY: str = Field(default="./data/chroma_db", validation_alias="CHROMA_PERSIST_DIRECTORY")
    BM25_INDEX_PATH: str = Field(default="./data/bm25_index.pkl", validation_alias="BM25_INDEX_PATH")
    CANONICAL_DATASET_PATH: str = Field(default="./backend/data/canonical_dataset.json", validation_alias="CANONICAL_DATASET_PATH")
    RAW_DATA_DIRECTORY: str = Field(default="./data/raw_scraped", validation_alias="RAW_DATA_DIRECTORY")
    SEED_DATA_DIRECTORY: str = Field(default="./data/seed", validation_alias="SEED_DATA_DIRECTORY")

    # Retrieval Engine Settings
    EMBEDDING_MODEL_NAME: str = Field(default="all-MiniLM-L6-v2", validation_alias="EMBEDDING_MODEL_NAME")
    MAX_RETRIEVAL_RESULTS: int = Field(default=6, validation_alias="MAX_RETRIEVAL_RESULTS")
    RRF_K: int = 60
    DENSE_WEIGHT: float = 0.6
    BM25_WEIGHT: float = 0.4

    # Security & CORS
    ADMIN_API_KEY: str = Field(default="", validation_alias="ADMIN_API_KEY")
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ORIGIN_REGEX: Optional[str] = Field(
        default=r"^https:\/\/.*\.vercel\.app$",
        validation_alias="CORS_ORIGIN_REGEX"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                import json
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["*"]

    # Target Web URLs
    DARGLOBAL_BASE_URL: str = "https://www.darglobal.co.uk"
    WASALT_BASE_URL: str = "https://wasalt.sa"

settings = Settings()
