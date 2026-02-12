"""
Main Query Engine.
Orchestrates the complete query processing pipeline.
"""

import logging
from typing import Optional

from src.rag.embeddings import EmbeddingClient
from src.rag.router import QueryRouter, QueryType
from src.rag.retrieval import HybridRetriever, RetrievalResult
from src.rag.generator import AnswerGenerator, GeneratedAnswer
from src.logic.calculator import ElectricalCalculator

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Main query processing engine.
    
    Coordinates:
    1. Query classification (router)
    2. Product retrieval (retrieval)
    3. Calculation (calculator) 
    4. Answer generation (generator)
    """
    
    def __init__(self):
        """Initialize the query engine components."""
        self.router = QueryRouter()
        self.retriever = HybridRetriever()
        self.generator = AnswerGenerator()
        self.calculator = ElectricalCalculator()
    
    async def query(self, user_query: str) -> GeneratedAnswer:
        """
        Process a user query and return an answer.
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            GeneratedAnswer with response and citations
        """
        if not user_query or not user_query.strip():
            return GeneratedAnswer(
                answer="Please provide a query.",
                query_type="error",
            )
        
        user_query = user_query.strip()
        logger.info(f"Processing query: {user_query[:100]}")
        
        try:
            # Step 1: Classify query intent
            query_type = await self.router.classify(user_query)
            logger.debug(f"Query type: {query_type.value}")
            
            # Step 2: Route to appropriate handler
            if query_type == QueryType.DIRECT_LOOKUP:
                return await self._handle_direct_lookup(user_query)
            
            elif query_type == QueryType.CALCULATION:
                return await self._handle_calculation(user_query)
            
            elif query_type == QueryType.PURCHASE_INTENT:
                return GeneratedAnswer(
                    answer="I am a technical assistant. For pricing and availability, please visit [Sales Portal URL].",
                    query_type="purchase_intent",
                )
            
            elif query_type == QueryType.DOMAIN_VIOLATION:
                return GeneratedAnswer(
                    answer="I can only provide information on Bose Professional products.",
                    query_type="domain_violation",
                )
            
            elif query_type == QueryType.SEMANTIC_SEARCH:
                return await self._handle_semantic_search(user_query)
            
            else:
                return GeneratedAnswer(
                    answer="I'm not sure how to handle that query. "
                           "Try asking about specific products or calculations.",
                    query_type="unknown",
                )
                
        except Exception as e:
            logger.error(f"Query processing error: {e}", exc_info=True)
            return GeneratedAnswer(
                answer=f"An error occurred: {str(e)}",
                query_type="error",
            )
    
    async def _handle_direct_lookup(self, query: str) -> GeneratedAnswer:
        """Handle direct product lookup queries."""
        # Extract model name from query
        model_name = self.router.extract_model_name(query)
        
        if not model_name:
            # Fall back to semantic search
            logger.debug("No model name found, falling back to semantic search")
            return await self._handle_semantic_search(query)
        
        # Look up product
        result = await self.retriever.direct_lookup(model_name)
        
        if not result:
            return GeneratedAnswer(
                answer=f"Product '{model_name}' was not found in my database. "
                       f"I couldn't find a matching product. Please check the model name or try a search.",
                query_type="direct_lookup",
                products_used=[],
            )
        
        # Generate formatted answer
        return await self.generator.generate_direct_answer(query, result)
    
    async def _handle_calculation(self, query: str) -> GeneratedAnswer:
        """Handle electrical calculation queries."""
        # Extract calculation parameters
        params = self.router.extract_calculation_params(query)
        
        if not params:
            return GeneratedAnswer(
                answer="I couldn't parse the calculation parameters. "
                       "Please specify speaker wattages and/or transformer capacity.",
                query_type="calculation",
            )
        
        # Perform calculation
        calc_result = self.calculator.process_calculation(params)
        
        # Format answer
        return self.generator.generate_calculation_answer(query, calc_result)
    
    async def _handle_semantic_search(self, query: str) -> GeneratedAnswer:
        """Handle semantic search queries."""
        # Extract filters
        filters = self.router.extract_filters(query)
        
        # Perform hybrid search
        results = await self.retriever.semantic_search(query, filters)
        
        if not results:
            return GeneratedAnswer(
                answer="I couldn't find any products matching your criteria. "
                       "Try broadening your search or asking about specific models.",
                query_type="semantic_search",
            )
        
        # Generate answer with LLM
        return await self.generator.generate_search_answer(query, results)
    
    async def get_product(self, model_name: str) -> Optional[RetrievalResult]:
        """Get a specific product by model name."""
        return await self.retriever.direct_lookup(model_name)
    
    async def search_products(
        self,
        query: str,
        filters: Optional[dict] = None,
        limit: int = 10,
    ) -> list[RetrievalResult]:
        """Search for products."""
        return await self.retriever.semantic_search(query, filters, limit)
    
    async def find_similar(
        self,
        model_name: str,
        limit: int = 5,
    ) -> list[RetrievalResult]:
        """Find products similar to a given model."""
        return await self.retriever.find_similar(model_name, limit)
    
    async def calculate(self, params: dict) -> dict:
        """Perform an electrical calculation."""
        return self.calculator.process_calculation(params)
    
    async def close(self) -> None:
        """Close all connections."""
        await self.router.close()
        await self.generator.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Global engine instance
_engine: Optional[QueryEngine] = None


async def get_engine() -> QueryEngine:
    """Get the global query engine instance."""
    global _engine
    if _engine is None:
        _engine = QueryEngine()
    return _engine


async def query(user_query: str) -> GeneratedAnswer:
    """
    Convenience function to process a query.
    
    Args:
        user_query: Natural language query
        
    Returns:
        GeneratedAnswer with response and citations
    """
    engine = await get_engine()
    return await engine.query(user_query)
