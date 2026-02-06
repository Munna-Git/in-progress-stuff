"""
MCP Tool Definitions for Bose Product Engine.
Defines the tools exposed via Model Context Protocol.
"""

import logging
from typing import Any, Optional

from src.rag.engine import QueryEngine
from src.rag.retrieval import RetrievalResult
from src.logic.calculator import ElectricalCalculator

logger = logging.getLogger(__name__)


class BoseProductTools:
    """
    Tool definitions for Bose Professional Product Engine.
    
    These tools are exposed via FastMCP for use by AI assistants.
    """
    
    def __init__(self):
        """Initialize tools with query engine."""
        self.engine = QueryEngine()
        self.calculator = ElectricalCalculator()
    
    async def query_products(
        self,
        query: str,
    ) -> dict[str, Any]:
        """
        Query the Bose product database with natural language.
        
        Supports:
        - Direct lookups: "What's the power of AM10/60?"
        - Semantic search: "Find 70V speakers for conference rooms"
        - Calculations: "Can I connect 4x30W speakers to 150W transformer?"
        
        Args:
            query: Natural language query
            
        Returns:
            Answer with citations and confidence score
        """
        result = await self.engine.query(query)
        return result.to_dict()
    
    async def get_product_specs(
        self,
        model_name: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get specifications for a specific product model.
        
        Args:
            model_name: Product model name (e.g., "AM10/60", "DM3SE")
            
        Returns:
            Product specifications or None if not found
        """
        result = await self.engine.get_product(model_name)
        
        if result:
            return result.to_dict()
        return None
    
    async def search_products(
        self,
        query: str,
        min_watts: Optional[int] = None,
        max_watts: Optional[int] = None,
        voltage_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for products with optional filters.
        
        Args:
            query: Search query for semantic matching
            min_watts: Minimum power in watts
            max_watts: Maximum power in watts
            voltage_type: "70V", "100V", "70V/100V", or "Low-Z"
            category: "loudspeaker", "amplifier", "controller", etc.
            limit: Maximum results to return
            
        Returns:
            List of matching products with similarity scores
        """
        filters = {}
        if min_watts is not None:
            filters['min_watts'] = min_watts
        if max_watts is not None:
            filters['max_watts'] = max_watts
        if voltage_type:
            filters['voltage_type'] = voltage_type
        if category:
            filters['category'] = category
        
        results = await self.engine.search_products(query, filters, limit)
        return [r.to_dict() for r in results]
    
    async def find_similar_products(
        self,
        model_name: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find products similar to a given model.
        
        Args:
            model_name: Reference product model name
            limit: Maximum results to return
            
        Returns:
            List of similar products
        """
        results = await self.engine.find_similar(model_name, limit)
        return [r.to_dict() for r in results]
    
    def verify_70v_compatibility(
        self,
        speaker_watts: list[int],
        transformer_watts: int,
    ) -> dict[str, Any]:
        """
        Check if speakers are compatible with a 70V transformer.
        
        Args:
            speaker_watts: List of speaker wattages (e.g., [30, 30, 25, 25])
            transformer_watts: Transformer capacity in watts
            
        Returns:
            Compatibility result with headroom percentage
        """
        total = self.calculator.calculate_total_power(speaker_watts)
        result = self.calculator.verify_70v_compatibility(total, transformer_watts)
        
        return {
            "compatible": result.compatible,
            "total_load": result.total_load,
            "capacity": result.capacity,
            "headroom_percent": result.headroom_percent,
            "message": result.message,
            "speakers": speaker_watts,
        }
    
    def calculate_impedance(
        self,
        impedances: list[float],
        connection: str,
    ) -> dict[str, Any]:
        """
        Calculate total impedance for series or parallel connection.
        
        Args:
            impedances: List of speaker impedances in ohms
            connection: "series" or "parallel"
            
        Returns:
            Total impedance calculation result
        """
        result = self.calculator.calculate_impedance(impedances, connection)
        
        return {
            "total_impedance": result.total_impedance,
            "connection": result.connection,
            "speakers": result.speakers,
            "message": result.message,
        }
    
    def recommend_transformer(
        self,
        total_speaker_watts: int,
    ) -> dict[str, Any]:
        """
        Recommend appropriate transformer size for speaker load.
        
        Args:
            total_speaker_watts: Total speaker wattage
            
        Returns:
            Recommended transformer with alternatives
        """
        return self.calculator.recommend_transformer(total_speaker_watts)
    
    def max_speakers_for_transformer(
        self,
        transformer_watts: int,
        speaker_watts: int,
        headroom_percent: float = 20.0,
    ) -> dict[str, Any]:
        """
        Calculate maximum speakers for a transformer.
        
        Args:
            transformer_watts: Transformer capacity
            speaker_watts: Wattage per speaker
            headroom_percent: Desired headroom (default 20%)
            
        Returns:
            Maximum speaker count with configuration
        """
        return self.calculator.max_speakers_for_transformer(
            transformer_watts,
            speaker_watts,
            headroom_percent,
        )
    
    async def close(self) -> None:
        """Close connections."""
        await self.engine.close()
