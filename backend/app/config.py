from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "PDF Mind Map Generator"
    debug: bool = True
    
    # Ollama Configuration
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    
    # Logging Configuration
    loki_host: Optional[str] = "http://localhost:3100"
    prometheus_port: int = 8001
    
    # Storage Configuration
    artifacts_path: str = "./artifacts"
    upload_path: str = "./uploads"
    
    # Agent Configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    max_repair_attempts: int = 2
    
    # Processing Configuration
    max_concurrent_sections: int = 2
    section_timeout: int = 300  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
