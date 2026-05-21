from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "taskinsight"
    postgres_user: str = "taskinsight"
    postgres_password: str = "change-me"

    redmine_base_url: str = ""
    redmine_api_key: str = ""
    collector_initial_lookback_days: int = 3650

    ollama_base_url: str = "http://localhost:11434"
    ollama_model_timeline: str = "qwen3.6:35b-a3b"
    ollama_model_narrative: str = "qwen2.5-coder:14b"
    ollama_model_heavy: str = "qwen3.6:35b-a3b"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
