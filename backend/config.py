from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "speech_recognition"
    
    # Audio Configuration
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    format: str = "int16"
    
    # Model Configuration
    whisper_model: str = "base"
    diarization_model: str = "pyannote/speaker-diarization-3.1"
    speaker_embedding_model: str = "pyannote/embedding"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Hugging Face
    huggingface_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
