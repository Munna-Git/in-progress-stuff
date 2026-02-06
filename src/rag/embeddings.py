"""
Ollama Embedding Client for RAG queries.
Generates embeddings for semantic search using local bge-m3 model.
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    Client for generating embeddings via Ollama bge-m3.
    
    Features:
    - Async HTTP client with connection pooling
    - In-memory caching for query embeddings
    - Batch embedding support
    - Health check functionality
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = 384,
        cache_enabled: bool = True,
    ):
        """
        Initialize embedding client.
        
        Args:
            base_url: Ollama API base URL
            model: Embedding model name
            dimension: Expected embedding dimension
            cache_enabled: Enable in-memory caching
        """
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        self.model = model or settings.ollama_embedding_model
        self.dimension = dimension
        self.cache_enabled = cache_enabled
        
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: dict[str, list[float]] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(max_connections=10),
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _hash_text(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is available and embedding model is loaded.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            
            if response.status_code != 200:
                return False
            
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            
            # Check for model (with or without version tag)
            model_base = self.model.split(':')[0]
            return any(model_base in m for m in models)
            
        except Exception as e:
            logger.error(f"Embedding health check failed: {e}")
            return False
    
    async def embed(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None on failure
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Check cache
        if self.cache_enabled:
            cache_key = self._hash_text(text)
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        try:
            client = await self._get_client()
            
            response = await client.post(
                "/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Embedding failed: {response.status_code}")
                return None
            
            data = response.json()
            embedding = data.get('embedding', [])
            
            if len(embedding) != self.dimension:
                logger.warning(
                    f"Unexpected dimension: {len(embedding)} (expected {self.dimension})"
                )
            
            # Cache result
            if self.cache_enabled:
                self._cache[cache_key] = embedding
            
            return embedding
            
        except httpx.TimeoutException:
            logger.warning(f"Embedding timeout for text: {text[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None
    
    async def embed_batch(
        self,
        texts: list[str],
        concurrency: int = 5,
    ) -> list[Optional[list[float]]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            concurrency: Max concurrent requests
            
        Returns:
            List of embeddings (None for failed items)
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def embed_with_semaphore(text: str) -> Optional[list[float]]:
            async with semaphore:
                return await self.embed(text)
        
        tasks = [embed_with_semaphore(t) for t in texts]
        return await asyncio.gather(*tasks)
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global embedding client instance
_embedding_client: Optional[EmbeddingClient] = None


async def get_embedding_client() -> EmbeddingClient:
    """Get the global embedding client instance."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = EmbeddingClient()
    return _embedding_client


async def embed_query(query: str) -> Optional[list[float]]:
    """
    Convenience function to embed a query string.
    
    Args:
        query: Query text to embed
        
    Returns:
        Embedding vector or None
    """
    client = await get_embedding_client()
    return await client.embed(query)
