from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "legal-rag"
    DATA_DIR: Path = Path("data")
    RAW_PDF_PATH: Path = Path("data/raw/egyptian_civil_code.pdf")
    PROCESSED_JSON_PATH: Path = Path("data/processed/egyptian_civil_code.json")
    CHUNKS_JSON_PATH: Path = Path("data/processed/chunks.json")

    # Vector Store & Embedding Configuration
    CHROMA_DB_DIR: Path = Path("data/processed/chroma_db")
    CHROMA_COLLECTION_NAME: str = "egyptian_civil_code"
    EMBEDDING_MODEL_NAME: str = "Qwen/Qwen3-Embedding-0.6B"

    # API Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
