"""
Hybrid Retrieval System.
Combines SQL filtering with vector similarity search for optimal results.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Any, Optional

from src.config import settings
from src.database import get_db
from src.rag.embeddings import embed_query

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieval result with product data and scores."""
    model_name: str
    category: Optional[str]
    series: Optional[str]
    specs: dict[str, Any]
    ai_summary: Optional[str]
    similarity_score: float = 0.0
    pdf_source: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


class HybridRetriever:
    """
    Hybrid SQL + Vector search for product retrieval.
    
    Strategy:
    1. Hard Filtering (SQL): WHERE watts_int > 50 AND voltage_type = '70V'
    2. Soft Reranking (Vector): ORDER BY embedding <=> query_embedding
    
    This two-stage approach ensures:
    - Fast filtering using indexed columns
    - Semantic relevance via vector similarity
    - Latency target: <3 seconds
    """
    
    def __init__(
        self,
        max_candidates: int = 100,
        final_limit: int = 10,
    ):
        """
        Initialize the retriever.
        
        Args:
            max_candidates: Max products to consider after SQL filter
            final_limit: Final number of results to return
        """
        self.max_candidates = max_candidates
        self.final_limit = final_limit
    
    async def direct_lookup(self, model_name: str) -> Optional[RetrievalResult]:
        """
        Direct lookup by model name.
        
        Args:
            model_name: Product model name (e.g., "AM10/60")
            
        Returns:
            RetrievalResult or None if not found
        """
        db = await get_db()
        
        # Try exact match first
        row = await db.fetchrow(
            """
            SELECT model_name, category, series, specs, ai_summary, pdf_source
            FROM products
            WHERE UPPER(model_name) = UPPER($1)
            """,
            model_name,
        )
        
        if row:
            return self._row_to_result(row)
        
        # Try partial match (for model variants)
        row = await db.fetchrow(
            """
            SELECT model_name, category, series, specs, ai_summary, pdf_source
            FROM products
            WHERE UPPER(model_name) LIKE UPPER($1)
            ORDER BY model_name
            LIMIT 1
            """,
            f"%{model_name}%",
        )
        
        if row:
            return self._row_to_result(row)
        
        return None
    
    async def semantic_search(
        self,
        query: str,
        filters: Optional[dict] = None,
        limit: Optional[int] = None,
    ) -> list[RetrievalResult]:
        """
        Semantic search with optional SQL filters.
        
        Args:
            query: User query for semantic matching
            filters: Optional SQL filters (min_watts, voltage_type, etc.)
            limit: Max results to return
            
        Returns:
            List of RetrievalResult sorted by relevance
        """
        limit = limit or self.final_limit
        filters = filters or {}
        
        # Generate query embedding
        query_embedding = await embed_query(query)
        
        if query_embedding is None:
            logger.warning("Failed to generate query embedding, falling back to SQL only")
            return await self._sql_only_search(filters, limit)
        
        # Build hybrid query
        results = await self._hybrid_search(query_embedding, filters, limit)
        
        return results
    
    async def _hybrid_search(
        self,
        query_embedding: list[float],
        filters: dict,
        limit: int,
    ) -> list[RetrievalResult]:
        """
        Two-stage hybrid search: SQL filter + vector rerank.
        """
        db = await get_db()
        
        # Build WHERE clause from filters
        where_clauses = ["embedding IS NOT NULL"]
        params = [query_embedding]
        param_idx = 2
        
        if 'min_watts' in filters:
            where_clauses.append(f"watts_int >= ${param_idx}")
            params.append(filters['min_watts'])
            param_idx += 1
        
        if 'max_watts' in filters:
            where_clauses.append(f"watts_int <= ${param_idx}")
            params.append(filters['max_watts'])
            param_idx += 1
        
        if 'voltage_type' in filters:
            where_clauses.append(f"voltage_type = ${param_idx}")
            params.append(filters['voltage_type'])
            param_idx += 1
        
        if 'category' in filters:
            where_clauses.append(f"category = ${param_idx}")
            params.append(filters['category'])
            param_idx += 1
        
        if 'series' in filters:
            where_clauses.append(f"series = ${param_idx}")
            params.append(filters['series'])
            param_idx += 1
        
        where_clause = " AND ".join(where_clauses)
        
        # Execute hybrid query with cosine distance
        query = f"""
            SELECT 
                model_name,
                category,
                series,
                specs,
                ai_summary,
                pdf_source,
                1 - (embedding <=> $1) as similarity
            FROM products
            WHERE {where_clause}
            ORDER BY embedding <=> $1
            LIMIT {limit}
        """
        
        rows = await db.fetch(query, *params)
        
        results = []
        for row in rows:
            result = self._row_to_result(row)
            result.similarity_score = float(row['similarity'])
            results.append(result)
        
        return results
    
    async def _sql_only_search(
        self,
        filters: dict,
        limit: int,
    ) -> list[RetrievalResult]:
        """
        Fallback search using only SQL filters (no vector).
        """
        db = await get_db()
        
        # Build WHERE clause
        where_clauses = []
        params = []
        param_idx = 1
        
        if 'min_watts' in filters:
            where_clauses.append(f"watts_int >= ${param_idx}")
            params.append(filters['min_watts'])
            param_idx += 1
        
        if 'max_watts' in filters:
            where_clauses.append(f"watts_int <= ${param_idx}")
            params.append(filters['max_watts'])
            param_idx += 1
        
        if 'voltage_type' in filters:
            where_clauses.append(f"voltage_type = ${param_idx}")
            params.append(filters['voltage_type'])
            param_idx += 1
        
        if 'category' in filters:
            where_clauses.append(f"category = ${param_idx}")
            params.append(filters['category'])
            param_idx += 1
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        query = f"""
            SELECT 
                model_name,
                category,
                series,
                specs,
                ai_summary,
                pdf_source
            FROM products
            WHERE {where_clause}
            ORDER BY model_name
            LIMIT {limit}
        """
        
        rows = await db.fetch(query, *params)
        
        return [self._row_to_result(row) for row in rows]
    
    async def find_similar(
        self,
        model_name: str,
        limit: int = 5,
    ) -> list[RetrievalResult]:
        """
        Find products similar to a given model.
        
        Args:
            model_name: Reference product model name
            limit: Max results to return
            
        Returns:
            List of similar products
        """
        db = await get_db()
        
        # Get the reference product's embedding
        ref_row = await db.fetchrow(
            """
            SELECT embedding, category
            FROM products
            WHERE UPPER(model_name) = UPPER($1)
            """,
            model_name,
        )
        
        if not ref_row or not ref_row['embedding']:
            return []
        
        # Find similar products (same category preferred)
        rows = await db.fetch(
            """
            SELECT 
                model_name,
                category,
                series,
                specs,
                ai_summary,
                pdf_source,
                1 - (embedding <=> $1) as similarity
            FROM products
            WHERE embedding IS NOT NULL
              AND UPPER(model_name) != UPPER($2)
            ORDER BY 
                CASE WHEN category = $3 THEN 0 ELSE 1 END,
                embedding <=> $1
            LIMIT $4
            """,
            ref_row['embedding'],
            model_name,
            ref_row['category'],
            limit,
        )
        
        results = []
        for row in rows:
            result = self._row_to_result(row)
            result.similarity_score = float(row['similarity'])
            results.append(result)
        
        return results
    
    async def get_by_category(
        self,
        category: str,
        limit: int = 20,
    ) -> list[RetrievalResult]:
        """
        Get all products in a category.
        
        Args:
            category: Product category
            limit: Max results
            
        Returns:
            List of products in category
        """
        db = await get_db()
        
        rows = await db.fetch(
            """
            SELECT 
                model_name,
                category,
                series,
                specs,
                ai_summary,
                pdf_source
            FROM products
            WHERE category = $1
            ORDER BY model_name
            LIMIT $2
            """,
            category,
            limit,
        )
        
        return [self._row_to_result(row) for row in rows]
    
    def _row_to_result(self, row) -> RetrievalResult:
        """Convert database row to RetrievalResult."""
        specs = row['specs']
        if isinstance(specs, str):
            specs = json.loads(specs)
        
        return RetrievalResult(
            model_name=row['model_name'],
            category=row.get('category'),
            series=row.get('series'),
            specs=specs,
            ai_summary=row.get('ai_summary'),
            pdf_source=row.get('pdf_source'),
        )
    
    async def get_stats(self) -> dict:
        """Get retrieval statistics."""
        db = await get_db()
        
        stats = {}
        
        # Total products
        stats['total_products'] = await db.fetchval(
            "SELECT COUNT(*) FROM products"
        )
        
        # Products with embeddings
        stats['with_embeddings'] = await db.fetchval(
            "SELECT COUNT(*) FROM products WHERE embedding IS NOT NULL"
        )
        
        # Products by category
        rows = await db.fetch(
            """
            SELECT category, COUNT(*) as count
            FROM products
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            """
        )
        stats['by_category'] = {row['category']: row['count'] for row in rows}
        
        return stats

    async def get_all_models(self) -> list[str]:
        """
        Get all model names from the database.
        
        Returns:
            List of model names sorted alphabetically
        """
        db = await get_db()
        rows = await db.fetch(
            "SELECT model_name FROM products ORDER BY model_name"
        )
        return [row['model_name'] for row in rows]
