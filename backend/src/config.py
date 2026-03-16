"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATA_DIR: str = "./data"
    ANTHROPIC_API_KEY: str = ""
    FRED_API_KEY: str = ""
    BACKTEST_TIMEOUT_SECONDS: int = 300
    PIPELINE_TIMEOUT_SECONDS: int = 700
    PAPER_RUN_SCHEDULE_HOUR: int = 16  # JST market close + 1hr
    DEFAULT_VIRTUAL_CAPITAL: int = 1_000_000
    DEFAULT_COMMISSION_BPS: int = 10
    DEFAULT_SPREAD_BPS: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
