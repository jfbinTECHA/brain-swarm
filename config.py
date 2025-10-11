"""
Unified configuration management for Brain Swarm
Uses pydantic-settings with Vault/AWS Secrets Manager integration
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import os
import json
import boto3
import hvac
from botocore.exceptions import ClientError


class APIKeys(BaseModel):
    """API keys for external services"""
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    grok_api_key: Optional[str] = Field(default=None, description="Grok API key")


class NodeConfig(BaseModel):
    """Configuration for swarm nodes"""
    node_name: str = Field(default="brain_swarm_node", description="Unique node identifier")
    swarm_id: str = Field(default="default_swarm", description="Swarm identifier")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    max_agents: int = Field(default=10, description="Maximum agents per node")
    max_agent_load: int = Field(default=3, description="Maximum concurrent tasks per agent")


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(default="sqlite:///brain_swarm.db", description="Database URL")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max overflow connections")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    file_path: Optional[str] = Field(default=None, description="Log file path")


class FederationConfig(BaseModel):
    """Federation configuration"""
    enabled: bool = Field(default=False, description="Enable federation")
    discovery_url: Optional[str] = Field(default=None, description="Federation discovery URL")
    shared_memory_url: Optional[str] = Field(default=None, description="Shared memory URL")


class ScalabilityConfig(BaseModel):
    """Scalability configuration for horizontal scaling and message queuing"""
    enabled: bool = Field(default=False, description="Enable scalable components")
    message_queue_mode: str = Field(default="single_node", description="Message queue mode (single_node/cluster/partitioned)")
    redis_urls: List[str] = Field(default_factory=lambda: ["redis://localhost:6379"], description="Redis URLs for message queue")
    partitions: int = Field(default=8, description="Number of message queue partitions")
    async_agents_enabled: bool = Field(default=False, description="Enable async agents with load balancing")
    agent_pool_min: int = Field(default=1, description="Minimum agents in pool")
    agent_pool_max: int = Field(default=10, description="Maximum agents in pool")
    load_balancing_strategy: str = Field(default="least_loaded", description="Load balancing strategy")
    multi_cluster_enabled: bool = Field(default=False, description="Enable multi-cluster federation")
    cluster_id: str = Field(default="default_cluster", description="Local cluster ID")
    cluster_role: str = Field(default="primary", description="Cluster role (primary/secondary/edge/specialized)")
    auto_scaling_enabled: bool = Field(default=False, description="Enable auto-scaling coordination")


class UserConfig(BaseModel):
    """User configuration for authentication"""
    username: str
    password_hash: str
    role: str = Field(default="viewer", description="User role")
    enabled: bool = Field(default=True, description="User account enabled")


class SecurityConfig(BaseModel):
    """Security configuration"""
    enable_policy_engine: bool = Field(default=True, description="Enable policy engine")
    enable_encryption: bool = Field(default=False, description="Enable message encryption")
    jwt_secret: str = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT token expiration in hours")
    refresh_token_expiration_days: int = Field(default=30, description="Refresh token expiration in days")
    api_keys: Dict[str, str] = Field(default_factory=dict, description="API keys for agent registration")
    users: Dict[str, UserConfig] = Field(default_factory=dict, description="Human users for authentication")
    enable_audit_logging: bool = Field(default=True, description="Enable security audit logging")
    password_min_length: int = Field(default=8, description="Minimum password length")
    max_login_attempts: int = Field(default=5, description="Maximum login attempts before lockout")
    lockout_duration_minutes: int = Field(default=15, description="Account lockout duration in minutes")


class SecretsManagerConfig(BaseModel):
    """Secrets manager configuration"""
    provider: str = Field(default="vault", description="Secrets provider (vault/aws)")
    vault_url: Optional[str] = Field(default=None, description="Vault server URL")
    vault_token: Optional[str] = Field(default=None, description="Vault token")
    vault_mount_point: str = Field(default="secret", description="Vault mount point")
    vault_path: str = Field(default="brain-swarm", description="Vault secret path")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_secret_name: str = Field(default="brain-swarm", description="AWS secret name")


class SecretsManager:
    """Unified secrets manager for Vault and AWS Secrets Manager"""

    def __init__(self, config: SecretsManagerConfig):
        self.config = config
        self._vault_client = None
        self._aws_client = None

    def get_secret(self, key: str, default: Any = None) -> Any:
        """Get a secret value by key"""
        try:
            if self.config.provider == "vault":
                return self._get_vault_secret(key, default)
            elif self.config.provider == "aws":
                return self._get_aws_secret(key, default)
            else:
                # Fallback to environment variables
                return os.getenv(key, default)
        except Exception as e:
            print(f"Error retrieving secret {key}: {e}")
            return default

    def _get_vault_secret(self, key: str, default: Any = None) -> Any:
        """Get secret from HashiCorp Vault"""
        if not self._vault_client:
            if not self.config.vault_url or not self.config.vault_token:
                raise ValueError("Vault URL and token required for Vault provider")

            self._vault_client = hvac.Client(
                url=self.config.vault_url,
                token=self.config.vault_token
            )

        try:
            response = self._vault_client.secrets.kv.v2.read_secret_version(
                mount_point=self.config.vault_mount_point,
                path=self.config.vault_path
            )

            data = response['data']['data']
            return data.get(key, default)
        except Exception as e:
            print(f"Vault error for key {key}: {e}")
            return default

    def _get_aws_secret(self, key: str, default: Any = None) -> Any:
        """Get secret from AWS Secrets Manager"""
        if not self._aws_client:
            self._aws_client = boto3.client('secretsmanager', region_name=self.config.aws_region)

        try:
            response = self._aws_client.get_secret_value(SecretId=self.config.aws_secret_name)
            secret_string = response['SecretString']

            # Parse JSON secret
            secrets = json.loads(secret_string)
            return secrets.get(key, default)
        except ClientError as e:
            print(f"AWS Secrets Manager error for key {key}: {e}")
            return default
        except json.JSONDecodeError:
            # If not JSON, return the whole string if key matches secret name
            if key == self.config.aws_secret_name:
                return secret_string
            return default


class Settings(BaseSettings):
    """Main settings class with all configuration"""

    # Environment
    environment: str = Field(default="development", description="Environment (development/production)")

    # Secrets manager configuration
    secrets: SecretsManagerConfig = Field(default_factory=SecretsManagerConfig, description="Secrets manager settings")

    # API Keys (will be populated from secrets manager)
    api_keys: APIKeys = Field(default_factory=APIKeys, description="External API keys")

    # Node configuration
    node: NodeConfig = Field(default_factory=NodeConfig, description="Node-specific settings")

    # Database
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")

    # Logging
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging settings")

    # Federation
    federation: FederationConfig = Field(default_factory=FederationConfig, description="Federation settings")

    # Scalability
    scalability: ScalabilityConfig = Field(default_factory=ScalabilityConfig, description="Scalability settings")

    # Security
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security settings")

    # Additional custom settings
    custom_settings: Dict[str, Any] = Field(default_factory=dict, description="Custom configuration")

    def __init__(self, **data):
        super().__init__(**data)
        self._load_secrets()

    def _load_secrets(self):
        """Load sensitive configuration from secrets manager"""
        secrets_manager = SecretsManager(self.secrets)

        # Load API keys from secrets
        self.api_keys.openai_api_key = secrets_manager.get_secret("OPENAI_API_KEY", self.api_keys.openai_api_key)
        self.api_keys.openrouter_api_key = secrets_manager.get_secret("OPENROUTER_API_KEY", self.api_keys.openrouter_api_key)
        self.api_keys.anthropic_api_key = secrets_manager.get_secret("ANTHROPIC_API_KEY", self.api_keys.anthropic_api_key)
        self.api_keys.grok_api_key = secrets_manager.get_secret("GROK_API_KEY", self.api_keys.grok_api_key)

        # Load security secrets
        self.security.jwt_secret = secrets_manager.get_secret("JWT_SECRET", self.security.jwt_secret)

        # Load database credentials if needed
        db_url = secrets_manager.get_secret("DATABASE_URL")
        if db_url:
            self.database.url = db_url

    class Config:
        env_file = ".env"  # Keep for backward compatibility, but secrets manager takes precedence
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Custom source priority: init > env > file > secrets_manager"""
            return init_settings, env_settings, file_secret_settings


# Global settings instance
settings = Settings()