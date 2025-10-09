from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


# =====================================================================
# 🧠  BrainSwarm Cortex Settings
# ---------------------------------------------------------------------
# Centralized configuration model for Cortex and summarizer modules.
# Supports absolute .env path for systemd/cron usage and allows
# additional environment variables from monitoring and automation layers.
# =====================================================================

class CortexSettings(BaseSettings):
    redis_url: str
    chroma_url: str
    duckdb_path: str
    s3_bucket: Optional[str] = None
    summarization_interval: int = 300
    embedding_model: str = "text-embedding-3-large"
    cortex_mode: str = "live"

    model_config = SettingsConfigDict(
        # Absolute path ensures reliability under systemd
        env_file="/home/sysop/brainswarm/.env",
        env_file_encoding="utf-8",
        extra="ignore"  # Allow unused env vars (e.g. Grafana URLs)
    )

# Instantiate global settings
settings = CortexSettings()

# Quick debug entry point
if __name__ == "__main__":
    print("✅ CortexSettings loaded successfully:")
    print(settings.model_dump())