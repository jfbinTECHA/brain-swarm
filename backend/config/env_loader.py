"""
Brain-Swarm Environment Loader
Centralized configuration management for API keys and service URLs.
"""

import os
import sys
from dotenv import load_dotenv

# Load from .env if present
load_dotenv()

REQUIRED_KEYS = [
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROK_API_KEY",
    "REDIS_URL",
    "DATABASE_URL"
]

def validate_env():
    """Check that all required environment variables are defined."""
    missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
    if missing:
        print("❌ Missing environment variables:\n  - " + "\n  - ".join(missing))
        print("⚠️  Please add them to your .env file before running the backend.")
        sys.exit(1)
    else:
        print("✅ Environment validation successful. All keys present.")


class Settings:
    """Centralized access to environment configuration."""

    # API keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")
    GROK_API_KEY: str = os.getenv("GROK_API_KEY")

    # Core infrastructure
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:swarm@localhost:5432/brainswarm"
    )

    CHROMA_URL: str = os.getenv("CHROMA_URL", "http://localhost:8002")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")


def get_settings() -> Settings:
    """Helper function to return validated settings object."""
    validate_env()
    return Settings()