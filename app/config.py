"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # PostgreSQL
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="agent_user")
    postgres_password: str = Field(default="change_me_in_production")
    postgres_db: str = Field(default="agent_db")

    # Qdrant
    qdrant_host: str = Field(default="qdrant")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(default="schema_memory")

    # Ollama
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="llama3")
    ollama_embed_model: str = Field(default="nomic-embed-text")

    # Browserless
    browserless_url: str = Field(default="http://browserless:3000")

    # App
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:8000")
    max_query_rows: int = Field(default=1000)
    sql_readonly: bool = Field(default=True)

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_dsn_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
