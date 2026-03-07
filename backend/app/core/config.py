import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Knowledge Search API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://ks_admin:ks_secret_2024@localhost:5432/knowledge_search"

    # JWT
    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_extra_headers: dict = {}

    # Search
    search_top_k: int = 10
    rag_context_chunks: int = 6
    web_extractor_url: str | None = None

    # Upload
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    print(f"DEBUG: Loading config from CWD: {os.getcwd()}")
    print(f"DEBUG: .env exists in CWD: {os.path.exists('.env')}")
    s = Settings()
    print(f"DEBUG: Config loaded. SECRET_KEY: {s.secret_key[:15]}...")
    return s
