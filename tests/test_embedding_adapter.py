"""
Tests for embedding adapter.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from cortex.adapters.embedding_adapter import (
    EmbeddingAdapter,
    OpenAIEmbeddingProvider,
    OpenRouterEmbeddingProvider,
    LocalEmbeddingProvider,
    FallbackEmbeddingProvider
)


class TestEmbeddingAdapter:
    """Test the main embedding adapter"""

    def setup_method(self):
        """Set up test instance"""
        self.config = {
            "providers": {
                "openai": {"enabled": False},
                "openrouter": {"enabled": False},
                "local": {"enabled": False},
                "fallback": {"enabled": True, "dimension": 256}
            },
            "default_provider": "fallback"
        }
        self.adapter = EmbeddingAdapter(self.config)

    def test_initialization(self):
        """Test adapter initializes with fallback provider"""
        assert self.adapter.current_provider is not None
        assert isinstance(self.adapter.current_provider, FallbackEmbeddingProvider)
        assert self.adapter.get_dimension() == 256

    def test_embed_texts(self):
        """Test basic text embedding"""
        texts = ["Hello world", "Test document"]
        embeddings = self.adapter.embed_texts(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 256
        assert len(embeddings[1]) == 256

        # Embeddings should be normalized (unit vectors)
        import numpy as np
        for embedding in embeddings:
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.1  # Should be approximately 1

    def test_provider_switching(self):
        """Test switching between providers"""
        # Should start with fallback
        assert isinstance(self.adapter.current_provider, FallbackEmbeddingProvider)

        # Switch to fallback (same provider)
        self.adapter.switch_provider("fallback")
        assert isinstance(self.adapter.current_provider, FallbackEmbeddingProvider)

    def test_get_available_providers(self):
        """Test getting available providers"""
        providers = self.adapter.get_available_providers()
        assert "fallback" in providers
        assert len(providers) >= 1


class TestOpenAIEmbeddingProvider:
    """Test OpenAI embedding provider"""

    def setup_method(self):
        """Set up test provider"""
        self.config = {
            "api_key": "test-key",
            "model": "text-embedding-3-small",
            "dimension": 1536
        }

    @patch('cortex.adapters.embedding_adapter.openai')
    def test_initialization(self, mock_openai):
        """Test OpenAI provider initialization"""
        mock_client = Mock()
        mock_openai.OpenAI.return_value = mock_client

        provider = OpenAIEmbeddingProvider(self.config)

        assert provider.api_key == "test-key"
        assert provider.model == "text-embedding-3-small"
        assert provider.get_dimension() == 1536
        mock_openai.OpenAI.assert_called_once_with(api_key="test-key")

    @patch('cortex.adapters.embedding_adapter.openai')
    def test_embed_texts(self, mock_openai):
        """Test OpenAI text embedding"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_openai.OpenAI.return_value = mock_client

        # Mock response
        mock_response = Mock()
        mock_data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_response.data = mock_data
        mock_client.embeddings.create.return_value = mock_response

        provider = OpenAIEmbeddingProvider(self.config)
        texts = ["Test text"]
        embeddings = provider.embed_texts(texts)

        assert embeddings == [[0.1, 0.2, 0.3]]
        mock_client.embeddings.create.assert_called_once()


class TestOpenRouterEmbeddingProvider:
    """Test OpenRouter embedding provider"""

    def setup_method(self):
        """Set up test provider"""
        self.config = {
            "api_key": "test-key",
            "model": "text-embedding-3-small",
            "dimension": 1536
        }

    @patch('cortex.adapters.embedding_adapter.requests')
    def test_embed_texts(self, mock_requests):
        """Test OpenRouter text embedding"""
        # Mock requests response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_requests.post.return_value = mock_response

        provider = OpenRouterEmbeddingProvider(self.config)
        texts = ["Test text"]
        embeddings = provider.embed_texts(texts)

        assert embeddings == [[0.1, 0.2, 0.3]]

        # Verify API call
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert "https://openrouter.ai/api/v1/embeddings" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"


