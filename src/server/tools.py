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
    
    async def ask(
        self,
        question: str,
    ) -> dict[str, Any]:
        """
        Ask a question about Bose products.
        
        Args:
            question: Natural language question
            
        Returns:
            Answer with citations and confidence score
        """
        result = await self.engine.query(question)
        return result.to_dict()
    
    async def get_specs(
        self,
        model: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get specifications for a specific product model.
        
        Args:
            model: Product model name (e.g., "AM10/60", "DM3SE")
            
        Returns:
            Product specifications or None if not found
        """
        result = await self.engine.get_product(model)
        
        if result:
            return result.to_dict()
        return None

    async def get_models(self) -> list[str]:
        """
        Get a list of all available product models.
        
        Returns:
            List of model names
        """
        # Efficiently fetch all model names via SQL
        models = await self.engine.retriever.get_all_models()
        return models

    async def compare(self, models: list[str]) -> dict[str, Any]:
        """
        Compare specifications of multiple products side-by-side.
        
        Args:
            models: List of model names to compare
            
        Returns:
            Comparison dictionary with common specs
        """
        metrics = [
            "power_watts", "impedance_ohms", "freq_min_hz", "freq_max_hz",
            "sensitivity_db", "coverage", "weight_kg"
        ]
        
        comparison = {}
        for model in models:
            product = await self.engine.get_product(model)
            if product:
                specs = product.specs
                product_data = {"model": product.model_name}
                for metric in metrics:
                    product_data[metric] = specs.get(metric, "N/A")
                comparison[model] = product_data
            else:
                comparison[model] = "Product not found"
                
        return comparison

    async def sources(self) -> list[dict[str, Any]]:
        """
        Get list of available source documents.
        
        Returns:
            List of source documents with metadata
        """
        # For now, return the static list of PDFs we processed
        # Ideally this would come from a distinct query or metadata table
        return [
            {
                "id": "bose_catalog_v1",
                "title": "Bose Professional Product Catalog",
                "filename": "Bose-Products 3.pdf",
                "updated": "2024-01-01",
                "type": "pdf"
            }
        ]

    async def health(self) -> dict[str, str]:
        """
        Check system health.
        
        Returns:
            Health status
        """
        return {"status": "healthy", "version": "1.0.0"}
    
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
