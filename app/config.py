from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Intelligent Observability Watchdog"
    database_url: str = "sqlite:///./observability.db"
    debug: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
