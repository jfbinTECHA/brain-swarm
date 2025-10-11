from fastapi import FastAPI
from backend.config.env_loader import get_settings

app = FastAPI()
settings = get_settings()

@app.get("/env/health")
def env_health():
    """Simple endpoint to verify environment setup."""
    return {
        "redis": settings.REDIS_URL,
        "database": settings.DATABASE_URL,
        "openai": "✅" if settings.OPENAI_API_KEY else "❌",
        "anthropic": "✅" if settings.ANTHROPIC_API_KEY else "❌"
    }
