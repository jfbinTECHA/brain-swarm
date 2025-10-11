"""
Embedding Adapter for Knowledge Cortex
Supports OpenAI, OpenRouter, and local embeddings
"""

from typing import List, Dict, Any, Optional, Union
import os
import json
import hashlib
import numpy as np
from config import settings
from core.base import logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    import sentence_transformers
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    sentence_transformers = None


class EmbeddingProvider:
    """Base class for embedding providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts"""
        raise NotImplementedError

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        raise NotImplementedError


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed")

        self.api_key = config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.model = config.get("model", "text-embedding-3-small")
        self.dimension = config.get("dimension", 1536)  # text-embedding-3-small dimension

        if not self.api_key:
            raise ValueError("OpenAI API key required")

        self.client = openai.OpenAI(api_key=self.api_key)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using OpenAI"""
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.log("ERROR", "OpenAIEmbedding", f"Embedding failed: {e}")
            raise

    def get_dimension(self) -> int:
        return self.dimension


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """OpenRouter embedding provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests package not installed")

        self.api_key = config.get("api_key", os.getenv("OPENROUTER_API_KEY"))
        self.model = config.get("model", "text-embedding-3-small")
        self.dimension = config.get("dimension", 1536)
        self.base_url = "https://openrouter.ai/api/v1"

        if not self.api_key:
            raise ValueError("OpenRouter API key required")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using OpenRouter"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "input": texts,
                "model": self.model
            }

            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code != 200:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

            result = response.json()
            return [data["embedding"] for data in result["data"]]

        except Exception as e:
            logger.log("ERROR", "OpenRouterEmbedding", f"Embedding failed: {e}")
            raise

    def get_dimension(self) -> int:
        return self.dimension


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local sentence transformer embedding provider"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers package not installed")

        self.model_name = config.get("model_name", "all-MiniLM-L6-v2")
        self.dimension = config.get("dimension", 384)  # all-MiniLM-L6-v2 dimension

        try:
            self.model = sentence_transformers.SentenceTransformer(self.model_name)
        except Exception as e:
            logger.log("ERROR", "LocalEmbedding", f"Failed to load model {self.model_name}: {e}")
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using local model"""
        try:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.log("ERROR", "LocalEmbedding", f"Embedding failed: {e}")
            raise

    def get_dimension(self) -> int:
        return self.dimension


class FallbackEmbeddingProvider(EmbeddingProvider):
    """Fallback provider using SHA256 hash (for when other providers fail)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dimension = config.get("dimension", 256)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using SHA256 hash (fallback)"""
        embeddings = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            vec = np.frombuffer(h[:self.dimension], dtype=np.uint8).astype("float32")
            vec = vec / (np.linalg.norm(vec) + 1e-9)
            embeddings.append(vec.tolist())
        return embeddings

    def get_dimension(self) -> int:
        return self.dimension


class EmbeddingAdapter:
    """Main embedding adapter that manages multiple providers"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.providers = {}
        self.current_provider = None
        self._init_providers()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "providers": {
                "openai": {
                    "enabled": False,
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": "text-embedding-3-small",
                    "dimension": 1536
                },
                "openrouter": {
                    "enabled": False,
                    "api_key": os.getenv("OPENROUTER_API_KEY"),
                    "model": "text-embedding-3-small",
                    "dimension": 1536
                },
                "local": {
                    "enabled": True,  # Default to local
                    "model_name": "all-MiniLM-L6-v2",
                    "dimension": 384
                },
                "fallback": {
                    "enabled": True,
                    "dimension": 256
                }
            },
            "default_provider": "local"
        }

    def _init_providers(self):
        """Initialize embedding providers"""
        provider_configs = self.config.get("providers", {})

        # Initialize OpenAI provider
        if provider_configs.get("openai", {}).get("enabled", False):
            try:
                self.providers["openai"] = OpenAIEmbeddingProvider(provider_configs["openai"])
                logger.log("INFO", "EmbeddingAdapter", "OpenAI embedding provider initialized")
            except Exception as e:
                logger.log("WARNING", "EmbeddingAdapter", f"Failed to initialize OpenAI provider: {e}")

        # Initialize OpenRouter provider
        if provider_configs.get("openrouter", {}).get("enabled", False):
            try:
                self.providers["openrouter"] = OpenRouterEmbeddingProvider(provider_configs["openrouter"])
                logger.log("INFO", "EmbeddingAdapter", "OpenRouter embedding provider initialized")
            except Exception as e:
                logger.log("WARNING", "EmbeddingAdapter", f"Failed to initialize OpenRouter provider: {e}")

        # Initialize local provider
        if provider_configs.get("local", {}).get("enabled", False):
            try:
                self.providers["local"] = LocalEmbeddingProvider(provider_configs["local"])
                logger.log("INFO", "EmbeddingAdapter", "Local embedding provider initialized")
            except Exception as e:
                logger.log("WARNING", "EmbeddingAdapter", f"Failed to initialize local provider: {e}")

        # Always initialize fallback
        self.providers["fallback"] = FallbackEmbeddingProvider(provider_configs.get("fallback", {}))

        # Set current provider
        default_provider = self.config.get("default_provider", "local")
        if default_provider in self.providers:
            self.current_provider = self.providers[default_provider]
        else:
            # Fallback to first available provider
            if self.providers:
                self.current_provider = next(iter(self.providers.values()))
            else:
                raise RuntimeError("No embedding providers available")

        logger.log("INFO", "EmbeddingAdapter", f"Using embedding provider: {type(self.current_provider).__name__}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed texts using current provider with fallback"""
        if not texts:
            return []

        # Try current provider first
        try:
            return self.current_provider.embed_texts(texts)
        except Exception as e:
            logger.log("WARNING", "EmbeddingAdapter", f"Current provider failed: {e}")

            # Try other providers in order
            for provider_name, provider in self.providers.items():
                if provider != self.current_provider:
                    try:
                        logger.log("INFO", "EmbeddingAdapter", f"Trying fallback provider: {provider_name}")
                        result = provider.embed_texts(texts)
                        # Switch to working provider
                        self.current_provider = provider
                        return result
                    except Exception as e2:
                        logger.log("WARNING", "EmbeddingAdapter", f"Fallback provider {provider_name} also failed: {e2}")
                        continue

            # All providers failed, this shouldn't happen since fallback should always work
            raise RuntimeError("All embedding providers failed")

    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.current_provider.get_dimension()

    def switch_provider(self, provider_name: str):
        """Switch to a different provider"""
        if provider_name in self.providers:
            self.current_provider = self.providers[provider_name]
            logger.log("INFO", "EmbeddingAdapter", f"Switched to provider: {provider_name}")
        else:
            raise ValueError(f"Provider {provider_name} not available")

    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.providers.keys())


# Global embedding adapter instance
_embedding_adapter_config = {
    "providers": {
        "openai": {
            "enabled": bool(os.getenv("OPENAI_API_KEY")),
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "text-embedding-3-small",
            "dimension": 1536
        },
        "openrouter": {
            "enabled": bool(os.getenv("OPENROUTER_API_KEY")),
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "model": "text-embedding-3-small",
            "dimension": 1536
        },
        "local": {
            "enabled": True,
            "model_name": "all-MiniLM-L6-v2",
            "dimension": 384
        },
        "fallback": {
            "enabled": True,
            "dimension": 256
        }
    },
    "default_provider": "local"
}

try:
    embedding_adapter = EmbeddingAdapter(_embedding_adapter_config)
    logger.log("INFO", "EmbeddingAdapter", "Embedding adapter initialized successfully")
except Exception as e:
    logger.log("ERROR", "EmbeddingAdapter", f"Failed to initialize embedding adapter: {e}")
    embedding_adapter = None