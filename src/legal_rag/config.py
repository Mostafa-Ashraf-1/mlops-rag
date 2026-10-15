from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Dynamically resolve repository root: mlops-rag/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "legal-rag"
    BASE_DIR: Path = REPO_ROOT
    DATA_DIR: Path = REPO_ROOT / "data"
    RAW_PDF_PATH: Path = REPO_ROOT / "data" / "raw" / "egyptian_civil_code.pdf"
    PROCESSED_JSON_PATH: Path = REPO_ROOT / "data" / "processed" / "egyptian_civil_code.json"
    CHUNKS_JSON_PATH: Path = REPO_ROOT / "data" / "processed" / "chunks.json"

    # Vector Store & Embedding Configuration
    CHROMA_DB_DIR: Path = REPO_ROOT / "data" / "processed" / "chroma_db"
    CHROMA_COLLECTION_NAME: str = "egyptian_civil_code"
    EMBEDDING_MODEL_NAME: str = "Qwen/Qwen3-Embedding-0.6B"

    # API Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )


settings = Settings()