class TestLocalEmbeddingProvider:
    """Test local embedding provider"""

    def setup_method(self):
        """Set up test provider"""
        self.config = {
            "model_name": "all-MiniLM-L6-v2",
            "dimension": 384
        }

    @patch('cortex.adapters.embedding_adapter.sentence_transformers')
    def test_initialization(self, mock_st):
        """Test local provider initialization"""
        mock_model = Mock()
        mock_st.SentenceTransformer.return_value = mock_model

        provider = LocalEmbeddingProvider(self.config)

        assert provider.model_name == "all-MiniLM-L6-v2"
        assert provider.get_dimension() == 384
        mock_st.SentenceTransformer.assert_called_once_with("all-MiniLM-L6-v2")

    @patch('cortex.adapters.embedding_adapter.sentence_transformers')
    def test_embed_texts(self, mock_st):
        """Test local text embedding"""
        # Mock sentence transformer
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_st.SentenceTransformer.return_value = mock_model

        provider = LocalEmbeddingProvider(self.config)
        texts = ["Test text"]
        embeddings = provider.embed_texts(texts)

        assert embeddings == [[0.1, 0.2, 0.3]]
        mock_model.encode.assert_called_once()


class TestFallbackEmbeddingProvider:
    """Test fallback embedding provider"""

    def setup_method(self):
        """Set up test provider"""
        self.config = {"dimension": 256}
        self.provider = FallbackEmbeddingProvider(self.config)

    def test_initialization(self):
        """Test fallback provider initialization"""
        assert self.provider.get_dimension() == 256

    def test_embed_texts(self):
        """Test fallback text embedding"""
        texts = ["Hello world", "Test document"]
        embeddings = self.provider.embed_texts(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == 256
        assert len(embeddings[1]) == 256

        # Same text should produce same embedding
        embeddings2 = self.provider.embed_texts(["Hello world"])
        assert embeddings[0] == embeddings2[0]

        # Different text should produce different embedding
        embeddings3 = self.provider.embed_texts(["Different text"])
        assert embeddings[0] != embeddings3[0]


class TestEmbeddingAdapterIntegration:
    """Integration tests for embedding adapter"""

    def test_provider_fallback(self):
        """Test automatic provider fallback"""
        # Create adapter with only fallback enabled
        config = {
            "providers": {
                "openai": {"enabled": False},
                "openrouter": {"enabled": False},
                "local": {"enabled": False},
                "fallback": {"enabled": True, "dimension": 128}
            },
            "default_provider": "openai"  # Will fall back since OpenAI disabled
        }

        adapter = EmbeddingAdapter(config)

        # Should fall back to fallback provider
        assert isinstance(adapter.current_provider, FallbackEmbeddingProvider)
        assert adapter.get_dimension() == 128

        # Should still work
        embeddings = adapter.embed_texts(["Test"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 128

    def test_environment_configuration(self):
        """Test configuration from environment variables"""
        # This would normally read from environment
        # For testing, we create a fresh adapter
        adapter = EmbeddingAdapter()

        # Should have providers initialized based on environment
        providers = adapter.get_available_providers()
        assert "fallback" in providers  # Always available

    @pytest.mark.asyncio
    async def test_concurrent_embedding(self):
        """Test concurrent embedding requests"""
        import asyncio

        adapter = EmbeddingAdapter({
            "providers": {
                "fallback": {"enabled": True, "dimension": 64}
            },
            "default_provider": "fallback"
        })

        # Generate multiple concurrent requests
        texts_list = [["Text 1"], ["Text 2"], ["Text 3"]]

        tasks = [
            asyncio.to_thread(adapter.embed_texts, texts)
            for texts in texts_list
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for embeddings in results:
            assert len(embeddings) == 1
            assert len(embeddings[0]) == 64