from pydantic_settings import BaseSettings
from pydantic import AnyUrl, Field

class CortexSettings(BaseSettings):
    # Cache (Redis)
    redis_url: AnyUrl = Field(default="redis://redis:6379/0")

    # Vector (Chroma server)
    chroma_host: str = Field(default="chroma")
    chroma_port: int = Field(default=8000)
    chroma_collection: str = Field(default="brainswarm")

    # Optional FAISS local cache
    faiss_enable: bool = Field(default=True)
    faiss_index_path: str = Field(default="/data/faiss.index")

    # Graph (DuckDB + NetworkX)
    duckdb_path: str = Field(default="/data/cortex.duckdb")

    # Long-term (S3 + DuckDB catalog)
    s3_endpoint_url: str | None = None           # e.g., https://s3.amazonaws.com or http://minio:9000
    s3_bucket: str = Field(default="brainswarm-cortex")
    s3_region: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_secure: bool = True

    # Security / JWT (reuse your platform secret if you prefer)
    jwt_public_key_pem: str | None = None
    jwt_audience: str | None = None
    jwt_issuer: str | None = None

    class Config:
        env_prefix = "CORTEX_"
        env_file = ".env"

settings = CortexSettings()