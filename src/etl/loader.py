"""
Product Loader for inserting normalized products into PostgreSQL.
Handles embedding generation and batch insertion with caching.
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

import httpx

from src.config import settings
from src.database import get_db, get_transaction

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """Client for generating embeddings via Ollama."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        dimension: int = 384,
    ):
        """Initialize embedding client."""
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        self.model = model or settings.ollama_embedding_model
        self.dimension = dimension
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(60.0),
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def generate(self, text: str) -> Optional[list[float]]:
        """Generate embedding for text."""
        if not text or not text.strip():
            return None
        
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
                logger.error(f"Embedding generation failed: {response.status_code}")
                return None
            
            data = response.json()
            embedding = data.get('embedding', [])
            
            if len(embedding) != self.dimension:
                logger.warning(
                    f"Unexpected embedding dimension: {len(embedding)} "
                    f"(expected {self.dimension})"
                )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None


class EmbeddingCache:
    """File-based cache for embeddings."""
    
    def __init__(self, cache_path: Optional[Path] = None):
        """Initialize cache."""
        self.cache_path = cache_path or settings.embeddings_cache
        self._cache: dict[str, list[float]] = {}
        self._loaded = False
    
    def _hash_text(self, text: str) -> str:
        """Generate hash for text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def load(self) -> None:
        """Load cache from disk."""
        if self._loaded:
            return
        
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} cached embeddings")
            except Exception as e:
                logger.warning(f"Failed to load embedding cache: {e}")
                self._cache = {}
        
        self._loaded = True
    
    def save(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(self._cache, f)
            logger.debug(f"Saved {len(self._cache)} embeddings to cache")
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")
    
    def get(self, text: str) -> Optional[list[float]]:
        """Get embedding from cache."""
        self.load()
        text_hash = self._hash_text(text)
        return self._cache.get(text_hash)
    
    def set(self, text: str, embedding: list[float]) -> None:
        """Add embedding to cache."""
        self.load()
        text_hash = self._hash_text(text)
        self._cache[text_hash] = embedding


class ProductLoader:
    """
    Load normalized products into PostgreSQL with embeddings.
    
    Features:
    - Embedding generation via Ollama bge-m3
    - Embedding caching to avoid regeneration
    - Batch insertion with UPSERT
    - Transaction management
    """
    
    def __init__(
        self,
        batch_size: Optional[int] = None,
        cache_embeddings: Optional[bool] = None,
    ):
        """Initialize the loader."""
        self.batch_size = batch_size or settings.batch_size
        self.cache_embeddings = cache_embeddings if cache_embeddings is not None else settings.cache_embeddings
        
        self.embedding_client = EmbeddingClient()
        self.embedding_cache = EmbeddingCache() if self.cache_embeddings else None
    
    async def close(self) -> None:
        """Clean up resources."""
        await self.embedding_client.close()
        if self.embedding_cache:
            self.embedding_cache.save()
    
    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate embedding with caching."""
        if not text:
            return None
        
        # Check cache first
        if self.embedding_cache:
            cached = self.embedding_cache.get(text)
            if cached:
                return cached
        
        # Generate new embedding
        embedding = await self.embedding_client.generate(text)
        
        # Cache the result
        if embedding and self.embedding_cache:
            self.embedding_cache.set(text, embedding)
        
        return embedding
    
    async def load(self, products: list[dict]) -> dict[str, Any]:
        """
        Load products into the database.
        
        Args:
            products: List of normalized product dicts
            
        Returns:
            Stats dict with counts
        """
        logger.info(f"Loading {len(products)} products into database")
        
        stats = {
            "total": len(products),
            "inserted": 0,
            "updated": 0,
            "failed": 0,
            "embeddings_generated": 0,
            "embeddings_cached": 0,
        }
        
        # Process in batches
        for i in range(0, len(products), self.batch_size):
            batch = products[i:i + self.batch_size]
            batch_stats = await self._load_batch(batch)
            
            stats["inserted"] += batch_stats["inserted"]
            stats["updated"] += batch_stats["updated"]
            stats["failed"] += batch_stats["failed"]
            stats["embeddings_generated"] += batch_stats["embeddings_generated"]
            stats["embeddings_cached"] += batch_stats["embeddings_cached"]
            
            logger.info(
                f"Loaded batch {i//self.batch_size + 1}: "
                f"{batch_stats['inserted']} inserted, {batch_stats['updated']} updated"
            )
        
        # Save embedding cache
        if self.embedding_cache:
            self.embedding_cache.save()
        
        logger.info(
            f"Load complete: {stats['inserted']} inserted, {stats['updated']} updated, "
            f"{stats['failed']} failed"
        )
        
        return stats
    
    async def _load_batch(self, batch: list[dict]) -> dict[str, int]:
        """Load a batch of products."""
        stats = {
            "inserted": 0,
            "updated": 0,
            "failed": 0,
            "embeddings_generated": 0,
            "embeddings_cached": 0,
        }
        
        # Generate embeddings for batch
        embedding_tasks = []
        for product in batch:
            # Create embedding text from raw_text or model_name + specs
            embed_text = product.get('raw_text') or self._create_embed_text(product)
            
            # Check if cached
            if self.embedding_cache and self.embedding_cache.get(embed_text):
                stats["embeddings_cached"] += 1
            
            embedding_tasks.append(self.generate_embedding(embed_text))
        
        embeddings = await asyncio.gather(*embedding_tasks, return_exceptions=True)
        stats["embeddings_generated"] = sum(
            1 for e in embeddings 
            if e is not None and not isinstance(e, Exception)
        ) - stats["embeddings_cached"]
        
        # Insert into database
        db = await get_db()
        
        async with db.transaction() as conn:
            for product, embedding in zip(batch, embeddings):
                try:
                    if isinstance(embedding, Exception):
                        embedding = None
                    
                    result = await self._upsert_product(conn, product, embedding)
                    
                    if result == "inserted":
                        stats["inserted"] += 1
                    elif result == "updated":
                        stats["updated"] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to load product {product.get('model_name')}: {e}")
                    stats["failed"] += 1
        
        return stats
    
    def _create_embed_text(self, product: dict) -> str:
        """Create text for embedding from product data."""
        parts = [
            product.get('model_name', ''),
            product.get('category', ''),
            product.get('series', ''),
        ]
        
        specs = product.get('specs', {})
        for key in ['power_watts', 'driver_components', 'voltage_type', 'coverage']:
            if key in specs:
                parts.append(f"{key}: {specs[key]}")
        
        if product.get('ai_summary'):
            parts.append(product['ai_summary'])
        
        return ' '.join(str(p) for p in parts if p)
    
    async def _upsert_product(
        self,
        conn,
        product: dict,
        embedding: Optional[list[float]],
    ) -> str:
        """
        Insert or update a product.
        
        Returns: "inserted" or "updated"
        """
        model_name = product.get('model_name')
        if not model_name:
            raise ValueError("Product must have model_name")
        
        # Check if product exists
        existing = await conn.fetchval(
            "SELECT id FROM products WHERE model_name = $1",
            model_name,
        )
        
        specs = product.get('specs', {})
        
        if existing:
            # Update existing product
            await conn.execute(
                """
                UPDATE products SET
                    specs = $2,
                    ai_summary = $3,
                    embedding = $4,
                    pdf_source = $5,
                    page_number = $6,
                    raw_text = $7,
                    updated_at = NOW()
                WHERE model_name = $1
                """,
                model_name,
                json.dumps(specs),
                product.get('ai_summary'),
                embedding,
                product.get('pdf_source'),
                product.get('page_number'),
                product.get('raw_text'),
            )
            return "updated"
        else:
            # Insert new product
            await conn.execute(
                """
                INSERT INTO products (
                    model_name, specs, ai_summary, embedding,
                    pdf_source, page_number, raw_text
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                model_name,
                json.dumps(specs),
                product.get('ai_summary'),
                embedding,
                product.get('pdf_source'),
                product.get('page_number'),
                product.get('raw_text'),
            )
            return "inserted"
    
    async def create_vector_index(self) -> bool:
        """
        Create IVFFlat index on embeddings after data load.
        
        Should be called after loading data for optimal index creation.
        """
        logger.info("Creating vector index...")
        
        try:
            db = await get_db()
            
            # Check how many products have embeddings
            count = await db.fetchval(
                "SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL"
            )
            
            if count < 10:
                logger.warning(
                    f"Only {count} products with embeddings. "
                    f"Skipping IVFFlat index (need at least 10 for lists=10)"
                )
                return False
            
            # Calculate optimal number of lists
            # Rule of thumb: sqrt(n) for n < 1M
            lists = max(10, min(100, int(count ** 0.5)))
            
            # Drop existing index if any
            await db.execute(
                "DROP INDEX IF EXISTS idx_products_embedding_ivfflat"
            )
            
            # Create new index
            await db.execute(
                f"""
                CREATE INDEX idx_products_embedding_ivfflat 
                ON products USING ivfflat(embedding vector_cosine_ops) 
                WITH (lists = {lists})
                """
            )
            
            logger.info(f"Created IVFFlat index with {lists} lists for {count} products")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
